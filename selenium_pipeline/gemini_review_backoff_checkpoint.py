"""Durable, no-dispatch Gemini academic review retry state machine.

It never sends a prompt, launches a browser, installs a schedule, or assumes
a vanished in-flight request is terminal. Original review/asset gates still
must independently validate any candidate model answer.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

STATUSES={"READY","CLAIMED_NOT_SENT","IN_FLIGHT","WAITING",
          "RECONCILIATION_REQUIRED","RESPONSE_CAPTURED_UNVERIFIED","EXHAUSTED"}
MAX_CONFIRMED_SUBMISSIONS=3
MAX_UNSENT_FAILURES=3
BASE_BACKOFF_SECONDS=(300,900,2700)
MAX_BACKOFF_SECONDS=14400
SCHEMA_VERSION=1

def _sha(path: Path)->str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        while chunk:=handle.read(1024*1024):digest.update(chunk)
    return digest.hexdigest()

def _origins(folder: Path)->dict:
    folder=folder.absolute()
    if not folder.is_dir():
        raise ValueError("Original source directory unavailable")
    files={}
    for key in ("source.pdf","slides.pdf","script.txt"):
        file=folder/key
        if not file.is_file() or file.is_symlink():
            raise ValueError("Original academic source missing or symlinked")
        files[key]=_sha(file)
    return files

def _check_destination(checkpoint:Path, original_folder:Path)->None:
    p=checkpoint.absolute()
    if (checkpoint.suffix!=".json" or not p.parent.is_dir()
        or p.is_symlink() or p.is_relative_to(original_folder.absolute())):
        raise ValueError("Checkpoint must be external AppData-style JSON, never an original")
    # File's parent cannot be a symlinked path redirected into originals.
    if p.resolve().is_relative_to(original_folder.resolve()):
        raise ValueError("Checkpoint location resolves inside original source")

@contextmanager
def _locked(file:Path):
    lock=Path(str(file)+".lock")
    # No stale lock stealing. Owner must investigate crashed worker first.
    fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        with os.fdopen(fd,"w",encoding="ascii") as handle:
            handle.write(str(os.getpid())+"\n")
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        # Only this lexical owner may remove the acquired lock.
        try:lock.unlink()
        except FileNotFoundError:pass


def _validate_checkpoint_invariants(state:dict)->None:
    """Stop impossible state transitions before scheduling or mutation."""
    status=state.get("status")
    claim=state.get("active_claim")
    next_due=state.get("next_due_unix_utc")
    if (type(state.get("job_id")) is not str or
        not state["job_id"].startswith("slide_") or
        type(state.get("history")) is not list or
        len(state["history"])>1000 or
        any(type(x) is not dict or type(x.get("event")) is not str
            for x in state["history"])):
        raise ValueError("Untrusted checkpoint identity/history")
    pending=status in ("CLAIMED_NOT_SENT","IN_FLIGHT","RECONCILIATION_REQUIRED")
    if pending:
        if type(claim) is not str or len(claim)!=32 or not all(
                c in "0123456789abcdef" for c in claim):
            raise ValueError("Pending Gemini checkpoint has no valid claim owner")
        if next_due is not None:
            raise ValueError("Pending Gemini may never carry a due resend time")
    else:
        if claim is not None:
            raise ValueError("Completed/waiting Gemini checkpoint retains a claim")
        if status in ("READY","WAITING"):
            if type(next_due) not in (float,int) or not 0<=next_due<=1e11:
                raise ValueError("Ready Gemini job lacks usable UTC due timestamp")
        elif next_due is not None:
            raise ValueError("Terminal checkpoint cannot be scheduled for retry")
    if (status=="EXHAUSTED" and
        state["confirmed_submissions"]<MAX_CONFIRMED_SUBMISSIONS and
        state["unsent_failures"]<MAX_UNSENT_FAILURES and
        not state.get("queue_root")):
        raise ValueError("Exhaustion lacks confirmed quota evidence")
    if status=="IN_FLIGHT" and state["confirmed_submissions"]<1:
        raise ValueError("In-flight Gemini has no confirmed submission")


def _read(file:Path,folder:Path)->dict:
    _check_destination(file,folder)
    payload=json.loads(file.read_text(encoding="utf8"))
    if (type(payload) is not dict or payload.get("schema_version")!=SCHEMA_VERSION
        or payload.get("original_folder")!=str(folder.absolute())
        or payload.get("status") not in STATUSES
        or type(payload.get("confirmed_submissions")) is not int
        or not 0<=payload["confirmed_submissions"]<=MAX_CONFIRMED_SUBMISSIONS
        or type(payload.get("unsent_failures")) is not int
        or not 0<=payload["unsent_failures"]<=MAX_UNSENT_FAILURES
        or payload.get("student_publication_authorized") is not False
        or payload.get("original_sha256")!=_origins(folder)):
        raise ValueError("Untrusted, stale or tampered Gemini review checkpoint")
    _validate_checkpoint_invariants(payload)
    if payload.get("queue_root") is not None:
        checked=_prior_review_queue(queue_root=Path(payload["queue_root"]),
                                     original_folder=folder,
                                     job_id=payload["job_id"])
        if checked.get("observed_attempts",0)>payload["confirmed_submissions"]:
            raise ValueError("Original review queue has newer attempts; reconcile before retry")
        if (checked["status"]=="ALREADY_COMPLETED_NO_RESUBMISSION" and
            payload["status"] not in ("RESPONSE_CAPTURED_UNVERIFIED","RECONCILIATION_REQUIRED")):
            raise ValueError("Original review completed outside checkpoint; reconcile")
    return payload

def _save(file:Path,state:dict)->None:
    # Atomic checkpoint only in a new external work directory; never originals.
    temp=file.with_name(file.name+"."+uuid.uuid4().hex+".pending")
    try:
        with temp.open("x",encoding="utf8") as stream:
            json.dump(state,stream,sort_keys=True,indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp,file)
    finally:
        if temp.exists():temp.unlink()

def _prior_review_queue(*,queue_root:Path,original_folder:Path,job_id:str)->dict:
    """Bind immutable academic attempt quota; never turn attempt #4 into #1."""
    import re
    from .review_retry_plan import plan_manual_review_attempt
    q=Path(queue_root).absolute()
    if not q.is_dir() or q.is_symlink():
        raise ValueError("Original immutable review queue unavailable")
    plan=json.loads((q/"queue.json").read_text(encoding="utf8"))
    if plan.get("original_source_folder")!=str(original_folder.absolute()):
        raise ValueError("Review queue not bound to these academic originals")
    match=re.fullmatch(r"slide_(\d{3})_(initial_review|independent_challenge)",job_id)
    if not match:
        raise ValueError("Academic checkpoint needs exact slide and review mode")
    return plan_manual_review_attempt(q,slide=int(match[1]),
        mode=match[2].upper())

def initialize(*,checkpoint:Path,original_folder:Path,job_id:str,
               queue_root:Path|None=None,now:float|None=None)->dict:
    checkpoint,original_folder=Path(checkpoint).absolute(),Path(original_folder).absolute()
    _check_destination(checkpoint,original_folder)
    if type(job_id) is not str or not job_id.startswith("slide_") or len(job_id)>90:
        raise ValueError("Stable original review stage identity required")
    instant=float(time.time() if now is None else now)
    import re
    academic=bool(re.fullmatch(r"slide_\d{3}_(?:initial_review|independent_challenge)",job_id))
    if academic and queue_root is None:
        raise ValueError("Academic review must preserve original three-attempt quota")
    prior=(_prior_review_queue(queue_root=queue_root,original_folder=original_folder,
                               job_id=job_id) if academic else None)
    if prior and prior["status"]=="MAX_THREE_ATTEMPTS_EXHAUSTED":
        initial_status="EXHAUSTED"
    elif prior and prior["status"]=="ALREADY_COMPLETED_NO_RESUBMISSION":
        initial_status="RESPONSE_CAPTURED_UNVERIFIED"
    elif prior and prior["status"] not in (
            "EXPLICIT_MANUAL_RETRY_DECISION_REQUIRED",
            "NEW_ATTEMPT_REQUIRES_EXPLICIT_REQUEST"):
        initial_status="RECONCILIATION_REQUIRED"
    else:
        initial_status="READY"
    state={"schema_version":SCHEMA_VERSION,"job_id":job_id,
           "original_folder":str(original_folder),
           "original_sha256":_origins(original_folder),
           "status":initial_status,
           "confirmed_submissions":prior["observed_attempts"] if prior and
                                    "observed_attempts" in prior else 0,
           "unsent_failures":0,
           "queue_root":str(Path(queue_root).absolute()) if academic else None,
           "next_due_unix_utc":instant if initial_status=="READY" else None,
           "active_claim":None,
           "history":[],"student_publication_authorized":False}
    # Create exclusively. Do not truncate an existing claim or receipts.
    with _locked(checkpoint):
        with checkpoint.open("x",encoding="utf8") as stream:
            json.dump(state,stream,sort_keys=True,indent=2)
            stream.write("\n");stream.flush();os.fsync(stream.fileno())
    return state

def inspect(*,checkpoint:Path,original_folder:Path, now:float|None=None)->dict:
    state=_read(Path(checkpoint),Path(original_folder))
    at=float(time.time() if now is None else now)
    status=state["status"]
    eligible=(status in ("READY","WAITING")
              and at>=state["next_due_unix_utc"]
              and state["confirmed_submissions"]<MAX_CONFIRMED_SUBMISSIONS
              and state["unsent_failures"]<MAX_UNSENT_FAILURES)
    return {"status":status,"job_id":state["job_id"],
            "confirmed_submissions":state["confirmed_submissions"],
            "unsent_failures":state["unsent_failures"],
            "next_due_unix_utc":state["next_due_unix_utc"],
            "eligible_for_single_authorized_dispatch":eligible,
            "requires_reconciliation":status in ("CLAIMED_NOT_SENT","IN_FLIGHT",
                                                   "RECONCILIATION_REQUIRED"),
            "student_publication_authorized":False}

def _transition(*,checkpoint:Path,original_folder:Path,modify):
    checkpoint,original_folder=Path(checkpoint),Path(original_folder)
    with _locked(checkpoint):
        state=_read(checkpoint,original_folder)
        result=modify(state)
        _save(checkpoint,state)
    return result

def claim_due(*,checkpoint:Path,original_folder:Path, now:float|None=None)->str|None:
    at=float(time.time() if now is None else now)
    def change(state):
        if (state["status"] not in ("READY","WAITING")
            or state["next_due_unix_utc"]>at
            or state["confirmed_submissions"]>=MAX_CONFIRMED_SUBMISSIONS
            or state["unsent_failures"]>=MAX_UNSENT_FAILURES):
            return None
        nonce=uuid.uuid4().hex
        state["status"]="CLAIMED_NOT_SENT"
        state["next_due_unix_utc"]=None
        state["active_claim"]=nonce
        state["history"].append({"event":"RESERVED_NO_MODEL_SUBMISSION",
                                 "at":at,"claim":nonce})
        return nonce
    return _transition(checkpoint=checkpoint,original_folder=original_folder,modify=change)

def _require_active(state:dict,claim:str,required:str):
    if (state["status"]!=required or type(claim) is not str or
        not claim or state["active_claim"]!=claim):
        raise ValueError("Only current owned request may update checkpoint")

def _delay(job_id:str,n:int,retry_after_s:float|None)->float:
    floor=BASE_BACKOFF_SECONDS[min(max(0,n-1),len(BASE_BACKOFF_SECONDS)-1)]
    # Deterministic stagger (0 to 20%) prevents synchronized thundering herd.
    stagger=int(hashlib.sha256(f"{job_id}:{n}".encode()).hexdigest()[:2],16)/255*.20
    delay=floor*(1+stagger)
    delay=min(MAX_BACKOFF_SECONDS,delay)
    if retry_after_s is not None:
        if not 0<=float(retry_after_s)<=86400:raise ValueError("Unsafe Retry-After")
        # Explicit provider back-off must not be shortened by local cap.
        delay=max(delay,float(retry_after_s))
    return delay

def unsent(*,checkpoint:Path,original_folder:Path,claim:str,
           reason:str,now:float|None=None)->dict:
    if reason not in ("VERIFIED_HIDDEN_SEND","VERIFIED_NO_SUBMISSION",
                      "VERIFIED_COMPOSER_NOT_READY"):
        raise ValueError("Only proven no-send outcomes can avoid attempt count")
    at=float(time.time() if now is None else now)
    def change(s):
        _require_active(s,claim,"CLAIMED_NOT_SENT")
        s["unsent_failures"]+=1
        s["status"]=("EXHAUSTED" if s["unsent_failures"]>=MAX_UNSENT_FAILURES
                     else "WAITING")
        s["next_due_unix_utc"]=(at+_delay(s["job_id"],s["unsent_failures"],None)
                               if s["status"]=="WAITING" else None)
        s["active_claim"]=None
        s["history"].append({"event":"PROVEN_UNSENT","at":at,"reason":reason})
        return inspect_simple(s)
    return _transition(checkpoint=checkpoint,original_folder=original_folder,modify=change)

def submitted(*,checkpoint:Path,original_folder:Path,claim:str,
              user_turn_created:bool,composer_cleared:bool,
              now:float|None=None)->dict:
    if user_turn_created is not True or composer_cleared is not True:
        raise ValueError("Submission requires positive two-part user-turn evidence")
    at=float(time.time() if now is None else now)
    def change(s):
        _require_active(s,claim,"CLAIMED_NOT_SENT")
        s["confirmed_submissions"]+=1
        s["status"]="IN_FLIGHT"
        s["history"].append({"event":"CONFIRMED_MODEL_SUBMISSION",
                             "at":at,"attempt":s["confirmed_submissions"]})
        return inspect_simple(s)
    return _transition(checkpoint=checkpoint,original_folder=original_folder,modify=change)

def ambiguous(*,checkpoint:Path,original_folder:Path,claim:str,
              now:float|None=None)->dict:
    at=float(time.time() if now is None else now)
    def change(s):
        if s["status"] not in ("CLAIMED_NOT_SENT","IN_FLIGHT"):
            raise ValueError("Only an unresolved live claim can become ambiguous")
        if s["active_claim"]!=claim:raise ValueError("Wrong owner")
        s["status"]="RECONCILIATION_REQUIRED"
        s["next_due_unix_utc"]=None
        s["history"].append({"event":"UNKNOWN_OUTCOME_NO_AUTO_RETRY","at":at})
        return inspect_simple(s)
    return _transition(checkpoint=checkpoint,original_folder=original_folder,modify=change)

def terminal_failure(*,checkpoint:Path,original_folder:Path,claim:str,
                     original_tab_terminal_verified:bool,
                     failure:str,proof_sha256:str,
                     retry_after_s:float|None=None,
                     now:float|None=None)->dict:
    if (original_tab_terminal_verified is not True or
        failure not in ("SERVER_BUSY_429","SERVER_UNAVAILABLE_503",
                        "VERIFIED_TERMINAL_EMPTY","VERIFIED_TERMINAL_ERROR")
        or type(proof_sha256) is not str or len(proof_sha256)!=64
        or any(c not in "0123456789abcdef" for c in proof_sha256)):
        raise ValueError("Need verified terminal evidence, not inactivity or timeouts")
    at=float(time.time() if now is None else now)
    def change(s):
        _require_active(s,claim,"IN_FLIGHT")
        s["status"]=("EXHAUSTED" if s["confirmed_submissions"]>=MAX_CONFIRMED_SUBMISSIONS
                     else "WAITING")
        s["next_due_unix_utc"]=(at+_delay(s["job_id"],s["confirmed_submissions"],
                                          retry_after_s)
                               if s["status"]=="WAITING" else None)
        s["active_claim"]=None
        s["history"].append({"event":"TERMINAL_FAILURE_PROVEN","at":at,
                             "category":failure,"evidence_sha256":proof_sha256})
        return inspect_simple(s)
    return _transition(checkpoint=checkpoint,original_folder=original_folder,modify=change)

def captured_unreviewed(*,checkpoint:Path,original_folder:Path,claim:str,
                        response_receipt:Path,now:float|None=None)->dict:
    """Stop model retries once real response exists; never certify its mathematics."""
    receipt=Path(response_receipt).absolute()
    folder=Path(original_folder).absolute()
    if (not receipt.is_file() or receipt.is_symlink()
        or receipt.is_relative_to(folder) or
        receipt.suffix not in (".json",".txt")
        or receipt.stat().st_size==0):
        raise ValueError("Actual external complete-response receipt is mandatory")
    receipt_digest=_sha(receipt)
    at=float(time.time() if now is None else now)
    def change(s):
        _require_active(s,claim,"IN_FLIGHT")
        s["status"]="RESPONSE_CAPTURED_UNVERIFIED"
        s["next_due_unix_utc"]=None
        s["active_claim"]=None
        s["history"].append({"event":"RESPONSE_CAPTURED_SOURCE_MATH_UNVERIFIED",
                             "at":at,"receipt_sha256":receipt_digest})
        return inspect_simple(s)
    return _transition(checkpoint=checkpoint,original_folder=original_folder,modify=change)


def inspect_simple(state:dict)->dict:
    return {"status":state["status"],
            "confirmed_submissions":state["confirmed_submissions"],
            "unsent_failures":state["unsent_failures"],
            "next_due_unix_utc":state["next_due_unix_utc"],
            "student_publication_authorized":False}
