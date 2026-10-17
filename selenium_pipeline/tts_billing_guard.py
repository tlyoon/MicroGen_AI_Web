"""Explicit per-invocation TTS billing authorization — never infer from keys.

This guard only authorizes the named provider *for a user-invoked command*.
It never treats environment variables, existing credentials, browser login,
or a generic "Proceed" conversation as cost authorization.
"""
from __future__ import annotations


class TTSCostAuthorizationError(ValueError):
    pass


def require_tts_cost_authorization(provider: str, *,
                                   gemini_approved: bool = False,
                                   cloud_approved: bool = False) -> None:
    if provider == "gemini":
        if not gemini_approved:
            raise TTSCostAuthorizationError(
                "Gemini API TTS may incur charges: explicit "
                "--confirm-gemini-api-cost is required")
    elif provider == "chirp3":
        if not cloud_approved:
            raise TTSCostAuthorizationError(
                "Google Cloud Chirp TTS is not an automatic fallback: "
                "explicit --confirm-google-cloud-tts-cost is required")
    else:
        raise TTSCostAuthorizationError("Unknown TTS provider")
