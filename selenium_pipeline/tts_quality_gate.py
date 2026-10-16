"""Review-only three-layer TTS quality screening for authored narration WAVs.

1. PCM acoustic integrity (clipping, volume, silence, pause measurements).
2. Independent ASR transcript agreement, plus conservative math-token alarms.
3. Heuristic pacing screening. Naturalness/pronunciation require listening review.

No microphone, API calls or external packages. Never grants academic or
production approval. Reports are immutable and bound to the exact plan/audio.
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import unicodedata
import wave


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = normalized.replace("’", "'")
    return re.findall(r"\w+", normalized, flags=re.UNICODE)


def word_error_rate(reference: str, heard: str) -> float:
    """Minimum word edit distance, not difflib's approximate alignment."""
    a, b = tokens(reference), tokens(heard)
    if not a:
        raise ValueError("Empty reference transcript")
    if len(a) > 2000 or len(b) > 2000:
        raise ValueError("Speech comparison too large")
    prev = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        row = [i]
        for j, right in enumerate(b, 1):
            row.append(min(row[-1] + 1, prev[j] + 1,
                           prev[j - 1] + (left != right)))
        prev = row
    return round(prev[-1] / len(a), 4)


# Intentionally conservative: a synonym may cause a *review flag*, never a pass.
MATH_TERMS = frozenset((
    "negative", "positive", "minus", "plus", "equals", "equal",
    "over", "divided", "times", "squared", "square", "cubed", "cube",
    "power", "root", "pi", "theta", "alpha", "beta", "delta",
    "sine", "cosine", "tangent", "secant", "integral", "derivative",
    "infinity", "zero", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten", "not", "less", "greater",
))


def math_marks(text: str) -> Counter:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = normalized.replace("π", " pi ").replace("θ", " theta ")
    normalized = normalized.replace("−", " minus ").replace("×", " times ")
    normalized = normalized.replace("÷", " divided ")
    normalized = re.sub(r"(?<=\w)/(?=\w)", " over ", normalized)
    normalized = re.sub(r"(?<=\d)\+(?=\d)", " plus ", normalized)
    normalized = re.sub(r"\b0\b", " zero ", normalized)
    normalized = re.sub(r"\b1\b", " one ", normalized)
    normalized = re.sub(r"\b2\b", " two ", normalized)
    words = tokens(normalized)
    aliases = {"sin": "sine", "cos": "cosine", "tan": "tangent",
               "eq": "equals", "equal": "equals"}
    return Counter(aliases.get(t, t) for t in words
                   if aliases.get(t, t) in MATH_TERMS)


def acoustic_check(path: Path, spoken_text: str) -> dict:
    """Streaming 30 ms window measurements of mono PCM16 WAV."""
    if not path.is_file() or path.is_symlink():
        raise ValueError("Missing/unsafe WAV: " + path.name)
    with wave.open(str(path), "rb") as wav:
        rate, nch, width = wav.getframerate(), wav.getnchannels(), wav.getsampwidth()
        frames = wav.getnframes()
        if nch != 1 or width != 2 or not 8000 <= rate <= 96000 or frames <= 0:
            raise ValueError("Unsupported PCM mono 16-bit WAV: " + path.name)
        if wav.getcomptype() != "NONE":
            raise ValueError("Compressed WAV: " + path.name)
        duration = frames / rate
        if duration > 120:
            raise ValueError("WAV longer than 120 seconds: " + path.name)
        window = max(1, round(rate * .03))
        squares, samples, max_sample, clipped = 0, 0, 0, 0
        rms_windows = []
        while True:
            data = wav.readframes(window)
            if not data:
                break
            chunk = array("h")
            chunk.frombytes(data)
            if sys.byteorder != "little":
                chunk.byteswap()
            if not chunk:
                break
            sumsq = sum(value * value for value in chunk)
            peak = max(abs(value) for value in chunk)
            clipped += sum(abs(value) >= 32600 for value in chunk)
            samples += len(chunk)
            squares += sumsq
            max_sample = max(max_sample, peak)
            rms_windows.append(math.sqrt(sumsq / len(chunk)))
    rms = math.sqrt(squares / samples) if samples else 0
    dbfs = 20 * math.log10(max(rms / 32768, 1e-9))
    peak_dbfs = 20 * math.log10(max(max_sample / 32768, 1e-9))
    clipped_fraction = clipped / samples if samples else 1
    # This is an energy-based screening proxy, not voice activity detection.
    threshold = max(350, max_sample * .025)
    silent = [value <= threshold for value in rms_windows]
    silent_fraction = sum(silent) / len(silent) if silent else 1
    before = next((i for i, state in enumerate(silent) if not state), len(silent))
    after = next((i for i, state in enumerate(reversed(silent)) if not state),
                 len(silent))
    largest = streak = 0
    for state in silent:
        streak = streak + 1 if state else 0
        largest = max(largest, streak)
    # Narrow thresholds: definite technical faults vs perceptual review cues.
    technical_flags = []
    if duration < .45:
        technical_flags.append("very_short_audio")
    if dbfs < -42 or max_sample == 0:
        technical_flags.append("very_quiet_or_silent")
    if clipped_fraction > .005:
        technical_flags.append("excessive_clipping")
    if silent_fraction > .80:
        technical_flags.append("mostly_silence")
    pace = 60 * len(tokens(spoken_text)) / duration
    review_flags = []
    if pace < 60 or pace > 250:
        review_flags.append("unusual_script_words_per_minute")
    if before * .03 > 2.5:
        review_flags.append("long_leading_silence")
    if after * .03 > 2.5:
        review_flags.append("long_trailing_silence")
    if largest * .03 > 3.5:
        review_flags.append("long_silent_interval")
    if dbfs > -6:
        review_flags.append("high_average_loudness")
    return {
        "duration_s": round(duration, 3),
        "rms_dbfs": round(dbfs, 2),
        "peak_dbfs": round(peak_dbfs, 2),
        "clipped_sample_fraction": round(clipped_fraction, 6),
        "energy_silence_fraction": round(silent_fraction, 3),
        "leading_energy_silence_s": round(before * .03, 2),
        "trailing_energy_silence_s": round(after * .03, 2),
        "longest_energy_silence_s": round(largest * .03, 2),
        "script_words_per_minute": round(pace, 1),
        "technical_flags": technical_flags,
        "perceptual_review_flags": review_flags,
        "energy_method_is_not_voice_activity_detection": True,
    }


def screen(*, plan: Path, audio: Path, output: Path,
           asr_dir: Path | None = None) -> dict:
    plan, audio, output = Path(plan).resolve(), Path(audio).resolve(), Path(output).resolve()
    if not plan.is_file() or not audio.is_dir() or output.exists():
        raise ValueError("Plan/audio missing or output report already exists")
    if not output.parent.is_dir() or output.is_relative_to(audio):
        raise ValueError("Unsafe report destination")
    authored = json.loads(plan.read_text(encoding="utf-8"))
    if authored.get("status") != "author_specified_unapproved_element_narration":
        raise ValueError("Not an authored review narration plan")
    events = [el for part in authored["parts"] for slide in part["slides"]
              for el in slide["elements"]]
    if not events or len(events) > 500:
        raise ValueError("Invalid audio segment count")
    names = [el["wav"] for el in events]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate narration WAV")
    job = None
    if asr_dir is not None:
        asr_dir = Path(asr_dir).resolve()
        job = json.loads((asr_dir / "asr_job.json").read_text(encoding="utf-8"))
        if (job.get("plan_sha256") != digest(plan) or
                job.get("clips") != names or
                job.get("source_model") != "gemini-3.8-flash-lite-tts" or
                job.get("model") not in ("gemini-3.1-flash-lite", "gemini-3.5-flash")):
            raise ValueError("Wrong or stale independent-ASR job")
    rows = []
    for item in events:
        name, script = item["wav"], item["spoken_text"]
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+\.wav", name) or len(tokens(script)) < 4:
            raise ValueError("Unsafe filename or script")
        wav = audio / name
        acoustics = acoustic_check(wav, script)
        file_hash = digest(wav)
        recognized = None
        wer = None
        math_diff = None
        evidence_state = "pending_independent_asr"
        flags = list(acoustics["perceptual_review_flags"])
        if job is not None:
            receipt = asr_dir / (name + ".asr.json")
            if receipt.is_file():
                entry = json.loads(receipt.read_text(encoding="utf-8"))
                recognized = entry.get("transcript")
                if (not isinstance(recognized, str) or
                        entry.get("wav") != name or
                        entry.get("wav_sha256") != file_hash or
                        entry.get("reference_sha256") != sha_text(script) or
                        entry.get("transcript_sha256") != sha_text(recognized) or
                        entry.get("asr_model") != job["model"]):
                    raise ValueError("Tampered, stale or unrelated ASR evidence: " + name)
                wer = word_error_rate(script, recognized)
                target = math_marks(script)
                heard = math_marks(recognized)
                math_diff = {
                    "missing": dict(target - heard),
                    "extra": dict(heard - target),
                }
                evidence_state = ("machine_transcript_consistent" if wer <= .20
                                  else "transcript_mismatch")
                if wer > .20:
                    flags.append("transcript_word_error_over_20_percent")
                if any(math_diff.values()):
                    flags.append("mathematical_spoken_token_discrepancy")
        if evidence_state == "pending_independent_asr":
            flags.append("independent_transcript_unavailable")
        rows.append({
            "wav": name, "wav_sha256": file_hash,
            "reference_sha256": sha_text(script),
            "acoustics": acoustics, "asr_status": evidence_state,
            "asr_model": job["model"] if job else None,
            "transcript": recognized, "word_error_rate": wer,
            "math_token_discrepancy": math_diff,
            "human_listening_approved": False,
            "quality_state": (
                "technical_reject" if acoustics["technical_flags"]
                else "manual_review_required" if flags
                else "machine_screen_consistent_not_certified"
            ),
            "review_flags": flags,
        })
    rejected = sum(r["quality_state"] == "technical_reject" for r in rows)
    pending = sum(r["asr_status"] == "pending_independent_asr" for r in rows)
    review = sum(r["quality_state"] == "manual_review_required" for r in rows)
    summary = {
        "schema_version": 1,
        "status": "QUALITY_SCREEN_REVIEW_ONLY",
        "plan_sha256": digest(plan),
        "asr_job_sha256": digest(asr_dir / "asr_job.json") if job else None,
        "total_clips": len(rows),
        "technical_rejected": rejected,
        "manual_review_required": review,
        "pending_asr": pending,
        "machine_screen_passed": len(rows) - rejected - review,
        "all_machine_checks_passed": not (rejected or review or pending),
        "human_listening_complete": False,
        "academic_approved": False,
        "production_approved": False,
        "limitations": (
            "Energy silence is not VAD; script pace is only an estimate; "
            "matching Gemini ASR is not verified pronunciation or naturalness."
        ),
        "clips": rows,
    }
    with output.open("x", encoding="utf-8") as dest:
        json.dump(summary, dest, ensure_ascii=False, indent=2)
        dest.write("\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--asr-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = screen(plan=args.plan, audio=args.audio, output=args.output,
                    asr_dir=args.asr_dir)
    print(json.dumps({k: v for k, v in result.items() if k != "clips"}, indent=2))


if __name__ == "__main__":
    main()
