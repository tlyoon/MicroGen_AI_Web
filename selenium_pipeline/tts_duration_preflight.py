"""Offline TTS duration calibration from a hashed, real pilot. Never approval."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path


class CalibrationError(ValueError):
    pass


def words(text):
    if not isinstance(text, str) or not text.strip():
        raise CalibrationError("Missing spoken words")
    n = len(re.findall(r"\b\w+(?:[-']\w+)*\b", text, flags=re.UNICODE))
    if not n:
        raise CalibrationError("Uncountable spoken text")
    return n


def _segments(storyboard):
    if (not isinstance(storyboard, dict) or
            storyboard.get("schema_version") != 1 or
            not isinstance(storyboard.get("part_id"), str) or
            not storyboard.get("part_id")):
        raise CalibrationError("Expected a version-1 joint storyboard")
    seq = storyboard.get("narration_segments")
    if not isinstance(seq, list) or not seq:
        raise CalibrationError("Missing narration segments")
    ids = set()
    for seg in seq:
        if not isinstance(seg, dict) or not isinstance(seg.get("segment_id"), str):
            raise CalibrationError("Bad segment identity")
        sid = seg["segment_id"]
        if not sid or sid in ids:
            raise CalibrationError("Duplicated segment identity")
        ids.add(sid)
        words(seg.get("spoken_text"))
    return seq


def calculate(pilot, receipt, candidates, *, video_seconds=None,
              slowdown=.20, reserve_seconds=24., limit_seconds=600.):
    seq = _segments(pilot)
    if (not isinstance(receipt, dict) or
            receipt.get("status") != "wave_chunk_timing_verified_spoken_content_unreviewed"):
        raise CalibrationError("No hash-verified pilot WAV receipt")
    wavs = receipt.get("wav_segments")
    if not isinstance(wavs, list) or len(wavs) != len(seq):
        raise CalibrationError("Pilot segment count mismatch")
    if not isinstance(candidates, list) or not candidates:
        raise CalibrationError("At least one candidate is required")
    if (type(slowdown) not in (int, float) or not 0 <= slowdown < 1 or
            type(reserve_seconds) not in (int, float) or reserve_seconds < 0 or
            not math.isfinite(reserve_seconds) or
            type(limit_seconds) not in (int, float) or
            not math.isfinite(limit_seconds) or
            not 0 < limit_seconds <= 600):
        raise CalibrationError("Invalid duration policy: strict ceiling is <600 seconds")
    voices = set()
    rates = set()
    audio_s = 0.
    pilot_words = 0
    for segment, wav in zip(seq, wavs):
        if not isinstance(wav, dict) or segment["segment_id"] != wav.get("segment_id"):
            raise CalibrationError("WAV segment identity or ordering mismatch")
        speech_hash = hashlib.sha256(segment["spoken_text"].encode("utf8")).hexdigest()
        if speech_hash != wav.get("speech_sha256"):
            raise CalibrationError("WAV script hash mismatch")
        frames, rate = wav.get("frames"), wav.get("sample_rate")
        if (type(frames) not in (int, float) or type(rate) not in (int, float)
                or frames <= 0 or rate <= 0 or not math.isfinite(frames)
                or not math.isfinite(rate)):
            raise CalibrationError("Invalid WAV frame data")
        voice = wav.get("voice_id")
        if not isinstance(voice, str) or not voice:
            raise CalibrationError("Voice ID missing")
        voices.add(voice)
        rates.add(rate)
        audio_s += frames / rate
        pilot_words += words(segment["spoken_text"])
    if len(voices) != 1 or len(rates) != 1:
        raise CalibrationError("Mixed voices or sample rates")
    if next(iter(voices)) != receipt.get("voice_id"):
        raise CalibrationError("Voice does not match receipt")
    if next(iter(rates)) != receipt.get("sample_rate"):
        raise CalibrationError("WAV rate does not match receipt")
    pause_s = 0.
    if video_seconds is not None:
        if (type(video_seconds) not in (int, float) or
                not math.isfinite(video_seconds) or video_seconds < audio_s - .025):
            raise CalibrationError("Pilot video shorter than verified speech audio")
        pause_s = max(0., video_seconds - audio_s)
    per_boundary = pause_s / max(1, len(seq) - 1)
    sec_per_word = audio_s / pilot_words
    parts = []
    seen = set()
    for candidate in candidates:
        items = _segments(candidate)
        name = candidate["part_id"]
        if name in seen:
            raise CalibrationError("Duplicate candidate part")
        seen.add(name)
        wc = sum(words(s["spoken_text"]) for s in items)
        speech_s = wc * sec_per_word
        pauses = (len(items) - 1) * per_boundary
        slower = speech_s / (1. - slowdown) + pauses + reserve_seconds
        parts.append({
            "part_id": name, "segments": len(items), "words": wc,
            "pilot_rate_s": round(speech_s + pauses, 2),
            "slow_rate_plus_reserve_s": round(slower, 2),
            "slow_scenario_exceeds_limit": slower >= limit_seconds,
            "storyboard_sha256": hashlib.sha256(json.dumps(
                candidate, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf8")).hexdigest(),
        })
    return {
        "status": "UNREVIEWED_EXPERIMENTAL_DURATION_ESTIMATE_NOT_APPROVAL",
        "pilot_voice_id": next(iter(voices)),
        "pilot_words": pilot_words,
        "pilot_wav_seconds": round(audio_s, 2),
        "pilot_video_seconds": round(video_seconds, 2) if video_seconds is not None else None,
        "pilot_inserted_pause_seconds": round(pause_s, 2) if video_seconds is not None else None,
        "pilot_words_per_minute": round(60. / sec_per_word, 2),
        "illustrative_slowdown_fraction": slowdown,
        "planning_reserve_seconds_per_part": reserve_seconds,
        "strict_video_limit_seconds": limit_seconds,
        "parts": parts,
        "math_approved": False, "tts_authorized": False,
        "mp4_authorized": False, "student_publication_permitted": False,
        "limitations": [
            "Text hashes bind scripts, not correctness of audible TTS words",
            "The slowdown case is illustrative, not a statistical confidence bound",
            "Same-voice model and expression-specific cadence may still change",
            "Real TTS WAV durations and final encoded MP4 require inspection"
        ],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Offline, nonapproving TTS runtime preflight")
    p.add_argument("--pilot-storyboard", type=Path, required=True)
    p.add_argument("--pilot-wav-receipt", type=Path, required=True)
    p.add_argument("--pilot-video-duration-s", type=float)
    p.add_argument("--candidate", action="append", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    load = lambda file: json.loads(file.read_text(encoding="utf8"))
    out = calculate(
        load(a.pilot_storyboard), load(a.pilot_wav_receipt),
        [load(x) for x in a.candidate],
        video_seconds=a.pilot_video_duration_s,
    )
    with a.out.open("x", encoding="utf8") as file:
        json.dump(out, file, indent=2, ensure_ascii=False)
        file.write("\n")
    print("Offline duration preflight (NOT APPROVED):", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
