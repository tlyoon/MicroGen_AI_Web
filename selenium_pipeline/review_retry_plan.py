"""Compute explicit next-step eligibility without ever dispatching Gemini."""
import json
from pathlib import Path
from .review_queue_source_audit import inspect_source_bound_queue
def plan_manual_review_attempt(queue_root:Path,*,slide:int,mode:str)->dict:
    q=Path(queue_root);inspect_source_bound_queue(q)
    if (type(slide) is not int or mode not in ("INITIAL_REVIEW","INDEPENDENT_CHALLENGE")):
        raise ValueError("Invalid bounded original Gemini reviewer stage")
    plan=json.loads((q/"queue.json").read_text(encoding="utf8"))
    if slide not in [x["slide"] for x in plan["slide_jobs"]]:
        raise ValueError("Slide absent from immutable queue")
    label=f"slide_{slide:03d}_{mode.lower()}"
    success=q/(label+".json")
    failures=[]
    for n in range(1,4):
        f=q/(label+f"_attempt_{n:02d}.json")
        if not f.exists():continue
        if f.is_symlink():raise ValueError("Attempt history is not a regular file")
        data=json.loads(f.read_text(encoding="utf8"))
        if (data.get("slide")!=slide or data.get("mode")!=mode
            or data.get("attempt")!=n):
            raise ValueError("Attempt receipt changed identity")
        failures.append((n,data.get("status"),
                         data.get("provider_submission_state"),
                         data.get("manual_retry_eligible")))
    if failures and [entry[0] for entry in failures]!=list(range(1,len(failures)+1)):
        raise ValueError("Missing observed attempt in retry chain")
    if success.exists() and (success.is_symlink() or not success.is_file()):
        raise ValueError("Saved successful review is not a regular file")
    if mode=="INDEPENDENT_CHALLENGE":
        prior=q/f"slide_{slide:03d}_initial_review.json"
        if not prior.is_file():return {"status":"BLOCKED_MISSING_INITIAL_REVIEW","dispatch_authorized":False}
    if success.exists():
        status="ALREADY_COMPLETED_NO_RESUBMISSION"
    elif any(e[1]!="FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED" for e in failures):
        status="BLOCKED_UNVERIFIED_ATTEMPT_RECEIPT"
    elif len(failures)==3:status="MAX_THREE_ATTEMPTS_EXHAUSTED"
    elif any(e[2]!="RETURNED_RESPONSE_INVALID" or e[3] is not True
             for e in failures):
        status="BLOCKED_AMBIGUOUS_PROVIDER_REQUEST_NEEDS_RECONCILIATION"
    elif failures:status="EXPLICIT_MANUAL_RETRY_DECISION_REQUIRED"
    else:status="NEW_ATTEMPT_REQUIRES_EXPLICIT_REQUEST"
    return {"status":status,"next_possible_attempt":(len(failures)+1 if status in
                ("NEW_ATTEMPT_REQUIRES_EXPLICIT_REQUEST",
                 "EXPLICIT_MANUAL_RETRY_DECISION_REQUIRED") else None),
            "observed_attempts":len(failures),"dispatch_authorized":False,
            "student_publication_authorized":False}
