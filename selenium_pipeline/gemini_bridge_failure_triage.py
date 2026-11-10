"""Privacy-preserving, fail-closed triage of a failed owned-tab Gemini request.

Never infer Gemini server saturation from a UI timeout or generic bridge
exception. Do not record error messages, model text, prompts, paths or tabs.
"""
from __future__ import annotations

from .series_bridge import SeriesBridgeError


def classify_owned_gemini_failure(error: BaseException) -> dict:
    if isinstance(error, SeriesBridgeError):
        detail = str(error)
        if detail.startswith("Could not type Gemini storyboard instruction"):
            stage = "OWNED_COMPOSER_INPUT_FAILED"
        elif detail.startswith("Could not submit Gemini storyboard instruction"):
            stage = "OWNED_SEND_NOT_CONFIRMED"
        elif detail.startswith("Gemini owned tab displayed a model UI error, but"):
            stage = "OWNED_GEMINI_ERROR_WITHOUT_NEW_USER_TURN_PROOF"
        elif detail.startswith("Gemini browser returned a visible owned-model UI error"):
            stage = (
                "OWNED_GEMINI_UI_ERROR_AFTER_VERIFIED_NEW_USER_TURN"
                if "AFTER a verified new user turn" in detail else
                "OWNED_GEMINI_UI_TERMINAL_ERROR_TEXT_NOT_API_PROOF")
        elif detail.startswith("Gemini reply text was captured without"):
            stage = "REPLY_UNTRUSTED_NO_NEW_USER_TURN_PROOF"
        elif detail.startswith("Gemini response present but NEW user turn"):
            stage = "RECOVERED_REPLY_UNTRUSTED_NO_NEW_USER_TURN_PROOF"
        elif detail.startswith("Gemini new user turn was independently registered"):
            stage = "REGISTERED_SEND_GENERATION_STALLED_ZERO_MODEL_TEXT"
        elif detail.startswith("No stable complete Gemini JSON"):
            stage = "OWNED_RESPONSE_UNVERIFIED_QUARANTINED"
        elif detail.startswith("Gemini JSON capture failed and recovery quarantine"):
            stage = "OWNED_CAPTURE_EVIDENCE_WRITE_FAILED"
        elif detail.startswith("Vendored Gemini Selenium client unavailable"):
            stage = "LOCAL_BROWSER_CLIENT_UNAVAILABLE"
        else:
            stage = "BRIDGE_STAGE_UNDETERMINED"
    elif isinstance(error, (TimeoutError, ConnectionError)):
        stage = "TRANSPORT_TIMEOUT_OR_CONNECTION_UNATTRIBUTED"
    elif isinstance(error, (ValueError, UnicodeError)):
        stage = "EXACT_HEALTH_RESPONSE_INVALID"
    else:
        stage = "UNCLASSIFIED_LOCAL_OR_REMOTE_FAILURE"
    return {
        "stage": stage,
        "stage_inferred_from_trusted_bridge_exception_only": True,
        "gemini_provider_overload_proven": False,
        "retry_or_scientific_approval_authorized": False,
        "private_error_detail_recorded": False,
    }
