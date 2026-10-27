"""Gemini 3.8 TTS via the current Interactions API; canonical PCM WAV output.

The older generate_content TTS payload and google-genai 1.x cannot deliver
Flash-Lite 3.8 TTS. Validate SDK and schema BEFORE any metered provider call.

This module never claims that a returned waveform speaks the intended text:
exact-script audible QA and the source academic gate remain independent.
"""
from __future__ import annotations
import base64
from io import BytesIO
from importlib.metadata import PackageNotFoundError, version
import re
import wave


class InteractionsTTSCompatError(RuntimeError):
    """Incompatible local SDK, unsafe voice or invalid audio result."""


APPROVED_MODELS = frozenset((
    "gemini-3.8-flash-lite-tts",
    "gemini-3.8-flash-tts",
))
APPROVED_VOICE = "Kore"


def require_modern_tts_sdk() -> str:
    """Fail without network when the installed Python SDK cannot use 3.8 TTS."""
    try:
        found=version("google-genai")
    except PackageNotFoundError as exc:
        raise InteractionsTTSCompatError(
            "google-genai is missing; install the Windows-pinned >=2.25,<3 SDK"
        ) from exc
    numbers=re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?",found)
    if (numbers is None or
            not ((2,25,0) <= tuple(int(x or 0) for x in numbers.groups())
                 < (3,0,0))):
        raise InteractionsTTSCompatError(
            "Gemini 3.8 Flash-Lite TTS requires google-genai >=2.25,<3; "
            "local version "+found+" is incompatible. "
            "Upgrade in an ISOLATED Windows environment, not the protected "
            "course workspace. No paid request was made."
        )
    from google.genai import types
    if not hasattr(types,"HttpRetryOptions"):
        raise InteractionsTTSCompatError(
            "SDK missing HttpRetryOptions; upgrade to compatible 2.25+ "
            "before any Gemini TTS provider request")
    return found


def canonical_single_speaker_3_8_request(*,text:str,model:str,voice:str)->dict:
    """Exact utterance transcript, prebuilt voice, no previous input/edits."""
    if model not in APPROVED_MODELS:
        raise InteractionsTTSCompatError("Unapproved TTS model")
    if voice != APPROVED_VOICE:
        raise InteractionsTTSCompatError(
            "Original calculus replacement must retain the Kore voice")
    if not isinstance(text,str) or not text.strip() or len(text)>12000:
        raise InteractionsTTSCompatError("Missing or oversized exact utterance text")
    if text != text.strip():
        raise InteractionsTTSCompatError(
            "Whitespace normalization could break utterance SHA provenance")
    return {
        "model":model,
        # Gemini 3.8 Interactions input is a typed user_input CONTENT ARRAY.
        # Directly passing a string makes this SDK request invalid.
        "input":[{
            "type":"user_input",
            "content":[{
                "type":"text",
                "text":text,
            }],
        }],
        "response_format":{"type":"audio"},
        "generation_config":{"speech_config":[{"voice":voice}]},
    }


def _decode_audio_bytes(audio) -> bytes:
    encoded=getattr(audio,"data",None)
    if encoded is None:
        raise InteractionsTTSCompatError("Provider returned no output_audio.data")
    if isinstance(encoded,str):
        try:
            payload=base64.b64decode(encoded,validate=True)
        except (ValueError,base64.binascii.Error) as exc:
            raise InteractionsTTSCompatError("Invalid provider base64 audio") from exc
    elif isinstance(encoded,bytes):
        payload=encoded
        if not payload.startswith(b"RIFF"):
            # Some SDK versions expose UTF-8 base64 bytes, others PCM bytes.
            try:
                decoded=base64.b64decode(payload,validate=True)
            except (ValueError,base64.binascii.Error):
                decoded=None
            if decoded is not None and len(decoded)>len(payload)//2:
                payload=decoded
    else:
        raise InteractionsTTSCompatError("Unexpected provider audio type")
    if not 1000<=len(payload)<=30_000_000:
        raise InteractionsTTSCompatError("Audio payload missing or oversized")
    return payload


def _canonical_wav(payload:bytes,audio)->bytes:
    if payload.startswith(b"RIFF") and payload[8:12]==b"WAVE":
        normalized=payload
    else:
        mime=str(getattr(audio,"mime_type",None) or
                 getattr(audio,"mimeType",None) or "")
        match=re.search(r"rate=(\d+)",mime)
        rate=int(match[1]) if match else 24000
        if rate not in (16000,22050,24000,32000,44100,48000):
            raise InteractionsTTSCompatError("Untrusted or unsupported PCM sample rate")
        if len(payload)%2:
            raise InteractionsTTSCompatError("Odd-length PCM16 payload")
        memory=BytesIO()
        with wave.open(memory,"wb") as result:
            result.setnchannels(1)
            result.setsampwidth(2)
            result.setframerate(rate)
            result.writeframes(payload)
        normalized=memory.getvalue()
    try:
        with wave.open(BytesIO(normalized),"rb") as wav:
            nframes=wav.getnframes()
            rate=wav.getframerate()
            valid=(wav.getnchannels()==1 and wav.getsampwidth()==2
                   and wav.getcomptype()=="NONE" and
                   16000<=rate<=48000 and .25<nframes/rate<150)
    except (wave.Error,EOFError,OSError) as exc:
        raise InteractionsTTSCompatError(
            "TTS response is not genuine decodable mono PCM16 WAV") from exc
    if not valid:
        raise InteractionsTTSCompatError(
            "TTS returned empty or nonstandard speech WAV")
    return normalized


def generate_3_8_kore_wav(
    client,text:str,model:str,voice:str, *,
    request_observation:dict|None=None,
) -> bytes:
    """Actual SDK call; client already constructed after SDK preflight.

    Per-call credential, timeout and retry policy is controlled by the caller.
    Never fill in an invented provider request_id or claim listened words.
    """
    request=canonical_single_speaker_3_8_request(
        text=text,model=model,voice=voice)
    require_modern_tts_sdk()
    interactions=getattr(client,"interactions",None)
    if interactions is None or not callable(getattr(interactions,"create",None)):
        raise InteractionsTTSCompatError(
            "Current Gemini 3.8 TTS SDK has no Interactions create client")
    response=interactions.create(**request)
    if request_observation is not None:
        from .tts_attempt_evidence import safe_provider_request_id
        request_observation["provider_request_id"]=safe_provider_request_id(response)
    audio=getattr(response,"output_audio",None)
    if audio is None:
        raise InteractionsTTSCompatError(
            "Interactions TTS response returned no output_audio")
    return _canonical_wav(_decode_audio_bytes(audio),audio)
