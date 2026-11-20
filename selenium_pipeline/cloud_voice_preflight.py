"""Fail closed on an unavailable or mismatched Google Cloud Chirp voice.

This is a read-only catalogue check before any metered Cloud TTS synthesis.
It cannot establish acoustic narrator identity and grants no billing authority.
"""
from __future__ import annotations

import re


class CloudVoicePreflightError(RuntimeError):
    """Voice catalogue uncertainty must never trigger paid synthesis."""


def verify_catalogue_voice(client, voice: str) -> dict:
    if not isinstance(voice, str) or not re.fullmatch(
        r"en-[A-Z]{2}-Chirp3-HD-[A-Za-z]+", voice
    ):
        raise CloudVoicePreflightError(
            "Invalid Cloud Chirp 3 HD voice identity; no synthesis authorized"
        )
    language = "-".join(voice.split("-")[:2])
    try:
        catalogue = client.list_voices(
            request={"language_code": language}, timeout=20
        )
        names = {row.name for row in catalogue.voices}
    except Exception as exc:
        raise CloudVoicePreflightError(
            "Cannot verify Cloud voice catalogue; no synthesis authorized"
        ) from exc
    if voice not in names:
        raise CloudVoicePreflightError(
            f"Cloud voice {voice} absent from live {language} catalogue; "
            "no synthesis authorized"
        )
    return {
        "voice": voice,
        "language_code": language,
        "catalogue_verified": True,
        "paid_synthesis_dispatched": False,
    }
