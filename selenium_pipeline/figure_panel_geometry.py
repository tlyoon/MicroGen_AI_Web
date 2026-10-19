"""Strict, read-only composite-raster panel geometry candidate preflight.

Only an explicitly supplied native-pixel strip partition is evaluated; the
partition and panel labels are NOT inferred from scientific imagery. Parent
PRs prove embedded source identity and unoccluded PDF raster equivalence.
This module proves pixel coverage and the source->slide coordinate mapping,
not semantic panel identity, completeness of author's labels or TTS readiness.
"""
from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

import pymupdf
from PIL import Image

from .figure_source_identity import _one_image, _sha, require
from .figure_render_equivalence import inspect_rendered_whole_raster_candidate


def _rgb_bitmap(document, xref: int, label: str) -> Image.Image:
    data = document.extract_image(xref)
    require(isinstance(data, dict) and isinstance(data.get("image"), bytes),
            f"{label}: cannot independently decode embedded bitmap")
    try:
        with Image.open(BytesIO(data["image"])) as inp:
            require(inp.mode == "RGB",
                    f"{label}: non-RGB/palette/alpha bitmap needs independent audit")
            bitmap = inp.copy()
    except (OSError, ValueError) as exc:
        require(False, f"{label}: unsupported or undecodable embedded bitmap: {exc}")
    return bitmap


def _page_rect(container: pymupdf.Rect, *, axis: str,
               start: int, end: int, length: int) -> list[float]:
    if axis == "horizontal":
        bounds = pymupdf.Rect(
            container.x0 + container.width * start / length,
            container.y0,
            container.x0 + container.width * end / length,
            container.y1,
        )
    else:
        bounds = pymupdf.Rect(
            container.x0,
            container.y0 + container.height * start / length,
            container.x1,
            container.y0 + container.height * end / length,
        )
    return [round(x, 4) for x in bounds]


def inspect_declared_composite_geometry(
    *, source: Path, slides: Path, source_page: int, slide_page: int,
    caption: str, axis: str, boundaries_px: list[int],
    declared_panel_ids: list[str], scale: int = 2,
) -> dict:
    """Verify an explicit complete partition and identical decoded panel pixels.

    This is a *candidate* report. Even a perfect full-width partition can cut
    through an actual panel or misidentify (a)/(b)/(c) content. Therefore it
    never certifies panel semantics/completeness or approves production TTS.
    """
    parent = inspect_rendered_whole_raster_candidate(
        source=source, slides=slides, source_page=source_page,
        slide_page=slide_page, caption=caption, scale=scale,
    )
    require(parent["rendered_raster_equivalence_verified"] is True,
            "Independent parent figure rendering proof absent")
    require(axis in ("horizontal", "vertical"),
            "Explicit native-pixel strip axis required")
    require(isinstance(boundaries_px, list)
            and all(type(x) is int for x in boundaries_px)
            and 3 <= len(boundaries_px) <= 7,
            "Two to six exact integer panel boundaries are required")
    count = len(boundaries_px) - 1
    require(isinstance(declared_panel_ids, list)
            and declared_panel_ids == list("abcdef"[:count]),
            "Panel identifiers must be unique, complete and in declared a.. order")
    source = Path(source).resolve(strict=True)
    slides = Path(slides).resolve(strict=True)
    require(_sha(source) == parent["source_sha256"]
            and _sha(slides) == parent["slides_sha256"],
            "Source or slide PDF changed during panel proof")

    with pymupdf.open(source) as textbook, pymupdf.open(slides) as deck:
        src_item, src_rect, sxref = _one_image(
            textbook, source_page, caption, "source")
        dst_item, dst_rect, dxref = _one_image(
            deck, slide_page, caption, "slide")
        a = _rgb_bitmap(textbook, sxref, "source")
        b = _rgb_bitmap(deck, dxref, "slide")
        require(a.size == b.size
                and a.size == (src_item["width"], src_item["height"])
                and b.size == (dst_item["width"], dst_item["height"]),
                "Source/slide native pixel dimensions changed")
        require(a.tobytes() == b.tobytes(),
                "Decoded source and slide pixels differ")
        length = a.width if axis == "horizontal" else a.height
        require(boundaries_px[0] == 0 and boundaries_px[-1] == length
                and all(0 <= left < right <= length
                        for left, right in zip(boundaries_px, boundaries_px[1:])),
                "Panel partition has gaps, overlaps, reversal or incomplete coverage")
        require(all(right - left >= 30
                    for left, right in zip(boundaries_px, boundaries_px[1:])),
                "One or more declared panels are too narrow in native pixels")

        records, identities = [], set()
        for index, (start, end) in enumerate(
            zip(boundaries_px, boundaries_px[1:])
        ):
            native = (
                (start, 0, end, a.height)
                if axis == "horizontal" else
                (0, start, a.width, end)
            )
            pixels_a = a.crop(native)
            pixels_b = b.crop(native)
            require(pixels_a.size == pixels_b.size
                    and pixels_a.tobytes() == pixels_b.tobytes(),
                    "Panel source and slide pixel content differs")
            require(pixels_a.width >= 30 and pixels_a.height >= 30,
                    "Panel raster is illegibly small")
            extrema = pixels_a.getextrema()
            require(any(lo != hi for lo, hi in extrema),
                    "Blank or uniform-color panel cannot establish identity")
            panel_id = hashlib.sha256(pixels_a.tobytes()).hexdigest()
            require(panel_id not in identities,
                    "Identical-looking panels cannot be uniquely identified")
            identities.add(panel_id)
            slide_box = _page_rect(
                dst_rect, axis=axis, start=start, end=end, length=length)
            source_box = _page_rect(
                src_rect, axis=axis, start=start, end=end, length=length)
            require((slide_box[2] - slide_box[0]) >= 30
                    and (slide_box[3] - slide_box[1]) >= 30,
                    "Panel occupies an insufficient slide region")
            records.append({
                "declared_id": declared_panel_ids[index],
                "native_bbox_px": list(native),
                "native_pixel_sha256": panel_id,
                "source_bbox": source_box,
                "slide_bbox": slide_box,
                "source_slide_pixels_identical": True,
                "panel_semantics_certified": False,
            })
    require(_sha(source) == parent["source_sha256"]
            and _sha(slides) == parent["slides_sha256"],
            "PDF changed during source-grounded panel proof")
    return {
        "schema_version": 1,
        "status": "EXPLICIT_PANEL_PARTITION_GEOMETRY_CANDIDATE_REVIEW_REQUIRED",
        "source_sha256": parent["source_sha256"],
        "slides_sha256": parent["slides_sha256"],
        "source_page": source_page,
        "slide_page": slide_page,
        "image_native_size": list(a.size),
        "axis": axis,
        "boundaries_px": list(boundaries_px),
        "panels": records,
        "panel_raster_partition_coverage_verified": True,
        "rendered_parent_raster_equivalence_verified": True,
        "declared_panel_labels_source_verified": False,
        "figure_panel_completeness_certified": False,
        "figure_semantics_certified": False,
        "tts_or_video_authorized": False,
        "human_review_claimed": False,
    }
