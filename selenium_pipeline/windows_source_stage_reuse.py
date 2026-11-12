"""Non-destructive reuse of accepted slides across separate, identical original-source trials.

Produces no Gemini Send. Never re-labels a failed source stage as successful.
A genuine already-passed slide artifact is reverified byte-for-byte against its
original immutable one-shot receipt and copied into a NEW source-only trial.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import _verified_json, require, _new_atomic
from .figures_failed_source_only_resume import verify_recovery_receipt
from .runner import check_valid

def adopt_accepted_slides(*, prior_trial: Path, new_trial: Path) -> dict:
    prior_trial, new_trial = Path(prior_trial).absolute(), Path(new_trial).absolute()
    require(os.name == "nt" and prior_trial != new_trial
            and prior_trial.parent == new_trial.parent
            and prior_trial.is_dir() and new_trial.is_dir()
            and not prior_trial.is_symlink() and not new_trial.is_symlink(),
            "Two distinct native Windows, sibling trial directories required")
    old = _verified_json(prior_trial / "fresh_trial_contract.json")
    new = _verified_json(new_trial / "fresh_trial_contract.json")
    sha = old.get("source_sha256")
    require(sha == new.get("source_sha256")
            and old.get("source_path") == new.get("source_path")
            and old.get("status") == new.get("status") ==
                "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL"
            and new.get("paid_tts_authorized") is False
            and new.get("student_publication_authorized") is False,
            "Cannot reuse slides across distinct/unsafe sources")
    previous_recovery = verify_recovery_receipt(prior_trial)
    new_recovery = verify_recovery_receipt(new_trial)
    old_start = _verified_json(prior_trial / "stage_slides_started.json")
    old_result_path = prior_trial / "stage_slides_result.json"
    old_result = _verified_json(old_result_path)
    old_log = prior_trial / "stage_slides_stdout.raw.log"
    require(old_log.is_file() and not old_log.is_symlink()
            and old_start.get("source_sha256") == sha
            and old_start.get("stage") == "slides"
            and old_start.get("predecessor_receipt_sha256") ==
                file_sha256(previous_recovery)
            and old_start.get("single_attempt_no_provider_resend") is True
            and old_result.get("schema_version") == 1
            and old_result.get("status") == "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND"
            and old_result.get("stage") == "slides"
            and old_result.get("source_sha256") == sha
            and old_result.get("predecessor_receipt_sha256") ==
                file_sha256(previous_recovery)
            and old_result.get("exit_code") == 0
            and old_result.get("new_video_rendered") is False
            and old_result.get("student_publication_authorized") is False,
            "No independently accepted one-shot slides to reuse")
    from .windows_lecture_progression_coordinator import _source_locked_ui_contract_breach
    require(not _source_locked_ui_contract_breach(prior_trial, "slides"),
            "Prior slides violate owned model/thinking evidence")
    old_lecture = Path(old["staged_source_path"]).parent
    new_lecture = Path(new["staged_source_path"]).parent
    old_work = old_lecture / ".microgen_work"
    new_work = new_lecture / ".microgen_work"
    require(check_valid("slides", old_work)
            and check_valid("figures", new_work)
            and file_sha256(old_work / "source.pdf") == sha
            and file_sha256(new_work / "source.pdf") == sha,
            "Original slides or recovered figure state changed")
    expected = old_result.get("output_sha256")
    require(type(expected) is dict and len(expected) >= 2,
            "Original slides output SHA map missing")
    for name in ("slides.pdf", "slides.tex"):
        old_p = old_lecture / name
        old_internal = old_work / name
        new_p = new_lecture / name
        new_internal = new_work / name
        require(old_p.is_file() and old_internal.is_file()
                and not old_p.is_symlink() and not old_internal.is_symlink()
                and file_sha256(old_p) == file_sha256(old_internal)
                    == expected.get(name)
                and not new_p.exists() and not new_internal.exists(),
                "Slide source changed or destination already populated")
    began = new_trial / "stage_slides_started.json"
    finished = new_trial / "stage_slides_result.json"
    require(not began.exists() and not finished.exists()
            and not any(new_trial.glob("stage_narration_*")),
            "Already attempted source trial; never overwrite or replay")
    # Immutable local reuse marker is NOT a new browser-Send claim.
    claim = {
        "schema_version": 1, "stage": "slides", "source_sha256": sha,
        "predecessor_receipt_sha256": file_sha256(new_recovery),
        "single_attempt_no_provider_resend": True,
        "paid_tts_authorized": False, "student_publication_authorized": False,
        "reused_source_artifacts_only": True,
        "new_model_sends": 0,
        "prior_accepted_slides_receipt_sha256": file_sha256(old_result_path),
    }
    for name in ("slides.pdf", "slides.tex"):
        shutil.copy2(old_lecture / name, new_lecture / name)
        shutil.copy2(old_work / name, new_work / name)
        require(file_sha256(new_lecture / name) ==
                file_sha256(new_work / name) == expected[name],
                "Copied slide bytes differ from original accepted artifact")
    _new_atomic(began, claim)
    result = {
        "schema_version": 1, "stage": "slides",
        "source_sha256": sha,
        "predecessor_receipt_sha256": file_sha256(new_recovery),
        "status": "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND",
        "exit_code": 0,
        "output_sha256": {x: expected[x] for x in ("slides.pdf", "slides.tex")},
        "new_model_or_tts_calls": False, "new_tts_calls": False,
        "new_video_rendered": False,
        "student_publication_authorized": False,
        "reused_previous_accepted_slides": True,
        "prior_accepted_slides_receipt_sha256": file_sha256(old_result_path),
        "prior_accepted_slides_log_sha256": file_sha256(old_log),
        "actual_source_sha256": sha,
        "full_sourcebound_original_lecture_completed": False,
        "independent_academic_or_media_qa_verified": False,
    }
    _new_atomic(finished, result)
    require(check_valid("slides", new_work), "Reused slide QA failed")
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prior-trial", type=Path, required=True)
    p.add_argument("--new-trial", type=Path, required=True)
    a=p.parse_args(argv)
    try:
        out=adopt_accepted_slides(prior_trial=a.prior_trial, new_trial=a.new_trial)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        out={"status": "ACCEPTED_SLIDES_REUSE_REJECTED",
             "reason":str(exc),"new_model_or_tts_calls": False}
    print(json.dumps(out, indent=2))
    return 0 if out.get("status") == "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND" else 2

if __name__=="__main__":
    raise SystemExit(main())
