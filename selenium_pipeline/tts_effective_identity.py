"""Single contract for source-bound, actual-provider TTS output identity.

This validates evidence and does not create approval, authorize paid calls,
or infer that separate Gemini and Cloud engines sound identical.
"""
from __future__ import annotations


class TTSEffectiveIdentityError(ValueError):
    pass


LITE = "gemini-3.8-flash-lite-tts"
FLASH = "gemini-3.8-flash-tts"
CHIRP = "chirp3-hd"
KORE = "Kore"
CLOUD_KORE = "en-US-Chirp3-HD-Kore"
DEFAULT = {"provider": "gemini", "model": LITE, "voice": KORE}
GEMINI_FLASH = {"provider": "gemini", "model": FLASH, "voice": KORE}
CLOUD = {"provider": "chirp3", "model": CHIRP, "voice": CLOUD_KORE}


def verify_effective_identity(manifest: dict, items: list[tuple[int, str]]) -> dict:
    """Check one voice/model for every slide and an unbroken fallback chain."""
    if not isinstance(manifest, dict) or not items:
        raise TTSEffectiveIdentityError("No valid source-bound TTS manifest")
    effective = manifest.get("primary")
    rows = manifest.get("slides")
    if (not isinstance(effective, dict) or
            effective not in (DEFAULT, GEMINI_FLASH, CLOUD) or
            not isinstance(rows, list) or len(rows) != len(items) or
            len({n for n, _ in items}) != len(items)):
        raise TTSEffectiveIdentityError("Unapproved provider/model/voice or slide coverage")
    requested = manifest.get("requested_primary")
    if requested is None:
        if effective not in (DEFAULT, GEMINI_FLASH):
            raise TTSEffectiveIdentityError("Direct Cloud is not an approved automatic fallback")
        if ("fallback_chain" in manifest or
                manifest.get("all_slides_one_effective_voice") is True):
            raise TTSEffectiveIdentityError("Unbound fallback evidence")
        fallback = False
        chain: list[str] = []
        requested = effective
    else:
        if requested != DEFAULT or manifest.get("all_slides_one_effective_voice") is not True:
            raise TTSEffectiveIdentityError("Fallback is not bound to Flash-Lite/Kore")
        if effective == GEMINI_FLASH:
            chain = [LITE]
        elif effective == CLOUD:
            chain = [LITE, FLASH]
        else:
            raise TTSEffectiveIdentityError("Invalid effective fallback destination")
        if manifest.get("fallback_chain") != chain:
            raise TTSEffectiveIdentityError("Incomplete or reordered Gemini fallback history")
        fallback = True

    for row, (number, narration) in zip(rows, items):
        if (not isinstance(row, dict) or type(row.get("slide")) is not int or
                row["slide"] != number or
                row.get("source_text") != narration or
                row.get("tts_text") != narration or
                any(row.get(field) != effective[field]
                    for field in ("provider", "model", "voice")) or
                row.get("fallback_used") is not fallback):
            raise TTSEffectiveIdentityError("Slide narration or effective voice provenance differs")
        if fallback:
            info = row.get("voice_consistency")
            if (row.get("primary_provider") != DEFAULT["provider"]
                    or row.get("primary_model") != DEFAULT["model"]
                    or row.get("primary_voice") != DEFAULT["voice"]
                    or not isinstance(info, dict)
                    or info.get("mode") != "full_batch_single_engine_voice"
                    or info.get("independent_listening_required") is not True
                    or info.get("cross_model_voice_equivalence_verified") is not False):
                raise TTSEffectiveIdentityError("Fallback voice provenance lacks independent-review gate")
    return {
        "provider": effective["provider"],
        "model": effective["model"],
        "voice": effective["voice"],
        "requested_primary": requested,
        "fallback_chain": chain,
        "fallback_used": fallback,
        "voice_listening_field": ("voice_cloud_kore_listening_verified"
                                  if effective == CLOUD
                                  else "voice_kore_listening_verified"),
    }
