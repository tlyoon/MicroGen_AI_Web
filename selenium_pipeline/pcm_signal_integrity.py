"""Reusable offline sample-level integrity checks for original TTS PCM recordings.

A valid RIFF container and TTS provenance are not sufficient: audio can be
silence, hard-clipped or have large mid-stream gaps. A structural signal pass
does NOT attest pronunciation, words, voice identity or per-element cues.
No network access, ASR, model, TTS regeneration, file mutation or guessing.
"""
from __future__ import annotations

from array import array
from hashlib import sha256
from io import BytesIO
from math import sqrt
from pathlib import Path
import sys
import wave

from .tts_pcm_contract import verify_pcm


class PCMIntegrityBlocked(ValueError):
    pass


_WINDOW_MS = 100
_QUIET_RMS = 0.004  # 0.4% full-scale; only used to detect *long* dropouts
_MAX_INTERIOR_QUIET_SECONDS = 6.0
_MIN_RMS = 0.006  # reject grossly inaudible outputs, not speaker-level normalization
_MAX_CLIPPED_FRACTION = 0.001  # >= 0.1% near-full-scale samples is objective damage
_MAX_CLIPPED_RUN = 48  # >= 2 ms at 24 kHz repeatedly railed is clipping
_MAX_DC_ABS = 0.08
_MIN_ACTIVE_100MS_FRACTION = 0.12


def need(ok: bool, reason: str):
    if not ok:
        raise PCMIntegrityBlocked(reason)


def _windows(samples: array, rate: int) -> list[float]:
    width = max(1, (rate * _WINDOW_MS) // 1000)
    return [sqrt(sum(v * v for v in samples[i:i + width])
                 / (min(width, len(samples) - i) * 32768.0 ** 2))
            for i in range(0, len(samples), width)]


def _longest_interior_quiet(windows: list[float]) -> float:
    # Silence at the start/end may be intentional speech padding. A long
    # interior dropout is not automatically assumed to be narration.
    active = [i for i, value in enumerate(windows) if value >= _QUIET_RMS]
    if len(active) < 2:
        return 0.0
    longest = 0
    current = 0
    for i in range(active[0] + 1, active[-1]):
        if windows[i] < _QUIET_RMS:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest * _WINDOW_MS / 1000.0


def inspect_pcm_signal(payload: bytes, *, label: str = "WAV") -> dict:
    """Byte-locked decoded signal diagnostics, strict for gross defects only."""
    need(type(payload) is bytes and len(payload) < 12_000_000,
         "A bounded real PCM16 WAV byte stream is required")
    proof = verify_pcm(payload, label=label)
    with wave.open(BytesIO(payload), "rb") as w:
        frames = w.getnframes()
        samples = w.readframes(frames)
    need(len(samples) == frames * 2, "PCM frames truncated")
    data = array("h")
    data.frombytes(samples)
    if sys.byteorder != "little":
        data.byteswap()
    need(len(data) == frames, "PCM sample count disagrees with RIFF data")
    n = len(data)
    total = sum(int(v) for v in data)
    power = sum(int(v) * int(v) for v in data)
    peak = max(abs(int(v)) for v in data)
    clipped = 0
    railed_run = 0
    max_railed_run = 0
    for sample in data:
        if abs(sample) >= 32760:
            clipped += 1
            railed_run += 1
            max_railed_run = max(max_railed_run, railed_run)
        else:
            railed_run = 0
    rms = sqrt(power / n) / 32768
    dc = abs(total / n) / 32768
    windows = _windows(data, proof["sample_rate_hz"])
    active = sum(v >= _QUIET_RMS for v in windows) / len(windows)
    dropout = _longest_interior_quiet(windows)
    activity_indices = [i for i, value in enumerate(windows)
                        if value >= _QUIET_RMS]
    lead_quiet = (activity_indices[0] * _WINDOW_MS / 1000.0
                  if activity_indices else len(windows) * _WINDOW_MS / 1000.0)
    trail_quiet = ((len(windows) - 1 - activity_indices[-1])
                   * _WINDOW_MS / 1000.0 if activity_indices
                   else len(windows) * _WINDOW_MS / 1000.0)
    clipped_ratio = clipped / n
    need(rms >= _MIN_RMS and active >= _MIN_ACTIVE_100MS_FRACTION,
         "Audio is silent, nearly silent, or has inadequate active PCM")
    need(dc <= _MAX_DC_ABS, "PCM has a large sustained DC offset")
    need(clipped_ratio < _MAX_CLIPPED_FRACTION
         and max_railed_run < _MAX_CLIPPED_RUN,
         "PCM contains sustained hard clipping")
    need(dropout < _MAX_INTERIOR_QUIET_SECONDS,
         "PCM contains a long interior audio dropout")
    need(max(lead_quiet, trail_quiet) < _MAX_INTERIOR_QUIET_SECONDS,
         "PCM contains excessive leading or trailing silence")
    return {
        "status": "OBJECTIVE_PCM_SIGNAL_INTEGRITY_PASS_NOT_LISTENING",
        "wav_sha256": sha256(payload).hexdigest(),
        "duration_s": proof["duration_seconds"],
        "sample_rate_hz": proof["sample_rate_hz"],
        "sample_count": n,
        "peak_fraction_full_scale": round(peak / 32768, 6),
        "rms_fraction_full_scale": round(rms, 6),
        "absolute_dc_fraction_full_scale": round(dc, 6),
        "near_rail_sample_fraction": round(clipped_ratio, 8),
        "max_consecutive_near_rail_samples": max_railed_run,
        "active_100ms_fraction": round(active, 5),
        "max_interior_quiet_seconds": round(dropout, 3),
        "leading_quiet_seconds": round(lead_quiet, 3),
        "trailing_quiet_seconds": round(trail_quiet, 3),
        "objective_pcm_signal_integrity_passed": True,
        "pronunciation_and_words_verified": False,
        "single_voice_identity_verified": False,
        "acoustic_listening_qa_verified": False,
        "narration_to_element_sync_verified": False,
        "student_publication_authorized": False,
    }


def inspect_pcm_file(path: Path) -> dict:
    path = Path(path).absolute()
    need(path.is_file() and not path.is_symlink(),
         "A regular original WAV file is required")
    before = path.read_bytes()
    result = inspect_pcm_signal(before, label=path.name)
    need(path.read_bytes() == before, "Original WAV changed during sample inspection")
    return result
