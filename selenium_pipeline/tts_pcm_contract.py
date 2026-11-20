"""Strict on-disk TTS WAV acceptance for separately reviewed audio.

A RIFF header or a matching SHA-256 alone does not establish that audio can
be decoded, has the expected voice pipeline's PCM format, or is in-bounds.
Does not contact the network, transcribe, or attest that words were heard.
"""
from __future__ import annotations

import io
import struct
import wave


class TTSPCMContractError(ValueError):
    pass


def verify_pcm(payload: bytes, *, label: str = "WAV") -> dict:
    if not isinstance(payload, bytes) or len(payload) < 44:
        raise TTSPCMContractError(f"{label}: absent or truncated audio")
    if payload[:4] != b"RIFF" or payload[8:12] != b"WAVE":
        raise TTSPCMContractError(f"{label}: expected real RIFF/WAVE PCM, not just an audio filename")
    if struct.unpack_from("<I", payload, 4)[0] + 8 != len(payload):
        raise TTSPCMContractError(f"{label}: RIFF declared byte length differs from file")
    try:
        with wave.open(io.BytesIO(payload), "rb") as wav:
            channels = wav.getnchannels()
            width = wav.getsampwidth()
            rate = wav.getframerate()
            comp = wav.getcomptype()
            frames = wav.getnframes()
            samples = wav.readframes(frames)
    except (wave.Error, OSError, EOFError, ValueError) as exc:
        raise TTSPCMContractError(f"{label}: WAV cannot be decoded") from exc
    if (channels != 1 or width != 2 or rate != 24000 or comp != "NONE"
            or frames <= 0 or len(samples) != frames * 2):
        raise TTSPCMContractError(f"{label}: invalid or incomplete 24kHz 16-bit mono PCM")
    duration = frames / rate
    if not (0.2 <= duration <= 120.0):
        raise TTSPCMContractError(f"{label}: duration outside 0.2–120 seconds")
    return {"sample_rate_hz": rate, "channels": channels,
            "sample_width_bytes": width, "frames": frames,
            "duration_seconds": round(duration, 6)}
