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
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path

from .runner import blocks

_LAST_PROVIDER_REQUEST_ID: ContextVar[str | None] = ContextVar(
    "microgen_tts_actual_provider_request_id", default=None)

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


def _gemini_say(client, text: str, model: str, voice: str,
                *, request_observation: dict | None = None) -> bytes:
    # Gemini 3.8 Flash/Flash-Lite TTS is an Interactions audio endpoint,
    # not the legacy generate_content model. The adapter returns real
    # mono 16-bit PCM WAV and never invents words/voice proof.
    if model in ("gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"):
        from .gemini38_tts_interactions import generate_3_8_kore_wav
        return generate_3_8_kore_wav(
            client, text, model, voice,
            request_observation=request_observation)
    response = client.models.generate_content(
        model=model,
        contents=[{"role": "user", "parts": [
            {"text": text, "speech_metadata": {"style": STYLE}}
        ]}],
        config={"response_modalities": ["AUDIO"],
                "speech_config": {"voice_config": {"voice": voice}}},
    )
    if request_observation is not None:
        from .tts_attempt_evidence import safe_provider_request_id
        request_observation["provider_request_id"] = safe_provider_request_id(response)
    return _wav_bytes(response)


def _gemini_failover_request(text: str, number: int, model: str, voice: str,
                             *, request_observation: dict | None = None) -> bytes:
    from gemini_keys import call_with_client_failover, create_gemini_client
    return call_with_client_failover(
        create_gemini_client,
        lambda client: (
            _gemini_say(client, text, model, voice)
            if request_observation is None else
            _gemini_say(client, text, model, voice,
                        request_observation=request_observation)),
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


def _tts_child_request_env(timeout_seconds: float) -> dict[str, str]:
    """Bound SDK per-key retries *inside* the outer TTS process watchdog.

    In the October 2026 Dell campaign the inner SDK's 120-second request
    timeout exceeded a 105-second outer child-process deadline. That killed
    requests before a second configured API key could be attempted, despite
    successful TTS on the other PCs. Reserve 25% of the outer budget for
    client startup, failover and shutdown, and divide the remainder among
    configured keys. Do not expose key values or relax narration QA.
    """
    from gemini_keys import get_gemini_api_keys

    env = os.environ.copy()
    configured_keys = max(1, len(get_gemini_api_keys()))
    budget_ms = max(
        1_000,
        int(timeout_seconds * 0.75 * 1000 / configured_keys),
    )
    requested_ms = int(env.get("MICROGEN_GEMINI_REQUEST_TIMEOUT_MS", "120000"))
    env["MICROGEN_GEMINI_REQUEST_TIMEOUT_MS"] = str(
        min(max(1_000, requested_ms), budget_ms)
    )
    env["MICROGEN_GEMINI_SDK_RETRY_ATTEMPTS"] = "1"
    env["MICROGEN_GEMINI_MAX_RETRIES"] = "0"
    env["MICROGEN_GEMINI_TRANSIENT_RETRIES_PER_KEY"] = "1"
    return env


def _modern_tts_worker_python(model: str) -> str:
    """Use configured isolated Windows SDK for 3.8 audio with preflight.

    No billable request may be sent from a legacy SDK 1.x interpreter.
    MICROGEN_TTS_WORKER_PYTHON belongs in per-device AppData Microvid .env
    and must not be hardcoded to a specific protected/dirty working tree.
    """
    if model not in ("gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"):
        return sys.executable
    selected = os.environ.get("MICROGEN_TTS_WORKER_PYTHON", "").strip()
    if not selected:
        from .gemini38_tts_interactions import require_modern_tts_sdk
        require_modern_tts_sdk()
        return sys.executable
    python = Path(selected).expanduser().absolute()
    if not python.is_file() or python.is_symlink():
        raise RuntimeError(
            "MICROGEN_TTS_WORKER_PYTHON is not a real isolated Windows Python executable")
    # No prompts, credentials or provider calls in this subprocess.
    check = (
        "import importlib.metadata as m;from google.genai import types;"
        "v=tuple(int(p) for p in m.version('google-genai').split('.')[:2]);"
        "assert (2,25)<=v<(3,0) and hasattr(types,'HttpRetryOptions')"
    )
    try:
        result = subprocess.run(
            [str(python), "-c", check],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(
            "Configured isolated Gemini TTS worker unavailable; no paid request sent"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(
            "Configured isolated Gemini TTS worker lacks google-genai>=2.25,<3; "
            "no provider request sent")
    return str(python)


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
    _LAST_PROVIDER_REQUEST_ID.set(None)
    timeout_seconds = _tts_timeout_seconds(text)
    attempts = (
        max(1, int(attempts_override))
        if attempts_override is not None
        else max(1, int(os.environ.get("MICROGEN_TTS_REQUEST_ATTEMPTS", "3")))
    )
    label = request_label or f"slide{number}"
    # Isolated SDK/version gate must run BEFORE first attempt or any fallback.
    worker_python = _modern_tts_worker_python(model)
    last_error: BaseException | None = None
    timed_out_attempts = 0

    for attempt in range(1, attempts + 1):
        with tempfile.TemporaryDirectory(prefix=f"microgen_tts_slide{number}_") as tmp:
            output = Path(tmp) / "result.wav"
            evidence_output = Path(tmp) / "request_observation.json"
            command = [
                worker_python,
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
                "--evidence-output",
                str(evidence_output),
                "--confirm-gemini-api-cost",
            ]
            try:
                completed = subprocess.run(
                    command,
                    input=text,
                    text=True,
                    capture_output=True,
                    timeout=timeout_seconds,
                    env=_tts_child_request_env(timeout_seconds),
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
                    if evidence_output.is_file() or evidence_output.is_symlink():
                        from .tts_worker_evidence import read_observation
                        _LAST_PROVIDER_REQUEST_ID.set(
                            read_observation(evidence_output, outcome="success"))
                    return payload

            observed_request_id = None
            if evidence_output.is_file() or evidence_output.is_symlink():
                from .tts_worker_evidence import read_observation
                observed_request_id = read_observation(
                    evidence_output, outcome="exception")
            detail = (completed.stderr or completed.stdout or "").strip()
            last_error = RuntimeError(
                f"Gemini TTS {label} worker failed on attempt {attempt}/{attempts}"
                + (f": {detail}" if detail else "")
            )
            if observed_request_id is not None:
                last_error.request_id = observed_request_id
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
            # Multiple chunks are separate provider requests. Their combined
            # slide WAV has no single provider request ID to claim.
            _LAST_PROVIDER_REQUEST_ID.set(None)
            return _merge_wav_payloads(payloads)

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Gemini TTS {label} failed without a result")


def _configure_cloud_adc_from_microvid() -> Path | None:
    """Point Google Cloud clients at Microvid's standard credential file when ADC is unset."""
    configured = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if configured:
        path = Path(configured)
        return path if path.is_file() else None

    roots: list[Path] = []
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        roots.append(Path(local))
    roots.append(Path.home() / "AppData" / "Local")

    filename = "google_cloud_" + "credentials.json"
    for root in roots:
        path = root / "Microvid" / filename
        if path.is_file():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(path)
            print(
                f"[tts] using Google Cloud credentials from Microvid config: {path}",
                flush=True,
            )
            return path
    return None


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
        "invalid wav", "not return a wav", "audio is empty",
        "malformed audio", "pcm format", "invalid audio",
    )
    if any(marker in message for marker in permanent_markers):
        return False
    # An arbitrary RuntimeError is NOT evidence of a provider outage and
    # must not trigger separately billable Cloud speech.
    return any(marker in message for marker in transient_markers)


def _tts_queue_delay_seconds(round_number: int) -> float:
    explicit = os.environ.get("MICROGEN_TTS_QUEUE_DELAY_SECONDS", "").strip()
    if explicit:
        return max(0.0, float(explicit))
    base = max(0.0, float(os.environ.get("MICROGEN_TTS_QUEUE_BASE_DELAY_SECONDS", "30")))
    maximum = max(base, float(os.environ.get("MICROGEN_TTS_QUEUE_MAX_DELAY_SECONDS", "300")))
    return min(maximum, base * (2 ** max(0, round_number - 1)))


def _named_voice(voice: str) -> str:
    return voice.split("-")[-1] if "Chirp3-HD-" in voice else voice


def _fallback_specs(provider: str, model: str, voice: str) -> list[dict[str, str]]:
    """Owner-approved full-batch fallback order; NEVER mix different voices."""
    # Restore the original same-named-voice fallback policy. The normal
    # Flash-Lite/Kore pipeline must use Cloud Chirp3-HD-Kore, never Corey.
    chirp = {"provider": "chirp3", "model": "chirp3-hd",
             "voice": f"en-US-Chirp3-HD-{_named_voice(voice)}"}
    if provider == "gemini" and model == "gemini-3.8-flash-lite-tts":
        return [
            {"provider": "gemini", "model": "gemini-3.8-flash-tts", "voice": voice},
            chirp,
        ]
    if provider == "gemini" and model == "gemini-3.8-flash-tts":
        return [chirp]
    return []

def _chirp_say_with_watchdog(
    text: str,
    number: int,
    voice: str,
    *,
    timeout_seconds: float | None = None,
) -> bytes:
    _configure_cloud_adc_from_microvid()
    timeout_seconds = timeout_seconds or max(
        60.0,
        float(os.environ.get("MICROGEN_CHIRP_TTS_HARD_TIMEOUT_SECONDS", "180")),
    )
    _LAST_PROVIDER_REQUEST_ID.set(None)
    with tempfile.TemporaryDirectory(prefix=f"microgen_chirp_slide{number}_") as tmp:
        output = Path(tmp) / "result.wav"
        evidence_output = Path(tmp) / "request_observation.json"
        command = [
            sys.executable,
            "-m",
            "selenium_pipeline.tts_worker",
            "--provider",
            "chirp3",
            "--output",
            str(output),
            "--model",
            "chirp3-hd",
            "--voice",
            voice,
            "--number",
            str(number),
            "--evidence-output",
            str(evidence_output),
            "--confirm-google-cloud-tts-cost",
        ]
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=os.environ.copy(),
            start_new_session=(os.name != "nt"),
            creationflags=creationflags,
        )
        try:
            worker_output, _ = proc.communicate(input=text, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                try:
                    os.killpg(proc.pid, 9)
                except Exception:
                    proc.kill()
            raise TimeoutError(
                f"Chirp3 TTS slide{number} exceeded hard timeout of "
                f"{timeout_seconds:.0f}s"
            )
        if proc.returncode != 0 or not output.is_file():
            observed_request_id = None
            if evidence_output.is_file() or evidence_output.is_symlink():
                from .tts_worker_evidence import read_observation
                observed_request_id = read_observation(
                    evidence_output, outcome="exception")
            error = RuntimeError(
                f"Chirp3 TTS slide{number} failed: {(worker_output or '')[-1200:]}"
            )
            if observed_request_id is not None:
                error.request_id = observed_request_id
            raise error
        if evidence_output.is_file() or evidence_output.is_symlink():
            from .tts_worker_evidence import read_observation
            _LAST_PROVIDER_REQUEST_ID.set(
                read_observation(evidence_output, outcome="success"))
        payload = output.read_bytes()
        if not payload.startswith((b"RIFF", b"RF64")):
            raise RuntimeError(f"Chirp3 TTS slide{number} did not return WAV")
        return payload


def _fallback_payload(
    narration: str,
    number: int,
    spec: dict[str, str],
) -> bytes:
    if spec["provider"] == "gemini":
        return _gemini_say_with_watchdog(
            narration,
            number,
            spec["model"],
            spec["voice"],
            allow_chunking=True,
            request_label=f"slide{number} fallback {spec['model']}",
            attempts_override=1,
        )
    if spec["provider"] == "chirp3":
        return _chirp_say_with_watchdog(narration, number, spec["voice"])
    raise ValueError(f"Unsupported fallback provider: {spec['provider']}")


def _stream_batch_fallback_progress(proc: subprocess.Popen, timeout: float) -> str:
    """Relay batch TTS progress so the parent worker's idle watch can see it.

    communicate() captured the entire fallback output until exit. On Dell a
    running fallback with multiple slides emitted *nothing* to its parent
    for 900 seconds and the stage watchdog killed good in-progress work.
    Keep a bounded tail for failure messages without buffering all output.
    """
    import queue
    import threading

    messages: queue.Queue[str | None] = queue.Queue()

    def reader() -> None:
        try:
            if proc.stdout is not None:
                for line in proc.stdout:
                    messages.put(line)
        finally:
            messages.put(None)

    threading.Thread(target=reader, daemon=True).start()
    deadline = time.monotonic() + timeout
    last_heartbeat = time.monotonic()
    tail: list[str] = []
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(proc.args, timeout)
        try:
            line = messages.get(timeout=min(1.0, remaining))
        except queue.Empty:
            if time.monotonic() - last_heartbeat >= 60:
                print("[tts] whole-batch fallback still running", flush=True)
                last_heartbeat = time.monotonic()
            continue
        if line is None:
            break
        cleaned = line.rstrip()
        print(f"[tts batch] {cleaned}", flush=True)
        tail.append(cleaned)
        if len(tail) > 35:
            tail.pop(0)
        last_heartbeat = time.monotonic()
    proc.wait(timeout=max(0.1, deadline - time.monotonic()))
    if proc.stdout is not None:
        proc.stdout.close()
    return "\n".join(tail)[-1800:]


class TTSFallbackModelExhausted(RuntimeError):
    """Provider/model retries failed, unlike disk/config/provenance errors."""


def _whole_batch_fallback(
    folder: Path,
    items: list[tuple[int, str]],
    spec: dict[str, str],
    *,
    requested: dict[str, str],
    completed_gemini_models: tuple[str, ...],
    attempt_evidence=None,
) -> dict[int, dict[str, object]]:
    """Complete one *entire* fallback batch isolated; keep original candidates.

    Never delete/replace incomplete primary WAVs or mix Kore/Cloud voices.
    Cloud is reachable only when both Gemini queues have been exhausted.
    No partial batch gets published to the final lecture folder.
    """
    from .tts_billing_guard import require_tts_cost_authorization

    # The manifest alone cannot authorize fallback: independently inspect
    # source-linked call outcomes preserved during the original model runs.
    if attempt_evidence is None:
        raise RuntimeError("Missing observed retry-attempt evidence; no paid fallback")
    exhausted_proof = attempt_evidence.verify_before(spec["provider"], spec["model"])
    if tuple(completed_gemini_models) != (
            ("gemini-3.8-flash-lite-tts",)
            if spec["provider"] == "gemini"
            else ("gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts")):
        raise RuntimeError("Claimed fallback chain differs from observed model order")

    if spec["provider"] == "chirp3":
        # Regression guard: automatic Cloud fallback is required to preserve
        # the ORIGINAL selected Kore voice, not the mistaken Corey string.
        # Reject a stale/default-corrupt spec BEFORE any billable Cloud call.
        from .tts_effective_identity import CLOUD, DEFAULT
        if spec != CLOUD or requested != DEFAULT:
            raise RuntimeError(
                "Unapproved Cloud fallback voice; original contract requires "
                "en-US-Chirp3-HD-Kore after Gemini Flash-Lite/Kore and Flash/Kore")
        required = {"gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"}
        if not required.issubset(set(completed_gemini_models)):
            raise RuntimeError(
                "Cloud TTS not authorized: both Gemini models must exhaust "
                "their three-attempt queues first")
        require_tts_cost_authorization(
            "chirp3", conditional_cloud_fallback=True)
    else:
        if spec["provider"] != "gemini" or spec["model"] != "gemini-3.8-flash-tts":
            raise RuntimeError("Unapproved TTS fallback provider/model")
        require_tts_cost_authorization("gemini", routine_gemini=True)

    # No rewriting any final files, even if a downstream owner already put
    # an unrecognized or partial WAV in the original subchapter.
    from .tts_candidate_integrity import reject_existing_final_audio
    reject_existing_final_audio(folder)
    with tempfile.TemporaryDirectory(prefix="microgen_tts_full_fallback_",
                                     dir=str(folder)) as tmp:
        batch = Path(tmp)
        (batch / "script.txt").write_bytes((folder / "script.txt").read_bytes())
        try:
            _synthesize_folder_unlocked(
                batch, spec["provider"], spec["model"], spec["voice"],
                allow_fallback=False, attempt_evidence=attempt_evidence)
        except RuntimeError as exc:
            if "queue exhausted" in str(exc) and "slide" in str(exc):
                raise TTSFallbackModelExhausted(
                    f"{spec['provider']}:{spec['model']} exhausted its retries") from exc
            raise
        expected = [f"slide{number}.wav" for number, _ in items]
        if sorted(expected) != sorted(p.name for p in batch.glob("slide[0-9]*.wav")):
            raise RuntimeError("Fallback did not render every slide exactly once")
        raw = (batch / "tts_input_manifest.json").read_bytes()
        metadata = json.loads(raw)
        if (metadata.get("primary") != spec
                or len(metadata.get("slides", [])) != len(items)):
            raise RuntimeError("Fallback audio/manifest identity is incomplete")
        for row, (number, narration) in zip(metadata["slides"], items):
            if (row.get("slide") != number
                    or row.get("tts_text") != narration
                    or row.get("model") != spec["model"]
                    or row.get("voice") != spec["voice"]
                    or row.get("provider") != spec["provider"]):
                raise RuntimeError("Fallback text, provider, or voice drift")
            row.update({
                "fallback_used": True,
                "primary_provider": requested["provider"],
                "primary_model": requested["model"],
                "primary_voice": requested["voice"],
                "voice_consistency": {
                    "mode": "full_batch_single_engine_voice",
                    "cross_model_voice_equivalence_verified": False,
                    "independent_listening_required": True,
                },
            })
        metadata["requested_primary"] = requested
        metadata["fallback_chain"] = list(completed_gemini_models)
        metadata["all_slides_one_effective_voice"] = True
        metadata["attempt_evidence"] = {
            "path": ".tts_attempt_evidence",
            "sha256": attempt_evidence.tip(),
            "effective_model": spec["model"],
            "observed_failed_models": exhausted_proof,
        }
        payload = (json.dumps(metadata, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        new_files = []
        try:
            for name in expected:
                wav = batch / name
                from .tts_pcm_contract import verify_pcm
                verify_pcm(wav.read_bytes(), label=f"fallback {name}")
                with wav.open("rb") as source, (folder / name).open("xb") as dest:
                    new_files.append(folder / name)
                    shutil.copyfileobj(source, dest)
            with (folder / "tts_input_manifest.json").open("xb") as out:
                new_files.append(folder / "tts_input_manifest.json")
                out.write(payload)
        except BaseException:
            # Roll back only files *this call* created. Never touch any
            # pre-existing lectures or the partially successful primary cache.
            for newly_written in reversed(new_files):
                newly_written.unlink(missing_ok=True)
            raise
    return {
        number: {**spec, "fallback_used": True,
                 "primary_provider": requested["provider"],
                 "primary_model": requested["model"],
                 "primary_voice": requested["voice"]}
        for number, _ in items
    }


def _synthesize_folder_unlocked(folder: Path, provider: str, model: str, voice: str, *, allow_fallback: bool = True, attempt_evidence=None) -> None:
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
    # No paid requests, credentials, candidate mkdir or repair attempt can
    # precede this immutable final-output guard. Previously the runner could
    # synthesize an entire batch before discovering a protected WAV collision.
    from .tts_candidate_integrity import reject_existing_final_audio
    reject_existing_final_audio(folder)
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
        # Always isolate Cloud requests behind the bounded process watchdog,
        # including conditional fallback on slower Dell-115 and Yoga6. Never
        # launch a Cloud API request in the coordinator process directly.
        chirp_voice = voice if "Chirp3-HD" in voice else f"en-US-Chirp3-HD-{_named_voice(voice)}"
        def say(narration: str, number: int, *, final_round: bool = False) -> bytes:
            return _chirp_say_with_watchdog(narration, number, chirp_voice)
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")

    from .tts_candidate_integrity import (
        job_identity, prepare as prepare_candidate,
        record_one, verify_one,
    )
    candidate = folder / ".tts_candidate"
    candidate.mkdir(parents=True, exist_ok=True)
    expected_names = {f"slide{n}.wav" for n, _ in items}
    candidate_identity = job_identity(
        items, provider=provider, model=model, voice=voice,
        script_sha256=__import__("hashlib").sha256(
            (folder / "script.txt").read_bytes()).hexdigest(),
    )
    # Never trust a RIFF header alone: old Flash, Chirp or changed-script
    # candidates would otherwise be silently relabeled as Flash-Lite/Kore.
    # All legacy/partial mismatches are preserved for explicit review.
    prepare_candidate(candidate, candidate_identity)

    # For an original production run, bind immutable observed call outcomes
    # to the exact source script before the first provider call. An ephemeral
    # whole-batch fallback passes this SAME root ledger explicitly.
    if attempt_evidence is None and allow_fallback and provider == "gemini":
        from .tts_attempt_evidence import AttemptEvidence
        attempt_evidence = AttemptEvidence(folder, items)

    # Never transition to a paid fallback after fewer than three primary
    # attempts. Test-only / explicitly disabled fallback can use shorter runs.
    automatic_fallback = (
        allow_fallback and provider == "gemini"
        and os.environ.get("MICROGEN_TTS_ENABLE_PROVIDER_FALLBACK", "1") != "0"
        and os.environ.get("MICROGEN_TTS_ENABLE_BATCH_FALLBACK", "1") != "0")
    # Preserve the owner's minimum three-round TTS retry contract even if
    # automatic fallback is explicitly disabled. A disabled circuit breaker
    # may still defer later slides to the subsequent round.
    queue_rounds = max(3, int(os.environ.get("MICROGEN_TTS_QUEUE_ROUNDS", "3")))
    pending = [(number, narration) for number, narration in items]
    last_failures: dict[int, BaseException] = {}
    attempts_by_slide: dict[int, int] = {}
    primary_spec = {"provider": provider, "model": model, "voice": voice}
    slide_provenance: dict[int, dict[str, object]] = {}

    # Recover ONLY genuine immutable provider-call outcomes. A restarted
    # Windows subprocess must not repeat three known-bad requests, falsely
    # count untried slides, or lose valid original Kore WAV candidates.
    prior_verified_exhaustion = False
    if attempt_evidence is not None and provider == "gemini":
        prior = attempt_evidence.read()
        histories: dict[int, list[dict]] = {}
        for event in prior:
            if event["provider"] == provider and event["model"] == model:
                histories.setdefault(event["slide"], []).append(event)
        for number, history in histories.items():
            dest = candidate / f"slide{number}.wav"
            outcomes = [event["outcome"] for event in history]
            if "permanent_failure" in outcomes:
                raise RuntimeError(
                    f"Recorded permanent error for slide{number}; "
                    "do not resume automatically or spend on fallback")
            if "success" in outcomes:
                if (outcomes.count("success") != 1
                        or outcomes[-1] != "success"
                        or not dest.is_file() or dest.is_symlink()):
                    raise RuntimeError(
                        f"Recorded success of slide{number} lacks a coherent "
                        "immutable retry sequence or verified candidate WAV")
                verify_one(candidate, dest.name, candidate_identity)
                slide_provenance[number] = {**primary_spec, "fallback_used": False}
                continue
            if dest.exists() or dest.is_symlink():
                raise RuntimeError(
                    f"Only failed slide{number} requests are recorded, "
                    "but an unaccounted candidate exists; stop")
            if outcomes and all(x == "transient_failure" for x in outcomes):
                attempts_by_slide[number] = len(outcomes)
                last_failures[number] = TimeoutError(
                    f"Observed source-bound provider outage for slide{number} "
                    f"already logged {len(outcomes)} real call(s)")
        prior_verified_exhaustion = any(
            count >= queue_rounds and
            not (candidate / f"slide{number}.wav").exists()
            for number, count in attempts_by_slide.items())
        if prior_verified_exhaustion:
            # Verify the ledger's real 3-call chain BEFORE skipping Lite.
            attempt_evidence.verify_exhausted(model,minimum_attempts=3)
            print(
                "[tts] verified hash-linked previously exhausted provider "
                "requests; do not repeat Lite attempts; advancing to "
                "approved single-voice complete-batch fallback",
                flush=True,
            )

    # Do not hammer one slide repeatedly during a transient provider outage.
    # Each slide gets one request per round. Transient failures move to the end
    # of the queue so later slides can make progress and successful WAVs survive.
    for round_number in range(1, queue_rounds + 1):
        if prior_verified_exhaustion:
            break
        if not pending:
            break
        next_pending: list[tuple[int, str]] = []
        consecutive_transient_failures = 0
        # Real provider outages must not cause all later slides to consume
        # minute-long timeouts. The hash-chained journal proves three actual
        # transient attempts for a failed slide before full-batch fallback.
        # An untried slide is NEVER recorded as a failed provider call.
        circuit_breaker_failures = max(1, int(os.environ.get(
            "MICROGEN_TTS_QUEUE_CIRCUIT_BREAKER_FAILURES", "2")))
        print(
            f"[tts] queue round {round_number}/{queue_rounds}: "
            f"{len(pending)} slide(s) pending",
            flush=True,
        )

        for index, (number, narration) in enumerate(pending):
            dest = candidate / f"slide{number}.wav"
            if dest.exists() or dest.is_symlink():
                verify_one(candidate, dest.name, candidate_identity)
                slide_provenance.setdefault(
                    number,
                    {**primary_spec, "fallback_used": False},
                )
                print(f"[tts] reusing verified {dest.name} ({dest.stat().st_size} bytes)",
                      flush=True)
                continue

            if attempts_by_slide.get(number,0) >= round_number:
                # This request already failed and is saved in the original
                # source-locked evidence journal. Reuse the failure receipt;
                # never add a fictitious new provider-call event.
                if round_number < queue_rounds:
                    next_pending.append((number,narration))
                continue
            print(f"[tts] requesting slide{number} ({len(narration)} chars)", flush=True)
            try:
                attempts_by_slide[number] = attempts_by_slide.get(number, 0) + 1
                _LAST_PROVIDER_REQUEST_ID.set(None)
                payload = say(
                    narration,
                    number,
                    # A global outage (previous slide already timed out)
                    # must not cause 3 more long chunk attempts. Chunk only
                    # when a lone long narration genuinely needs splitting.
                    final_round=(round_number == queue_rounds
                                 and consecutive_transient_failures == 0),
                )
                if not payload.startswith((b"RIFF", b"RF64")):
                    raise RuntimeError(f"slide{number}: TTS did not return a WAV file")
                partial = candidate / f"slide{number}.wav.partial"
                with partial.open("xb") as out:
                    out.write(payload)
                if partial.stat().st_size <= 44:
                    raise RuntimeError(f"slide{number}: audio is empty")
                partial.replace(dest)
                record_one(candidate, dest.name, candidate_identity)
                if attempt_evidence is not None:
                    attempt_evidence.record(
                        provider=provider, model=model, slide=number,
                        round_number=round_number, outcome="success",
                        provider_request_id=_LAST_PROVIDER_REQUEST_ID.get())
                last_failures.pop(number, None)
                slide_provenance[number] = {**primary_spec, "fallback_used": False}
                consecutive_transient_failures = 0
                print(f"[tts] prepared {dest.name} ({len(payload)} bytes)", flush=True)
            except Exception as exc:
                if attempt_evidence is not None:
                    from .tts_attempt_evidence import safe_provider_request_id
                    attempt_evidence.record(
                        provider=provider, model=model, slide=number,
                        round_number=round_number,
                        outcome=("transient_failure" if _is_transient_tts_failure(exc)
                                 else "permanent_failure"),
                        error_type=type(exc).__name__,
                        provider_request_id=safe_provider_request_id(exc))
                last_failures[number] = exc
                if _is_transient_tts_failure(exc):
                    consecutive_transient_failures += 1
                    if round_number < queue_rounds:
                        next_pending.append((number, narration))
                    print(
                        f"[tts] slide{number} transient failure: "
                        f"{type(exc).__name__}: {exc}; "
                        + ("deferred to a later queue round"
                           if round_number < queue_rounds
                           else "last configured primary round"),
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
    narration_by_slide = dict(items)
    for number, _narration in items:
        dest = candidate / f"slide{number}.wav"
        if not (dest.is_file() and dest.stat().st_size > 44):
            exc = last_failures.get(number, RuntimeError("no completed WAV"))
            unresolved.append((number, exc))

    # Approved escalation is by WHOLE BATCH, never interleave narrators.
    # Lite: 3 queue rounds -> Flash: 3 queue rounds -> Cloud Chirp HD.
    # Flash: 3 queue rounds -> Cloud Chirp HD.
    # A failed attempt preserves all verified primary WAV candidates.
    exhausted_real_slide = any(
        attempts_by_slide.get(number, 0) >= 3
        and _is_transient_tts_failure(exc)
        for number, exc in unresolved)
    observed_permanent = any(
        number in last_failures and not _is_transient_tts_failure(exc)
        for number, exc in unresolved)
    if (unresolved and automatic_fallback
            and exhausted_real_slide and not observed_permanent
            and os.environ.get("MICROGEN_TTS_ENABLE_PROVIDER_FALLBACK", "1") != "0"
            and os.environ.get("MICROGEN_TTS_ENABLE_BATCH_FALLBACK", "1") != "0"):
        requested = {"provider": provider, "model": model, "voice": voice}
        exhausted = [model]
        errors = []
        for spec in _fallback_specs(provider, model, voice):
            if spec["provider"] == "chirp3":
                # Flash was attempted and exhausted only if it is listed here.
                # Starting directly on Flash also counts as owner-selected
                # Flash after its own complete three-round exhaustion; Cloud
                # still requires documented Lite exhaustion in the same job.
                if "gemini-3.8-flash-lite-tts" not in exhausted:
                    errors.append("Cloud blocked: Lite failure not proven in this job")
                    break
            print(f"[tts] escalating full batch to "
                  f"{spec['provider']}:{spec['model']}:{spec['voice']}",flush=True)
            try:
                _whole_batch_fallback(
                    folder, items, spec, requested=requested,
                    completed_gemini_models=tuple(exhausted),
                    attempt_evidence=attempt_evidence)
            except TTSFallbackModelExhausted as exc:
                errors.append(
                    f"{spec['provider']}:{spec['model']} "
                    f"{type(exc).__name__}: {exc}")
                if spec["provider"] == "gemini":
                    exhausted.append(spec["model"])
                continue
            except Exception as exc:
                # Never spend Cloud credits because Flash failed for reasons
                # unrelated to Gemini outages (disk full, credentials,
                # invalid script, malformed WAV, expired attestation).
                errors.append(
                    f"non-provider fallback fault {type(exc).__name__}: {exc}")
                break
            print(f"[tts] complete single-voice fallback batch accepted: "
                  f"{spec['provider']}:{spec['model']}; "
                  "independent listening still mandatory",flush=True)
            return
        if errors:
            unresolved = [(n, RuntimeError(
                f"{err}; whole-batch fallback attempts: " + " | ".join(errors)))
                for n,err in unresolved]

    if unresolved:
        details = "; ".join(
            f"slide{number}: {type(exc).__name__}: {exc}"
            for number, exc in unresolved
        )
        # Slides skipped by the outage breaker were never submitted.
        # They are unknown, not permanent provider failures.
        permanent = any(number in last_failures
                        and not _is_transient_tts_failure(exc)
                        for number, exc in unresolved)
        if permanent:
            raise RuntimeError(
                f"TTS permanent failure with {len(unresolved)} unresolved slide(s); "
                f"no provider escalation for invalid input/auth: {details}")
        raise RuntimeError(
            f"TTS queue exhausted with {len(unresolved)} unresolved slide(s); "
            f"approved fallback exhausted or unavailable. {details}"
        )
    # Verify complete frozen candidates BEFORE touching final audio or metadata.
    for number, narration in items:
        verify_one(candidate, f"slide{number}.wav", candidate_identity)
    for wav in candidate.glob("slide*.wav"):
        published = folder / wav.name
        if published.exists() or published.is_symlink():
            if (published.is_symlink() or not published.is_file()
                    or published.read_bytes() != wav.read_bytes()):
                raise RuntimeError(
                    "Existing final WAV differs; preserve output and candidate "
                    f"for reviewed replacement: {published.name}")
    # All responses have been validated; publish after the complete batch.
    stale = [p for p in folder.glob("slide*.wav") if p.name not in expected_names]
    if stale:
        from datetime import datetime, timezone
        old_dir = folder / ".history" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f") / "tts"
        old_dir.mkdir(parents=True, exist_ok=True)
        for item in stale:
            item.replace(old_dir / item.name)
    manifest = {
        "version": 2,
        "primary": {
            "provider": provider,
            "model": model,
            "voice": voice,
        },
        "slides": [
            {
                "slide": number,
                "source_text": narration,
                "tts_text": narration,
                **slide_provenance.get(
                    number,
                    {**primary_spec, "fallback_used": False},
                ),
            }
            for number, narration in items
        ],
    }
    receipt = folder / "tts_input_manifest.json"
    encoded_manifest = json.dumps(manifest, indent=2, ensure_ascii=False)
    if receipt.exists() or receipt.is_symlink():
        if receipt.is_symlink() or not receipt.is_file() or receipt.read_text(
                encoding="utf-8") != encoded_manifest:
            raise RuntimeError(
                "Existing TTS manifest differs; preserve both outputs for reviewed repair")
    # Previous WAVs/manifest were checked in advance; never replace distinct
    # final audio. Once all outputs are published, keep the candidate hashes.
    for wav in candidate.glob("slide*.wav"):
        target = folder / wav.name
        if target.exists():
            wav.unlink()  # exact byte equality already verified
        else:
            wav.replace(target)
    if not receipt.exists():
        with receipt.open("x", encoding="utf-8") as out:
            out.write(encoded_manifest)
    from uuid import uuid4
    audit_root = folder / ".tts_candidate_receipts"
    audit_root.mkdir(exist_ok=True)
    candidate.rename(audit_root / uuid4().hex)
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
    parser.add_argument("--confirm-gemini-api-cost", action="store_true",
                        help="Explicit authorization for metered Gemini TTS")
    parser.add_argument("--confirm-google-cloud-tts-cost", action="store_true",
                        help="Separate explicit authorization for Google Cloud Chirp TTS")
    args = parser.parse_args(argv)
    from .tts_billing_guard import require_tts_cost_authorization
    require_tts_cost_authorization(
        args.provider, gemini_approved=args.confirm_gemini_api_cost,
        cloud_approved=args.confirm_google_cloud_tts_cost,
        routine_gemini=(args.provider == "gemini"))
    # A direct `python -m selenium_pipeline.tts` subprocess must load the
    # same per-user AppData Microvid settings as the main pipeline runner.
    # Otherwise Gemini/Cloud credentials may exist but be unavailable to
    # this interpreter, causing a false 'No Gemini API key is loaded' error.
    # The loader never overwrites explicitly exported environment variables.
    from .runner import load_microvid_env
    load_microvid_env()
    synthesize_folder(args.folder, args.provider, args.model, args.voice)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
