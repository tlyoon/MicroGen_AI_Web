"""Build a waveform-derived, segment-level highlight timeline.

The exact WAV **chunk boundaries** are known. The content spoken inside a WAV
is not verified by this module; word-level precision needs a forced aligner
or trusted TTS provider timestamps with separate review.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import wave

from .storyboard_gate import StoryboardError, canonical_sha256
from .pdf_element_geometry import ElementGeometryError


class AudioAlignmentError(StoryboardError):
    """Missing/stale or mismatched TTS chunk; never guess its timestamps."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _speech_sha(text: str) -> str:
    return _sha(text.encode("utf-8"))


def build_segment_timeline(
    storyboard: dict, geometry: dict, segment_manifest: list[dict], *,
    audio_root: str | Path, output_wav: str | Path,
) -> tuple[dict, dict]:
    """Concatenate verified-format TTS WAV chunks and emit actual times.

    Each manifest entry must be in storyboard narration order and contain:
    segment_id, filename (relative to audio_root), speech_sha256, voice_id,
    pause_after_ms (0..1500). Misordered inputs and uncertain content block.
    """
    if geometry.get("storyboard_sha256") != canonical_sha256(storyboard):
        raise AudioAlignmentError("Geometry is stale for the selected storyboard")
    segments = storyboard.get("narration_segments", [])
    if (not isinstance(segments, list) or not segments
            or len(segment_manifest) != len(segments)):
        raise AudioAlignmentError("TTS segment count does not match storyboard")
    elements = {r["element_id"]: r for r in geometry.get("elements", [])}
    root = Path(audio_root).resolve()
    output = Path(output_wav).resolve()
    if not root.is_dir() or not output.parent.is_dir():
        raise AudioAlignmentError("Audio root or output directory is missing")
    if output.exists():
        raise AudioAlignmentError("Refusing to overwrite an existing combined WAV")
    voices = set()
    events, receipts = [], []
    specs, samples = None, []
    frame_clock = 0
    for index, (seg, manifest) in enumerate(zip(segments, segment_manifest)):
        expected = {"segment_id", "filename", "speech_sha256", "voice_id", "pause_after_ms"}
        if not isinstance(manifest, dict) or set(manifest) != expected:
            raise AudioAlignmentError("WAV receipt must declare all required keys")
        if seg["segment_id"] != manifest["segment_id"]:
            raise AudioAlignmentError("WAV manifest order/IDs differ from narration")
        if manifest["speech_sha256"] != _speech_sha(seg["spoken_text"]):
            raise AudioAlignmentError("Audio receipt linked to wrong spoken text")
        voice = manifest["voice_id"]
        if not isinstance(voice, str) or not voice.strip():
            raise AudioAlignmentError("Missing voice ID")
        voices.add(voice)
        delay_ms = manifest["pause_after_ms"]
        if type(delay_ms) is not int or not 0 <= delay_ms <= 1500:
            raise AudioAlignmentError("pause_after_ms must be integer 0..1500")
        relative = Path(manifest["filename"])
        if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() != ".wav":
            raise AudioAlignmentError("Unsafe or non-WAV audio filename")
        filename = (root/relative).resolve()
        if not filename.is_relative_to(root) or not filename.is_file():
            raise AudioAlignmentError("WAV missing or outside selected audio root")
        with wave.open(str(filename), "rb") as reader:
            fmt = (reader.getnchannels(), reader.getsampwidth(),
                   reader.getframerate(), reader.getcomptype())
            nframes = reader.getnframes()
            wave_data = reader.readframes(nframes)
        if fmt[3] != "NONE" or fmt[0] not in (1, 2) or fmt[1] not in (1, 2, 3, 4):
            raise AudioAlignmentError("Only uncompressed mono/stereo PCM WAV is supported")
        if fmt[2] < 8000 or fmt[2] > 96000 or nframes <= fmt[2] // 20:
            raise AudioAlignmentError("Audio sample rate or WAV duration is invalid")
        if specs is not None and fmt != specs:
            raise AudioAlignmentError("WAV chunks differ in audio format; normalize upstream")
        specs = fmt
        start = frame_clock
        end = start + nframes
        eids = seg["element_ids"]
        if not eids or any(eid not in elements or elements[eid]["slide_id"] != seg["slide_id"]
                           for eid in eids):
            raise AudioAlignmentError("Speech refers to missing or incorrect geometry")
        events.append({
            "slide_id": seg["slide_id"], "segment_id": seg["segment_id"],
            "element_ids": eids,
            "start_ms": round(start * 1000 / fmt[2]),
            "end_ms": round(end * 1000 / fmt[2]),
            "timing_method": "speech_segment", "confidence": 1.0,
        })
        receipts.append({
            "segment_id": seg["segment_id"],
            "wav_sha256": _sha(filename.read_bytes()),
            "speech_sha256": manifest["speech_sha256"],
            "voice_id": voice,
            "frames": nframes, "sample_rate": fmt[2],
        })
        pad = int(round(delay_ms * fmt[2] / 1000))
        samples.append((wave_data, pad))
        frame_clock = end + pad
    if len(voices) != 1:
        raise AudioAlignmentError("Mixed TTS voices in a single video part")
    if frame_clock / specs[2] >= 630:
        raise AudioAlignmentError("Audio alone exceeds the video hard cap (<630 s)")
    if any(e["end_ms"] <= e["start_ms"] for e in events):
        raise AudioAlignmentError("WAV timing collapsed to zero-duration emphasis")

    # Assemble only after all fail-closed checks. Safe output creation is exclusive.
    with output.open("xb") as target:
        with wave.open(target, "wb") as sink:
            sink.setnchannels(specs[0])
            sink.setsampwidth(specs[1])
            sink.setframerate(specs[2])
            for data, pad in samples:
                sink.writeframesraw(data)
                sink.writeframesraw(b"\x00" * (pad * specs[0] * specs[1]))
            sink.writeframes(b"")
    try:
        with wave.open(str(output), "rb") as check:
            if check.getnframes() != frame_clock:
                raise AudioAlignmentError("Combined audio frame count mismatch")
    except Exception:
        output.unlink(missing_ok=True)
        raise
    timeline = {
        "schema_version": 1, "part_id": storyboard["part_id"],
        "slide_pdf_sha256": geometry["instrumented_pdf_sha256"],
        "audio_sha256": _sha(output.read_bytes()),
        "storyboard_sha256": canonical_sha256(storyboard),
        "duration_ms": round(frame_clock * 1000 / specs[2]),
        "events": events,
    }
    receipt = {
        "status": "wave_chunk_timing_verified_spoken_content_unreviewed",
        "voice_id": next(iter(voices)), "sample_rate": specs[2],
        "wav_segments": receipts, "audio_sha256": timeline["audio_sha256"],
        "unverified": [
            "tts_words_match_script", "speech_onset_and_offset_inside_chunk",
            "visual_semantic_correctness", "actual_encoded_mp4_runtime",
        ],
    }
    return timeline, receipt
