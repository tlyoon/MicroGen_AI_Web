"""Source-only mixed equation + photographed Figure recovery from owned refusal.

An embedded PDF raster adjacent to one printed numbered Figure caption can be
matched to that caption while a *separate* text-dominant math crop is assigned
an explicit, NOT-PRINTED source equation label. Exact two-crop geometry, SHA
and source raster/text corroboration are required. No Gemini resend, invented
caption, panel split, scientific approval, or publication permission.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

import pymupdf

from .figure_composites import validate_and_prepare_mappings
from .figure_uncaptioned_source_recovery import _digest


class MixedSourceMappingNotProven(ValueError):
    pass


def _must(value: bool, message: str) -> None:
    if not value:
        raise MixedSourceMappingNotProven(message)


def _intersection_ratio(a: pymupdf.Rect, b: pymupdf.Rect) -> float:
    area = max(a.get_area(), 0)
    return ((a & b).get_area() / area) if area else 0.0


def recover_mixed_source_equation_photo(
    *, response: str, source_pdf: Path, page_png: Path,
    crops_dir: Path, geometry_manifest: Path,
) -> tuple[list[tuple[str, str, str]], dict]:
    """Recover only physically unique equation/photo-caption pairs."""
    _must(response == "MAPPING_REVIEW_REQUIRED",
          "Only exact owned model refusal is eligible")
    source_pdf = Path(source_pdf)
    page_png = Path(page_png)
    crops_dir = Path(crops_dir)
    geometry_manifest = Path(geometry_manifest)
    match = re.fullmatch(r"page_([1-9][0-9]*)\.png", page_png.name)
    _must(match is not None, "Untrusted original page filename")
    number = int(match[1])
    _must(crops_dir.is_dir() and not crops_dir.is_symlink()
          and geometry_manifest.parent == crops_dir
          and geometry_manifest.name == f"page_{number}_crop_geometry.json",
          "Source crop workspace/geometry identity changed")
    pdfsha = _digest(source_pdf, 25_000_000)
    pagesha = _digest(page_png, 25_000_000)
    manifestsha = _digest(geometry_manifest, 2_000_000)
    try:
        record = json.loads(geometry_manifest.read_text(encoding="utf8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise MixedSourceMappingNotProven("Source geometry unreadable") from exc
    _must(type(record) is dict
          and record.get("schema_version") == 1
          and record.get("status") == "SOURCE_DECLARED_CROP_GEOMETRY_CANDIDATES_NOT_VERIFIED"
          and record.get("crop_count") == 2
          and record.get("page_number") == number
          and record.get("original_source_pdf_sha256") == pdfsha
          and record.get("page_image_sha256") == pagesha
          and record.get("source_crop_pixel_correspondence_verified") is False
          and record.get("figure_composite_layout_certified") is False
          and record.get("student_publication_authorized") is False
          and type(record.get("crops")) is list
          and len(record["crops"]) == 2,
          "Only original SHA-grounded exact two-crop geometry qualifies")
    items = {}
    for item in record["crops"]:
        name = item.get("crop_file") if isinstance(item, dict) else None
        _must(type(name) is str
              and re.fullmatch(r"fig_[1-9][0-9]*\.png", name) is not None
              and name not in items
              and item.get("status") == "DOCLING_SINGLE_SOURCE_RECT_CANDIDATE"
              and item.get("source_pdf_sha256") == pdfsha
              and item.get("source_page") == number
              and item.get("page_image_sha256") == pagesha
              and item.get("source_crop_pixel_correspondence_verified") is False
              and item.get("original_caption_and_panel_semantics_verified") is False
              and item.get("automatic_composite_or_publication_authorized") is False
              and item.get("crop_sha256") == _digest(crops_dir / name, 25_000_000),
              "Original Docling source crop not byte/geometry-grounded")
        box = item.get("bbox_source_pdf_top_left_pt")
        size = item.get("source_page_size_pt")
        _must(type(box) is list and len(box) == 4
              and type(size) is list and len(size) == 2
              and all(type(v) in (int, float) and math.isfinite(v)
                      for v in box+size)
              and 0 <= box[0] < box[2] <= size[0]
              and 0 <= box[1] < box[3] <= size[1],
              "Untrusted original source-space crop rectangle")
        items[name] = {"bbox": pymupdf.Rect(box),
                       "size": size, "hash": item["crop_sha256"]}
    _must(set(items) == {p.name for p in crops_dir.glob("fig_*.png")},
          "Exactly two original source crop files required")
    with pymupdf.open(source_pdf) as doc:
        _must(0 < number <= len(doc), "Original page out of bounds")
        page = doc[number-1]
        _must(all(abs(v-s) < .1 for v,s in zip(page.rect[2:], next(iter(items.values()))["size"])),
              "Original source page dimensions changed")
        words = page.get_text("words")
        _must(len(words) >= 60, "Insufficient original selectable text")
        picture_bboxes = [pymupdf.Rect(row["bbox"])
                         for row in page.get_image_info(xrefs=True)
                         if row.get("xref", 0) > 0]
        _must(len(picture_bboxes) >= 1, "No actual embedded source photo evidence")
        profiles = {}
        for name, item in items.items():
            box = item["bbox"]
            hitwords = [w for w in words if pymupdf.Rect(w[:4]).intersects(box)]
            near_raster = [r for r in picture_bboxes if _intersection_ratio(r, box) >= .90
                           and _intersection_ratio(box, r) >= .70]
            profiles[name] = {"words": hitwords,
                              "embedded_raster_count": len(near_raster),
                              "box": box}
        image_candidates = [n for n,p in profiles.items()
                            if p["embedded_raster_count"] == 1
                            and len(p["words"]) <= 4]
        equation_candidates = [n for n,p in profiles.items()
                               if p["embedded_raster_count"] == 0
                               and len(p["words"]) >= 10
                               and p["box"].height <= 70]
        _must(len(image_candidates) == len(equation_candidates) == 1
              and image_candidates[0] != equation_candidates[0],
              "Ambiguous math-versus-photograph original source crop geometry")
        photo = image_candidates[0]
        eq = equation_candidates[0]
        rect = profiles[photo]["box"]
        captions = []
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                text = "".join(span.get("text","") for span in line.get("spans", []))
                m = re.match(r"^\s*Figure\s+([1-9][0-9]*\.[1-9][0-9]*)\b",
                             text, flags=re.I)
                if m:
                    candidate = pymupdf.Rect(line["bbox"])
                    if 0 <= candidate.y0 - rect.y1 <= 25:
                        captions.append((m[1], candidate))
        _must(len(captions) == 1, "Unique printed original Figure caption required")
        identifier, heading = captions[0]
        horizontal = max(0, min(rect.x1, heading.x1)-max(rect.x0,heading.x0))
        _must(0 <= heading.y0-rect.y1 <= 25
              and horizontal / max(1, min(rect.width, heading.width)) >= .65
              and heading.y0 > profiles[eq]["box"].y1,
              "Printed caption not uniquely aligned directly below embedded image")
    rows = [(name,
             f"Figure {identifier}" if name == photo else "Unlabeled source equation",
             f"Figure {identifier}.png" if name == photo
             else f"Unlabeled source equation page_{number} {Path(name).stem}.png")
            for name in items]
    validate_and_prepare_mappings(rows)
    evidence = {
        "schema_version": 1,
        "status": "ORIGINAL_MIXED_MATH_PHOTO_CAPTION_GEOMETRY_VERIFIED_NOT_ACADEMIC_QA",
        "source_pdf_sha256": pdfsha,
        "page_number": number,
        "page_png_sha256": pagesha,
        "original_crop_manifest_sha256": manifestsha,
        "original_crop_sha256": {n:item["hash"] for n,item in items.items()},
        "printed_figure_id": identifier,
        "printed_caption_geometry_verified": True,
        "equation_is_unlabeled_not_printed_caption": True,
        "embedded_photo_crop": photo,
        "unnumbered_math_crop": eq,
        "new_model_sends": 0,
        "source_crop_pixel_correspondence_verified": False,
        "independent_scientific_and_diagram_semantics_verified": False,
        "full_lecture_figure_mapping_verified": False,
        "student_publication_authorized": False,
        "resolution": [list(row) for row in rows],
        "original_model_response_sha256": hashlib.sha256(response.encode("utf8")).hexdigest(),
    }
    return rows, evidence
