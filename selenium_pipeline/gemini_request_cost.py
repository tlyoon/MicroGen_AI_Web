"""Durable, privacy-safe accounting for Gemini browser and permitted API attempts.

Every potentially dispatched request gets a committed SQLite record BEFORE send.
A crashed/ambiguous send remains 'possible_send', never silently treated as free.
Token usage from the provider is preferred. Heuristic estimates are explicitly
marked, and missing/unknown prices are NULL, never invented as zero.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import csv
import io
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import sys
import tempfile
import threading
import time
import uuid
import wave


PRICING_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"
PRICING_VERSION = "gemini-standard-2026-11-21-through-2026-12-31"
# Standard paid Gemini Developer API USD per 1,000,000 input/output tokens.
# The TTS audio output is a different modality from text generation.
RATES = {
    "gemini-3.8-flash-lite-tts": (0.50, 6.00),
    "gemini-3.8-flash-tts": (0.50, 9.00),
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.1-pro": (2.00, 12.00),
    "gemini-3.1-pro-preview": (2.00, 12.00),
}
CURRENT_ATTEMPT: ContextVar[tuple[str, int] | None] = ContextVar(
    "microgen_gemini_attempt", default=None)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def ledger_path() -> Path:
    explicit = os.environ.get("MICROGEN_GEMINI_COST_LEDGER_PATH", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return Path(tempfile.gettempdir()) / (
            f"microgen_cost_pytest_{os.getpid()}.sqlite3")
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        root = Path(local_appdata)
    else:
        # HOME can be deliberately unset in isolated retry/security tests.
        try:
            root = Path.home() / ".local" / "share"
        except RuntimeError:
            root = Path(tempfile.gettempdir())
    return root / "MicroGen_AI_Web_Costs" / "gemini_requests.sqlite3"


_SCHEMA_LOCK = threading.Lock()


def _connect() -> sqlite3.Connection:
    destination = ledger_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with _SCHEMA_LOCK:
        con = sqlite3.connect(str(destination), timeout=30, isolation_level=None)
        con.execute("PRAGMA busy_timeout=30000")
        # Only change journal mode once: reissuing WAL PRAGMA in many parallel
        # workers can itself raise SQLITE_BUSY before a request is recorded.
        for number in range(5):
            try:
                if con.execute("PRAGMA journal_mode").fetchone()[0].lower() != "wal":
                    con.execute("PRAGMA journal_mode=WAL")
                break
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower() or number == 4:
                    con.close()
                    raise
                time.sleep(0.05 * (number + 1))
        con.execute("PRAGMA synchronous=FULL")
        con.execute("""CREATE TABLE IF NOT EXISTS gemini_requests (
        request_id TEXT PRIMARY KEY,
        logical_id TEXT NOT NULL,
        attempt_number INTEGER NOT NULL,
        retry_count INTEGER NOT NULL,
        started_utc TEXT NOT NULL,
        updated_utc TEXT NOT NULL,
        host TEXT NOT NULL,
        transport TEXT NOT NULL,
        purpose TEXT NOT NULL,
        stage TEXT NOT NULL,
        chapter TEXT,
        subsection TEXT,
        model TEXT NOT NULL,
        status TEXT NOT NULL,
        input_tokens INTEGER,
        output_tokens INTEGER,
        input_token_source TEXT NOT NULL,
        output_token_source TEXT NOT NULL,
        estimated_usd_cost REAL,
        price_version TEXT NOT NULL,
        price_source TEXT NOT NULL,
        billing_note TEXT NOT NULL,
        failure_class TEXT,
        UNIQUE(logical_id,attempt_number)
    )""")
        con.execute("CREATE INDEX IF NOT EXISTS ix_gemini_context ON gemini_requests(chapter,subsection,started_utc)")
    return con


@contextmanager
def _db():
    con = _connect()
    try:
        with con:
            yield con
    finally:
        con.close()


def set_job_context(folder: Path) -> None:
    for part in reversed(Path(folder).parts):
        if re.fullmatch(r"\d+\.\d+(?:\.\d+)?", part):
            os.environ["MICROGEN_SUBSECTION"] = part
            os.environ["MICROGEN_CHAPTER"] = part.split(".")[0]
            os.environ["MICROGEN_JOB_FOLDER"] = str(folder)
            return


def _context() -> tuple[str | None, str | None, str]:
    subsection = os.getenv("MICROGEN_SUBSECTION", "").strip()
    stage = os.getenv("MICROGEN_ACTIVE_GENERATION_STAGE", "").strip() or "unknown"
    if not subsection:
        for path_text in (os.getenv("MICROGEN_JOB_FOLDER", ""), str(Path.cwd())):
            for piece in reversed(Path(path_text).parts):
                if re.fullmatch(r"\d+\.\d+(?:\.\d+)?", piece):
                    subsection = piece
                    break
            if subsection:
                break
    chapter = os.getenv("MICROGEN_CHAPTER", "").strip() or (
        subsection.split(".")[0] if subsection else None)
    return chapter, subsection or None, stage


def _text_tokens(value: str) -> int:
    # A reproducible rough heuristic, NOT Google's tokenizer.
    return max(1, (len(value.encode("utf-8")) + 3) // 4) if value else 0


def _text_parts(value, depth: int = 0) -> tuple[str, bool]:
    if depth > 7:
        return "", True
    if isinstance(value, str):
        return value, False
    if isinstance(value, (bytes, bytearray, memoryview)):
        return "", True
    if isinstance(value, (tuple, list)):
        parts = [_text_parts(item, depth + 1) for item in value]
        return " ".join(p[0] for p in parts), any(p[1] for p in parts)
    if isinstance(value, dict):
        parts = [_text_parts(v, depth + 1) for k, v in value.items()
                 if k in {"text", "parts", "contents", "content", "input",
                          "role", "prompt"}]
        opaque = any(k in value for k in (
            "inline_data", "file_data", "data", "mime_type", "file_uri"))
        return " ".join(p[0] for p in parts), opaque or any(p[1] for p in parts)
    if hasattr(value, "text") and isinstance(getattr(value, "text", None), str):
        return getattr(value, "text"), False
    if hasattr(value, "inline_data") or hasattr(value, "file_data"):
        return "", True
    return "", True


def _usage_number(metadata, *names: str) -> int | None:
    if metadata is None:
        return None
    for name in names:
        val = (metadata.get(name) if isinstance(metadata, dict)
               else getattr(metadata, name, None))
        if isinstance(val, int) and not isinstance(val, bool) and val >= 0:
            return val
    return None


def _audio_token_estimate(response) -> int | None:
    try:
        # Gemini 3.8 Interactions returns output_audio rather than candidates.
        audio = getattr(response, "output_audio", None)
        if audio is not None:
            encoded = getattr(audio, "data", None)
            if encoded:
                raw = (base64.b64decode(encoded, validate=True)
                       if isinstance(encoded, str) else bytes(encoded))
                if not raw.startswith(b"RIFF"):
                    # Some SDK builds expose base64 as bytes, not a string.
                    try:
                        decoded = base64.b64decode(raw, validate=True)
                    except (ValueError, base64.binascii.Error):
                        decoded = None
                    if decoded is not None and len(decoded) > len(raw) // 2:
                        raw = decoded
                try:
                    with wave.open(io.BytesIO(raw), "rb") as wav:
                        seconds = wav.getnframes() / wav.getframerate()
                except (wave.Error, EOFError, ZeroDivisionError):
                    mime = str(getattr(audio, "mime_type", None) or "")
                    matched = re.search(r"rate=(\d+)", mime)
                    rate = int(matched.group(1)) if matched else 24000
                    seconds = len(raw) / (rate * 2)
                return max(1, round(seconds * 25))
        candidates = getattr(response, "candidates", None) or []
        raw_parts = getattr(getattr(candidates[0], "content", None),
                            "parts", []) or []
        for part in raw_parts:
            inline = getattr(part, "inline_data", None)
            data = getattr(inline, "data", None)
            if not data:
                continue
            content = base64.b64decode(data) if isinstance(data, str) else bytes(data)
            try:
                with wave.open(io.BytesIO(content), "rb") as wav:
                    seconds = wav.getnframes() / wav.getframerate()
            except (wave.Error, EOFError, ZeroDivisionError):
                # Google TTS typically returns mono 24-kHz, 16-bit PCM.
                seconds = len(content) / (24000 * 2)
            return max(1, round(seconds * 25))
    except (AttributeError, TypeError, ValueError):
        return None
    return None


def _cost(model: str, transport: str, input_count: int | None,
          output_count: int | None) -> tuple[float | None, str]:
    if transport == "selenium":
        return 0.0, "browser session: $0 incremental Gemini Developer API metering; excludes Gemini subscription"
    if datetime.now(timezone.utc).date().isoformat() > "2026-12-31":
        return None, "published 2026 promotional prices expired; refresh tariff before estimating"
    rates = RATES.get(model)
    if rates is None:
        return None, "unknown model tariff; cost intentionally NULL"
    if input_count is None and output_count is None:
        return None, "no usage information; cost intentionally NULL"
    estimate = ((input_count or 0) * rates[0] +
                (output_count or 0) * rates[1]) / 1_000_000
    if input_count is None or output_count is None:
        return round(estimate, 9), "partial minimum from known token side only; not a complete bill"
    return round(estimate, 9), "estimate at listed standard rate; actual invoice may differ"


def begin(*, model: str, purpose: str, transport: str,
          input_text: str = "", opaque_input: bool = False,
          logical_id: str | None = None, retry_count: int = 0) -> str:
    if transport not in {"selenium", "api"}:
        raise ValueError("unknown Gemini accounting transport")
    # Versioned executable recovery contract: do not send without a registered
    # durable accounting mechanism. Never repair by replaying a model request.
    from .recovery_registry import lookup_mechanism
    try:
        mechanism = lookup_mechanism(
            "request_cost_accounting", "GEMINI_REQUEST_COST_SQLITE_V1")
    except (ValueError, OSError) as exc:
        raise RuntimeError("GEMINI_ACCOUNTING_REGISTRY_INVALID_NO_SEND") from exc
    if mechanism != "PERSIST_BEFORE_SEND_UPDATE_ON_RESPONSE":
        raise RuntimeError("GEMINI_ACCOUNTING_REGISTRY_INVALID_NO_SEND")
    if type(retry_count) is not int or retry_count < 0:
        raise ValueError("retry_count must be a nonnegative integer")
    request_id = uuid.uuid4().hex
    logical_id = logical_id or request_id
    chapter, subsection, stage = _context()
    input_count = _text_tokens(input_text) if input_text else None
    source = ("heuristic_text_partial_multimodal" if opaque_input else
              "heuristic_text") if input_count is not None else "unknown"
    price, billing = _cost(model, transport, input_count, None)
    with _db() as con:
        con.execute("""INSERT INTO gemini_requests (
            request_id,logical_id,attempt_number,retry_count,started_utc,
            updated_utc,host,transport,purpose,stage,chapter,subsection,model,
            status,input_tokens,output_tokens,input_token_source,
            output_token_source,estimated_usd_cost,price_version,
            price_source,billing_note,failure_class)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (request_id, logical_id, retry_count + 1, retry_count, utc(), utc(),
             socket.gethostname(), transport, purpose, stage, chapter,
             subsection, model, "possible_send", input_count, None, source,
             "unknown", price, PRICING_VERSION, PRICING_SOURCE, billing, None))
    return request_id


def finish(request_id: str, *, response=None, output_text: str | None = None,
           failure: BaseException | None = None, status: str | None = None) -> None:
    with _db() as con:
        row = con.execute("""SELECT model,transport,input_tokens,
            input_token_source FROM gemini_requests WHERE request_id=?""",
            (request_id,)).fetchone()
        if row is None:
            raise ValueError("unknown Gemini accounting request ID")
        model, transport, input_count, input_source = row
        output = None
        output_source = "unknown"
        meta = (getattr(response, "usage_metadata", None)
                or getattr(response, "usage", None))
        reported_in = _usage_number(
            meta, "prompt_token_count", "promptTokenCount",
            "input_tokens", "input_token_count")
        reported_out = _usage_number(
            meta, "candidates_token_count", "candidatesTokenCount",
            "output_tokens", "output_token_count")
        thinking = _usage_number(meta, "thoughts_token_count", "thoughtsTokenCount") or 0
        if reported_in is not None:
            input_count, input_source = reported_in, "provider_reported"
        if reported_out is not None:
            output, output_source = reported_out + thinking, "provider_reported_including_thinking"
        elif output_text is not None:
            output, output_source = _text_tokens(output_text), "heuristic_text"
        elif response is not None:
            audio = _audio_token_estimate(response)
            if audio is not None:
                output, output_source = audio, "estimated_audio_duration_25_tokens_per_sec"
            else:
                text = getattr(response, "text", None)
                if isinstance(text, str):
                    output, output_source = _text_tokens(text), "heuristic_text"
        price, billing = _cost(model, transport, input_count, output)
        final_status = status or ("response_captured" if failure is None else "send_uncertain")
        if final_status not in {"response_captured", "send_uncertain",
                                "registered_response_pending", "failed_pre_send"}:
            raise ValueError("unknown Gemini accounting status")
        # Once response usage is recorded, never allow a later retry/cleanup to
        # downgrade it to an unknown outcome.
        con.execute("""UPDATE gemini_requests SET updated_utc=?,status=?,
            input_tokens=?,output_tokens=?,input_token_source=?,
            output_token_source=?,estimated_usd_cost=?,billing_note=?,
            failure_class=?
            WHERE request_id=? AND status != 'response_captured'""",
            (utc(), final_status, input_count, output, input_source,
             output_source, price, billing,
             type(failure).__name__ if failure is not None else None,
             request_id))


def next_attempt_index(logical_id: str) -> int:
    """Recover counts after a worker timeout/restart without reusing an ordinal."""
    with _db() as con:
        row = con.execute(
            "SELECT COALESCE(MAX(attempt_number),0) FROM gemini_requests WHERE logical_id=?",
            (logical_id,)).fetchone()
    return int(row[0])


def browser_begin(client, *, prompt_text: str | None = None) -> str:
    existing = getattr(client, "_microgen_cost_request_id", None)
    if existing:
        # The same browser instance can send successive requests; the previous
        # uncompleted request must remain visible as uncertain.
        pass
    text = prompt_text if prompt_text is not None else (
        getattr(client, "_microgen_cost_prompt_text", "") or "")
    model = os.getenv("MICROGEN_LLM_MODEL", "gemini-web-model-unverified")
    purpose = os.getenv("MICROGEN_ACTIVE_GENERATION_STAGE", "lecture_generation")
    marker = (model, purpose, text)
    previous_marker = getattr(client, "_microgen_cost_previous_prompt", None)
    previous = (int(getattr(client, "_microgen_cost_repeat_count", 0)) + 1
                if previous_marker == marker else 0)
    logical_id = (getattr(client, "_microgen_cost_previous_logical_id", None)
                  if previous_marker == marker else None)
    req = begin(model=model, purpose=purpose, transport="selenium",
                input_text=text, opaque_input=(purpose in {
                    "figures", "slides", "narration", "academic_review",
                    "scientific_review", "pedagogy_review"}),
                logical_id=logical_id, retry_count=previous)
    if logical_id is None:
        logical_id = req
    client._microgen_cost_previous_logical_id = logical_id
    client._microgen_cost_previous_prompt = marker
    client._microgen_cost_repeat_count = previous
    client._microgen_cost_request_id = req
    return req


def browser_finish(client, response_text: str | None = None, *,
                   status: str | None = None) -> None:
    req = getattr(client, "_microgen_cost_request_id", None)
    if req:
        finish(req, output_text=response_text,
               status=status or ("response_captured" if response_text else "send_uncertain"))
        if response_text:
            client._microgen_cost_request_id = None


class _ModelsMeter:
    def __init__(self, original, purpose: str, logical_id: str, attempt: int):
        self._original = original
        self._purpose = purpose
        self._logical_id = logical_id
        self._attempt = attempt

    def __getattr__(self, attr):
        return getattr(self._original, attr)

    def generate_content(self, *, model, contents, **kwargs):
        # The metering adapter is not an alternative paid-API permission.
        from .paid_api_policy import (
            require_paid_gemini_api, tts_qa_explicitly_approved)
        require_paid_gemini_api(
            self._purpose, qa_approved=tts_qa_explicitly_approved(),
            model=model)
        text, opaque = _text_parts(contents)
        req = begin(model=model, purpose=self._purpose, transport="api",
                    input_text=text, opaque_input=opaque,
                    logical_id=self._logical_id, retry_count=self._attempt)
        try:
            response = self._original.generate_content(
                model=model, contents=contents, **kwargs)
        except BaseException as exc:
            finish(req, failure=exc)
            raise
        finish(req, response=response)
        return response


class _InteractionsMeter:
    """Meter real Gemini 3.8 TTS Interactions sends, including failed attempts."""

    def __init__(self, original, purpose: str, logical_id: str, attempt: int):
        self._original = original
        self._purpose = purpose
        self._logical_id = logical_id
        self._attempt = attempt

    def create(self, **kwargs):
        from .paid_api_policy import (
            require_paid_gemini_api, tts_qa_explicitly_approved,
        )
        require_paid_gemini_api(
            self._purpose, qa_approved=tts_qa_explicitly_approved(),
            model=kwargs.get("model"),
        )
        model = kwargs.get("model")
        text, opaque = _text_parts(kwargs.get("input"))
        if not isinstance(model, str) or not model or not text.strip():
            raise ValueError("Unmeterable Gemini Interactions payload: NO SEND")
        request_id = begin(
            model=model, purpose=self._purpose, transport="api",
            input_text=text, opaque_input=opaque,
            logical_id=self._logical_id, retry_count=self._attempt,
        )
        try:
            result = self._original.create(**kwargs)
        except BaseException as exc:
            finish(request_id, failure=exc)
            raise
        finish(request_id, response=result)
        return result


class MeteredGeminiClient:
    def __init__(self, client, *, purpose: str, logical_id: str, attempt: int):
        self._client = client
        self._purpose = purpose
        self._logical_id = logical_id
        self._attempt = attempt

    @property
    def models(self):
        return _ModelsMeter(self._client.models, self._purpose,
                            self._logical_id, self._attempt)

    @property
    def interactions(self):
        return _InteractionsMeter(self._client.interactions, self._purpose,
                                  self._logical_id, self._attempt)

    def __getattr__(self, attr):
        return getattr(self._client, attr)

    def close(self):
        close = getattr(self._client, "close", None)
        if callable(close):
            close()


def export_csv(destination: Path) -> int:
    with _db() as con:
        cur = con.execute("SELECT * FROM gemini_requests ORDER BY started_utc,request_id")
        names = [column[0] for column in cur.description]
        rows = cur.fetchall()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(names)
        writer.writerows(rows)
    return len(rows)


def summary() -> dict:
    with _db() as con:
        stats = con.execute("""SELECT COUNT(*),COALESCE(SUM(
            CASE WHEN transport='api' AND status='response_captured'
            THEN estimated_usd_cost ELSE 0 END),0),
            COALESCE(SUM(CASE WHEN transport='api' AND status!='response_captured'
                     THEN 1 ELSE 0 END),0) FROM gemini_requests""").fetchone()
        by_context = con.execute("""SELECT chapter,subsection,purpose,model,
            transport,COUNT(*),ROUND(SUM(estimated_usd_cost),8)
            FROM gemini_requests GROUP BY 1,2,3,4,5
            ORDER BY 1,2,3,4,5""").fetchall()
    return {
        "requests": stats[0],
        "captured_api_cost_estimate_usd": round(stats[1], 8),
        "uncertain_api_attempts_excluded_from_captured_total": stats[2],
        "ledger_path": str(ledger_path()),
        "groups": [dict(zip(("chapter","subsection","purpose","model",
                             "transport","requests","row_estimate_usd"), row))
                   for row in by_context],
        "warning": "Estimated, not invoiced. Uncertain API attempts may have been charged. Selenium subscription excluded.",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="MicroGen Gemini per-request cost ledger")
    p.add_argument("--csv", type=Path, help="Export all request attempts to CSV")
    p.add_argument("--summary", action="store_true")
    args = p.parse_args(argv)
    if args.csv:
        print(json.dumps({"csv": str(args.csv), "rows": export_csv(args.csv)}))
    if args.summary or not args.csv:
        print(json.dumps(summary(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
