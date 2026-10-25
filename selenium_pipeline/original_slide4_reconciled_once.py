"""One explicitly owner-approved source-math review after a reconciled pre-send failure.

Writes a NEW external window, never edits the original 71-unit queue or retries
after a possible provider submission. The caller must explicitly choose the
bounded owner-approved review scope and supply immutable forensic evidence.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from .figure_source_identity import _sha, require
from .ai_academic_review_queue import _check_queue
from .ai_academic_web_review import build_review_job, run_web_review
from .ai_academic_review_consensus import _independently_check_saved_pass
from .review_retry_plan import plan_manual_review_attempt

APPROVAL = "OWNER_AUTHORIZED_20261025_ORIGINAL_THOMAS84_SLIDE004_ONE_RECONCILED_INITIAL_REVIEW"


def _write_new(path: Path, document: dict) -> None:
    with path.open("x", encoding="utf8") as target:
        json.dump(document, target, sort_keys=True, indent=2, ensure_ascii=False)
        target.write("\n")
        target.flush()
        os.fsync(target.fileno())


def reconcile_original_slide4(*,folder:Path,queue_root:Path,
                               forensic_path:Path,intent_path:Path)->dict:
    """Check immutable historic error; do not rewrite its UNKNOWN receipt."""
    folder,queue_root=Path(folder).absolute(),Path(queue_root).absolute()
    forensic_path,intent_path=Path(forensic_path).absolute(),Path(intent_path).absolute()
    _check_queue(queue_root=queue_root,folder=folder,slide=4,mode="INITIAL_REVIEW")
    historical=queue_root/"slide_004_initial_review_attempt_01.json"
    require(historical.is_file() and not historical.is_symlink()
            and forensic_path.is_file() and not forensic_path.is_symlink()
            and intent_path.is_file() and not intent_path.is_symlink(),
            "Original Slide4 failure/forensic/intent evidence required")
    old=json.loads(historical.read_text(encoding="utf8"))
    f=json.loads(forensic_path.read_text(encoding="utf8"))
    before=json.loads(intent_path.read_text(encoding="utf8"))
    require(old.get("slide")==4 and old.get("mode")=="INITIAL_REVIEW"
            and old.get("attempt")==1 and old.get("error_type")=="GeminiModelError"
            and old.get("provider_submission_state")=="UNKNOWN_AFTER_POSSIBLE_SUBMISSION"
            and old.get("manual_retry_eligible") is False
            and old.get("requires_owner_reconciliation") is True
            and old.get("reason","").startswith("Model selection not confirmed for flash")
            and f.get("status")
                =="ORIGINAL_SLIDE4_PRE_SEND_MODEL_SELECTOR_CODEPATH_WITNESSED_NO_RETRY_AUTHORIZATION"
            and f.get("selector_before_upload_typing_and_click") is True
            and f.get("actual_provider_received_request_independently_confirmed") is False
            and f.get("historical_receipt_sha256")==_sha(historical)
            and f.get("intent_sha256")==_sha(intent_path)
            and before.get("scope")
                =="ORIGINAL_THOMAS84_SLIDE004_INITIAL_REVIEW_ATTEMPT01_ONLY",
            "Original model-selection failure not independently reconciled")
    require(not (queue_root/"slide_004_initial_review.json").exists()
            and not (queue_root/"slide_004_initial_review_attempt_02.json").exists(),
            "Original queue has later evidence or already completed")
    plan=plan_manual_review_attempt(queue_root,slide=4,mode="INITIAL_REVIEW")
    require(plan["status"]
            =="BLOCKED_AMBIGUOUS_PROVIDER_REQUEST_NEEDS_RECONCILIATION"
            and plan["observed_attempts"]==1,
            "Historical queue is not in the exact one-attempt state")
    job=build_review_job(folder=folder,slide_numbers=[4])
    require(job["utterance_count"]==5,
            "Expected five original source-bound utterances")
    hashes={name:_sha(folder/name) for name in
            ("source.pdf","slides.pdf","script.txt")}
    require((job["source_sha256"],job["slides_sha256"],job["script_sha256"])
            ==tuple(hashes.values()),
            "Source witness identities diverged")
    return {
        "original_attempt_receipt_sha256":_sha(historical),
        "original_forensic_sha256":_sha(forensic_path),
        "original_attempt_intent_sha256":_sha(intent_path),
        "original_queue_sha256":_sha(queue_root/"queue.json"),
        "original_source_sha256":hashes["source.pdf"],
        "original_slides_sha256":hashes["slides.pdf"],
        "original_script_sha256":hashes["script.txt"],
        "original_utterance_count":5,
        "original_unknown_receipt_unchanged":True,
    }


def execute_one_reconciled_initial_review(*,folder:Path,queue_root:Path,
    forensic_path:Path,intent_path:Path,window_root:Path,
    approval_reference:str,transport=None)->dict:
    require(approval_reference==APPROVAL,
            "One new Slide4 initial review requires exact owner authorization")
    root=Path(window_root).absolute()
    original=Path(folder).absolute()
    queue=Path(queue_root).absolute()
    require(root.parent.is_dir() and not root.parent.is_symlink()
            and not root.exists()
            and not root.is_relative_to(original)
            and not root.is_relative_to(queue),
            "One fresh external review-only window required; no reuse")
    proof=reconcile_original_slide4(
        folder=original,queue_root=queue,
        forensic_path=forensic_path,intent_path=intent_path)
    root.mkdir()
    manifest={
        "status":"USER_APPROVED_SINGLE_RECONCILED_ORIGINAL_SLIDE4_INITIAL_REVIEW",
        "approval_reference":approval_reference,
        "historical_proof":proof,
        "maximum_new_provider_attempts":1,
        "automatic_retry_authorized":False,
        "academic_approval":False,
        "student_publication_authorized":False,
    }
    _write_new(root/"window_manifest.json",manifest)
    # This exists BEFORE any possible provider contact. A crash is ambiguous
    # and must NOT permit rerunning this one-use window.
    _write_new(root/"possible_submission_intent.json",{
        "status":"ONE_ATTEMPT_INTENT_FSYNCED_BEFORE_PROVIDER",
        "approval_reference":approval_reference,
        "created_unix_s":time.time(),
        "may_have_submitted":True,
        "provider_response_confirmed":False,
        "no_resubmission":True,
    })
    observed=reconcile_original_slide4(
        folder=original,queue_root=queue,
        forensic_path=forensic_path,intent_path=intent_path)
    require(observed==proof,"Historical original evidence changed before send")
    job=build_review_job(folder=original,slide_numbers=[4])
    returned=False
    def observed_response(text):
        nonlocal returned
        returned=type(text) is str and bool(text.strip())
    try:
        reviewed=run_web_review(folder=original,job=job,
                                mode="INITIAL_REVIEW",
                                transport=transport,
                                response_observer=observed_response)
        _independently_check_saved_pass(
            folder=original,job=job,record=reviewed,mode="INITIAL_REVIEW")
        require(reconcile_original_slide4(
            folder=original,queue_root=queue,
            forensic_path=forensic_path,intent_path=intent_path)==proof,
            "Source/previous immutable receipts drifted during model review")
    except Exception as exc:
        error={
            "status":"NEW_SCOPED_INITIAL_REVIEW_FAILURE_QUARANTINED",
            "error_type":type(exc).__name__,
            "reason":str(exc)[:400],
            "provider_submission_state":(
                "RETURNED_RESPONSE_INVALID" if returned
                else "UNKNOWN_AFTER_POSSIBLE_SUBMISSION"),
            "request_was_received_independently_confirmed":False,
            "new_attempts_remaining_in_this_window":0,
            "requires_owner_reconciliation":True,
            "source_math_approved":False,
            "student_publication_authorized":False,
        }
        _write_new(root/"quarantined_outcome.json",error)
        return error
    _write_new(root/"original_slide4_first_pass_candidate.json",reviewed)
    outcome={
        "status":"ONE_SCOPED_ORIGINAL_SLIDE4_FIRST_PASS_SOURCE_WITNESSED",
        "original_utterances_reviewed":reviewed["review_count"],
        "candidate_receipt_sha256":_sha(root/"original_slide4_first_pass_candidate.json"),
        "new_attempts_remaining_in_this_window":0,
        "independent_second_pass_completed":False,
        "mathematics_independently_approved":False,
        "tts_authorized":False,
        "student_publication_authorized":False,
    }
    _write_new(root/"completed_outcome.json",outcome)
    return outcome


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("folder","queue-root","forensic-path","intent-path","window-root"):
        p.add_argument("--"+name,required=True,type=Path)
    p.add_argument("--allow-single-authorized-submission",action="store_true")
    a=p.parse_args(argv)
    require(a.allow_single_authorized_submission,
            "Explicit one-use user-approved dispatch flag required")
    result=execute_one_reconciled_initial_review(
        folder=a.folder,queue_root=a.queue_root,
        forensic_path=a.forensic_path,intent_path=a.intent_path,
        window_root=a.window_root,approval_reference=APPROVAL)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
