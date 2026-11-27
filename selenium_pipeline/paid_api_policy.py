"""Production paid-provider egress policy for MicroGen_AI_Web.

Gemini browser Selenium is the ONLY model transport for figures, slide/script
creation, and scientific review. No exception for an outage, timeout, low
remaining web quota, browser failure, retry exhaustion, old configuration or
an installed API key. Paid Gemini API is reserved solely for TTS synthesis or
an approved TTS audio-quality check. The owner granted standing automatic
permission on 27 Nov 2026 for the exact gemini-3.8-flash QA model.
Other paid QA models still need an explicit per-run approval.

The default for every unknown API purpose is NO SEND. Do not infer QA approval
from successful TTS, a saved web login, available credits or a generic model
authorization. API key rotation cannot broaden the operation's purpose.
"""
from __future__ import annotations

import os


class PaidAPIPolicyBlocked(RuntimeError):
    """No chargeable request may be dispatched under this operation."""


TTS_QA_APPROVAL_ENV = "MICROGEN_PAID_TTS_QA_APPROVAL"
TTS_QA_APPROVAL_LITERAL = "EXPLICIT_APPROVAL_FOR_THIS_RUN"
STANDING_TTS_QA_MODEL = "gemini-3.8-flash"
STANDING_TTS_QA_POLICY = "USER_CONFIRMED_MICROGEN_AI_WEB_2026_11_27"


def tts_qa_explicitly_approved() -> bool:
    """Exact opt-in set only by a TTS-QA-specific CLI/launcher action."""
    return os.environ.get(TTS_QA_APPROVAL_ENV) == TTS_QA_APPROVAL_LITERAL


def set_tts_qa_approval_for_run(approved: bool) -> None:
    """Reset inherited approval on every CLI invocation: no sticky approval."""
    if type(approved) is not bool:
        raise TypeError("TTS-QA approval must be an explicit boolean")
    if approved:
        os.environ[TTS_QA_APPROVAL_ENV] = TTS_QA_APPROVAL_LITERAL
    else:
        os.environ.pop(TTS_QA_APPROVAL_ENV, None)


def _require_registered_paid_scope() -> None:
    from .recovery_registry import lookup_mechanism
    try:
        mechanism = lookup_mechanism(
            "paid_api_scope", "SELENIUM_ONLY_CONTENT_TTS_PAID_GATE")
    except (ValueError, OSError) as exc:
        raise PaidAPIPolicyBlocked(
            "PAID_API_POLICY_REGISTRY_MISSING_OR_DISABLED_NO_SEND") from exc
    if mechanism != "DENY_CONTENT_API_ALLOW_TTS_AND_EXPLICIT_TTS_QA":
        raise PaidAPIPolicyBlocked(
            "PAID_API_POLICY_REGISTRY_NOT_VERIFIED_NO_SEND")


def require_paid_gemini_api(
    purpose: str, *, qa_approved: bool = False, model: str | None = None
) -> None:
    """Fail closed before billed Send; standing permission is model-and-purpose pinned.

    On 27 Nov 2026 the owner clarified that paid gemini-3.8-flash is
    automatically permitted for MicroGen_AI_Web TTS/acoustic QA. It is not
    permission to use paid APIs for slides, narration or scientific review.
    The actual egress adapter MUST pass the model, not rely on a preflight.
    """
    if purpose == "tts":
        _require_registered_paid_scope()
        return
    if purpose == "tts_qa":
        if model == STANDING_TTS_QA_MODEL:
            _require_registered_paid_scope()
            return
        # Preserve the historical per-run opt-in for other QA models.
        if qa_approved is True and tts_qa_explicitly_approved():
            _require_registered_paid_scope()
            return
        raise PaidAPIPolicyBlocked(
            "PAID_GEMINI_TTS_QA_MODEL_NOT_AUTHORIZED; "
            "automatic standing approval applies only to gemini-3.8-flash "
            "for TTS QA; alternative paid QA models still require "
            "--confirm-paid-tts-qa for this run")
    raise PaidAPIPolicyBlocked(
        "PAID_GEMINI_API_CONTENT_FORBIDDEN_SELENIUM_ONLY; "
        "all lecture creation and scientific review must use owned Gemini "
        "Selenium; no paid API fallback or alternative provider")
