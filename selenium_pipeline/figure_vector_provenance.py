"""Read-only vector-source figure-region and labelled-panel provenance candidate.

Conservative, explicit-region preflight. It proves that the declared source
vector paths and extractable (a)/(b)/(c) labels are enclosed in a declared
nonoverlapping panel partition and that source/slide *rendered pixels* match
at one recorded resolution. It cannot prove the author's intended crop,
scientific meaning, or panel completeness; it NEVER approves narration.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pymupdf

from .figure_source_identity import FigureIdentityReviewRequired, require, _sha, _caption_boxes


def _checked_pdf(raw: Path) -> Path:
    path = Path(raw).absolute()
    for part in (path, *path.parents):
        require(not part.is_symlink() and
                not getattr(part, "is_junction", lambda: False)(),
                "Symlink/junction PDF path prohibited")
    require(path.is_file() and path.suffix.lower() == ".pdf",
            "An existing regular PDF is required")
    return path.resolve(strict=True)


def _rect(raw, page, label: str) -> pymupdf.Rect:
    require(isinstance(raw, (tuple, list)) and len(raw) == 4
            and all(type(x) in (int, float) for x in raw),
            f"{label}: four finite numeric rectangle coordinates required")
    box = pymupdf.Rect(*raw)
    require(not box.is_empty and not box.is_infinite
            and all(abs(float(x)) < 1e6 for x in box)
            and page.rect.contains(box) and box.width >= 30
            and box.height >= 30,
            f"{label}: invalid, clipped or too small region")
    return box


def _inside(inner: pymupdf.Rect, outer: pymupdf.Rect, eps: float = .25) -> bool:
    return (inner.x0 >= outer.x0 - eps and inner.y0 >= outer.y0 - eps
            and inner.x1 <= outer.x1 + eps and inner.y1 <= outer.y1 + eps)


def _labels(page, region: pymupdf.Rect):
    words = []
    for item in page.get_text("words"):
        if len(item) < 5:
            continue
        box = pymupdf.Rect(item[:4])
        if box.intersects(region):
            token = item[4].strip()
            if re.fullmatch(r"\([a-z]\)", token, flags=re.I):
                words.append((token[1].lower(), box))
    return words


def _render(page, region: pymupdf.Rect, width: int, height: int) -> bytes:
    matrix = pymupdf.Matrix(width / region.width, height / region.height)
    pix = page.get_pixmap(matrix=matrix, clip=region,
                          colorspace=pymupdf.csRGB, alpha=False, annots=True)
    require(pix.n == 3 and pix.width == width and pix.height == height,
            "Exact integer rendered comparison dimensions unavailable")
    return bytes(pix.samples)


def inspect_vector_figure_region(
    *, source: Path, slides: Path, source_page: int, slide_page: int,
    source_bbox: list[float], slide_bbox: list[float],
    panel_boxes: list[list[float]], caption: str,
    panel_ids: list[str], scale: int = 2,
) -> dict:
    """Return a strict technical candidate; all production permissions false.

    Panel rectangles and figure region are *declared* by the caller, never
    inferred from scientific content. Every intersecting vector path must
    belong wholly to exactly one declared panel; boundaries cannot bisect
    paths. Text labels must exist uniquely in the ORIGINAL source PDF.
    """
    source, slides = _checked_pdf(source), _checked_pdf(slides)
    require(source != slides, "Source and slides must be distinct PDFs")
    require(type(scale) is int and 2 <= scale <= 4,
            "Only bounded 2-4x independent rendering supported")
    require(type(source_page) is int and type(slide_page) is int,
            "Integer one-based pages required")
    require(isinstance(caption, str) and 9 <= len(caption) <= 500
            and re.search(r"\bfig(?:ure)?[\s.]*\d", caption, re.I),
            "Exact numbered figure caption required")
    require(isinstance(panel_ids, list) and
            panel_ids == list("abcdef"[:len(panel_ids)]) and
            2 <= len(panel_ids) <= 6 and
            isinstance(panel_boxes, list) and
            len(panel_boxes) == len(panel_ids),
            "Two to six ordered explicit (a).. panel regions required")
    src_hash, dst_hash = _sha(source), _sha(slides)
    with pymupdf.open(source) as original, pymupdf.open(slides) as deck:
        require(1 <= source_page <= len(original)
                and 1 <= slide_page <= len(deck),
                "Source or slide page is out of range")
        sp, dp = original[source_page - 1], deck[slide_page - 1]
        sr, dr = _rect(source_bbox, sp, "source figure"), _rect(
            slide_bbox, dp, "slide figure")
        require(abs(sr.width / sr.height - dr.width / dr.height) <= .001,
                "Source and slide figure aspect ratios differ")
        require(abs(sr.width * scale - round(sr.width * scale)) < 1e-5
                and abs(sr.height * scale - round(sr.height * scale)) < 1e-5,
                "Source region must render to exact integer pixel dimensions")
        width, height = round(sr.width * scale), round(sr.height * scale)
        require(120 <= width <= 3000 and 75 <= height <= 3000
                and width * height <= 6_000_000,
                "Unsupported render size or excessive pixel count")
        for label, page, region in (
            ("source", sp, sr), ("slide", dp, dr)
        ):
            boxes = _caption_boxes(page, caption)
            require(len(boxes) == 1 and
                    boxes[0].y0 >= region.y1 - 2 and
                    boxes[0].y0 - region.y1 < 150 and
                    boxes[0].x1 >= region.x0 and
                    boxes[0].x0 <= region.x1,
                    f"{label}: exact caption must appear once below figure")
        require(not any(pymupdf.Rect(info["bbox"]).intersects(sr)
                        for info in sp.get_image_info()),
                "Source figure region contains raster; vector-only proof invalid")
        source_paths = []
        for item in sp.get_drawings():
            box = pymupdf.Rect(item["rect"])
            # Degenerate vector line bounding boxes are empty PyMuPDF Rects:
            # Rect.intersects() misses them even when they cross panel seams.
            # Conservative coordinate intersection includes zero-width/height paths.
            if (box.x1 >= sr.x0 and box.x0 <= sr.x1 and
                    box.y1 >= sr.y0 and box.y0 <= sr.y1):
                require(_inside(box, sr),
                        "Source vector path crosses figure crop boundary")
                source_paths.append(box)
        require(len(source_paths) >= len(panel_ids),
                "Insufficient original vector paths for declared panels")
        boxes = [_rect(raw, sp, "source panel") for raw in panel_boxes]
        require(all(_inside(box, sr) for box in boxes),
                "Declared panel extends beyond source figure")
        # A complete axis-aligned strip tiling is necessary, not proof that
        # these are the actual scientific panel boundaries.
        horizontal = all(abs(b.y0 - sr.y0) < .01 and
                         abs(b.y1 - sr.y1) < .01 for b in boxes)
        vertical = all(abs(b.x0 - sr.x0) < .01 and
                       abs(b.x1 - sr.x1) < .01 for b in boxes)
        require(horizontal != vertical, "Panels must tile one unambiguous axis")
        if horizontal:
            require(abs(boxes[0].x0 - sr.x0) < .01 and
                    abs(boxes[-1].x1 - sr.x1) < .01 and
                    all(abs(a.x1 - b.x0) < .01 for a, b in
                        zip(boxes, boxes[1:])),
                    "Source panel partition has gaps, overlaps or reversal")
        else:
            require(abs(boxes[0].y0 - sr.y0) < .01 and
                    abs(boxes[-1].y1 - sr.y1) < .01 and
                    all(abs(a.y1 - b.y0) < .01 for a, b in
                        zip(boxes, boxes[1:])),
                    "Source panel partition has gaps, overlaps or reversal")
        labels = _labels(sp, sr)
        require(len(labels) == len(panel_ids) and
                sorted(x[0] for x in labels) == panel_ids,
                "Source (a)/(b)/(c) labels missing, duplicated or extra")
        counts = [0] * len(boxes)
        for vector in source_paths:
            owners = [i for i, box in enumerate(boxes)
                      if _inside(vector, box)]
            require(len(owners) == 1,
                    "Vector path crosses declared panel boundary")
            counts[owners[0]] += 1
        require(all(counts), "Declared panel contains no source vector path")
        for label, region in labels:
            owner = panel_ids.index(label)
            require(_inside(region, boxes[owner]),
                    "Source panel label is missing from its declared region")
        # Require a single unmasked slide raster fully covering the claimed
        # figure region; any overlay changes independently rendered pixels.
        slide_images = [info for info in dp.get_image_info(xrefs=True)
                        if pymupdf.Rect(info["bbox"]).intersects(dr)]
        require(len(slide_images) == 1 and
                slide_images[0].get("xref", 0) > 0 and
                _inside(dr, pymupdf.Rect(slide_images[0]["bbox"])) and
                len(dp.get_image_rects(slide_images[0]["xref"])) == 1,
                "Slide figure must be one identifiable covering raster")
        require(not any(pymupdf.Rect(item["rect"]).intersects(dr)
                        for item in dp.get_drawings()),
                "Slide figure region has extra vector artwork")
        a, b = _render(sp, sr, width, height), _render(dp, dr, width, height)
        require(a == b, "Source vector and slide visible RGB pixels differ")
        panel_evidence = []
        for panel_id, box, count in zip(panel_ids, boxes, counts):
            panel_evidence.append({
                "label": panel_id, "source_bbox": list(box),
                "original_vector_path_count": count,
                "label_in_source_pdf_text": True,
            })
    require(_sha(source) == src_hash and _sha(slides) == dst_hash,
            "Original PDF changed during read-only verification")
    return {
        "schema_version": 1,
        "status": "VECTOR_SOURCE_PANEL_RENDER_CANDIDATE_REVIEW_REQUIRED",
        "source_sha256": src_hash, "slides_sha256": dst_hash,
        "source_page": source_page, "slide_page": slide_page,
        "source_bbox": list(sr), "slide_bbox": list(dr),
        "render_scale": scale, "render_size": [width, height],
        "rendered_rgb_sha256": hashlib.sha256(a).hexdigest(),
        "source_vector_paths_inside_declared_panels": len(source_paths),
        "source_panel_label_geometry_verified": True,
        "source_slide_rendered_equivalence_verified": True,
        "panels": panel_evidence,
        "author_intended_crop_certified": False,
        "true_panel_boundary_semantics_certified": False,
        "figure_panel_completeness_certified": False,
        "figure_semantics_certified": False,
        "tts_or_video_authorized": False,
        "human_review_claimed": False,
    }
