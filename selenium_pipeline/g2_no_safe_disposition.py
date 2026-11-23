"""No-Send original G2 incident disposition for restart-aware development.

This module deliberately has no provider/browser transport imports. A stale,
ambiguous or already claimed scientific review is NEVER submitted again.
Only source-bound immutable historical facts are recorded. Pending source
science, acoustic acceptance and student publication are never approved.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from .figure_source_identity import require, _sha
from .historical_quarantine_evidence_v1 import inspect_historical_quarantine

RECOVERY_REGISTRY=Path(__file__).with_name("g2_no_safe_recovery_registry_v1.json")
MECHANISM="ATTEST_EXISTING_UNCERTAIN_CLAIMS_AND_PERSIST_NO_SEND_DISPOSITION"
SIGNATURE="G2_ORIGINAL_NO_SAFE_SOURCE_REVIEW_UNIT"
ALLOWED_REASONS={
    "RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND",
    "AMBIGUOUS_OLD_SEND_NO_RESUBMISSION",
    "SOURCE_REVIEW_QUARANTINED_INVALID_SAVED_REPLY",
    "PRIOR_SAVED_REPLY_RECONCILIATION_ALREADY_ATTEMPTED",
}


def _registry_check(*, path:Path|None=None)->None:
    source=Path(path or RECOVERY_REGISTRY)
    require(source.is_file() and not source.is_symlink()
            and 1<=source.stat().st_size<=4096,
            "Source-bound G2 no-Send recovery registry unavailable")
    data=json.loads(source.read_text(encoding="utf8"))
    expected={
        "schema_version":1,
        "status":"ORIGINAL_G2_NO_SAFE_SOURCE_DISPOSITION_REGISTRY_V1",
        "mechanism":MECHANISM,
        "signature":SIGNATURE,
        "enabled":True,
        "max_model_sends":0,
    }
    require(data==expected,"Unknown, disabled or corrupted no-Send recovery mechanism")


def preserve_g2_no_safe_disposition(
    *, queue_root:Path, folder:Path, work_root:Path,
    source_sha:str, selection:dict, registry_path:Path|None=None,
)->dict:
    """Persist evidence only; do not dispatch, retry or clear any old claim."""
    _registry_check(path=registry_path)
    queue_root,folder,work_root=[Path(v).absolute() for v in
                                 (queue_root,folder,work_root)]
    require(queue_root.is_dir() and not queue_root.is_symlink()
            and folder.is_dir() and not folder.is_symlink()
            and work_root.is_dir() and not work_root.is_symlink()
            and not queue_root.is_relative_to(folder)
            and not folder.is_relative_to(queue_root)
            and not work_root.is_relative_to(folder),
            "Invalid original-source G2 checkpoint isolation")
    require(re.fullmatch(r"[a-f0-9]{64}",source_sha) is not None
            and _sha(folder/"source.pdf")==source_sha,
            "Original source SHA mismatch during historical disposition")
    q_file=queue_root/"queue.json"
    require(q_file.is_file() and not q_file.is_symlink(),
            "Missing immutable original G2 review queue")
    q=json.loads(q_file.read_text(encoding="utf8"))
    require(q.get("status")=="IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE"
            and q.get("original_source_folder")==str(folder)
            and q.get("student_publication_authorized") is False
            and type(q.get("slide_jobs")) is list and bool(q["slide_jobs"])
            and all(row.get("original_source_sha256")==source_sha
                    for row in q["slide_jobs"]),
            "Original source-review queue identity cannot be attested")
    require(type(selection) is dict
            and selection.get("status")=="NO_SAFE_REVIEW_UNIT_REMAINING"
            and selection.get("student_publication_authorized") is False
            and selection.get("new_model_requests") is False,
            "Cannot treat an eligible or untrusted review selection as blocked")
    blocked=selection.get("blocked_other_slides")
    require(type(blocked) is list and bool(blocked),
            "Empty or unbound G2 no-Send evidence")
    eligible={row.get("slide") for row in q["slide_jobs"]}
    seen=set()
    reasons=[]
    for rec in blocked:
        require(type(rec) is dict
                and type(rec.get("slide")) is int
                and rec["slide"] in eligible
                and rec.get("mode") in ("INITIAL_REVIEW","INDEPENDENT_CHALLENGE")
                and rec.get("reason") in ALLOWED_REASONS
                and (rec["slide"],rec["mode"]) not in seen,
                "Unknown G2 historical review state; no automatic bypass")
        seen.add((rec["slide"],rec["mode"]))
        slide, mode=rec["slide"],rec["mode"]
        stem=f"slide_{slide:03d}_{mode.lower()}"
        attempts=[]
        for n in range(1,4):
            f=queue_root/f"{stem}_attempt_{n:02d}.json"
            checkpoint=queue_root/f"{stem}_attempt_{n:02d}_request"
            claim=checkpoint/"dispatch_attempted.claim"
            if not f.exists():
                # Historical interrupted sends may have no final attempt
                # result, but do retain an independently pinned pre-Send
                # request_state.json. Inventory that claim, never invent an
                # absent model answer or allow another Send.
                statefile=checkpoint/"request_state.json"
                if statefile.exists():
                    require(statefile.is_file() and not statefile.is_symlink()
                            and claim.is_file() and not claim.is_symlink(),
                            "Untrusted original pre-Send request state")
                    request_state=json.loads(statefile.read_text(encoding="utf8"))
                    require(request_state.get("schema_version")==1
                            and request_state.get("status")=="SUBMITTED_OR_UNCERTAIN"
                            and request_state.get("review_mode")==mode
                            and request_state.get("source_sha256")==source_sha
                            and request_state.get("slides_sha256")==_sha(folder/"slides.pdf")
                            and request_state.get("script_sha256")==_sha(folder/"script.txt")
                            and request_state.get("can_auto_retry") is False
                            and request_state.get("submission_may_have_occurred") is True,
                            "Original historical request state not source-bound")
                    attempts.append({
                        "number":n,"status":"SUBMITTED_OR_UNCERTAIN_NO_REPLY",
                        "provider_submission_state":"UNKNOWN_AFTER_POSSIBLE_SUBMISSION",
                        "receipt_sha256":_sha(statefile),
                        "claim_present":True,
                        "quarantine_capture":inspect_historical_quarantine(None),
                    })
                continue
            require(f.is_file() and not f.is_symlink(),
                    "Unsafe prior G2 attempt evidence")
            data=json.loads(f.read_text(encoding="utf8"))
            require(data.get("slide")==slide and data.get("mode")==mode
                    and data.get("attempt")==n,
                    "Historical attempt changed original identity")
            checkpoint=queue_root/f"{stem}_attempt_{n:02d}_request"
            claim=checkpoint/"dispatch_attempted.claim"
            if data.get("provider_submission_state")=="UNKNOWN_AFTER_POSSIBLE_SUBMISSION":
                require(claim.is_file() and not claim.is_symlink()
                        and not (checkpoint/"model_response_untrusted.txt").exists(),
                        "Ambiguous source request has a saved reply or missing claim; "
                        "invoke original saved-response reconciliation instead")
            attempts.append({"number":n,
                             "status":data.get("status"),
                             "provider_submission_state":
                                 data.get("provider_submission_state"),
                             "receipt_sha256":_sha(f),
                             "claim_present":claim.is_file(),
                             "quarantine_capture":inspect_historical_quarantine(
                                 data.get("reason"))})
        claim1=queue_root/f"{stem}_attempt_01_request"/"dispatch_attempted.claim"
        if rec["reason"] in {
                "RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND",
                "AMBIGUOUS_OLD_SEND_NO_RESUBMISSION"}:
            require(attempts or claim1.is_file(),
                    "Unaccounted old provider Send, no new request permitted")
        reasons.append({"slide":slide,"mode":mode,
                        "reason":rec["reason"],
                        "attempts":attempts,
                        "old_request_replay_authorized":False})
    original_queue_sha=_sha(q_file)
    require(_sha(folder/"source.pdf")==source_sha
            and _sha(q_file)==original_queue_sha,
            "Source changed while preserving old review claims")
    payload={
        "schema_version":1,
        "status":"G2_HISTORICAL_CLAIMS_PRESERVED_NO_SEND",
        "original_source_sha256":source_sha,
        "original_queue_sha256":original_queue_sha,
        "mechanism":MECHANISM,
        "blocked":reasons,
        "new_provider_requests":0,
        "old_original_claims_replayed":False,
        "G2_academic_scientific_acceptance_claimed":False,
        "G3_acoustic_video_acceptance_claimed":False,
        "student_publication_authorized":False,
        "next_safe_development_work":"INDEPENDENT_OFFLINE_QA_PREFLIGHT_ELIGIBLE",
        "offline_work_executed":False,
    }
    serialized=json.dumps(payload,indent=2,sort_keys=True)+"\n"
    # Hash-derived names preserve each exact historical version without
    # altering earlier receipts. All writes are atomic under supervisor lock.
    key=hashlib.sha256(serialized.encode("utf8")).hexdigest()[:24]
    destination=work_root/"g2_no_safe_dispositions"
    require(not destination.is_symlink(),"Unsafe no-Send checkpoint root")
    destination.mkdir(exist_ok=True)
    result=destination/(key+".json")
    require(not result.is_symlink(),"Unsafe historical G2 disposition receipt")
    if result.exists():
        require(result.is_file() and result.read_text(encoding="utf8")==serialized,
                "Existing no-Send disposition receipt mutated")
    else:
        temporary=destination/(key+".tmp")
        require(not temporary.exists() and not temporary.is_symlink(),
                "Interrupted no-Send staging requires separate recovery")
        with temporary.open("x",encoding="utf8") as out:
            out.write(serialized)
        os.replace(temporary,result)
    return {"status":payload["status"],"receipt":str(result),
            "blocked_review_units":len(reasons),
            "new_provider_requests":0,
            "old_original_claims_replayed":False,
            "student_publication_authorized":False,
            "next_safe_development_work":payload["next_safe_development_work"],
            "offline_work_executed":False}
