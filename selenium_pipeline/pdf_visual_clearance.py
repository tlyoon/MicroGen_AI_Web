"""Reject body text touching embedded scientific figure images.

A Figure-in-PDF may have perfectly valid semantic anchors yet place a
separate caption or explanation on top of its rasterized panel labels.
This checks rendered PDF layout before geometry acceptance/TTS, without
editing, rescaling, clipping, or separating source figure panels.
"""
from __future__ import annotations

import math
from pathlib import Path

import pymupdf

DEFAULT_MIN_CLEARANCE_PT = 8.0
DEFAULT_MIN_HORIZONTAL_INTERSECTION_PT = 5.0


def audit_raster_image_text_clearance(
    pdf_path: str | Path, *,
    min_clearance_pt: float = DEFAULT_MIN_CLEARANCE_PT,
    min_horizontal_intersection_pt: float = DEFAULT_MIN_HORIZONTAL_INTERSECTION_PT,
) -> list[dict]:
    """Describe suspicious body-text/image gaps, without mutating the PDF.

    Header (<25 pt from page top) and footer (within 20 pt of bottom)
    are excluded because many Beamer themes intentionally use those areas.
    A raster image contains its own printed diagram labels; PyMuPDF returns
    those as image pixels, so they are never treated as separate body text.
    Vector drawing-only backgrounds are out of scope of this narrow gate.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise ValueError("PDF unavailable for image/text clearance audit")
    for value, name in ((min_clearance_pt, "min_clearance_pt"),
                        (min_horizontal_intersection_pt, "min_horizontal_intersection_pt")):
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Invalid " + name)
    issues: list[dict] = []
    with pymupdf.open(pdf_path) as doc:
        for index, page in enumerate(doc):
            body = []
            for block in page.get_text("blocks"):
                if len(block) < 7 or block[6] != 0 or not str(block[4]).strip():
                    continue
                rect = pymupdf.Rect(block[:4])
                if (rect.is_empty or rect.y0 < 25.0
                        or rect.y1 > page.rect.height - 20.0):
                    continue
                body.append((rect, str(block[4]).strip()))
            if not body:
                continue
            seen: set[tuple[float, float, float, float]] = set()
            for entry in page.get_images(full=True):
                for rect in page.get_image_rects(entry[0]):
                    key = tuple(round(float(v), 3) for v in rect)
                    if key in seen or rect.is_empty:
                        continue
                    seen.add(key)
                    for text_rect, caption in body:
                        horizontal = min(rect.x1, text_rect.x1) - max(rect.x0, text_rect.x0)
                        if horizontal < min_horizontal_intersection_pt:
                            continue
                        if text_rect.y0 >= rect.y1:
                            vertical = text_rect.y0 - rect.y1
                        elif rect.y0 >= text_rect.y1:
                            vertical = rect.y0 - text_rect.y1
                        else:
                            vertical = -min(rect.y1 - text_rect.y0,
                                            text_rect.y1 - rect.y0)
                        if vertical < min_clearance_pt:
                            issues.append({
                                "page": index + 1,
                                "reason": "raster_figure_body_text_clearance",
                                "image_rect_pt": list(key),
                                "text_rect_pt": [round(float(v), 3) for v in text_rect],
                                "gap_pt": round(float(vertical), 3),
                                "required_gap_pt": min_clearance_pt,
                                "text_excerpt": caption[:110],
                            })
    return issues
