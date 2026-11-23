"""Pinned, no-Send compatibility recovery for SHA-bound cross-PC artifacts.

Only exact handlers may turn a byte-identical source into a bounded
cross-renderer or page-text ABI check. No broader model/retry/publication.
"""
from __future__ import annotations
import json
from pathlib import Path

REGISTRY=Path(__file__).with_name("cross_pc_artifact_recovery_registry_v1.json")
_HANDLERS={
    "SOURCE_CROP_PIXELS_DIFFER_ACROSS_RENDERERS":
        "COMPARE_SHA_BOUND_PNG_SOURCE_PIXELS_UNDER_BOUNDED_ANTIALIASING",
    "PUBLISHED_PDF_TEXT_HASH_DIFFERS_ACROSS_RENDERERS":
        "ATTEST_EXACT_SOURCE_PDF_SCRIPT_WAV_AND_RECEIPT_BEFORE_PARSER_DRIFT",
    "UNRELEASED_NARRATED_PREVIEW_DERIVED_TEXT_DIFFERS_ACROSS_PYMUPDF":
        "VERIFY_STAGE_ONLY_UNCHANGED_PDF_SCRIPT_WAV_PREVIEW_AND_RETAIN_REVIEW_GATE",
}


def require_cross_pc_handler(signature: str, *,path:Path|None=None)->str:
    source=Path(path or REGISTRY)
    if (not source.is_file() or source.is_symlink()
        or not 1<=source.stat().st_size<=4096):
        raise ValueError("Cross-PC artifact recovery registry missing or unsafe")
    data=json.loads(source.read_text(encoding="utf-8"))
    if (type(data) is not dict
        or set(data)!={"schema_version","status","handlers","max_model_sends",
                        "may_modify_published_artifacts","student_release"}
        or data["schema_version"]!=1
        or data["status"]!="CROSS_PC_SOURCE_BOUND_ARTIFACT_RECOVERY_V1"
        or type(data["handlers"]) is not dict
        or data["handlers"]!=_HANDLERS
        or type(data["max_model_sends"]) is not int
        or data["max_model_sends"]!=0
        or data["may_modify_published_artifacts"] is not False
        or data["student_release"] is not False
        or signature not in _HANDLERS):
        raise ValueError("Unknown, disabled or modified cross-PC recovery")
    return _HANDLERS[signature]
