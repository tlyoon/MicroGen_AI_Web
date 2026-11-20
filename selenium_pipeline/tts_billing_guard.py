"""Standing TTS production authorization, distinct from experimental billing.

The course owner authorized routine Gemini Flash-Lite/Flash paid speech and
conditional Cloud Chirp *after* the two approved Gemini models each fail their
three-attempt queues. The standing authorization never authorizes independent
API experiments or directly selected Google Cloud speech.
"""
from __future__ import annotations


class TTSCostAuthorizationError(ValueError):
    pass


def require_tts_cost_authorization(provider: str, *,
                                   gemini_approved: bool = False,
                                   cloud_approved: bool = False,
                                   routine_gemini: bool = False,
                                   conditional_cloud_fallback: bool = False) -> None:
    if provider == "gemini":
        if not (gemini_approved or routine_gemini):
            raise TTSCostAuthorizationError(
                "Experimental Gemini API TTS requires explicit "
                "--confirm-gemini-api-cost; routine production TTS is "
                "covered by the standing course authorization")
    elif provider == "chirp3":
        if not (cloud_approved or conditional_cloud_fallback):
            raise TTSCostAuthorizationError(
                "Direct Google Cloud Chirp requires "
                "--confirm-google-cloud-tts-cost. The standing policy covers "
                "Cloud only *after* both Gemini models exhaust three attempts.")
    else:
        raise TTSCostAuthorizationError("Unknown TTS provider")
