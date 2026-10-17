"""Contract-locked, isolated Gemini 3.8 Flash-Lite/Kore Interactions TTS trial.

Default invocation is an OFFLINE preflight, with no key access or network.
A real API request requires three distinct affirmative command-line flags.
This is not a production worker, academic approval, or a browser fallback.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import io
import json
import re
import wave
from importlib import metadata
from pathlib import Path

MODEL = "gemini-3.8-flash-lite-tts"
VOICE = "Kore"
SENTENCE = "This is a synthetic speech test for the Kore narrator voice."
STYLE = "Clear, calm university teaching voice at a measured pace."
MIN_SDK = (2, 25, 0)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_new(path: Path, data: dict) -> None:
    with path.open("x", encoding="utf-8") as out:
        json.dump(data, out, indent=2, sort_keys=True)
        out.write("\n")


def sdk_preflight(version_override: str | None = None) -> dict:
    try:
        version = (version_override if version_override is not None
                   else metadata.version("google-genai"))
    except metadata.PackageNotFoundError:
        version = ""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    allowed = bool(match and tuple(map(int, match.groups())) >= MIN_SDK)
    return {"google_genai_version": version if match else None,
            "sdk_supports_documented_interactions": allowed,
            "sdk_minimum": "2.25.0"}


def interactions_request() -> dict:
    """Matches Google's documented non-streaming 3.8 TTS schema."""
    return {
        "model": MODEL,
        "input": [{"type": "user_input", "content": [
            {"type": "text", "text": SENTENCE,
             "annotations": [{"type": "speech_metadata", "style": STYLE}]}]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": VOICE}]},
    }


def verify_wav(response) -> tuple[bytes, dict]:
    """Never accept a made-up WAV header or decoded raw PCM as complete WAV."""
    audio = getattr(response, "output_audio", None)
    if audio is None:
        raise ValueError("Gemini Interactions returned no output_audio")
    content_type = getattr(audio, "mime_type", None)
    if content_type not in (None, "audio/wav"):
        raise ValueError("Unexpected Gemini audio MIME type")
    raw = getattr(audio, "data", None)
    if not isinstance(raw, (str, bytes)) or not raw:
        raise ValueError("Missing base64 audio data")
    try:
        payload = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid Gemini base64 audio data") from exc
    if len(payload) < 100 or payload[:4] != b"RIFF" or payload[8:12] != b"WAVE":
        raise ValueError("Gemini response is not a full RIFF/WAVE file")
    try:
        with wave.open(io.BytesIO(payload), "rb") as wav:
            channels, width, rate, compression = (
                wav.getnchannels(), wav.getsampwidth(),
                wav.getframerate(), wav.getcomptype())
            frames = wav.getnframes()
            samples = wav.readframes(frames)
    except (wave.Error, EOFError, ValueError) as exc:
        raise ValueError("Cannot decode Gemini WAV") from exc
    duration = frames / rate if rate else 0
    if (channels != 1 or width != 2 or rate != 24000
            or compression != "NONE" or not .2 < duration < 30
            or len(samples) != frames * channels * width
            or not any(samples)):
        raise ValueError("Invalid, truncated or silent Gemini WAV")
    return payload, {"sample_rate": rate, "channels": channels,
                     "sample_width_bytes": width,
                     "duration_seconds": round(duration, 3),
                     "audio_sha256": _sha(payload)}


def _authorized(live: bool, paid: bool, synthetic: bool) -> bool:
    if any((live, paid, synthetic)) and not all((live, paid, synthetic)):
        raise ValueError("Three explicit flags required: --confirm-live, "
                         "--confirm-gemini-api-cost, --confirm-synthetic-trial")
    return all((live, paid, synthetic))


def run_trial(output_dir: Path, *, confirm_live: bool = False,
              confirm_gemini_api_cost: bool = False,
              confirm_synthetic_trial: bool = False,
              source_root: Path | None = None,
              sdk_version_override: str | None = None,
              client_factory=None) -> dict:
    """No network by default; one explicitly authorized live request maximum."""
    authorized = _authorized(confirm_live, confirm_gemini_api_cost,
                             confirm_synthetic_trial)
    proposed = Path(output_dir)
    if proposed.is_symlink():
        raise ValueError("Symlink trial directory forbidden")
    folder = proposed.resolve()
    if folder.exists() or not folder.parent.is_dir():
        raise ValueError("Trial requires a NEW isolated directory")
    if source_root is not None and folder.is_relative_to(Path(source_root).resolve()):
        raise ValueError("Trial must not touch the protected source root")
    sdk = sdk_preflight(sdk_version_override)
    if authorized and not sdk["sdk_supports_documented_interactions"]:
        raise RuntimeError("google-genai >=2.25.0 required; no API requested")
    folder.mkdir()
    request = interactions_request()
    common = {
        "schema_version": 1,
        "model": MODEL, "voice": VOICE,
        "source": "fixed_non_course_synthetic_sentence",
        "text_sha256": _sha(SENTENCE.encode("utf-8")),
        "request_schema": "gemini_interactions_nonstreaming_audio",
        "request_sha256": _sha(json.dumps(request, sort_keys=True).encode("utf-8")),
        "academic_approval": False, "student_publication": False,
        "production_approved": False, "browser_tts_verified": False,
        "live_api_authorized": authorized, **sdk,
    }
    if not authorized:
        report = {**common, "status": "API_INTERACTIONS_PREFLIGHT_ONLY",
                  "api_request_started": False, "real_audio_generated": False}
        _write_new(folder / "preflight.json", report)
        return report
    # Record intent before API invocation. Do not retry a failed/ambiguous call.
    _write_new(folder / "request_intent.json",
               {**common, "status": "LIVE_SYNTHETIC_API_REQUEST_INTENDED",
                "max_requests": 1})
    client = None
    try:
        if client_factory is None:
            # Credentials are not accessed on the offline/preflight path.
            from .runner import load_microvid_env
            load_microvid_env()
            from gemini_keys import get_gemini_api_keys, create_gemini_client
            keys = get_gemini_api_keys()
            if not keys:
                raise RuntimeError("Gemini API credential unavailable; no request")
            # No failover across keys and no manual fallback to Google Cloud.
            # The installed creator must be independently configured for one SDK attempt.
            client = create_gemini_client(keys[0])
        else:
            client = client_factory()
        endpoint = getattr(getattr(client, "interactions", None), "create", None)
        if not callable(endpoint):
            raise RuntimeError("Installed client lacks Gemini Interactions.create")
        interaction = endpoint(**request)
        payload, metrics = verify_wav(interaction)
        with (folder / "synthetic_kore.wav").open("xb") as out:
            out.write(payload)
        report = {**common, "status": "SYNTHETIC_GEMINI_API_WAV_UNREVIEWED",
                  "api_request_started": True, "real_audio_generated": True,
                  "speech_content_verified_by_asr": False,
                  "voice_identity_acoustically_verified": False,
                  **metrics}
        _write_new(folder / "trial_receipt.json", report)
        return report
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--confirm-live", action="store_true")
    parser.add_argument("--confirm-gemini-api-cost", action="store_true")
    parser.add_argument("--confirm-synthetic-trial", action="store_true")
    args = parser.parse_args(argv)
    report = run_trial(args.output_dir, source_root=args.source_root,
                       confirm_live=args.confirm_live,
                       confirm_gemini_api_cost=args.confirm_gemini_api_cost,
                       confirm_synthetic_trial=args.confirm_synthetic_trial)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
