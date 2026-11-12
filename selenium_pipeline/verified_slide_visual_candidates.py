"""Physical figure and composite-math targets for ordinary academic review.

A text-only review target inventory made real multi-panel art impossible to
select. This module adds real PDF-bounded, uniquely positioned image objects
and physically anchored multi-block equation regions. They are REVIEW choices:
the pictured scientific meaning, actual panel boundaries, source image identity,
equation semantics, pronunciation and audio timing are never inferred here.
"""
from __future__ import annotations

import math

import pymupdf

from .figure_source_identity import require
from .sourcebound_math_row_focus import discover_math_rows, math_row_rect


def _bbox(rect: pymupdf.Rect) -> list[float]:
    return [round(float(x), 3) for x in rect]


def _valid_rect(rect: pymupdf.Rect, page) -> bool:
    return (not rect.is_empty and not rect.is_infinite
            and all(math.isfinite(float(x)) for x in rect)
            and page.rect.contains(rect)
            and rect.width >= 25 and rect.height >= 25
            and rect.get_area() < page.rect.get_area() * .80)


def registered_raster_targets(page, slide_number: int) -> list[dict]:
    """Expose only unique, directly verifiable unmasked embedded image regions."""
    require(type(slide_number) is int and slide_number >= 1,
            "Invalid physical slide index")
    registry = page.get_images(full=True)
    registered = {int(x[0]): x for x in registry
                  if type(x[0]) is int and x[0] > 0 and x[1] == 0}
    counts = {}
    for item in registry:
        counts[int(item[0])] = counts.get(int(item[0]), 0) + 1
    out = []
    for image in page.get_image_info(hashes=True, xrefs=True):
        xref = image.get("xref")
        fingerprint = image.get("digest")
        rect = pymupdf.Rect(image.get("bbox", ()))
        native = (image.get("width"), image.get("height"))
        if (type(xref) is not int or xref not in registered
                or counts.get(xref) != 1
                or not isinstance(fingerprint, bytes) or len(fingerprint) != 16
                or any(type(n) is not int or n < 60 for n in native)
                or not _valid_rect(rect, page)):
            continue
        placements = page.get_image_rects(xref)
        if (len(placements) != 1
                or not all(abs(a-b) < .002 for a,b in zip(placements[0], rect))):
            continue
        element_id = f"s{slide_number:03d}.figure.{len(out)+1:03d}"
        out.append({
            "draft_element_id": element_id,
            "kind": "image_whole",
            "visible_text": "",
            "bbox_pdf_pt": _bbox(rect),
            "panel_identity_review_required": True,
            "actual_source_panel_identity_verified": False,
            "figure_semantics_verified": False,
            "anchor": {"type": "registered_image",
                       "xref": xref,
                       "native_dimensions_px": list(native),
                       "decoded_image_md5": fingerprint.hex(),
                       "rendered_bbox_pdf_pt": _bbox(rect)},
        })
        require(len(out) <= 16,
                "Unbounded material raster inventory on a single slide")
    return out


def composite_math_targets(page, slide_number: int,
                           existing_text_targets: list[dict]) -> list[dict]:
    """Recognize PDF-backed, grouped equations; never approve their meaning."""
    out=[]
    for candidate in discover_math_rows(page, slide_number, existing_text_targets):
        rect=math_row_rect(page, candidate["anchor"])
        if not _valid_rect(rect,page):
            continue
        out.append({
            "draft_element_id": candidate["draft_element_id"],
            "kind": "math_row_group",
            "visible_text": candidate["visible_text"],
            "bbox_pdf_pt": _bbox(rect),
            "panel_identity_review_required": False,
            "math_semantics_verified": False,
            "anchor": candidate["anchor"],
        })
    return out


def verify_visual_target(page, slide_number: int, supplied: dict) -> dict:
    """Reconstruct exact image/math geometry; forged tags and pixels are denied."""
    require(type(supplied) is dict
            and supplied.get("kind") in ("image_whole", "math_row_group"),
            "Expected an actual image or PDF equation target")
    kind = supplied["kind"]
    if kind == "image_whole":
        options = registered_raster_targets(page, slide_number)
    else:
        options = composite_math_targets(page, slide_number, [])
    matched = [x for x in options
               if x["draft_element_id"] == supplied.get("draft_element_id")]
    require(len(matched) == 1 and matched[0] == supplied,
            "Original PDF visual element geometry, image hash or claim changed")
    return matched[0]
