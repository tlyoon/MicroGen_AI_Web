"""Fault injection for evidence-only, no-replay original Gemini quarantines."""
from __future__ import annotations
import json
from pathlib import Path
import pytest
from selenium_pipeline.gemini_response_recovery import quarantine_snapshot
from selenium_pipeline.historical_quarantine_evidence_v1 import (
    inspect_historical_quarantine, KIND, SIGNATURE, REPAIR)
from selenium_pipeline.recovery_registry import lookup_mechanism


def fixture(tmp_path: Path, text: str = ""):
    root = tmp_path / "gemini_quarantine"
    item = quarantine_snapshot({
        "text": text,
        "generating": False,
        "capture_status": "empty_model_response" if not text else "visible_model_response",
    }, directory=root)
    return root, Path(item["raw_path"]), Path(item["meta_path"])


def classify(root: Path, raw: Path):
    return inspect_historical_quarantine(
        f"No stable complete Gemini JSON; untrusted response quarantined at {raw}. "
        "Do not resubmit source files.", quarantine_root=root)


def test_registered_executable_handler():
    assert lookup_mechanism(KIND, SIGNATURE) == REPAIR


def test_real_zero_byte_quarantine_does_not_claim_failed_send(tmp_path):
    root, raw, meta = fixture(tmp_path)
    got = classify(root, raw)
    assert got["status"] == "EMPTY_ORIGINAL_CAPTURE_VERIFIED_NO_REPLAY"
    assert got["raw_bytes"] == 0
    assert len(got["raw_sha256"]) == 64
    for key in ("retrievable_original_reply_proven", "provider_outage_proven",
                "provider_send_failed_proven", "retry_authorized",
                "academic_accepted", "student_publication_authorized"):
        assert got[key] is False
    assert got["new_model_requests"] == 0
    assert raw.stat().st_size == 0 and meta.is_file()
    assert classify(root, raw) == got


def test_nonempty_untrusted_text_is_never_automatically_promoted(tmp_path):
    root, raw, _ = fixture(tmp_path, '{"status":"claim"}')
    got = classify(root, raw)
    assert got["status"] == "NONEMPTY_UNTRUSTED_CAPTURE_NEEDS_SOURCE_REVIEW"
    assert got["retrievable_original_reply_proven"] is False
    assert got["retry_authorized"] is False
    assert got["academic_accepted"] is False


@pytest.mark.parametrize("mutation", [
    "raw_modified", "meta_missing", "meta_sha_corrupted",
    "meta_retry_true", "meta_wrong_filename", "meta_wrong_schema",
])
def test_missing_corrupt_or_forged_original_capture_stays_unverified(tmp_path, mutation):
    root, raw, meta_path = fixture(tmp_path)
    meta = json.loads(meta_path.read_text())
    if mutation == "raw_modified":
        raw.write_text("injected")
    elif mutation == "meta_missing":
        meta_path.unlink()
    else:
        if mutation == "meta_sha_corrupted":
            meta["raw_sha256"] = "0" * 64
        elif mutation == "meta_retry_true":
            meta["original_source_retry_authorized"] = True
        elif mutation == "meta_wrong_filename":
            meta["raw_filename"] = "foreign.raw.txt"
        elif mutation == "meta_wrong_schema":
            meta["schema_version"] = 77
        meta_path.write_text(json.dumps(meta))
    got = classify(root, raw)
    assert got["status"] == "UNVERIFIED_QUARANTINE_NO_REPLAY"
    assert got["new_model_requests"] == 0 and not got["academic_accepted"]


def test_no_reference_or_foreign_root_cannot_be_silent_approval(tmp_path):
    root, raw, _ = fixture(tmp_path)
    no_ref = inspect_historical_quarantine("Browser returned no text",
        quarantine_root=root)
    assert no_ref["status"] == "NO_QUARANTINE_REFERENCE_NO_REPLAY"
    other = tmp_path / "different_root"
    other.mkdir()
    result = classify(other, raw)
    assert result["status"] == "UNVERIFIED_QUARANTINE_NO_REPLAY"
    assert not result["provider_send_failed_proven"]


def test_modified_error_message_cannot_read_arbitrary_file(tmp_path):
    root, raw, _ = fixture(tmp_path)
    foreign = tmp_path / "private" / raw.name
    foreign.parent.mkdir()
    foreign.write_text("not a quarantine")
    result = classify(root, foreign)
    assert result["status"] == "UNVERIFIED_QUARANTINE_NO_REPLAY"
    assert not result["retrievable_original_reply_proven"]
