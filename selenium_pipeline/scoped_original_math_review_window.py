"""An explicitly authorized *new* math-review window, NEVER reset old attempts.

Separate user-approved scope allows at most three NEW browser submissions,
while binding the original exhausted three-attempt historical queue to an
immutable fingerprint. Code is non-dispatching; no provider fees or timers.
"""
from __future__ import annotations
import hashlib,json,os,re
from pathlib import Path
from .gemini_review_backoff_checkpoint import initialize,inspect,claim_due
from .review_queue_source_audit import inspect_source_bound_queue
from .review_retry_plan import plan_manual_review_attempt
SCHEMA=1

def digest(file:Path)->str:
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()

def historical_evidence(*,queue_root:Path,original_folder:Path,
                        slide:int=1)->dict:
    q,f=Path(queue_root).absolute(),Path(original_folder).absolute()
    report=inspect_source_bound_queue(q)
    raw=json.loads((q/"queue.json").read_text(encoding="utf8"))
    if raw.get("original_source_folder")!=str(f) or type(slide) is not int:
        raise ValueError("Original queue folder identity must match")
    if slide not in [row["slide"] for row in raw["slide_jobs"]]:
        raise ValueError("Original slide not in immutable queue")
    first=q/f"slide_{slide:03d}_initial_review.json"
    if not first.is_file() or first.is_symlink():
        raise ValueError("Real first model review must exist")
    attempts=plan_manual_review_attempt(q,slide=slide,mode="INDEPENDENT_CHALLENGE")
    if attempts["status"]!="MAX_THREE_ATTEMPTS_EXHAUSTED":
        raise ValueError("New review window is ONLY for existing exhausted original scope")
    receipts={}
    for i in range(1,4):
        path=q/f"slide_{slide:03d}_independent_challenge_attempt_{i:02d}.json"
        if not path.is_file() or path.is_symlink():
            raise ValueError("Historical attempt evidence is missing or unsafe")
        data=json.loads(path.read_text(encoding="utf8"))
        if (data.get("status")!="FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED"
            or data.get("slide")!=slide or data.get("attempt")!=i
            or data.get("mode")!="INDEPENDENT_CHALLENGE"):
            raise ValueError("Attempt is not an original quarantined failure")
        receipts[path.name]=digest(path)
    return {"source_sha256":report["source_sha256"],
            "original_utterances":report["original_utterances"],
            "first_review_sha256":digest(first),
            "original_queue_sha256":digest(q/"queue.json"),
            "historical_attempt_receipt_sha256":receipts,
            "historical_attempt_count":3}

def create_window(*,original_folder:Path,queue_root:Path,window_root:Path,
                  approval_reference:str,slide:int=1,now:float|None=None)->dict:
    # Caller must supply a new consent reference for this one academic scope;
    # a previous project's generic automation consent is insufficient.
    if (type(approval_reference) is not str or
        not re.fullmatch(r"USER_APPROVED_NEW_ORIGINAL_REVIEW_\d{8}_[a-z0-9_-]{3,50}",
                         approval_reference)):
        raise ValueError("New academic attempt window requires explicit user approval")
    f,q,w=map(lambda p:Path(p).absolute(),
                (original_folder,queue_root,window_root))
    if (w.exists() or not w.parent.is_dir() or w.parent.is_symlink() or
        w.is_relative_to(f) or w.is_relative_to(q)):
        raise ValueError("Fresh external window folder only")
    original=historical_evidence(queue_root=q,original_folder=f,slide=slide)
    w.mkdir(mode=0o700)
    manifest={
       "schema_version":SCHEMA,"status":"USER_APPROVED_NEW_SCOPED_WINDOW",
       "user_approval_reference":approval_reference,
       "original_folder":str(f),"original_queue_root":str(q),
       "slide":slide,"review_mode":"INDEPENDENT_CHALLENGE",
       "parent_historical":original,
       "max_new_confirmed_submissions":3,
       "new_window_automatic_review_approval":False,
       "student_publication_authorized":False,
       "closed_to_main_original_queue_mutation":True}
    mp=w/"window_manifest.json"
    with mp.open("x",encoding="utf8") as s:
        json.dump(manifest,s,sort_keys=True,indent=2);s.write("\n")
        s.flush();os.fsync(s.fileno())
    name=f"slide_{slide:03d}_independent_challenge_newwindow_{approval_reference[-15:]}"
    # This job is intentionally separate from the original immutable queue.
    # The live dispatcher MUST verify manifest via inspect_window first.
    cp=w/"separate_window_checkpoint.json"
    initialize(checkpoint=cp,original_folder=f,job_id=name,now=now)
    return {"status":"NEW_REVIEW_WINDOW_STAGED_NO_PROVIDER_DISPATCH",
            "manifest":str(mp),"checkpoint":str(cp),
            "original_attempts_preserved":3,
            "new_confirmed_submissions":0,
            "user_review_window_approved":True,
            "student_publication_authorized":False}

def _healthy_external_probe(*,window_root:Path,now:float|None=None)->bool:
    """Fresh, externally recorded SUCCESSFUL longer no-attachment JSON.

    This is a dispatch *precondition*, NEVER academic approval. A model reply
    from another tab, a copied quote, or a short 54-char canary is insufficient.
    """
    import time
    path=Path(window_root).absolute()/"source_transport_health.json"
    if not path.is_file() or path.is_symlink() or path.stat().st_size>9000:
        return False
    try:
        payload=json.loads(path.read_text(encoding="utf8"))
        tick=float(time.time() if now is None else now)
        stamp=payload.get("completed_unix_utc")
        response_digest=payload.get("verified_response_sha256")
        raw_reply=Path(window_root).absolute()/"source_transport_health.response.json"
        if (not raw_reply.is_file() or raw_reply.is_symlink() or
            raw_reply.stat().st_size>4096 or raw_reply.stat().st_size<10):
            return False
        if digest(raw_reply)!=response_digest:
            return False
        if json.loads(raw_reply.read_text(encoding="utf8"))!={"probe":"microgen_source_transport_ok"}:
            return False
        return bool(
            payload.get("status")=="COMPLETE_STRUCTURED_TEXT_ONLY_RESPONSE"
            and payload.get("same_owned_gemini_session") is True
            and payload.get("model_stopped_generating") is True
            and payload.get("exact_expected_json") is True
            and type(payload.get("prompt_characters")) is int
            and 1200<=payload["prompt_characters"]<=3000
            and type(stamp) in (int,float) and 0<=tick-stamp<=1800
            and type(response_digest) is str and len(response_digest)==64
            and all(c in "0123456789abcdef" for c in response_digest))
    except (ValueError,TypeError,OSError,KeyError):
        return False

def inspect_window(*,window_root:Path,now:float|None=None)->dict:
    w=Path(window_root).absolute();mp=w/"window_manifest.json"
    if not mp.is_file() or mp.is_symlink():
        raise ValueError("External review window manifest absent")
    m=json.loads(mp.read_text(encoding="utf8"))
    if (type(m) is not dict or m.get("schema_version")!=SCHEMA
        or m.get("status")!="USER_APPROVED_NEW_SCOPED_WINDOW"
        or m.get("closed_to_main_original_queue_mutation") is not True
        or m.get("student_publication_authorized") is not False
        or m.get("max_new_confirmed_submissions")!=3
        or m.get("review_mode")!="INDEPENDENT_CHALLENGE"):
        raise ValueError("Untrusted new academic scope")
    f,q=Path(m["original_folder"]),Path(m["original_queue_root"])
    current=historical_evidence(queue_root=q,original_folder=f,slide=m["slide"])
    if current!=m.get("parent_historical"):
        raise ValueError("Original review or source evidence changed since approval")
    cp=w/"separate_window_checkpoint.json"
    checkpoint=inspect(checkpoint=cp,original_folder=f,now=now)
    if checkpoint["confirmed_submissions"]>3:
        raise ValueError("New original-source review budget exceeded")
    probe_healthy=_healthy_external_probe(window_root=w,now=now)
    return {"status":checkpoint["status"],
        "live_source_transport_health_verified":probe_healthy,
        "original_historical_attempts_unchanged":3,
        "new_window_confirmed_submissions":checkpoint["confirmed_submissions"],
        "eligible_for_single_authorized_dispatch":
          (checkpoint["eligible_for_single_authorized_dispatch"] and
           probe_healthy),
        "checkpoint_due_without_probe":
          checkpoint["eligible_for_single_authorized_dispatch"],
        "requires_reconciliation":checkpoint["requires_reconciliation"],
        "checkpoint":str(cp),"original_folder":str(f),
        "original_source_sha256":current["source_sha256"],
        "student_publication_authorized":False}

def dispatch_single_approved_window_tick(*,window_root:Path,send_once,
                                         now:float|None=None)->dict:
    """Only allowed send entry point for NEW approval window.

    The original reviewed queue is checked anew before any worker callback.
    No task installed; no provider invoked if probe absent or exhausted.
    """
    if not callable(send_once):
        raise ValueError("Explicit single owned-tab Gemini callback required")
    report=inspect_window(window_root=window_root,now=now)
    if not report["eligible_for_single_authorized_dispatch"]:
        return {"status":"BLOCKED_NO_VERIFIED_SOURCE_TRANSPORT_HEALTH_OR_DUE",
                "model_request_sent":False,"student_publication_authorized":False}
    from .gemini_single_tick_dispatch_boundary import one_authorized_tick
    import time
    return one_authorized_tick(
        checkpoint=Path(report["checkpoint"]),
        original_folder=Path(report["original_folder"]),
        send_once=send_once,
        now=float(time.time() if now is None else now))
