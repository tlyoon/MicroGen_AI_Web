from __future__ import annotations

import argparse
import json
from pathlib import Path

from .figure_source_identity import _sha, require
from .figure_real_source_slide_gate import assess_real_source_slide_figure
from .lecture_acceptance_audit import (
    _regular_path, _scan_mp4, inspect_real_lecture_acceptance,
)


def inspect_joint_original_lecture(*, folder: Path, source_page: int,
                                   slide_page: int, figure_id: str) -> dict:
    root = _regular_path(folder, directory=True)
    source = _regular_path(root / "source.pdf")
    slides = _regular_path(root / "slides.pdf")
    originals = _scan_mp4(root)
    before = {str(p): _sha(p) for p in [source, slides, *originals]}
    figure = assess_real_source_slide_figure(
        source=source, slides=slides, source_page=source_page,
        slide_page=slide_page, figure_id=figure_id)
    media = inspect_real_lecture_acceptance(
        source=source, slides=slides, lecture_folder=root,
        source_page=source_page, slide_page=slide_page, figure_id=figure_id)
    pilot = media["source_report"]
    require(figure["source_sha256"] == pilot["source_sha256"]
            == before[str(source)], "Conflicting original source hashes")
    require(figure["slides_sha256"] == pilot["slides_sha256"]
            == before[str(slides)], "Conflicting original slide hashes")
    require(pilot["figure_id"] == figure_id
            and pilot["source_page"] == source_page
            and pilot["slide_page"] == slide_page, "Figure locators mismatch")
    require(media["status"] == "TECHNICAL_ACCEPTANCE_BLOCKED"
            and media["synthetic_duration_probe_used"] is False
            and media["student_publication_permitted"] is False
            and media["source_figure_evidence_complete"] is False,
            "Independent media audit not valid for actual lecture")
    require(figure["status"] == "REAL_SOURCE_SLIDE_FIGURE_EVIDENCE_BLOCKED"
            and figure["figure_video_authorized"] is False,
            "Original figure audit has unexpected status")
    videos = media["video_candidates"]
    require(isinstance(videos, list) and len(videos) == len(originals),
            "Media inventory differs between independent audits")
    original_names = {str(p.relative_to(root)).replace(chr(92), "/"): p
                      for p in originals}
    require(set(v["relative_path"] for v in videos)
            == set(original_names), "Media file names disagree")
    require(all(v["mp4_sha256"] == before[str(original_names[v["relative_path"]])]
                for v in videos), "Media file hash mismatch")
    require(all(_sha(Path(p)) == digest for p, digest in before.items()),
            "Original media or PDFs changed during joint audit")
    require({str(p.relative_to(root)).replace(chr(92), "/")
             for p in _scan_mp4(root)} == set(original_names),
            "Media inventory changed during joint audit")
    violations = [v["relative_path"] for v in videos
                  if v["duration_measured_from_actual_media"]
                  and not v["duration_below_strict_600_s"]]
    unmeasured = [v["relative_path"] for v in videos
                  if not v["duration_measured_from_actual_media"]]
    # Valid source-to-slide graph reflow resolves the old *aspect-only*
    # objection, not the original mathematical content or media QA.
    reflow_found = figure["automatically_detected_layout_reflow"]
    blockers = ([
        "UNVERIFIED_MATH_AXES_LABELS_AND_WHOLE_FIGURE_CONTENT"
    ] if reflow_found else [
        "UNVERIFIED_SOURCE_FIGURE_AND_SLIDE_CORRESPONDENCE"
    ])
    if figure["source_caption_layout_status"] == (
            "CAPTION_PARALLEL_PROSE_COLLISION_REVIEW_REQUIRED"):
        blockers.append("SOURCE_CAPTION_OVERLAPS_UNRELATED_PROSE")
    if violations:
        blockers.append("MEASURED_ENCODED_VIDEO_AT_OR_ABOVE_600_SECONDS")
    if unmeasured:
        blockers.append("UNMEASURED_ENCODED_VIDEO")
    if not media["multipart_media_verified"]:
        blockers.append("UNVERIFIED_SPEECH_TIMED_MULTIPART_HIGHLIGHTS")
    return {
        "schema_version": 1,
        "status": "JOINT_ORIGINAL_LECTURE_ACCEPTANCE_BLOCKED",
        "source_sha256": before[str(source)],
        "slides_sha256": before[str(slides)],
        "source_page": source_page, "slide_page": slide_page,
        "figure_id": figure_id,
        "figure_caption_layout_status": figure["source_caption_layout_status"],
        "automatically_detected_layout_reflow":reflow_found,
        "source_layout_automatic_disposition":figure["layout_recovery_diagnostic"]["status"],
        "legacy_whole_crop_aspect_rejection_resolved_as_layout_only":
            figure["legacy_whole_crop_aspect_rejection_resolved_as_layout_only"],
        "original_vector_objects_unassigned":
            figure["source_pre_caption_drawing_count"],
        "video_candidates": videos,
        "strict_duration_violations": violations,
        "unmeasured_video_candidates": unmeasured,
        "multipart_media_verified": media["multipart_media_verified"],
        "multipart_media_failure_reason": media["multipart_media_failure_reason"],
        "blocker_codes": blockers,
        "complete_figure_and_panels_certified": False,
        "source_to_slide_equivalence_certified": False,
        "spoken_element_highlight_certified": False,
        "all_video_parts_strictly_under_600_certified": False,
        "human_academic_qa_certified": False,
        "student_publication_authorized": False,
        "all_original_assets_unchanged": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--source-page", type=int, required=True)
    parser.add_argument("--slide-page", type=int, required=True)
    parser.add_argument("--figure-id", required=True)
    a = parser.parse_args(argv)
    report = inspect_joint_original_lecture(
        folder=a.folder, source_page=a.source_page,
        slide_page=a.slide_page, figure_id=a.figure_id)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
