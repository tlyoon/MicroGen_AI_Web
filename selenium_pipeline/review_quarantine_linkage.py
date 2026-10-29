"""Verify an original failure attempt points to a real unmodified owned quarantine."""
import json,re
from pathlib import Path
from .review_quarantine_integrity import audit_quarantine_metadata
def verify_failed_attempt_link(*, attempt_file:Path, quarantine_root:Path)->dict:
    f=Path(attempt_file); q=Path(quarantine_root).resolve()
    if not f.is_file() or f.is_symlink() or not q.is_dir():
        raise ValueError("Absent original failed attempt or quarantine")
    a=json.loads(f.read_text(encoding="utf8"))
    if (a.get("status")!="FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED"
        or type(a.get("attempt")) is not int or a["attempt"] not in (1,2,3)
        or a.get("mode") not in ("INITIAL_REVIEW","INDEPENDENT_CHALLENGE")
        or type(a.get("slide")) is not int or not 1<=a["slide"]<=200
        or a.get("student_publication_authorized") is not False):
        raise ValueError("Original failed-attempt receipt invalid")
    m=re.fullmatch(r"slide_(\d{3})_(initial_review|independent_challenge)_attempt_(\d{2}).json",f.name)
    if not m or int(m[1])!=a["slide"] or m[2]!=a["mode"].lower() or int(m[3])!=a["attempt"]:
        raise ValueError("Original receipt filename does not match attempt")
    found=re.search(r"quarantined at (.+?\.raw\.txt)",str(a.get("reason","")))
    if not found:
        raise ValueError("No proven original owned quarantine reference")
    raw=Path(found[1])
    if raw.is_symlink() or raw.resolve().parent!=q:
        raise ValueError("Attempt points outside declared quarantine directory")
    meta=raw.with_name(raw.name[:-8]+".meta.json")
    check=audit_quarantine_metadata(meta)
    if raw.name != meta.name[:-len(".meta.json")]+".raw.txt":
        raise ValueError("Mismatched raw/model receipt")
    return {"status":"FAILED_ATTEMPT_QUARANTINE_LINK_VERIFIED",
        "slide":a["slide"],"attempt":a["attempt"],
        "capture_classification":check["classification"],
        "original_raw_sha256":check["raw_sha256"],
        "scientifically_approved":False,"retry_automatically_authorized":False}
