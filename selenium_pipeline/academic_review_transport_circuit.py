"""Evidence-locked finite halt after repeated academic Gemini response failure.

Reuse the ordinary provider-halt principle for original academic reviews:
two distinct source-SHA-locked request checkpoints with uncertain/no accepted
reply suspend NEW requests from the same academic model on this source for a
bounded window. The mechanism NEVER retries an old original utterance, does
not claim a Google server outage, and rechecks every persisted witness.

Only observations from source-review request_state.json with durable global
claim, no accepted model response and explicit no-resend flags qualify.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import time

EVENT_FOLDER=".microgen_academic_transport_health"
WINDOW_SECONDS=3600
THRESHOLD=2
SUSPENSION_SECONDS=1800


class AcademicTransportCircuitError(ValueError):
    pass


def _require(ok, message):
    if not ok:
        raise AcademicTransportCircuitError(message)


def _read(path:Path)->dict:
    _require(path.is_file() and not path.is_symlink(),
             "Missing or unsafe original academic transport evidence")
    obj=json.loads(path.read_text(encoding="utf8"))
    _require(type(obj) is dict,"Academic transport evidence must be an object")
    return obj


def _sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _event_home(*, checkpoint_parent:Path, source_sha:str)->Path:
    checkpoint_parent=Path(checkpoint_parent).absolute()
    _require(checkpoint_parent.is_dir() and
             not checkpoint_parent.is_symlink()
             and type(source_sha) is str
             and re.fullmatch(r"[0-9a-f]{64}",source_sha),
             "Unsafe or absent source-specific academic transport directory")
    root=checkpoint_parent/EVENT_FOLDER
    _require(not root.is_symlink(), "Academic transport health may not be a link")
    return root/source_sha


def _verified_original_failure(*, checkpoint:Path, source_sha:str)->dict:
    checkpoint=Path(checkpoint).absolute()
    state_path=checkpoint/"request_state.json"
    state=_read(state_path)
    identity=state.get("request_fingerprint")
    _require(re.fullmatch(r"[0-9a-f]{64}",str(identity)) is not None
             and state.get("source_sha256")==source_sha
             and state.get("status") in (
                 "SUBMITTED_OR_UNCERTAIN","NO_RESPONSE_UNRESOLVED")
             and state.get("submission_may_have_occurred") is True
             and state.get("can_auto_retry") is False
             and state.get("academic_approval") is False
             and state.get("tts_authorized") is False
             and state.get("student_publication_authorized") is False
             and not (checkpoint/"model_response_identity.json").exists()
             and not (checkpoint/"model_response_untrusted.txt").exists()
             and not (checkpoint.parent/(checkpoint.name.replace(
                     "_checkpoint","")+"_result.json")).exists(),
             "No certified source-owned failed academic reply checkpoint")
    claim=checkpoint/"dispatch_attempted.claim"
    _require(claim.is_file() and not claim.is_symlink()
             and claim.read_text(encoding="utf8").strip()==identity,
             "Original academic submission claim was not retained")
    return {"fingerprint":identity,"state_sha256":_sha(state_path),
            "checkpoint":str(checkpoint)}


def record_original_failure(*, checkpoint:Path, route_receipt:Path,
                            checkpoint_parent:Path, now:float|None=None)->dict:
    """Record a real uncertain academic window, no browser or model action."""
    route=_read(Path(route_receipt).absolute())
    source_sha=route.get("source_sha256")
    _require(route.get("schema_version")==1
             and route.get("selected_academic_model_family") in ("flash","pro")
             and route.get("selected_thinking_level")=="medium"
             and route.get("G2_approved") is False
             and route.get("academic_approval") is False
             and route.get("student_publication_authorized") is False,
             "Unverified academic model selection cannot contribute health")
    original=_verified_original_failure(
        checkpoint=checkpoint,source_sha=source_sha)
    home=_event_home(checkpoint_parent=checkpoint_parent,source_sha=source_sha)
    _require(not home.is_symlink(), "Unsafe source transport-health subfolder")
    home.mkdir(parents=True,exist_ok=True)
    event_path=home/(original["fingerprint"]+".json")
    if event_path.exists():
        return _read_and_verify(event_path)
    instant=float(time.time() if now is None else now)
    _require(instant>=0,"Invalid transport-health observation time")
    record={
        "schema_version":1,"source_sha256":source_sha,
        "academic_model_family":route["selected_academic_model_family"],
        "academic_thinking_level":"medium",
        "checkpoint":original["checkpoint"],
        "request_fingerprint":original["fingerprint"],
        "request_state_sha256":original["state_sha256"],
        "observed_unix":instant,
        "outcome":"NO_ACCEPTED_ACADEMIC_MODEL_RESPONSE",
        "model_send_may_have_occurred":True,
        "provider_server_outage_proven":False,
        "old_original_request_may_be_resent":False,
        "academic_approval":False,"G2_approved":False,
        "student_publication_authorized":False,
    }
    payload=json.dumps(record,sort_keys=True,indent=2)+"\n"
    try:
        with event_path.open("x",encoding="utf8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
    except FileExistsError:
        return _read_and_verify(event_path)
    return record


def _read_and_verify(path:Path)->dict:
    event=_read(path)
    fingerprint=event.get("request_fingerprint")
    _require(path.stem==fingerprint
             and event.get("schema_version")==1
             and event.get("outcome")==
                "NO_ACCEPTED_ACADEMIC_MODEL_RESPONSE"
             and event.get("academic_model_family") in ("flash","pro")
             and event.get("academic_thinking_level")=="medium"
             and event.get("model_send_may_have_occurred") is True
             and event.get("provider_server_outage_proven") is False
             and event.get("old_original_request_may_be_resent") is False
             and event.get("academic_approval") is False
             and event.get("G2_approved") is False
             and event.get("student_publication_authorized") is False
             and type(event.get("observed_unix")) in (int,float)
             and path.parent.name==event.get("source_sha256"),
             "Foreign/tampered academic provider health event")
    # Event records may only reference source checkpoint windows under
    # the same authorized Windows checkpoint parent, never arbitrary files.
    original_checkpoint=Path(event["checkpoint"]).absolute()
    _require(original_checkpoint.is_relative_to(path.parents[2]) and
             not original_checkpoint.is_symlink(),
             "Academic transport witness outside its checkpoint parent")
    witness=_verified_original_failure(
        checkpoint=original_checkpoint,
        source_sha=event["source_sha256"])
    _require(witness["fingerprint"]==fingerprint
             and witness["state_sha256"]==event["request_state_sha256"],
             "Original source-locked transport evidence changed")
    return event


def inspect(*, checkpoint_parent:Path, source_sha:str, family:str,
            now:float|None=None)->dict:
    """Fail-closed read-only circuit; no Send, API, login or time-based task."""
    home=_event_home(checkpoint_parent=checkpoint_parent,source_sha=source_sha)
    _require(family in ("flash","pro"),"Unknown contracted academic model")
    instant=float(time.time() if now is None else now)
    _require(instant>=0,"Invalid provider circuit clock")
    entries=[]
    if home.exists():
        _require(home.is_dir() and not home.is_symlink(),
                 "Unsafe academic transport health index")
        paths=list(home.iterdir())
        _require(len(paths)<=200,"Academic source transport ledger needs audit")
        for path in paths:
            _require(path.suffix==".json" and path.is_file()
                     and not path.is_symlink(),
                     "Unexpected academic source transport evidence")
            event=_read_and_verify(path)
            if event["academic_model_family"]==family:
                _require(event["observed_unix"]<=instant,
                         "Academic response failure dated in future")
                entries.append(event)
    entries.sort(key=lambda x:x["observed_unix"])
    # CRITICAL recurrence fix: the previous implementation deleted failures
    # from the *decision* after 3600 s and reopened source-bound Sends
    # merely because 1800 s elapsed. Gemini's model responsiveness was never
    # re-established, so a later campaign would consume further original
    # claims on precisely the same failed transport. Retain the witnessed
    # historical pair forever. Cooldown enables a SOURCE-FREE diagnostic,
    # never fresh original PDF submissions by itself.
    tripped=any(
        0 <= entries[i]["observed_unix"]-entries[i-1]["observed_unix"]
           <=WINDOW_SECONDS
        for i in range(1,len(entries))
    )
    cooldown_due=False
    recovered=False
    recovery_observed=None
    if tripped:
        last_failure=entries[-1]["observed_unix"]
        cooldown_due=instant-last_failure>=SUSPENSION_SECONDS
        from .academic_provider_requalification import latest_success
        evidence=latest_success(
            checkpoint_parent=checkpoint_parent,source_sha=source_sha,
            family=family,after_unix=last_failure,now=instant)
        recovered=evidence is not None
        if recovered:
            recovery_observed=evidence["observed_unix"]
    active=tripped and not recovered
    status=(
        "ACADEMIC_GEMINI_REQUALIFIED_NEW_SOURCE_SEND_ALLOWED"
        if tripped and recovered else
        "ACADEMIC_GEMINI_SOURCE_FREE_REQUALIFICATION_REQUIRED"
        if active and cooldown_due else
        "ACADEMIC_GEMINI_RESPONSES_TEMPORARILY_SUSPENDED"
        if active else "NO_ACTIVE_ACADEMIC_RESPONSE_HEALTH_SUSPENSION")
    return {
        "schema_version":2,
        "status":status,
        "source_sha256":source_sha,"model_family":family,
        "distinct_failed_requests":len(entries),
        "persistent_unrequalified_failure_pair":bool(active),
        "source_free_health_probe_due":bool(active and cooldown_due),
        "independent_source_free_reply_reverified":bool(recovered),
        "recovery_observed_unix":recovery_observed,
        "automatic_new_academic_model_send_allowed":not active,
        "provider_outage_proven":False,
        "old_request_retry_authorized":False,
        "G2_approved":False,
        "student_publication_authorized":False,
    }
