"""Fail-closed source-versus-slide figure evidence, *not* a media promoter.

Combines independently observed source figure heading/column collisions and
pre-caption vector objects with an untouched lecture slide PDF inventory.
No invented figure crop, panel mapping or semantic approval is permitted.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pymupdf

from .figure_caption_column_audit import audit_caption_column_collision
from .figure_pre_caption_vector_inventory import inventory_pre_caption_vectors
from .figure_source_identity import require, _sha


def assess_real_source_slide_figure(*, source: Path, slides: Path,
                                    source_page: int, slide_page: int,
                                    figure_id: str,
                                    automatic_layout_review: bool = True) -> dict:
    caption = audit_caption_column_collision(
        source=source, page_number=source_page, figure_id=figure_id
    )
    vectors = inventory_pre_caption_vectors(
        source=source, page_number=source_page, figure_id=figure_id
    )
    require(vectors["source_sha256"] == caption["source_sha256"],
            "Source changed between independent audits")
    slide_path = Path(slides).absolute()
    for part in (slide_path, *slide_path.parents):
        require(not part.is_symlink()
                and not getattr(part, "is_junction", lambda: False)(),
                "Symlink or junction slide path prohibited")
    require(slide_path.is_file() and slide_path.suffix.lower() == ".pdf",
            "Real regular slide PDF required")
    require(type(slide_page) is int and slide_page > 0,
            "One-based slide page required")
    slide_sha = _sha(slide_path)
    with pymupdf.open(slide_path) as deck:
        require(len(deck) <= 250 and slide_page <= len(deck),
                "Slide page out of bounds")
        page = deck[slide_page - 1]
        original_text = page.get_text("text")
        exact_text_matches = len(re.findall(
            r"\bFIGURE\s+" + re.escape(figure_id) + r"\b",
            original_text, flags=re.I
        ))
        raster_count = len(page.get_images(full=True))
        drawing_count = len(page.get_drawings())
        # Do not call an expensive optional reflow detector for pages that
        # contain only vector decorations or tiny bullet raster glyphs.
        material_bitmaps = [item for item in page.get_image_info(xrefs=True)
                            if int(item["width"]) >= 48 and int(item["height"]) >= 48
                            and pymupdf.Rect(item["bbox"]).width >= 50
                            and pymupdf.Rect(item["bbox"]).height >= 25
                            and type(item.get("xref")) is int and item["xref"] > 0]
    if (automatic_layout_review and len(material_bitmaps) == 1
            and vectors["pre_caption_object_count"] > 0):
        from .figure_layout_recovery_dispatch import discover_source_slide_reflow
        reflow = discover_source_slide_reflow(
            source=source, slides=slides, source_page=source_page,
            slide_page=slide_page, figure_id=figure_id)
    else:
        reflow = {"status":"NO_UNIQUE_MATERIAL_BITMAP_FOR_AUTOMATIC_REFLOW",
                  "layout_reflow_detected":False,
                  "previous_whole_source_crop_aspect_mismatch_resolved_as_layout_only":False,
                  "publication_authorized":False}
    require(not reflow["publication_authorized"],
            "Optional layout detector must never authorize production")
    if reflow["layout_reflow_detected"]:
        require(reflow["source_sha256"] == caption["source_sha256"]
                and reflow["slides_sha256"] == slide_sha,
                "Automatic layout evidence refers to changed original files")
    require(_sha(Path(source).absolute()) == caption["source_sha256"],
            "Original source changed during review")
    require(_sha(slide_path) == slide_sha, "Slide PDF changed during review")
    return {
        "schema_version": 1,
        "status": "REAL_SOURCE_SLIDE_FIGURE_EVIDENCE_BLOCKED",
        "source_sha256": caption["source_sha256"],
        "slides_sha256": slide_sha,
        "source_page": source_page,
        "slide_page": slide_page,
        "figure_id": figure_id,
        "source_caption_layout_status": caption["status"],
        "source_parallel_prose_line_count": caption["parallel_prose_line_count"],
        "source_pre_caption_drawing_count": vectors["pre_caption_object_count"],
        "slide_exact_figure_caption_text_matches": exact_text_matches,
        "slide_raster_object_count": raster_count,
        "slide_vector_drawing_count": drawing_count,
        "automatically_detected_layout_reflow":reflow["layout_reflow_detected"],
        "legacy_whole_crop_aspect_rejection_resolved_as_layout_only":
            reflow["previous_whole_source_crop_aspect_mismatch_resolved_as_layout_only"],
        "layout_recovery_diagnostic":reflow,
        "source_graph_objects_scientifically_assigned": False,
        "original_complete_panel_boundaries_verified": False,
        "source_to_slide_figure_identity_verified": False,
        "narrated_element_highlight_verified": False,
        "video_part_duration_verified": False,
        "figure_video_authorized": False,
        "student_publication_authorized": False,
        "human_academic_review_claimed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail-closed original figure/slide evidence")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--slides", type=Path, required=True)
    parser.add_argument("--source-page", type=int, required=True)
    parser.add_argument("--slide-page", type=int, required=True)
    parser.add_argument("--figure-id", required=True)
    args = parser.parse_args(argv)
    report = assess_real_source_slide_figure(
        source=args.source, slides=args.slides,
        source_page=args.source_page, slide_page=args.slide_page,
        figure_id=args.figure_id
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    # Never let automation mistake this evidence packet for acceptance.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
