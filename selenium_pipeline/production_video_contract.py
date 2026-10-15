"""Strict acceptance for MicroGen narrated, highlighted, multipart lessons.

Historical single-file slides.mp4 may remain archived, but must never satisfy
this contract.  An MP4 and ordinary structural slide/WAV alignment are not
evidence that narration-time highlighting occurred.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import wave
from pathlib import Path

MAX_PART_DURATION_SECONDS = 600.0
PART_ID = re.compile(r"part_[0-9]{2}$")
HEX = re.compile(r"[0-9a-f]{64}$")


class VideoContractError(ValueError):
    """Reject incomplete, overlong or unproven narrated/highlighted parts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VideoContractError(message)


def _read_json(path: Path) -> dict:
    _require(path.is_file() and not path.is_symlink(), f"Required receipt missing: {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise VideoContractError(f"Invalid JSON in {path.name}") from exc
    _require(isinstance(obj, dict), f"Expected JSON object: {path.name}")
    return obj


def _hash(path: Path) -> str:
    _require(path.is_file() and not path.is_symlink(), f"Required file missing: {path}")
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _checked_hash(path: Path, value: object, label: str) -> None:
    _require(isinstance(value, str) and HEX.fullmatch(value) is not None,
             f"Invalid {label} hash")
    _require(_hash(path) == value, f"Stale or modified {label} file: {path}")


def _mp4_duration(path: Path, *, ffmpeg: str | None = None) -> float:
    """Measure actual MP4 container duration, never trust the JSON duration."""
    from .video_ffmpeg import ffmpeg_executable
    exe = ffmpeg or ffmpeg_executable()
    output = subprocess.run([exe, "-hide_banner", "-i", str(path)],
                            capture_output=True, text=True, errors="replace",
                            timeout=45, check=False)
    detail = output.stderr + output.stdout
    _require("Video:" in detail and "Audio:" in detail,
             "MP4 needs a video and an audio stream")
    matched = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", detail)
    _require(matched is not None, "Unable to measure MP4 duration")
    duration = int(matched[1]) * 3600 + int(matched[2]) * 60 + float(matched[3])
    _require(math.isfinite(duration), "Nonfinite video duration")
    return duration


def _events(data: dict, *, label: str, audio_ms: int) -> list[tuple]:
    events = data.get("events")
    _require(isinstance(events, list) and bool(events),
             f"{label} has no confirmed synchronized highlights")
    previous_end = 0
    result = []
    for row in events:
        _require(isinstance(row, dict), f"{label} has invalid event")
        start, end = row.get("start_ms"), row.get("end_ms")
        target, slide = row.get("target_id"), row.get("slide_id")
        _require(type(start) is int and type(end) is int
                 and 0 <= start < end <= audio_ms and start >= previous_end,
                 f"{label} has overlapping or out-of-range event")
        _require(isinstance(target, str) and bool(target.strip())
                 and isinstance(slide, str) and bool(slide.strip()),
                 f"{label} has unanchored event")
        previous_end = end
        result.append((slide, target, start, end))
    return result


def verify_series(folder: Path, *, probe=None) -> dict:
    """Fail closed on legacy output, fake timing, incomplete or overlong parts.

    An injected probe is supported only for deterministic offline unit tests.
    Production always inspects the actual MP4 container with FFmpeg.
    """
    root = Path(folder)
    manifest = _read_json(root / "lecture_completion.json")
    _require(manifest.get("schema_version") == 1
             and manifest.get("status") == "accepted_synchronized_series",
             "Lesson has no accepted multipart-and-highlight receipt")
    _checked_hash(root / "source.pdf", manifest.get("source_sha256"), "source")
    parts = manifest.get("parts")
    _require(isinstance(parts, list) and 1 <= len(parts) <= 40,
             "Expected one to forty finalized video parts")
    checked = []
    for i, reference in enumerate(parts, 1):
        _require(isinstance(reference, dict), "Invalid part reference")
        part_id = f"part_{i:02d}"
        _require(reference.get("part_id") == part_id
                 and PART_ID.fullmatch(part_id) is not None,
                 "Multipart indexes must be contiguous and ordered")
        location = root / part_id
        receipt_file = location / "part_receipt.json"
        _checked_hash(receipt_file, reference.get("receipt_sha256"),
                      f"{part_id} receipt")
        receipt = _read_json(receipt_file)
        _require(receipt.get("schema_version") == 1
                 and receipt.get("part_id") == part_id
                 and receipt.get("status") == "accepted_synchronized_part",
                 f"{part_id} lacks accepted synchronized-part proof")
        _require(receipt.get("renderer") == "audio_timed_highlight_renderer"
                 and not receipt.get("unverified"),
                 f"{part_id} is a static or experimental preview")
        video = location / f"{part_id}.mp4"
        audio = location / "narration.wav"
        cues_file = location / "visual_cues.json"
        timing_file = location / "narration_alignment.json"
        _checked_hash(video, receipt.get("mp4_sha256"), f"{part_id} MP4")
        _checked_hash(audio, receipt.get("audio_sha256"), f"{part_id} audio")
        _checked_hash(cues_file, receipt.get("visual_cues_sha256"),
                      f"{part_id} visual cues")
        _checked_hash(timing_file, receipt.get("alignment_sha256"),
                      f"{part_id} alignment")
        with wave.open(str(audio), "rb") as wav:
            audio_seconds = wav.getnframes() / wav.getframerate()
        _require(0 < audio_seconds < MAX_PART_DURATION_SECONDS,
                 f"{part_id} audio does not fit the strict ten-minute limit")
        audio_ms = round(audio_seconds * 1000)
        cues, timing = _read_json(cues_file), _read_json(timing_file)
        _require(cues.get("status") == "approved_audio_timed_visual_cues"
                 and timing.get("status") == "verified_final_audio_alignment",
                 f"{part_id} alignment and cues need verification")
        _require(timing.get("audio_sha256") == receipt["audio_sha256"]
                 and cues.get("audio_sha256") == receipt["audio_sha256"],
                 f"{part_id} cues/timing refer to a different WAV")
        declared_ms = timing.get("duration_ms")
        _require(type(declared_ms) is int
                 and abs(declared_ms-audio_ms) <= 2,
                 f"{part_id} timing and measured WAV duration disagree")
        cue_events = _events(cues, label="visual cues", audio_ms=audio_ms)
        speech_events = _events(timing, label="speech alignment", audio_ms=audio_ms)
        _require(cue_events == speech_events,
                 f"{part_id} visual highlights are not bound to spoken events")
        transition = receipt.get("encoded_transition_qa")
        _require(isinstance(transition, dict)
                 and type(transition.get("verified_transition_count")) is int
                 and transition["verified_transition_count"] >= len(cue_events)
                 and type(transition.get("max_encoded_frame_drift_s")) in (int, float)
                 and 0 <= transition["max_encoded_frame_drift_s"] <= 0.15,
                 f"{part_id} has no acceptable encoded transition proof")
        measured = (probe or _mp4_duration)(video)
        _require(type(measured) in (int, float) and math.isfinite(measured)
                 and 0 < measured < MAX_PART_DURATION_SECONDS,
                 f"{part_id} video violates strict <600-second limit")
        _require(abs(measured - audio_seconds) <= 0.40,
                 f"{part_id} audio/video length drift")
        _require(type(receipt.get("duration_s")) in (int, float)
                 and abs(measured - receipt["duration_s"]) <= 0.10,
                 f"{part_id} duration receipt disagrees with MP4")
        checked.append({"part_id": part_id, "duration_s": round(measured, 3),
                        "highlight_events": len(cue_events)})
    return {"status": "accepted_synchronized_series", "parts": checked,
            "total_duration_s": round(sum(p["duration_s"] for p in checked), 3)}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Verify strict multipart highlighted media")
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify_series(args.folder), indent=2))
        return 0
    except (VideoContractError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"CONTRACT_REJECTED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
