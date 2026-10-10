"""Interchangeable Gemini 3.8 and Google Cloud Chirp 3 HD speech backends.

Generates one slideN.wav per narration block into a temporary folder first.
Never replaces good audio files with a partially completed TTS batch.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import math
import re
import wave
import os
import shutil
import subprocess
import sys
import tempfile
import time
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


def _tts_timeout_seconds(text: str) -> float:
    """Return a length-aware hard timeout for one Gemini TTS request."""
    override = os.environ.get("MICROGEN_TTS_HARD_TIMEOUT_SECONDS", "").strip()
    if override:
        return max(10.0, float(override))

    base = max(30.0, float(os.environ.get("MICROGEN_TTS_TIMEOUT_BASE_SECONDS", "90")))
    per_100 = max(0.0, float(os.environ.get("MICROGEN_TTS_TIMEOUT_PER_100_CHARS_SECONDS", "15")))
    cap = max(base, float(os.environ.get("MICROGEN_TTS_TIMEOUT_MAX_SECONDS", "300")))
    estimated = base + per_100 * math.ceil(max(1, len(text)) / 100)
    return min(cap, estimated)


def _split_tts_text(text: str, max_chars: int | None = None) -> list[str]:
    """Split narration at sentence boundaries, then whitespace, as a last-resort fallback."""
    if max_chars is None:
        max_chars = max(200, int(os.environ.get("MICROGEN_TTS_CHUNK_MAX_CHARS", "450")))
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned or len(cleaned) <= max_chars:
        return [cleaned] if cleaned else []

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    chunks: list[str] = []
    current = ""

    def flush_current() -> None:
        nonlocal current
        if current:
            chunks.append(current.strip())
            current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) <= max_chars:
            trial = sentence if not current else f"{current} {sentence}"
            if len(trial) <= max_chars:
                current = trial
            else:
                flush_current()
                current = sentence
            continue

        flush_current()
        remaining = sentence
        while len(remaining) > max_chars:
            cut = remaining.rfind(" ", 0, max_chars + 1)
            if cut < max_chars // 2:
                cut = max_chars
            chunks.append(remaining[:cut].strip())
            remaining = remaining[cut:].strip()
        if remaining:
            current = remaining

    flush_current()
    return [chunk for chunk in chunks if chunk]


def _merge_wav_payloads(payloads: list[bytes]) -> bytes:
    """Concatenate compatible PCM WAV payloads into one valid WAV."""
    if not payloads:
        raise ValueError("No WAV payloads to merge")

    params = None
    frames: list[bytes] = []
    for payload in payloads:
        with wave.open(io.BytesIO(payload), "rb") as wav:
            signature = (
                wav.getnchannels(),
                wav.getsampwidth(),
                wav.getframerate(),
                wav.getcomptype(),
                wav.getcompname(),
            )
            if params is None:
                params = signature
            elif signature != params:
                raise RuntimeError("TTS chunk WAV formats do not match")
            frames.append(wav.readframes(wav.getnframes()))

    channels, sampwidth, framerate, comptype, compname = params
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sampwidth)
        wav.setframerate(framerate)
        wav.setcomptype(comptype, compname)
        wav.writeframes(b"".join(frames))
    return output.getvalue()


def _gemini_say_with_watchdog(
    text: str,
    number: int,
    model: str,
    voice: str,
    *,
    allow_chunking: bool = True,
    request_label: str | None = None,
    attempts_override: int | None = None,
) -> bytes:
    timeout_seconds = _tts_timeout_seconds(text)
    attempts = (
        max(1, int(attempts_override))
        if attempts_override is not None
        else max(1, int(os.environ.get("MICROGEN_TTS_REQUEST_ATTEMPTS", "3")))
    )
    label = request_label or f"slide{number}"
    last_error: BaseException | None = None
    timed_out_attempts = 0

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
                timed_out_attempts += 1
                last_error = TimeoutError(
                    f"Gemini TTS {label} exceeded hard timeout of "
                    f"{timeout_seconds:.0f}s on attempt {attempt}/{attempts}"
                )
                if attempt < attempts:
                    print(f"[tts] {last_error}; retrying", flush=True)
                    continue
                break

            if completed.returncode == 0 and output.is_file():
                payload = output.read_bytes()
                if payload:
                    return payload

            detail = (completed.stderr or completed.stdout or "").strip()
            last_error = RuntimeError(
                f"Gemini TTS {label} worker failed on attempt {attempt}/{attempts}"
                + (f": {detail}" if detail else "")
            )
            if attempt < attempts:
                print(f"[tts] {last_error}; retrying", flush=True)
                continue
            raise last_error

    if (
        allow_chunking
        and timed_out_attempts == attempts
        and len(text) > max(200, int(os.environ.get("MICROGEN_TTS_CHUNK_MAX_CHARS", "450")))
    ):
        chunks = _split_tts_text(text)
        if len(chunks) > 1:
            print(
                f"[tts] {label}: full narration timed out {attempts} times; "
                f"falling back to {len(chunks)} sentence-aware chunks",
                flush=True,
            )
            payloads: list[bytes] = []
            for index, chunk in enumerate(chunks, start=1):
                chunk_label = f"{label} chunk {index}/{len(chunks)}"
                print(f"[tts] requesting {chunk_label} ({len(chunk)} chars)", flush=True)
                payloads.append(
                    _gemini_say_with_watchdog(
                        chunk,
                        number,
                        model,
                        voice,
                        allow_chunking=False,
                        request_label=chunk_label,
                    )
                )
            return _merge_wav_payloads(payloads)

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Gemini TTS {label} failed without a result")


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


def _is_transient_tts_failure(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    message = str(exc).lower()
    transient_markers = (
        "429", "500", "502", "503", "504", "unavailable", "high demand",
        "timeout", "timed out", "temporar", "connection", "reset", "overload",
        "resource exhausted",
    )
    permanent_markers = (
        "400 invalid_argument", "401", "403", "permission denied",
        "unauthenticated", "invalid api key", "unapproved tts model",
    )
    if any(marker in message for marker in permanent_markers):
        return False
    return any(marker in message for marker in transient_markers) or isinstance(exc, RuntimeError)


def _tts_queue_delay_seconds(round_number: int) -> float:
    explicit = os.environ.get("MICROGEN_TTS_QUEUE_DELAY_SECONDS", "").strip()
    if explicit:
        return max(0.0, float(explicit))
    base = max(0.0, float(os.environ.get("MICROGEN_TTS_QUEUE_BASE_DELAY_SECONDS", "30")))
    maximum = max(base, float(os.environ.get("MICROGEN_TTS_QUEUE_MAX_DELAY_SECONDS", "300")))
    return min(maximum, base * (2 ** max(0, round_number - 1)))


def _synthesize_folder_unlocked(folder: Path, provider: str, model: str, voice: str) -> None:
    text = (folder / "script.txt").read_text(encoding="utf-8")
    items = blocks(text)

    # Never silently normalize or rewrite risky narration here.  The script
    # generator is expected to produce speech-ready text; this is a final
    # non-destructive guard for direct TTS invocations that bypass script_qa.
    from .vendor_template_v2.script_tts_risk import analyze_script_text
    risk_report = analyze_script_text(text)
    blocking_risks = [
        item for item in risk_report["findings"] if item["severity"] == "blocking"
    ]
    if blocking_risks:
        preview = "; ".join(
            f"slide {item.get('slide')}: {item['kind']} {item['text']!r}"
            for item in blocking_risks[:6]
        )
        raise RuntimeError(
            "Narration contains TTS-ambiguous text. Regenerate or revise the "
            f"narration before synthesis. Findings: {preview}"
        )
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

        def say(narration: str, number: int, *, final_round: bool = False) -> bytes:
            if use_watchdog:
                return _gemini_say_with_watchdog(
                    narration,
                    number,
                    model,
                    voice,
                    allow_chunking=final_round,
                    attempts_override=1,
                )
            return call_with_client_failover(
                create_gemini_client,
                lambda client: _gemini_say(client, narration, model, voice),
                label=f"Gemini TTS slide{number}",
                max_retries=0,
            )
    elif provider == "chirp3":
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()  # Use ADC / GOOGLE_APPLICATION_CREDENTIALS
        chirp_voice = voice if "Chirp3-HD" in voice else "en-US-Chirp3-HD-Aoede"
        say = lambda narration, number, final_round=False: _chirp_say(client, narration, chirp_voice)
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

    queue_rounds = max(1, int(os.environ.get("MICROGEN_TTS_QUEUE_ROUNDS", "3")))
    pending = [(number, narration) for number, narration in items]
    last_failures: dict[int, BaseException] = {}

    # Do not hammer one slide repeatedly during a transient provider outage.
    # Each slide gets one request per round. Transient failures move to the end
    # of the queue so later slides can make progress and successful WAVs survive.
    for round_number in range(1, queue_rounds + 1):
        if not pending:
            break
        next_pending: list[tuple[int, str]] = []
        consecutive_transient_failures = 0
        circuit_breaker_failures = max(
            1,
            int(os.environ.get("MICROGEN_TTS_QUEUE_CIRCUIT_BREAKER_FAILURES", "2")),
        )
        print(
            f"[tts] queue round {round_number}/{queue_rounds}: "
            f"{len(pending)} slide(s) pending",
            flush=True,
        )

        for index, (number, narration) in enumerate(pending):
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
                payload = say(
                    narration,
                    number,
                    final_round=(round_number == queue_rounds),
                )
                if not payload.startswith((b"RIFF", b"RF64")):
                    raise RuntimeError(f"slide{number}: TTS did not return a WAV file")
                partial = candidate / f"slide{number}.wav.partial"
                partial.write_bytes(payload)
                if partial.stat().st_size <= 44:
                    partial.unlink(missing_ok=True)
                    raise RuntimeError(f"slide{number}: audio is empty")
                partial.replace(dest)
                last_failures.pop(number, None)
                consecutive_transient_failures = 0
                print(f"[tts] prepared {dest.name} ({len(payload)} bytes)", flush=True)
            except Exception as exc:
                last_failures[number] = exc
                if _is_transient_tts_failure(exc) and round_number < queue_rounds:
                    consecutive_transient_failures += 1
                    next_pending.append((number, narration))
                    print(
                        f"[tts] slide{number} transient failure: "
                        f"{type(exc).__name__}: {exc}; deferred to a later queue round",
                        flush=True,
                    )
                    if (
                        consecutive_transient_failures >= circuit_breaker_failures
                        and index + 1 < len(pending)
                    ):
                        remaining = pending[index + 1 :]
                        next_pending.extend(remaining)
                        print(
                            f"[tts] circuit breaker opened after "
                            f"{consecutive_transient_failures} consecutive transient "
                            f"failure(s); deferring {len(remaining)} untried slide(s)",
                            flush=True,
                        )
                        break
                    continue
                print(
                    f"[tts] slide{number} final failure: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )

        if not next_pending:
            pending = []
            break

        # Only transient failures are eligible for another round.
        pending = next_pending
        if pending and round_number < queue_rounds:
            delay = _tts_queue_delay_seconds(round_number)
            print(
                f"[tts] cooling down {delay:.0f}s before retrying "
                f"{len(pending)} deferred slide(s)",
                flush=True,
            )
            if delay:
                time.sleep(delay)

    unresolved = []
    for number, _narration in items:
        dest = candidate / f"slide{number}.wav"
        if not (dest.is_file() and dest.stat().st_size > 44):
            exc = last_failures.get(number, RuntimeError("no completed WAV"))
            unresolved.append((number, exc))
    if unresolved:
        details = "; ".join(
            f"slide{number}: {type(exc).__name__}: {exc}"
            for number, exc in unresolved
        )
        raise RuntimeError(
            f"TTS queue exhausted with {len(unresolved)} unresolved slide(s): {details}"
        )
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

    manifest = {
        "version": 1,
        "provider": provider,
        "model": model,
        "voice": voice,
        "slides": [
            {
                "slide": number,
                "source_text": narration,
                "tts_text": narration,
            }
            for number, narration in items
        ],
    }
    (folder / "tts_input_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
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
