"""Read-only evidence-locked health gate before any NEW academic slide Send.

A claimed no-response Gemini review is never retried. Before consuming the
NEXT fresh source slide, require an independently attributable source-free
response from the same verified full-model family AFTER the most recent
unreconciled Send. A single per-source/model/day nonce probe is allowed when
the caller opts into autonomous execution. This does not prove provider outage
or certify a textbook statement; it merely establishes new response ability.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import time

from .figure_source_identity import require


@contextmanager
def _full_family_scope(family: str):
    require(family in ("flash", "pro"),
            "Source reviewer cannot use Flash-Lite or unknown Gemini model")
    names=("MICROGEN_ACTIVE_GENERATION_STAGE","MICROGEN_GEMINI_UI_MODE",
           "MICROGEN_LLM_MODEL","MICROGEN_GEMINI_THINKING_LEVEL",
           "MICROGEN_MODEL_ROUTE_REASON","MICROGEN_MODEL_ROUTE_REQUESTED",
           "MICROGEN_MODEL_ROUTE_OFFERED",
           "MICROGEN_ACADEMIC_SOURCE_MODEL_REQUALIFICATION_PENDING")
    saved={n:os.environ.get(n) for n in names}
    try:
        os.environ["MICROGEN_ACTIVE_GENERATION_STAGE"]="academic_review"
        os.environ["MICROGEN_GEMINI_UI_MODE"]=family
        os.environ["MICROGEN_LLM_MODEL"]=(
            "gemini-3.8-flash" if family=="flash" else "gemini-3.1-pro")
        from .gemini_dynamic_task_router import task_policy
        os.environ["MICROGEN_GEMINI_THINKING_LEVEL"]=(
            task_policy("academic_review")["preferred_thinking"])
        yield
    finally:
        for name,value in saved.items():
            if value is None: os.environ.pop(name,None)
            else: os.environ[name]=value


def unreconciled_source_send_claims(*,queue_root: Path, source_sha: str) -> list[dict]:
    """Derive last unsafe claimed Send from its immutable request state."""
    q=Path(queue_root).absolute()
    require(q.is_dir() and not q.is_symlink()
            and type(source_sha) is str
            and re.fullmatch(r"[0-9a-f]{64}",source_sha) is not None,
            "Original source review/sha required")
    found=[]
    for entry in sorted(q.glob("slide_*_attempt_*_request")):
        if not (entry.is_dir() and not entry.is_symlink()
                and re.fullmatch(
                    r"slide_[0-9]{3}_(?:initial_review|independent_challenge)_attempt_0[1-3]_request",
                    entry.name)):
            raise ValueError("Unsafe academic checkpoint matching potential source Send")
        state_path=entry/"request_state.json"
        require(state_path.is_file() and not state_path.is_symlink(),
                "Claimed review needs original immutable model state")
        state=json.loads(state_path.read_text(encoding="utf8"))
        require(state.get("source_sha256")==source_sha,
                "Foreign original source cannot contribute provider health")
        if state.get("status") not in (
            "SUBMITTED_OR_UNCERTAIN","NO_RESPONSE_UNRESOLVED"):
            continue
        claim=entry/"dispatch_attempted.claim"
        require(claim.is_file() and not claim.is_symlink()
                and claim.read_text(encoding="utf8").strip() ==
                    state.get("request_fingerprint")
                and state.get("submission_may_have_occurred") is True
                and state.get("can_auto_retry") is False
                and state.get("student_publication_authorized") is False,
                "Unaccounted academic Send claim or forged no-response state")
        require(not (entry/"model_response_identity.json").exists()
                and not (entry/"model_response_untrusted.txt").exists(),
                "An observed response must be reconciled, not treated as no-response")
        found.append({
            "request_fingerprint":state["request_fingerprint"],
            "checkpoint_name":entry.name,
            "last_original_unsafe_claim_unix":state_path.stat().st_mtime,
        })
    return found


def check(*,queue_root:Path, checkpoint_parent:Path,source_sha:str,
          family:str,execute_source_free_probe:bool=False,
          probe_fn=None, latest_success_fn=None, clock=None) -> dict:
    """No source/PDF/model prompt is sent unless a fresh source-free health response exists."""
    from .academic_provider_requalification import latest_success, probe_once
    from .academic_incident_response_health import (
        incident_identity, latest_incident_success, probe_incident_once,
    )
    require(family in ("flash","pro"),"Original Gemini family not independently known")
    clock = clock or time.time
    now=float(clock())
    claims=unreconciled_source_send_claims(
        queue_root=queue_root,source_sha=source_sha)
    if not claims:
        return {
            "status":"NO_UNRECONCILED_GEMINI_SOURCE_SEND",
            "original_unattributed_requests":0,
            "new_source_review_send_allowed":True,
            "source_free_new_requests":0,
            "existing_claims_resent":False,
        }
    newest=max(claims,key=lambda x:x["last_original_unsafe_claim_unix"])
    last=newest["last_original_unsafe_claim_unix"]
    incident=incident_identity(newest,source_sha=source_sha,family=family)
    require(last<=now+3,"Source review claim timestamp from future")
    # This stronger incident-specific check requires Gemini to read BOTH
    # synthetic PDF attachments and return distinct hidden file tokens.
    # Unlike the older text-only canary it exercises the original browser
    # document-upload + response route, without uploading a textbook.
    if len(claims)>=2:
        initial_slides=sorted({
            int(m.group(1)) for x in claims
            if (m:=re.fullmatch(
                r"slide_([0-9]{3})_initial_review_attempt_0[1-3]_request",
                x["checkpoint_name"])) is not None
        })
        if len(initial_slides)>=2:
            from .academic_dual_pdf_capability import qualifying_proof
            enhanced=qualifying_proof(
                queue_root=queue_root,checkpoint_parent=checkpoint_parent,
                source_sha=source_sha,prior_slides=initial_slides,
                family=family,now=now)
            if enhanced is not None:
                return {
                    "status":"NEW_SOURCE_MODALITY_PDF_CAPABILITY_VERIFIED",
                    "original_unattributed_requests":len(claims),
                    "new_source_review_send_allowed":True,
                    "source_free_new_requests":0,
                    "existing_claims_resent":False,
                    "source_modality_proof_incident":
                        enhanced["incident_sha256"],
                    "original_source_uploaded":False,
                }
    lookup=latest_success if latest_success_fn is None else latest_success_fn
    historical=lookup(checkpoint_parent=checkpoint_parent,source_sha=source_sha,
                      family=family,after_unix=last,now=now)
    if historical is not None:
        require(historical.get("status") ==
                "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED"
                and historical.get("source_sha256")==source_sha
                and historical.get("model_family")==family
                and last<historical["observed_unix"]<=now,
                "Untrusted previous source-free health result")
        return {
            "status":"NEW_INDEPENDENT_SOURCE_FREE_RESPONSE_REVERIFIED",
            "original_unattributed_requests":len(claims),
            "new_source_review_send_allowed":True,
            "source_free_new_requests":0,
            "existing_claims_resent":False,
        }
    # A past successful probe does not cover a subsequent uncertain model
    # submission. Reuse a separately immutable, source-free response bound to
    # the newest incident before attempting any new diagnostic Send.
    incident_proof=latest_incident_success(
        checkpoint_parent=checkpoint_parent, source_sha=source_sha,
        family=family, incident=incident, after_unix=last, now=now)
    if incident_proof is not None:
        return {
            "status":"NEW_INCIDENT_SOURCE_FREE_RESPONSE_REVERIFIED",
            "original_unattributed_requests":len(claims),
            "new_source_review_send_allowed":True,
            "source_free_new_requests":0,
            "existing_claims_resent":False,
            "incident_sha256":incident,
            "health_proof_scope":"LATEST_UNCERTAIN_SOURCE_INCIDENT",
        }
    if not execute_source_free_probe:
        return {
            "status":"G2_FRESH_REVIEW_DEFERRED_PENDING_SOURCE_FREE_PROBE",
            "original_unattributed_requests":len(claims),
            "new_source_review_send_allowed":False,
            "source_free_new_requests":0,
            "existing_claims_resent":False,
        }
    probe=probe_once if probe_fn is None else probe_fn
    with _full_family_scope(family):
        outcome=probe(checkpoint_parent=checkpoint_parent,source_sha=source_sha,
                      family=family)
        # The legacy once-daily slot may have succeeded *before* the latest
        # uncertain academic Send. Requalify a distinct incident with a new
        # bounded nonce, never replaying the old diagnostic or source request.
        # An immediately failed NEW legacy probe must not trigger another Send.
        if (probe_fn is None
                and (outcome.get("reused_immutable_probe") is True or
                     outcome.get("status") ==
                         "PRIOR_SOURCE_FREE_PROBE_UNCERTAIN_NO_RESEND")
                and not (outcome.get("status") ==
                         "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED"
                         and outcome.get("observed_unix",0) > last)):
            outcome=probe_incident_once(
                checkpoint_parent=checkpoint_parent,source_sha=source_sha,
                family=family,incident=incident,after_unix=last,now=now)
    safe=(outcome.get("status") ==
          "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED"
          and outcome.get("source_sha256")==source_sha
          and outcome.get("model_family")==family
          and last<outcome.get("observed_unix",0)<=float(clock())+3
          and outcome.get("no_original_source_uploaded") is True
          and outcome.get("gemini_new_user_turn_verified") is True)
    return {
        "status":("G2_FRESH_REVIEW_CAPABILITY_REQUALIFIED"
                  if safe else "G2_FRESH_REVIEW_DEFERRED_UNHEALTHY_OR_UNATTRIBUTED"),
        "original_unattributed_requests":len(claims),
        "new_source_review_send_allowed":bool(safe),
        "source_free_new_requests":outcome.get("new_provider_requests",0),
        "existing_claims_resent":False,
        "source_free_result_status":outcome.get("status"),
        "health_proof_scope":("LATEST_UNCERTAIN_SOURCE_INCIDENT"
                              if outcome.get("incident_sha256")==incident
                              else "LEGACY_SOURCE_MODEL_DAILY"),
        "incident_sha256":incident,
    }
