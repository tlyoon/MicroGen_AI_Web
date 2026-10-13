"""Quarantine incomplete Gemini responses before browser-tab teardown.

Only the final visible model-response of the owned Gemini tab is sampled.
Never capture user prompt text, other browser tabs, credentials or screenshots.
Quarantined text is UNTRUSTED and must not be used as scientific approval.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets

MAX_CAPTURE_CHARS = 1_800_000

_LATEST_MODEL_ONLY = """
const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
const response = [...document.querySelectorAll('model-response')].filter(visible);
const element = response.length ? response[response.length - 1] : null;
const text = element ? (element.innerText || element.textContent || '') : '';
const generating = [...document.querySelectorAll('button')].some(
    b => visible(b) && /stop/i.test((b.getAttribute('aria-label') || ''))
);
return {text: String(text).slice(0, 1800000), generating: generating};
"""


def latest_owned_response(driver, owned_handle: str | None) -> dict:
    """Get latest model reply only, provided the browser owns this tab.

    If the owned handle is unknown, navigation changed, or DOM inspection fails,
    report no text rather than risking retrieval of unrelated chats.
    """
    empty = {"text": "", "generating": False, "capture_status": "unavailable"}
    if not owned_handle:
        return empty
    try:
        if driver.current_window_handle != owned_handle:
            return empty
        if not str(driver.current_url).startswith("https://gemini.google.com/"):
            return empty
        result = driver.execute_script(_LATEST_MODEL_ONLY)
        if not isinstance(result, dict):
            return empty
        txt = result.get("text")
        if not isinstance(txt, str):
            return empty
        return {
            "text": txt[:MAX_CAPTURE_CHARS],
            "generating": bool(result.get("generating")),
            "capture_status": "visible_model_response" if txt.strip() else "empty_model_response",
        }
    except Exception:
        return empty


def default_quarantine_dir() -> Path:
    """A per-user local directory, never the textbook or cloned repo."""
    return Path(os.getenv("LOCALAPPDATA") or (Path.home() / ".cache")) / "Microvid" / "gemini_quarantine"


def quarantine_snapshot(snapshot: dict, *, directory: Path | None = None,
                        reason: str = "incomplete_json") -> dict:
    """Write no-overwrite untrusted text and hash-bound metadata for review.

    The files live only in a local user-owned directory. No automatic re-prompt,
    cleanup, publication, or approval occurs. Keep evidence on timeout even if
    the visible answer is empty; metadata accurately records that condition.
    """
    root = (directory or default_quarantine_dir()).expanduser().resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not root.is_dir():
        raise OSError("Recovery quarantine is not a directory")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    identifier = f"gemini_{stamp}_{secrets.token_hex(6)}"
    raw_path = root / f"{identifier}.raw.txt"
    meta_path = root / f"{identifier}.meta.json"
    raw = snapshot.get("text", "")
    if not isinstance(raw, str):
        raw = ""
    raw = raw[:MAX_CAPTURE_CHARS]
    payload = raw.encode("utf-8")
    sha = hashlib.sha256(payload).hexdigest()
    meta = {
        "schema_version": 1,
        "status": "incomplete_untrusted",
        "reason": str(reason)[:128],
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "capture_status": str(snapshot.get("capture_status", "unavailable"))[:64],
        "generation_active_at_capture": bool(snapshot.get("generating")),
        "model_response_chars": len(raw),
        "raw_sha256": sha,
        "raw_filename": raw_path.name,
        "not_scientifically_reviewed": True,
    }
    with raw_path.open("xb") as stream:
        stream.write(payload)
    with meta_path.open("x", encoding="utf-8") as stream:
        json.dump(meta, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    if os.name != "nt":
        raw_path.chmod(0o600)
        meta_path.chmod(0o600)
    return {"raw_path": raw_path, "meta_path": meta_path, **meta}


def read_quarantined_response(raw_file: Path) -> str:
    """Recover only a complete reply whose stored bytes match its receipt.

    A valid hash proves local file integrity, not the accuracy or completeness
    of Gemini's answer. Strict JSON and source/storyboard gates apply downstream.
    """
    raw_file = Path(raw_file)
    if raw_file.suffix != ".txt" or not raw_file.name.endswith(".raw.txt"):
        raise ValueError("Expected a .raw.txt quarantine artifact")
    meta_path = raw_file.with_name(raw_file.name[:-8] + ".meta.json")
    if not raw_file.is_file() or not meta_path.is_file():
        raise ValueError("Missing quarantine payload or metadata")
    if raw_file.stat().st_size > MAX_CAPTURE_CHARS * 4:
        raise ValueError("Oversized quarantine artifact")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if (meta.get("schema_version") != 1
            or meta.get("status") != "incomplete_untrusted"
            or meta.get("raw_filename") != raw_file.name):
        raise ValueError("Quarantine metadata is not trusted for recovery")
    payload = raw_file.read_bytes()
    if hashlib.sha256(payload).hexdigest() != meta.get("raw_sha256"):
        raise ValueError("Quarantine payload changed after capture")
    text = payload.decode("utf-8")
    if len(text) != meta.get("model_response_chars"):
        raise ValueError("Quarantine text length mismatch")
    return text
