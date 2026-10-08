"""Interchangeable Gemini 3.8 and Google Cloud Chirp 3 HD speech backends.

Generates one slideN.wav per narration block into a temporary folder first.
Never replaces good audio files with a partially completed TTS batch.
"""
from __future__ import annotations

import base64
import os
import shutil
from pathlib import Path

from .runner import blocks

STYLE = ("Natural and clear university-level physics teaching narration, "
         "calm pacing, precise mathematical and scientific terminology. "
         "Read the transcript faithfully, with appropriate short pauses.")


def _wav_bytes(response) -> bytes:
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                value = inline.data
                return base64.b64decode(value) if isinstance(value, str) else bytes(value)
    raise RuntimeError("TTS response had no audio; nothing has been published")


def _gemini_say(client, text: str, model: str, voice: str) -> bytes:
    response = client.models.generate_content(
        model=model,
        contents=[{"role": "user", "parts": [
            {"text": text, "speech_metadata": {"style": STYLE}}
        ]}],
        config={"response_modalities": ["AUDIO"],
                "speech_config": {"voice_config": {"voice": voice}}},
    )
    return _wav_bytes(response)


def _chirp_say(client, text: str, voice: str) -> bytes:
    from google.cloud import texttospeech
    # Default to a genuine Chirp 3 HD voice, configurable by name.
    lang = voice.split("-")[0] + "-" + voice.split("-")[1]
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(language_code=lang, name=voice),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=0.9,
        ),
    )
    return response.audio_content


def synthesize_folder(folder: Path, provider: str, model: str, voice: str) -> None:
    text = (folder / "script.txt").read_text(encoding="utf-8")
    items = blocks(text)
    if provider == "gemini":
        if model not in ("gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"):
            raise ValueError("Unapproved TTS model; select Gemini 3.8 Flash-Lite or Flash TTS")
        if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            raise EnvironmentError("Set GEMINI_API_KEY for Gemini API TTS; UI subscription is separate")
        from google import genai
        client = genai.Client()
        say = lambda narration: _gemini_say(client, narration, model, voice)
    elif provider == "chirp3":
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()  # Use ADC / GOOGLE_APPLICATION_CREDENTIALS
        chirp_voice = voice if "Chirp3-HD" in voice else "en-US-Chirp3-HD-Aoede"
        say = lambda narration: _chirp_say(client, narration, chirp_voice)
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")

    candidate = folder / ".tts_candidate"
    if candidate.exists():
        shutil.rmtree(candidate)
    candidate.mkdir(parents=True)
    for number, narration in items:
        payload = say(narration)
        if not payload.startswith((b"RIFF", b"RF64")):
            raise RuntimeError(f"slide{number}: TTS did not return a WAV file")
        dest = candidate / f"slide{number}.wav"
        dest.write_bytes(payload)
        if dest.stat().st_size <= 44:
            raise RuntimeError(f"slide{number}: audio is empty")
        print(f"[tts] prepared {dest.name} ({len(payload)} bytes)", flush=True)
    # All responses have been validated; publish after the complete batch.
    expected_names = {f"slide{n}.wav" for n, _ in items}
    stale = [p for p in folder.glob("slide*.wav") if p.name not in expected_names]
    if stale:
        from datetime import datetime, timezone
        old_dir = folder / ".history" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f") / "tts"
        old_dir.mkdir(parents=True, exist_ok=True)
        for item in stale:
            item.replace(old_dir / item.name)
    for wav in candidate.glob("slide*.wav"):
        wav.replace(folder / wav.name)
    candidate.rmdir()
    print(f"[tts] completed {len(items)} WAV files via {provider}", flush=True)
