"""v6.1 critical-path recovery evidence gate for PDF-dependent G2.

Support-work success is deliberately orthogonal to original-operation recovery.
This gate is used by the normal G2 forward controller; it never submits
providers, assumes an existing Send is repeatable, changes science approval,
or authorizes paid TTS/publication.

Positive evidence arguments MUST originate from separately verified, owned,
source-bound and persisted receipts; never pass raw model output or UI flags.
"""
from __future__ import annotations

import re


STATES=frozenset({
    "BLOCKED_EXTERNAL_DEPENDENCY",
    "LIVE_CAPABILITY_VERIFIED",
    "ORIGINAL_OPERATION_RECOVERED",
    "NEXT_MILESTONE_ADVANCED",
})


def pdf_critical_path_verdict(
    *, source_sha256:str, original_accepted:int, original_total:int,
    supporting_work_completed:bool=False,
    verified_modality_receipt:dict|None=None,
    accepted_original_operation_receipt:dict|None=None,
    next_milestone_receipt:dict|None=None,
)->dict:
    """Classify *evidence*, not desired progress or a registry label.

    LIVE_CAPABILITY_VERIFIED needs the exact source-family bound, externally
    challenge-verified dual-PDF receipt. Original operation recovery additionally
    needs a distinct accepted source-review receipt with a measurable increase
    from before that operation. Advancement then needs its own source-bound
    downstream journal receipt. No field alone promotes the primary blocker.
    """
    if (type(source_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}",source_sha256) is None
            or type(original_accepted) is not int
            or type(original_total) is not int
            or not 0<=original_accepted<=original_total<=100_000
            or type(supporting_work_completed) is not bool):
        raise ValueError("Invalid source identity or original QA count")

    if verified_modality_receipt is None:
        if accepted_original_operation_receipt is not None or next_milestone_receipt is not None:
            raise ValueError("Cannot claim original PDF recovery without live modality proof")
        state="BLOCKED_EXTERNAL_DEPENDENCY"
    else:
        proof=verified_modality_receipt
        if (type(proof) is not dict
                or proof.get("status")!="DUAL_SYNTHETIC_PDF_RESPONSE_VERIFIED"
                or proof.get("source_sha256")!=source_sha256
                or proof.get("new_source_review_send_allowed") is not True
                or proof.get("gemini_new_user_turn_verified") is not True
                or proof.get("send_registration_status") not in {
                    "NEW_USER_TURN_AND_COMPOSER_CLEARED",
                    "NEW_MODEL_RESPONSE_AND_COMPOSER_CLEARED",
                    "NEW_CONVERSATION_ROUTE_AND_COMPOSER_CLEARED",
                }
                or type(proof.get("incident_sha256")) is not str
                or re.fullmatch(r"[0-9a-f]{64}",proof["incident_sha256"]) is None
                or type(proof.get("claim_sha256")) is not str
                or re.fullmatch(r"[0-9a-f]{64}",proof["claim_sha256"]) is None
                or type(proof.get("model_response_json")) is not dict
                or set(proof["model_response_json"])!={"probe","a","b"}
                or not all(type(proof["model_response_json"][k]) is str
                    for k in ("probe","a","b"))
                or len(proof["model_response_json"]["a"])!=18
                or len(proof["model_response_json"]["b"])!=18
                or proof["model_response_json"]["a"]==
                    proof["model_response_json"]["b"]
                or proof.get("original_source_uploaded") is not False
                or proof.get("academic_approval") is not False):
            raise ValueError("PDF capability evidence is not independently qualified")
        state="LIVE_CAPABILITY_VERIFIED"
        if accepted_original_operation_receipt is not None:
            science=accepted_original_operation_receipt
            if (type(science) is not dict
                    or science.get("status")!="ORIGINAL_SOURCE_TWO_PASS_REVIEW_ACCEPTED"
                    or science.get("source_sha256")!=source_sha256
                    or science.get("pdf_incident_sha256")!=proof["incident_sha256"]
                    or type(science.get("accepted_before")) is not int
                    or type(science.get("accepted_after")) is not int
                    or science["accepted_before"]!=original_accepted
                    or not original_accepted<science["accepted_after"]<=original_total
                    or type(science.get("verified_receipt_sha256")) is not str
                    or re.fullmatch(r"[0-9a-f]{64}",science["verified_receipt_sha256"]) is None):
                raise ValueError("Original PDF source review has not been accepted")
            state="ORIGINAL_OPERATION_RECOVERED"
            if next_milestone_receipt is not None:
                next_stage=next_milestone_receipt
                if (type(next_stage) is not dict
                        or next_stage.get("status")!="NEXT_ELIGIBLE_MILESTONE_ACTUALLY_ENTERED"
                        or next_stage.get("source_sha256")!=source_sha256
                        or next_stage.get("prior_accepted_receipt_sha256")!=science["verified_receipt_sha256"]
                        or type(next_stage.get("checkpoint_sha256")) is not str
                        or re.fullmatch(r"[0-9a-f]{64}",next_stage["checkpoint_sha256"]) is None):
                    raise ValueError("Next eligible stage has no linked real checkpoint")
                state="NEXT_MILESTONE_ADVANCED"
        elif next_milestone_receipt is not None:
            raise ValueError("Cannot claim downstream progress without accepted original review")

    return {
        "schema_version":1,
        "status":state,
        "original_source_sha256":source_sha256,
        "original_accepted_before":original_accepted,
        "original_total":original_total,
        "supporting_work_completed":supporting_work_completed,
        "supporting_work_is_primary_repair":False,
        "live_pdf_modality_verified":state!="BLOCKED_EXTERNAL_DEPENDENCY",
        "original_operation_recovered":state in (
            "ORIGINAL_OPERATION_RECOVERED","NEXT_MILESTONE_ADVANCED"),
        "next_milestone_advanced":state=="NEXT_MILESTONE_ADVANCED",
        "scientific_approval_fabricated":False,
        "paid_operations_authorized":False,
        "retry_consumed_original_send_authorized":False,
    }
