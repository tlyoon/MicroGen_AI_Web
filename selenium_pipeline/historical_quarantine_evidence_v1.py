"""Evidence-only classification of historic empty Gemini response quarantines.

This does NOT prove a provider Send failed, recover a model reply, permit
retries, satisfy academic QA, or reset an across-restart circuit breaker.
Original artifact bytes are never changed or returned to the caller.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .gemini_response_recovery import default_quarantine_dir
from .recovery_registry import lookup_mechanism

KIND = "historical_quarantine_integrity"
SIGNATURE = "EMPTY_GEMINI_QUARANTINE_REVISITED_AS_RETRIEVABLE_REPLY"
REPAIR = "VERIFY_ORIGINAL_CAPTURE_HASH_AND_PERSIST_NO_REPLAY"
_PATTERN = re.compile(
    r"untrusted response quarantined at (.+?gemini_"
    r"\d{8}T\d{6}Z_[0-9a-f]{12}\.raw\.txt)(?:\.|\s|$)"
)
_FILENAME = re.compile(r"gemini_\d{8}T\d{6}Z_[0-9a-f]{12}\.raw\.txt\Z")
MAX_RAW_BYTES = 7_200_000
MAX_META_BYTES = 32_000


def _result(status: str, *, filename: str | None = None,
            raw_sha256: str | None = None, raw_bytes: int | None = None) -> dict:
    return {
        "status": status,
        "filename": filename,
        "raw_sha256": raw_sha256,
        "raw_bytes": raw_bytes,
        "retrievable_original_reply_proven": False,
        "provider_outage_proven": False,
        "provider_send_failed_proven": False,
        "retry_authorized": False,
        "academic_accepted": False,
        "student_publication_authorized": False,
        "new_model_requests": 0,
    }


def inspect_historical_quarantine(reason: str | None, *,
                                  quarantine_root: Path | None = None) -> dict:
    """Verify existing original raw+meta integrity, not provider outcome.

    Only the exact configured quarantine root is admissible; a file path
    embedded in an untrusted model/error message never authorizes arbitrary
    filesystem reads. Tests may inject an isolated temporary root.
    """
    if lookup_mechanism(KIND, SIGNATURE) != REPAIR:
        raise ValueError("Historical quarantine recovery not registered")
    if not isinstance(reason, str):
        return _result("NO_QUARANTINE_REFERENCE_NO_REPLAY")
    match = _PATTERN.search(reason)
    if match is None:
        return _result("NO_QUARANTINE_REFERENCE_NO_REPLAY")
    candidate = Path(match.group(1))
    name = candidate.name
    if _FILENAME.fullmatch(name) is None:
        return _result("UNVERIFIED_QUARANTINE_NO_REPLAY")
    root = Path(quarantine_root or default_quarantine_dir())
    if (not candidate.is_absolute() or root.is_symlink()
            or candidate.is_symlink() or not root.is_dir()):
        return _result("UNVERIFIED_QUARANTINE_NO_REPLAY", filename=name)
    try:
        if candidate.resolve(strict=False) != (root / name).resolve(strict=False):
            return _result("UNVERIFIED_QUARANTINE_NO_REPLAY", filename=name)
        meta_file = root / name.replace(".raw.txt", ".meta.json")
        if (not candidate.is_file() or not meta_file.is_file()
                or meta_file.is_symlink()
                or not 0 <= candidate.stat().st_size <= MAX_RAW_BYTES
                or not 2 <= meta_file.stat().st_size <= MAX_META_BYTES):
            return _result("UNVERIFIED_QUARANTINE_NO_REPLAY", filename=name)
        raw = candidate.read_bytes()
        meta = json.loads(meta_file.read_text(encoding="utf8"))
        sha = hashlib.sha256(raw).hexdigest()
        if (type(meta) is not dict
                or meta.get("schema_version") != 1
                or meta.get("status") != "incomplete_untrusted"
                or meta.get("raw_filename") != name
                or meta.get("raw_sha256") != sha
                or meta.get("model_response_chars") != len(raw.decode("utf8"))
                or meta.get("original_source_retry_authorized") is not False
                or meta.get("provider_server_outage_proven") is not False):
            return _result("UNVERIFIED_QUARANTINE_NO_REPLAY", filename=name)
        if not raw:
            return _result("EMPTY_ORIGINAL_CAPTURE_VERIFIED_NO_REPLAY",
                           filename=name, raw_sha256=sha, raw_bytes=0)
        return _result("NONEMPTY_UNTRUSTED_CAPTURE_NEEDS_SOURCE_REVIEW",
                       filename=name, raw_sha256=sha, raw_bytes=len(raw))
    except (OSError, ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        return _result("UNVERIFIED_QUARANTINE_NO_REPLAY", filename=name)
