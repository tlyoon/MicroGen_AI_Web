"""Read-only declared multi-crop source-to-slide tile evidence.

Never infer author panel count, labels or source provenance from supplied
rectangles or equality of pixels. Intended only for bounded hypothesis QA.
"""
from __future__ import annotations
import math
from pathlib import Path
import pymupdf
from .figure_source_identity import require, _sha
from .figure_caption_column_audit import audit_caption_column_collision
from .figure_slide_raster_visibility import audit_vector_source_slide_raster


def audit_declared_panel_reflow(*, source: Path, slides: Path,
                                 source_page: int, slide_page: int,
                                 figure_id: str, tiles: list) -> dict:
    base = audit_vector_source_slide_raster(
        source=source, slides=slides, source_page=source_page,
        slide_page=slide_page, figure_id=figure_id)
    caption = audit_caption_column_collision(
        source=source, page_number=source_page, figure_id=figure_id)
    require(caption["source_sha256"] == base["source_sha256"],
            "Original source changed between independent audits")
    require(type(tiles) is list and 2 <= len(tiles) <= 12,
            "Between two and twelve declared tile candidates required")
    require(all(type(x) is dict
                and set(x) == {"source_bbox", "slide_px_bbox"}
                for x in tiles), "Each tile requires only two rectangles")
    spath, dpath = Path(source).absolute(), Path(slides).absolute()
    row_results, bad, prior_source, prior_slide = [], [], [], []
    with pymupdf.open(spath) as book, pymupdf.open(dpath) as deck:
        original, slide = book[source_page - 1], deck[slide_page - 1]
        material = [x for x in slide.get_image_info(xrefs=True)
                    if int(x["width"]) >= 48 and int(x["height"]) >= 48
                    and pymupdf.Rect(x["bbox"]).width >= 50
                    and pymupdf.Rect(x["bbox"]).height >= 25]
        require(len(material) == 1 and
                type(material[0]["xref"]) is int and material[0]["xref"] > 0,
                "Require one independent material slide bitmap")
        pix = pymupdf.Pixmap(deck, material[0]["xref"])
        require(pix.n == 3 and pix.alpha == 0 and
                pix.width * pix.height <= 4_000_000,
                "Material bitmap must have bounded RGB pixels")
        for index, tile in enumerate(tiles, 1):
            a, b = tile["source_bbox"], tile["slide_px_bbox"]
            require(type(a) is list and type(b) is list and
                    len(a) == len(b) == 4 and
                    all(type(v) in (int, float) and math.isfinite(v) for v in a) and
                    all(type(v) is int for v in b),
                    f"Tile {index}: invalid source bbox or integer pixel bbox")
            rect, px = pymupdf.Rect(a), pymupdf.IRect(b)
            require(rect.is_valid and not rect.is_empty
                    and original.rect.contains(rect)
                    and rect.width >= 12 and rect.height >= 12
                    and rect.y1 < caption["heading_bbox"][1] - 2,
                    f"Tile {index}: source crop outside original pre-caption area")
            require(px.is_valid and not px.is_empty
                    and 0 <= px.x0 < px.x1 <= pix.width
                    and 0 <= px.y0 < px.y1 <= pix.height
                    and px.width * px.height <= 2_000_000,
                    f"Tile {index}: slide pixel bounds are invalid")
            require(not any(rect.intersects(x) for x in prior_source)
                    and not any(px.intersects(x) for x in prior_slide),
                    "Source panel rectangles or slide tile rectangles overlap")
            prior_source.append(rect)
            prior_slide.append(px)
            ar_a = rect.width / rect.height
            ar_b = px.width / px.height
            equal = False
            result = "DECLARED_TILE_ASPECT_MISMATCH"
            if abs(ar_a / ar_b - 1) <= .02 and base["slide_reference_render_pixels_equal"]:
                rendered = original.get_pixmap(
                    matrix=pymupdf.Matrix(px.width / rect.width,
                                          px.height / rect.height),
                    clip=rect, colorspace=pymupdf.csRGB,
                    alpha=False, annots=True)
                if rendered.n == 3 and rendered.width == px.width and rendered.height == px.height:
                    bitmap = bytes(pix.samples)
                    target = b"".join(
                        bitmap[y * pix.stride + px.x0 * 3:
                               y * pix.stride + px.x1 * 3]
                        for y in range(px.y0, px.y1))
                    equal = bytes(rendered.samples) == target
                    result = ("DECLARED_TILE_PIXELS_EQUAL_BUT_PANEL_UNVERIFIED"
                              if equal else "DECLARED_TILE_PIXEL_MISMATCH")
                else:
                    result = "DECLARED_TILE_RENDER_GRID_MISMATCH"
            elif not base["slide_reference_render_pixels_equal"]:
                result = "SLIDE_BITMAP_VISIBILITY_BLOCKED"
            if not equal:
                bad.append(index)
            row_results.append({
                "tile_index": index, "source_bbox": [round(float(v),3) for v in rect],
                "slide_px_bbox": list(b), "pixel_equal": equal,
                "observation": result,
                "author_intended_panel_label_verified": False,
            })
    require(_sha(spath) == base["source_sha256"] and
            _sha(dpath) == base["slides_sha256"],
            "Source or slide modified during independent tile comparison")
    return {
        "schema_version": 1,
        "status": ("DECLARED_REFLOW_PIXELS_EQUAL_UNTRUSTED_MAPPING_REVIEW_REQUIRED"
                   if not bad else "DECLARED_REFLOW_PIXEL_EVIDENCE_INCOMPLETE"),
        "source_sha256": base["source_sha256"],
        "slides_sha256": base["slides_sha256"],
        "figure_id": figure_id,
        "source_page": source_page, "slide_page": slide_page,
        "declared_tile_count": len(row_results),
        "mismatched_tile_indices": bad,
        "declared_tile_observations": row_results,
        "original_source_panel_ownership_verified": False,
        "original_complete_figure_panels_verified": False,
        "scientific_panel_labels_semantics_verified": False,
        "full_slide_image_coverage_verified": False,
        "narrated_element_highlights_verified": False,
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
    p.add_argument("--tiles-json",type=Path,required=True)
    a=p.parse_args(argv)
    raw=Path(a.tiles_json)
    require(raw.is_file() and not raw.is_symlink() and raw.stat().st_size <= 25000,
            "Bounded external tile manifest required")
    tiles=json.loads(raw.read_text(encoding="utf8"))
    report=audit_declared_panel_reflow(source=a.source,slides=a.slides,
        source_page=a.source_page,slide_page=a.slide_page,
        figure_id=a.figure_id,tiles=tiles)
    print(json.dumps(report,indent=2,sort_keys=True))
    return 2

if __name__=="__main__":
    raise SystemExit(main())
