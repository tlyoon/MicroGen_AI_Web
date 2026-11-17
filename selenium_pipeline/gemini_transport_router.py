"""Pre-Send Gemini transport routing, separate from response acceptance.

Only an already-authorized, independently verified owned Selenium tab can be
selected. Never replay a consumed Send. API transport is a non-operational
future adapter: no secrets, requests or chargeable operations are implemented.
"""
from __future__ import annotations

from dataclasses import dataclass

_SIGNATURE="EXACT_GEMINI_BROWSER_ROUTE_PRE_SEND"
_MECHANISM="SELECT_OWNED_PRIMARY_OR_ALREADY_RUNNING_ALT_NO_API"


class GeminiTransportNotAuthorized(ValueError):
    """No admissible route; no external Send performed."""


@dataclass(frozen=True)
class TransportDecision:
    status: str
    transport: str
    port: int
    model_family: str
    thinking_level: str
    alternate_account_used: bool
    new_model_requests: int = 0
    original_request_replayed: bool = False
    paid_api_authorized: bool = False


def verified_browser_route(*,family:str,claimed_send_state:str,
                           evidence_provider=None,backend:str="selenium"):
    """Choose route ONLY while invoking an already unique eligible request.

    Academic claim creation/one-Send enforcement remains owned by submit_once.
    No route will be selected for an already consumed/uncertain claim. This is
    called during the FIRST execution of a newly reserved transport callback,
    before any prompt upload or browser Send.
    """
    if (backend!="selenium" or family not in ("flash","pro")
            or claimed_send_state!="NEW_CLAIM_BEFORE_SEND"):
        raise GeminiTransportNotAuthorized(
            "GEMINI_TRANSPORT_REPLAY_OR_PAID_ROUTE_FORBIDDEN")
    from .recovery_registry import lookup_mechanism
    if lookup_mechanism("transport_selection",_SIGNATURE)!=_MECHANISM:
        raise GeminiTransportNotAuthorized(
            "GEMINI_TRANSPORT_SELECTOR_NOT_REGISTERED")
    from .academic_queue_fresh_send_health import _full_family_scope
    from .academic_gemini_presend_preflight import select_ready_existing_session
    inspector=evidence_provider or select_ready_existing_session
    try:
        with _full_family_scope(family):
            info=inspector(primary_port=9222,allow_active_alternate=True)
    except Exception as exc:
        raise GeminiTransportNotAuthorized(
            "NO_INDEPENDENTLY_VERIFIED_GEMINI_BROWSER_SESSION_NO_SEND") from exc
    if (type(info) is not dict
            or info.get("status") !=
                 "EXACT_OWNED_GEMINI_MODEL_AND_THINKING_READY_NO_SEND"
            or info.get("verified_port") not in (9222,9225)
            or type(info.get("verified_port")) is not int
            or info.get("model_family") != family
            or info.get("thinking_level") != "medium"
            or info.get("existing_profile_only") is not True
            or info.get("alternate_account_used") is not (
                info["verified_port"] == 9225)
            or info.get("gemini_requests_submitted") != 0
            or info.get("files_uploaded") != 0
            or info.get("model_prompt_typed") is not False
            or info.get("academic_approval") is not False
            or info.get("student_publication_authorized") is not False):
        raise GeminiTransportNotAuthorized(
            "UNTRUSTED_GEMINI_ROUTE_OR_MODEL_THINKING_EVIDENCE_NO_SEND")
    return TransportDecision(
        status="EXACT_EXISTING_GEMINI_BROWSER_READY_BEFORE_SEND",
        transport="selenium_owned",
        port=info["verified_port"],model_family=family,
        thinking_level="medium",
        alternate_account_used=info["alternate_account_used"])


def gemini_api_status():
    """Explicitly non-operational paid adapter. Env vars cannot enable it."""
    return {"status":"BLOCKED_AUTHORIZATION_NO_GEMINI_API_REQUEST",
            "adapter":"gemini_api",
            "installed":False,
            "provider_requests":0,
            "paid_api_authorized":False,
            "user_consent_inferred":False}


def execute_gemini_api(*_args,**_kwargs):
    raise GeminiTransportNotAuthorized(
        "GEMINI_API_DISABLED_EXPLICIT_SEPARATE_AUTHORIZATION_REQUIRED")
