"""Restart-safe, source-bound Gemini slide response claims.

Only a verified pre-send failure may select a new transport. Once a Send or
SDK request might have happened, an unresolved result is never replayed.
Previously captured raw responses can be revalidated by ordinary Beamer QA.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path


class PreSendFailure(RuntimeError):
    """An error occurred before any external model request was attempted."""


class IndeterminateSend(RuntimeError):
    """A provider request may have been accepted; do not automatically retry."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _default_root() -> Path:
    root = os.getenv("MICROGEN_SLIDE_CLAIM_ROOT")
    if root:
        return Path(root).expanduser()
    base = Path(os.getenv("LOCALAPPDATA") or (Path.home() / ".cache"))
    return base / "Microvid" / "slide_send_claims"


class SlideAttemptClaim:
    def __init__(self, source: Path, prompt: Path, instruction: str,
                 *, backend: str, ordinal: int, root: Path | None = None):
        if backend not in {"selenium", "api"} or not 1 <= ordinal <= 10:
            raise ValueError("Invalid slide communication attempt")
        src = Path(source)
        prm = Path(prompt)
        if not src.is_file() or not prm.is_file() or not isinstance(instruction, str):
            raise ValueError("Cannot claim a slide send without source and prompt")
        self.source_sha256 = _sha(src.read_bytes())
        self.prompt_sha256 = _sha(prm.read_bytes())
        self.backend = backend
        self.model = (
            os.getenv("MICROGEN_LLM_MODEL", "gemini-3.8-flash")
            if backend == "api"
            else os.getenv("MICROGEN_GEMINI_UI_MODE", "flash")
        )
        fingerprint = _sha(("slide-v1\n" + self.source_sha256 + "\n" +
                            self.prompt_sha256 + "\n" + _sha(instruction.encode("utf-8")) +
                            "\n" + backend + "\n" + str(ordinal)).encode("utf-8"))
        directory = (Path(root) if root else _default_root()) / fingerprint[:2]
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / (fingerprint + ".json")
        self.raw_path = directory / (fingerprint + ".response.txt")

    def read_existing(self) -> str | None:
        """Returns captured response; raises if a prior Send remains uncertain."""
        if not self.path.exists():
            return None
        try:
            record = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise IndeterminateSend("Corrupt slide send claim; no duplicate request") from exc
        if (record.get("source_sha256") != self.source_sha256
                or record.get("prompt_sha256") != self.prompt_sha256
                or record.get("backend") != self.backend
                or record.get("model", self.model) != self.model):
            raise IndeterminateSend("Slide send claim/source mismatch")
        if record.get("status") != "RESPONSE_CAPTURED":
            raise IndeterminateSend("Prior slide request has an unresolved Send claim")
        if not self.raw_path.is_file():
            raise IndeterminateSend("Captured slide response is missing")
        data = self.raw_path.read_bytes()
        if not data or _sha(data) != record.get("response_sha256"):
            raise IndeterminateSend("Captured slide response checksum mismatch")
        return data.decode("utf-8")

    def mark_send_may_have_occurred(self) -> None:
        """Atomic exclusive claim MUST precede any Send or SDK invocation."""
        record = {
            "schema_version": 1,
            "status": "SEND_MAY_HAVE_OCCURRED",
            "backend": self.backend,
            "model": self.model,
            "source_sha256": self.source_sha256,
            "prompt_sha256": self.prompt_sha256,
            "claimed_utc": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with self.path.open("x", encoding="utf-8") as stream:
                json.dump(record, stream, indent=2)
        except FileExistsError as exc:
            raise IndeterminateSend("Slide Send already claimed; refusing replay") from exc

    def capture(self, response: str) -> None:
        if not isinstance(response, str) or not response.strip():
            raise IndeterminateSend("Gemini answer not captured after claimed Send")
        current = json.loads(self.path.read_text(encoding="utf-8"))
        if current.get("status") != "SEND_MAY_HAVE_OCCURRED":
            raise IndeterminateSend("Inconsistent slide Send state")
        payload = response.encode("utf-8")
        with self.raw_path.open("xb") as stream:
            stream.write(payload)
        current["status"] = "RESPONSE_CAPTURED"
        current["response_sha256"] = _sha(payload)
        current["captured_utc"] = datetime.now(timezone.utc).isoformat()
        temp = self.path.with_suffix(".pending")
        with temp.open("x", encoding="utf-8") as stream:
            json.dump(current, stream, indent=2)
        temp.replace(self.path)
