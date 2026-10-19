"""Independent visual-gutter evidence for declared vector source panel seams.

Cannot infer or certify the author's intended panel boundaries. An ambiguous
whitespace band can pass. No production narration/video authorization.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf

from .figure_source_identity import require, _sha
from .figure_vector_provenance import inspect_vector_figure_region


def inspect_vector_panel_seams(
    *, source: Path, slides: Path, source_page: int, slide_page: int,
    source_bbox: list[float], slide_bbox: list[float],
    panel_boxes: list[list[float]], caption: str, panel_ids: list[str],
    scale: int = 2, gutter_half_width_px: int = 3,
) -> dict:
    """Validate full-height/width *white* gutters at all declared panel seams.

    This is a necessary visual separation predicate only for the narrow
    white-background strip diagrams it supports. Absence of a gutter blocks.
    Presence of a gutter is NOT sufficient for scientifically correct panel
    segmentation; the output remains an unapproved candidate.
    """
    parent = inspect_vector_figure_region(
        source=source, slides=slides, source_page=source_page,
        slide_page=slide_page, source_bbox=source_bbox,
        slide_bbox=slide_bbox, panel_boxes=panel_boxes,
        caption=caption, panel_ids=panel_ids, scale=scale,
    )
    require(type(gutter_half_width_px) is int
            and 2 <= gutter_half_width_px <= 8,
            "Gutter evidence needs a bounded integer pixel half-width")
    original = Path(source).resolve(strict=True)
    slide = Path(slides).resolve(strict=True)
    require(parent["source_sha256"] == _sha(original)
            and parent["slides_sha256"] == _sha(slide),
            "Inputs changed after vector provenance check")
    sr = pymupdf.Rect(parent["source_bbox"])
    boxes = [pymupdf.Rect(record["source_bbox"])
             for record in parent["panels"]]
    horizontal = (len(boxes) >= 2
                  and abs(boxes[0].y0 - boxes[1].y0) < .01)
    span = sr.width if horizontal else sr.height
    length = parent["render_size"][0 if horizontal else 1]
    seam_pixels = []
    with pymupdf.open(original) as doc:
        page = doc[source_page-1]
        matrix = pymupdf.Matrix(scale, scale)
        image = page.get_pixmap(matrix=matrix, clip=sr,
                                colorspace=pymupdf.csRGB, alpha=False,
                                annots=True)
        width, height = image.width, image.height
        require([width,height] == parent["render_size"]
                and image.n == 3, "Independent seam render dimensions drifted")
        raw=bytes(image.samples)
        # Only source figure pixels, never raw slide image guessed from names.
        for prev,next_box in zip(boxes, boxes[1:]):
            boundary = prev.x1 if horizontal else prev.y1
            relative = (boundary-sr.x0 if horizontal
                        else boundary-sr.y0)
            coordinate = relative * scale
            require(abs(coordinate-round(coordinate)) < .02,
                    "Panel seam does not map to exact native render pixel grid")
            pos = round(coordinate)
            require(gutter_half_width_px < pos < length-gutter_half_width_px,
                    "Seam too near figure's outer edge")
            # Verify complete vertical/horizontal stripe, not sample points
            # selected near labels. Any non-white pixel is a conservative BLOCK.
            low=pos-gutter_half_width_px
            high=pos+gutter_half_width_px
            checked=0
            for row in range(0 if horizontal else low,
                             height if horizontal else high):
                for column in range(low if horizontal else 0,
                                    high if horizontal else width):
                    offset=(row*width+column)*3
                    rgb=raw[offset:offset+3]
                    require(len(rgb)==3 and all(ch>=247 for ch in rgb),
                            "Declared source panel seam has visible nonwhite content")
                    checked+=1
            require(checked>=width if not horizontal else checked>=height,
                    "Insufficient visual gutter pixels checked")
            seam_pixels.append({
                "figure_axis": "horizontal" if horizontal else "vertical",
                "seam_coordinate_pdf": round(boundary,4),
                "render_pixel_coordinate": pos,
                "stripe_pixel_count": checked,
                "gutter_rgb_min": 247,
                "all_stripe_pixels_near_white": True,
            })
    require(parent["source_sha256"] == _sha(original)
            and parent["slides_sha256"] == _sha(slide),
            "PDF mutated during seam evidence inspection")
    return {
        **parent,
        "status":"VECTOR_PANEL_WHITE_GUTTER_CANDIDATE_REVIEW_REQUIRED",
        "panel_gutter_stripes_verified":True,
        "declared_seam_count":len(seam_pixels),
        "seam_evidence":seam_pixels,
        "seam_evidence_source_sha256":parent["source_sha256"],
        "seam_evidence_slides_sha256":parent["slides_sha256"],
        "source_panel_semantic_boundaries_certified":False,
        "true_panel_boundary_semantics_certified":False,
        "figure_panel_completeness_certified":False,
        "figure_semantics_certified":False,
        "tts_or_video_authorized":False,
        "human_review_claimed":False,
    }
