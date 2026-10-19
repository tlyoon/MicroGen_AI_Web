"""Independent on-slide raster visibility audit for vector-source textbook art.

Exact displayed embedded-raster pixels are NOT evidence of source-panel
identity, author-intended completeness, or narration/video authorization.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pymupdf

from .figure_real_source_slide_gate import assess_real_source_slide_figure
from .figure_source_identity import _sha, require


def audit_vector_source_slide_raster(*, source: Path, slides: Path,
                                     source_page: int, slide_page: int,
                                     figure_id: str) -> dict:
    parent = assess_real_source_slide_figure(
        source=source, slides=slides, source_page=source_page,
        slide_page=slide_page, figure_id=figure_id)
    spath, dpath = Path(source).absolute(), Path(slides).absolute()
    require(spath != dpath, "Source and slide must be distinct PDFs")
    shash, dhash = parent["source_sha256"], parent["slides_sha256"]
    report = {
        "schema_version": 1,
        "status": "SOURCE_SLIDE_RASTER_PROVENANCE_REVIEW_REQUIRED",
        "figure_id": figure_id, "source_page": source_page,
        "slide_page": slide_page, "source_sha256": shash,
        "slides_sha256": dhash,
        "source_pre_caption_unassigned_vector_objects":
            parent["source_pre_caption_drawing_count"],
        "source_image_instances": 0,
        "slide_image_instances": 0,
        "slide_material_image_instances": 0,
        "slide_tiny_image_instances": 0,
        "slide_embedded_raster_bbox": None,
        "slide_embedded_raster_dimensions": None,
        "slide_embedded_encoded_sha256": None,
        "slide_reference_render_pixels_equal": False,
        "original_complete_figure_proven": False,
        "original_panel_count_and_labels_proven": False,
        "source_to_slide_figure_identity_proven": False,
        "scientific_semantics_proven": False,
        "narrated_highlight_proven": False,
        "encoded_video_accepted": False,
        "student_publication_authorized": False,
    }
    with pymupdf.open(spath) as book, pymupdf.open(dpath) as deck:
        original, slide = book[source_page - 1], deck[slide_page - 1]
        original_images = original.get_image_info(xrefs=True)
        slide_images = slide.get_image_info(xrefs=True)
        report["source_image_instances"] = len(original_images)
        report["slide_image_instances"] = len(slide_images)
        # Tiny PDF inline glyphs (for example slide-list bullets) are
        # separate draw instances, not evidence of figure content.
        # Excluding them from material candidates NEVER certifies a figure.
        material = [item for item in slide_images
                    if int(item["width"]) >= 48
                    and int(item["height"]) >= 48
                    and pymupdf.Rect(item["bbox"]).width >= 50
                    and pymupdf.Rect(item["bbox"]).height >= 25]
        report["slide_material_image_instances"] = len(material)
        report["slide_tiny_image_instances"] = len(slide_images) - len(material)
        if original_images:
            report["status"] = "SOURCE_NOT_EXCLUSIVELY_VECTOR_REVIEW_REQUIRED"
        elif len(material) != 1:
            report["status"] = "SLIDE_MATERIAL_IMAGE_MISSING_OR_MULTIPLE_REVIEW_REQUIRED"
        else:
            item = material[0]
            xref = item.get("xref")
            rectangle = pymupdf.Rect(item["bbox"])
            embedded = [entry for entry in slide.get_images(full=True)
                        if entry[0] == xref]
            placements = slide.get_image_rects(xref) if type(xref) is int and xref > 0 else []
            aspect = float(item["width"]) / max(1, float(item["height"]))
            positioned = (len(embedded) == 1 and embedded[0][1] == 0
                          and len(placements) == 1
                          and pymupdf.Rect(placements[0]).intersects(rectangle)
                          and rectangle.is_valid and not rectangle.is_empty
                          and slide.rect.contains(rectangle)
                          and rectangle.width >= 50 and rectangle.height >= 25
                          and float(item["width"]) >= 48
                          and float(item["height"]) >= 48
                          and math.isfinite(aspect)
                          and abs(rectangle.width / rectangle.height - aspect)
                              <= .02 * aspect
                          and rectangle.width * rectangle.height * 4 <= 4_000_000)
            if type(xref) is not int or xref <= 0 or not positioned:
                report["status"] = "SLIDE_RASTER_PLACEMENT_AMBIGUOUS_REVIEW_REQUIRED"
            else:
                extracted = deck.extract_image(xref)
                require(isinstance(extracted, dict)
                        and isinstance(extracted.get("image"), bytes)
                        and 0 < len(extracted["image"]) <= 15_000_000,
                        "Slide embedded raster missing or excessively large")
                report["slide_embedded_raster_bbox"] = [
                    round(float(v), 3) for v in rectangle]
                report["slide_embedded_raster_dimensions"] = [
                    int(item["width"]), int(item["height"])]
                report["slide_embedded_encoded_sha256"] = hashlib.sha256(
                    extracted["image"]).hexdigest()
                with pymupdf.open() as ref:
                    page = ref.new_page(
                        width=slide.rect.width, height=slide.rect.height)
                    page.insert_image(
                        rectangle, stream=extracted["image"],
                        keep_proportion=False)
                    matrix = pymupdf.Matrix(2, 2)
                    current = slide.get_pixmap(
                        matrix=matrix, clip=rectangle, annots=True,
                        colorspace=pymupdf.csRGB, alpha=False)
                    expected = page.get_pixmap(
                        matrix=matrix, clip=rectangle, annots=False,
                        colorspace=pymupdf.csRGB, alpha=False)
                    require(current.n == expected.n == 3
                            and current.width == expected.width
                            and current.height == expected.height
                            and current.width * current.height <= 4_000_000,
                            "Slide raster reference dimension mismatch")
                    identical = bytes(current.samples) == bytes(expected.samples)
                report["slide_reference_render_pixels_equal"] = identical
                report["status"] = (
                    "VISIBLE_SLIDE_RASTER_ONLY_SOURCE_FIGURE_UNVERIFIED"
                    if identical else
                    "SLIDE_RASTER_VISIBLE_PIXELS_DIFFER_REVIEW_REQUIRED")
    require(_sha(spath) == shash and _sha(dpath) == dhash,
            "Original textbook or slide PDF changed during read-only audit")
    return report
def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--slides", type=Path, required=True)
    parser.add_argument("--source-page", type=int, required=True)
    parser.add_argument("--slide-page", type=int, required=True)
    parser.add_argument("--figure-id", required=True)
    args = parser.parse_args(argv)
    report = audit_vector_source_slide_raster(
        source=args.source, slides=args.slides,
        source_page=args.source_page, slide_page=args.slide_page,
        figure_id=args.figure_id)
    print(json.dumps(report, indent=2, sort_keys=True))
    # Even identical on-screen pixels do NOT establish textbook origin.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
