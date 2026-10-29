"""Strict read-only local Gemini model-response quarantine integrity audit."""
from __future__ import annotations
import hashlib,json
from pathlib import Path

def audit_quarantine_metadata(meta_file: Path) -> dict:
    path=Path(meta_file)
    if (path.is_symlink() or path.suffix!=".json" or
        not path.name.endswith(".meta.json") or not path.is_file()):
        raise ValueError("Refuse noncanonical or symlink quarantine metadata")
    m=json.loads(path.read_text(encoding="utf8"))
    if (type(m) is not dict or m.get("schema_version")!=1
        or m.get("status")!="incomplete_untrusted"
        or m.get("not_scientifically_reviewed") is not True):
        raise ValueError("Untrusted recovery receipt")
    stem=path.name[:-len(".meta.json")]
    expected=stem+".raw.txt"
    if (m.get("raw_filename")!=expected or
        type(m.get("model_response_chars")) is not int or
        not 0<=m["model_response_chars"]<=1800000):
        raise ValueError("Quarantine identity or length invalid")
    raw=path.with_name(expected)
    if raw.is_symlink() or not raw.is_file() or raw.stat().st_size>7200000:
        raise ValueError("Unsafe or missing original model-response payload")
    bytes_=raw.read_bytes()
    if hashlib.sha256(bytes_).hexdigest()!=m.get("raw_sha256"):
        raise ValueError("Quarantine SHA mismatch")
    data=bytes_.decode("utf8")
    if len(data)!=m["model_response_chars"]:
        raise ValueError("Quarantine character count mismatch")
    pending=m.get("generation_active_at_capture") is True
    classification=("PENDING_EMPTY" if pending and not data else
        "PENDING_PARTIAL" if pending else
        "COMPLETED_UNTRUSTED_TEXT" if data else "STOPPED_EMPTY")
    return {"status":"UNTRUSTED_QUARANTINE_INTEGRITY_VERIFIED",
        "classification":classification,
        "raw_sha256":m["raw_sha256"],"captured_characters":len(data),
        "retry_or_approval_authorized":False,
        "original_quarantine_file":path.name}
