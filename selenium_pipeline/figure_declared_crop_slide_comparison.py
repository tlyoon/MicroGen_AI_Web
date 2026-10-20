"""Compare a declared source-PDF vector render crop to a visible slide bitmap.

A supplied crop is only an untrusted HYPOTHESIS. Equal raster pixels at a
scale do not prove complete original figure/panel selection or semantics.
"""
from __future__ import annotations
import math
from pathlib import Path
import pymupdf
from .figure_source_identity import require, _sha
from .figure_caption_column_audit import audit_caption_column_collision
from .figure_slide_raster_visibility import audit_vector_source_slide_raster


def audit_declared_crop_match(*, source: Path, slides: Path, source_page: int,
                              slide_page: int, figure_id: str, crop: list) -> dict:
    baseline = audit_vector_source_slide_raster(
        source=source, slides=slides, source_page=source_page,
        slide_page=slide_page, figure_id=figure_id)
    heading = audit_caption_column_collision(
        source=source, page_number=source_page, figure_id=figure_id)
    require(heading["source_sha256"] == baseline["source_sha256"],
            "Inconsistent original textbook identity")
    require(type(crop) is list and len(crop) == 4
            and all(type(v) in (float, int) and math.isfinite(v) for v in crop),
            "Declared crop requires four finite numeric bounds")
    region = pymupdf.Rect(crop)
    spath, dpath = Path(source).absolute(), Path(slides).absolute()
    status = "DECLARED_SOURCE_CROP_MATCH_REVIEW_REQUIRED"
    matched = False
    rect = None
    evidence = {}
    with pymupdf.open(spath) as book, pymupdf.open(dpath) as deck:
        page, slide = book[source_page-1], deck[slide_page-1]
        require(region.is_valid and not region.is_empty
                and page.rect.contains(region)
                and region.width >= 12 and region.height >= 12
                and region.width * region.height <= 300_000,
                "Declared source crop outside bounded original page")
        require(region.y1 < float(heading["heading_bbox"][1]) - 2,
                "Declared source crop is not demonstrably above heading")
        if not baseline["slide_reference_render_pixels_equal"]:
            status = "SLIDE_BITMAP_VISIBILITY_UNVERIFIED"
        else:
            material = [i for i in slide.get_image_info(xrefs=True)
                        if int(i["width"]) >= 48 and int(i["height"]) >= 48
                        and pymupdf.Rect(i["bbox"]).width >= 50
                        and pymupdf.Rect(i["bbox"]).height >= 25]
            require(len(material) == 1 and type(material[0].get("xref")) is int,
                    "One independently visible material slide bitmap required")
            xref = material[0]["xref"]
            pix = pymupdf.Pixmap(deck, xref)
            require(pix.n == 3 and pix.alpha == 0
                    and 48 <= pix.width <= 4000
                    and 48 <= pix.height <= 4000
                    and pix.width * pix.height <= 4_000_000,
                    "Invalid encoded slide bitmap RGB pixels")
            aspect = region.width / region.height
            slide_aspect = pix.width / pix.height
            evidence = {"source_crop_aspect": round(aspect, 6),
                        "slide_bitmap_aspect": round(slide_aspect, 6),
                        "source_crop_bbox": [round(float(x), 3) for x in region],
                        "slide_bitmap_dimensions": [pix.width,pix.height]}
            if abs(aspect / slide_aspect - 1) > .02:
                status = "DECLARED_SOURCE_CROP_SLIDE_ASPECT_MISMATCH"
            else:
                raster = page.get_pixmap(
                    matrix=pymupdf.Matrix(pix.width / region.width,
                                          pix.height / region.height),
                    clip=region, colorspace=pymupdf.csRGB,
                    alpha=False, annots=True)
                if raster.n == 3 and raster.width == pix.width and raster.height == pix.height:
                    matched = bytes(raster.samples) == bytes(pix.samples)
                    status = ("DECLARED_CROP_RGB_PIXELS_MATCH_UNTRUSTED_HYPOTHESIS"
                              if matched else "DECLARED_CROP_RGB_PIXELS_DIFFER")
                else:
                    status = "DECLARED_CROP_RENDER_GRID_MISMATCH"
    require(_sha(spath) == baseline["source_sha256"]
            and _sha(dpath) == baseline["slides_sha256"],
            "Original PDFs changed during bounded source crop comparison")
    return {
        "schema_version": 1, "status": status, "figure_id": figure_id,
        "source_page": source_page, "slide_page": slide_page,
        "source_sha256": baseline["source_sha256"],
        "slides_sha256": baseline["slides_sha256"],
        "declared_crop_observation": evidence,
        "declared_crop_visible_rgb_pixels_equal": matched,
        "declared_crop_authoritatively_selected": False,
        "author_original_figure_completeness_certified": False,
        "original_panel_semantics_verified": False,
        "source_slide_figure_identity_certified": False,
        "narrated_highlights_certified": False,
        "video_or_publication_authorized": False,
    }


def main(argv=None) -> int:
    import argparse,json
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--slides",type=Path,required=True)
    p.add_argument("--source-page",type=int,required=True)
    p.add_argument("--slide-page",type=int,required=True)
    p.add_argument("--figure-id",required=True)
    p.add_argument("--crop",nargs=4,type=float,required=True)
    a=p.parse_args(argv)
    result=audit_declared_crop_match(
        source=a.source,slides=a.slides,source_page=a.source_page,
        slide_page=a.slide_page,figure_id=a.figure_id,crop=a.crop)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 2

if __name__=="__main__":
    raise SystemExit(main())
