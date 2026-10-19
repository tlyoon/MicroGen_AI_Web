"""Read-only pre-caption vector drawing object inventory, not figure inference.

Scientific graph ownership, panel boundaries, and source-slide identity must
be independently supplied/verified before any narration/video authorization.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf

from .figure_caption_column_audit import audit_caption_column_collision
from .figure_source_identity import require, _sha


def inventory_pre_caption_vectors(*, source: Path, page_number: int,
                                  figure_id: str) -> dict:
    heading = audit_caption_column_collision(
        source=source, page_number=page_number, figure_id=figure_id
    )
    path = Path(source).absolute()
    sha = heading["source_sha256"]
    with pymupdf.open(path) as doc:
        page = doc[page_number - 1]
        y_stop = float(heading["heading_bbox"][1]) - 3.0
        # ONLY a conservative scan corridor, NEVER a figure crop.
        x_stop = min(page.rect.width * .34,
                     float(heading["heading_bbox"][2]) + 130.0)
        require(y_stop > 0 and x_stop > 0, "Invalid pre-caption corridor")
        drawings = page.get_drawings()
        require(len(drawings) <= 2000, "Unbounded drawing inventory")
        included, exclusions = [], {
            "empty_or_invalid": 0,
            "outside_source_page": 0,
            "after_heading": 0,
            "outside_caption_column": 0,
        }
        for index, drawing in enumerate(drawings):
            r = pymupdf.Rect(drawing["rect"])
            if (r.is_infinite or r.width < 0 or r.height < 0
                or (r.width < .5 and r.height < .5)):
                exclusions["empty_or_invalid"] += 1
                continue
            if not page.rect.contains(r):
                exclusions["outside_source_page"] += 1
                continue
            if r.y1 >= y_stop:
                exclusions["after_heading"] += 1
                continue
            if r.x0 < 0 or r.x1 >= x_stop:
                exclusions["outside_caption_column"] += 1
                continue
            included.append({
                "drawing_index": index,
                "bbox": [round(float(v), 3) for v in r],
                "drawing_operation_count": len(drawing.get("items", [])),
                "drawing_type": str(drawing.get("type", "")),
            })
        result = {
            "schema_version": 1,
            "status": ("PRECAPTION_VECTOR_OBJECTS_REQUIRE_INDEPENDENT_GROUPING"
                       if included else "PRECAPTION_VECTOR_OBJECTS_ABSENT_REVIEW_REQUIRED"),
            "source_sha256": sha,
            "source_page": page_number,
            "figure_id": figure_id,
            "heading_bbox": heading["heading_bbox"],
            "caption_column_audit_status": heading["status"],
            "candidate_scan_corridor": [0.0, 0.0,
                                        round(x_stop, 3), round(y_stop, 3)],
            "total_page_drawing_count": len(drawings),
            "pre_caption_object_count": len(included),
            "pre_caption_drawing_objects": included,
            "excluded_drawing_reasons": exclusions,
            "source_object_membership_certified": False,
            "whole_graph_bbox_certified": False,
            "original_panel_labels_certified": False,
            "figure_scientific_semantics_certified": False,
            "source_to_slide_equivalence_certified": False,
            "tts_or_video_authorized": False,
        }
    require(_sha(path) == sha, "Source changed during inventory")
    return result
