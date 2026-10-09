"""Interchangeable Gemini 3.8 and Google Cloud Chirp 3 HD speech backends.

Generates one slideN.wav per narration block into a temporary folder first.
Never replaces good audio files with a partially completed TTS batch.
"""
from __future__ import annotations

import argparse
import base64
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .runner import blocks

STYLE = ("Natural and clear university-level physics teaching narration, "
         "calm pacing, precise mathematical and scientific terminology. "
         "Read the transcript faithfully, with appropriate short pauses.")


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, OSError):
        return False


@contextmanager
def _tts_workspace_lock(folder: Path):
    """Allow only one TTS writer per workspace; recover stale locks safely."""
    lock = folder / ".tts.lock"
    folder.mkdir(parents=True, exist_ok=True)

    for _ in range(2):
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                owner = int((lock.read_text(encoding="utf-8") or "0").strip().split()[0])
            except Exception:
                owner = 0
            if owner and _pid_alive(owner):
                raise RuntimeError(
                    f"Another TTS process is already active for {folder} (PID {owner})."
                )
            try:
                lock.unlink()
            except FileNotFoundError:
                pass
            continue

        try:
            os.write(fd, f"{os.getpid()}\n".encode("ascii"))
        finally:
            os.close(fd)
        try:
            yield
        finally:
            try:
                lock.unlink()
            except FileNotFoundError:
                pass
        return

    raise RuntimeError(f"Could not acquire TTS workspace lock: {lock}")


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


def _gemini_failover_request(text: str, number: int, model: str, voice: str) -> bytes:
    from gemini_keys import call_with_client_failover, create_gemini_client
    return call_with_client_failover(
        create_gemini_client,
        lambda client: _gemini_say(client, text, model, voice),
        label=f"Gemini TTS slide{number}",
    )


def _gemini_say_with_watchdog(text: str, number: int, model: str, voice: str) -> bytes:
    timeout_seconds = max(10.0, float(os.environ.get("MICROGEN_TTS_HARD_TIMEOUT_SECONDS", "90")))
    attempts = max(1, int(os.environ.get("MICROGEN_TTS_REQUEST_ATTEMPTS", "3")))
    last_error: BaseException | None = None

    for attempt in range(1, attempts + 1):
        with tempfile.TemporaryDirectory(prefix=f"microgen_tts_slide{number}_") as tmp:
            output = Path(tmp) / "result.wav"
            command = [
                sys.executable,
                "-m",
                "selenium_pipeline.tts_worker",
                "--output",
                str(output),
                "--model",
                model,
                "--voice",
                voice,
                "--number",
                str(number),
            ]
            try:
                completed = subprocess.run(
                    command,
                    input=text,
                    text=True,
                    capture_output=True,
                    timeout=timeout_seconds,
                    env=os.environ.copy(),
                )
            except subprocess.TimeoutExpired:
                last_error = TimeoutError(
                    f"Gemini TTS slide{number} exceeded hard timeout of "
                    f"{timeout_seconds:.0f}s on attempt {attempt}/{attempts}"
                )
                if attempt < attempts:
                    print(f"[tts] {last_error}; retrying", flush=True)
                    continue
                raise last_error

            if completed.returncode == 0 and output.is_file():
                payload = output.read_bytes()
                if payload:
                    return payload

            detail = (completed.stderr or completed.stdout or "").strip()
            last_error = RuntimeError(
                f"Gemini TTS slide{number} worker failed on attempt {attempt}/{attempts}"
                + (f": {detail}" if detail else "")
            )
            if attempt < attempts:
                print(f"[tts] {last_error}; retrying", flush=True)
                continue
            raise last_error

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Gemini TTS slide{number} failed without a result")


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


def _synthesize_folder_unlocked(folder: Path, provider: str, model: str, voice: str) -> None:
    text = (folder / "script.txt").read_text(encoding="utf-8")
    items = blocks(text)
    if provider == "gemini":
        if model not in ("gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"):
            raise ValueError("Unapproved TTS model; select Gemini 3.8 Flash-Lite or Flash TTS")
        from gemini_keys import (
            call_with_client_failover,
            create_gemini_client,
            get_gemini_api_keys,
        )
        if not get_gemini_api_keys():
            raise EnvironmentError(
                "No Gemini API key is loaded. Configure GEMINI_API_KEY_1 and optionally "
                "GEMINI_API_KEY_2 in the standard Microvid .env file."
            )
        use_watchdog = getattr(create_gemini_client, "__module__", "") == "gemini_keys"

        def say(narration: str, number: int) -> bytes:
            if use_watchdog:
                return _gemini_say_with_watchdog(narration, number, model, voice)
            return call_with_client_failover(
                create_gemini_client,
                lambda client: _gemini_say(client, narration, model, voice),
                label=f"Gemini TTS slide{number}",
            )
    elif provider == "chirp3":
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()  # Use ADC / GOOGLE_APPLICATION_CREDENTIALS
        chirp_voice = voice if "Chirp3-HD" in voice else "en-US-Chirp3-HD-Aoede"
        say = lambda narration, number: _chirp_say(client, narration, chirp_voice)
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")

    candidate = folder / ".tts_candidate"
    candidate.mkdir(parents=True, exist_ok=True)
    expected_names = {f"slide{n}.wav" for n, _ in items}

    # Preserve completed candidate WAVs across retries. Remove only incomplete
    # or stale candidate artifacts so a transient failure does not force all
    # earlier slides to be synthesized again.
    for item in list(candidate.iterdir()):
        if item.name.endswith(".partial") or item.name not in expected_names:
            if item.is_file():
                item.unlink()

    for number, narration in items:
        dest = candidate / f"slide{number}.wav"
        if dest.is_file() and dest.stat().st_size > 44:
            try:
                magic = dest.read_bytes()[:4]
            except Exception:
                magic = b""
            if magic in (b"RIFF", b"RF64"):
                print(f"[tts] reusing {dest.name} ({dest.stat().st_size} bytes)", flush=True)
                continue
            dest.unlink(missing_ok=True)

        print(f"[tts] requesting slide{number} ({len(narration)} chars)", flush=True)
        try:
            payload = say(narration, number)
        except Exception as exc:
            print(f"[tts] slide{number} failed: {type(exc).__name__}: {exc}", flush=True)
            raise
        if not payload.startswith((b"RIFF", b"RF64")):
            raise RuntimeError(f"slide{number}: TTS did not return a WAV file")
        partial = candidate / f"slide{number}.wav.partial"
        partial.write_bytes(payload)
        if partial.stat().st_size <= 44:
            partial.unlink(missing_ok=True)
            raise RuntimeError(f"slide{number}: audio is empty")
        partial.replace(dest)
        print(f"[tts] prepared {dest.name} ({len(payload)} bytes)", flush=True)
    # All responses have been validated; publish after the complete batch.
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


def synthesize_folder(folder: Path, provider: str, model: str, voice: str) -> None:
    with _tts_workspace_lock(folder):
        _synthesize_folder_unlocked(folder, provider, model, voice)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate MicroGen slide narration audio")
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--provider", choices=("gemini", "chirp3"), default="gemini")
    parser.add_argument("--model", default="gemini-3.8-flash-lite-tts")
    parser.add_argument("--voice", default="Kore")
    args = parser.parse_args(argv)
    synthesize_folder(args.folder, args.provider, args.model, args.voice)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
