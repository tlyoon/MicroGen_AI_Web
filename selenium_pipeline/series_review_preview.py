"""Offline, source-linked multipart highlight REVIEW previews.

This bridge intentionally NEVER writes an accepted production-series receipt.
It runs only from frozen local prepared parts and does not call Gemini/TTS.
Pedagogical, exact spoken-word and mathematical approvals remain separate.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .highlight_video_preview import compose_highlight_preview
from .pdf_element_geometry import extract_element_geometry, strip_instrumentation_links
from .speech_segment_timing import build_segment_timeline
from .storyboard_gate import canonical_sha256

PART = re.compile(r"part_[0-9]{2}$")
SHA = re.compile(r"[0-9a-f]{64}$")


class PreviewSeriesError(ValueError):
    """Unbound lesson source, unsafe workspace, or incomplete staged media."""


def _require(condition: bool, why: str) -> None:
    if not condition:
        raise PreviewSeriesError(why)


def _sha(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1048576), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _json(path: Path) -> dict:
    _require(path.is_file() and not path.is_symlink(), f"Missing review input: {path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf8"))
    except (UnicodeError, ValueError, OSError) as exc:
        raise PreviewSeriesError(f"Invalid JSON input {path}") from exc
    _require(isinstance(parsed, dict), f"Expected a JSON object: {path}")
    return parsed


def _write_new(path: Path, data: dict) -> None:
    with path.open("x", encoding="utf8") as out:
        json.dump(data, out, indent=2, ensure_ascii=False)
        out.write("\n")


def _not_in(location: Path, parent: Path) -> bool:
    return not location.is_relative_to(parent)


def render_review_series(*, source_pdf: Path, inputs_root: Path,
                         output_root: Path) -> dict:
    """Produce independent, review-only part MP4s from prepared semantic inputs.

    Expected input layout:
        inputs_root/series_inputs.json
        inputs_root/part_01/storyboard.json
        inputs_root/part_01/instrumented.pdf
        inputs_root/part_01/tts_chunks.json
        inputs_root/part_01/wav/n1.wav, ...

    The input JSON binds exact source SHA, plan SHA and ordered part IDs.
    One part consists of pre-approved-for-processing (not scientifically
    certified) storyboard, anchored rendered PDF and final PCM WAV chunks.
    No generated input is overwritten; no accepted-production receipt is
    created. Missing or invalid records fail before creating output_root.
    """
    source = Path(source_pdf).resolve()
    inputs = Path(inputs_root).resolve()
    output = Path(output_root).resolve()
    _require(source.is_file() and not source.is_symlink(),
             "Original source PDF is missing or symlinked")
    _require(inputs.is_dir() and not inputs.is_symlink(),
             "Prepared input folder is missing")
    _require(_not_in(inputs, source.parent),
             "Prepared review inputs must be outside textbook folder")
    _require(not output.exists() and output.parent.is_dir(),
             "A new, nonexistent output directory is mandatory")
    _require(_not_in(output, source.parent) and _not_in(output, inputs),
             "Output must not be inside source or prepared-input tree")
    _require(_not_in(inputs, output) and source != output,
             "Input and output locations must be independent")
    series = _json(inputs/"series_inputs.json")
    _require(series.get("schema_version") == 1
             and series.get("status") == "review_only_source_bound_inputs",
             "Expected review-only source-bound manifest")
    source_sha = series.get("source_sha256")
    plan_sha = series.get("plan_sha256")
    _require(isinstance(source_sha, str) and SHA.fullmatch(source_sha) is not None
             and _sha(source) == source_sha, "Textbook source hash does not match")
    _require(isinstance(plan_sha, str) and SHA.fullmatch(plan_sha) is not None,
             "Expected a validated plan hash")
    parts = series.get("parts")
    _require(isinstance(parts, list) and 1 <= len(parts) <= 40
             and all(x == f"part_{i:02d}" for i, x in enumerate(parts, 1)),
             "Expected 1-40 contiguous, ordered part IDs")
    prepared = []
    for part_id in parts:
        folder = inputs/part_id
        _require(folder.is_dir() and not folder.is_symlink(),
                 f"Missing prepared part: {part_id}")
        board = _json(folder/"storyboard.json")
        tts = _json(folder/"tts_chunks.json")
        instrumented = folder/"instrumented.pdf"
        audio_dir = folder/"wav"
        _require(instrumented.is_file() and not instrumented.is_symlink()
                 and audio_dir.is_dir() and not audio_dir.is_symlink(),
                 f"{part_id}: missing approved-for-processing PDF/WAV input")
        _require(board.get("schema_version") == 1
                 and board.get("part_id") == part_id
                 and board.get("plan_sha256") == plan_sha,
                 f"{part_id}: storyboard mismatches source-linked part plan")
        _require(tts.get("schema_version") == 1 and tts.get("part_id") == part_id
                 and isinstance(tts.get("segments"), list)
                 and len(tts["segments"]) == len(board.get("narration_segments", [])),
                 f"{part_id}: TTS manifest not bound to the storyboard")
        for index, row in enumerate(tts["segments"], 1):
            _require(isinstance(row, dict)
                     and row.get("filename") == f"n{index}.wav"
                     and (audio_dir/row["filename"]).is_file()
                     and not (audio_dir/row["filename"]).is_symlink(),
                     f"{part_id}: missing, duplicate or unsafe source WAV")
        prepared.append((part_id, folder, board, tts, instrumented, audio_dir))
    # The original input is verified before any rendering or copy operations.
    output.mkdir()
    results = []
    for part_id, folder, board, tts, instrumented, audio_dir in prepared:
        target = output/part_id
        target.mkdir()
        geometry = extract_element_geometry(instrumented, board)
        clean = target/"clean_slides.pdf"
        clean_receipt = strip_instrumentation_links(instrumented, clean, geometry)
        combined = target/"narration.wav"
        timeline, wav_receipt = build_segment_timeline(
            board, geometry, tts["segments"], audio_root=audio_dir,
            output_wav=combined,
        )
        _write_new(target/"element_geometry.json", geometry)
        _write_new(target/"clean_pdf_receipt.json", clean_receipt)
        _write_new(target/"narration_timeline.json", timeline)
        _write_new(target/"wave_timing_receipt.json", wav_receipt)
        workspace = target/"scratch_frames"
        workspace.mkdir()
        video = target/f"{part_id}_review.mp4"
        encoded = compose_highlight_preview(
            clean_pdf=clean, clean_receipt=clean_receipt,
            storyboard=board, geometry=geometry, timeline=timeline,
            wav_file=combined, workspace=workspace, output_mp4=video,
        )
        _require(0 < encoded["duration_s"] < 600,
                 f"{part_id}: final preview exceeds strict <600 seconds")
        result = {
            "part_id":part_id,
            "status":"review_only_not_approved",
            "original_source_sha256":source_sha,
            "plan_sha256":plan_sha,
            "storyboard_sha256":canonical_sha256(board),
            "mp4_sha256":_sha(video),
            "wav_sha256":_sha(combined),
            "clean_slides_sha256":_sha(clean),
            "audio_seconds":encoded["audio_duration_s"],
            "encoded_mp4_seconds":encoded["duration_s"],
            "highlight_segments":encoded["highlight_segments"],
            "encoded_transition_qa":encoded["encoded_transition_qa"],
            "unverified": [
                "actual_tts_spoken_words_match_script",
                "mathematical_pedagogical_approval",
                "semantic_highlight_correctness",
                "decoded_frame_content_audit",
            ],
        }
        _write_new(target/"review_receipt.json", result)
        results.append(result)
    _require(_sha(source) == source_sha,
             "Source PDF changed during rendering; reject review previews")
    summary = {
        "schema_version":1,
        "status":"review_only_not_approved",
        "source_sha256":source_sha,
        "plan_sha256":plan_sha,
        "parts":results,
        "accepted_lecture_completion_created":False,
        "student_published":False,
        "description":"Review-only source-bound multipart timed-highlight preview",
    }
    _write_new(output/"series_review_receipt.json", summary)
    return summary
