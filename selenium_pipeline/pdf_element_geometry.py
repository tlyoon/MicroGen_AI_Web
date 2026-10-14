"""Precise, PDF-rendered semantic element geometry from temporary Beamer links.

The private microgen-element: URI is only an instrumentation marker.
Never treat a synthetic link rectangle as proof of actual figure-panel fidelity.
Published PDF copies must have those links removed or be separately compiled.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pymupdf

from .storyboard_gate import StoryboardError, canonical_sha256
from .pdf_visual_clearance import audit_raster_image_text_clearance

URI_PREFIX = "microgen-element:"
VERSION = 1


class ElementGeometryError(StoryboardError):
    """Cannot prove exactly which rendered visual region a concept occupies."""


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def _expected(storyboard: dict) -> dict[str, int]:
    expected = {}
    for index, slide in enumerate(storyboard["slides"]):
        for element in slide["elements"]:
            element_id = element["element_id"]
            if element_id in expected:
                raise ElementGeometryError("Duplicate storyboard visual element")
            expected[element_id] = index
    if not expected:
        raise ElementGeometryError("Storyboard needs visual elements")
    return expected


def extract_element_geometry(pdf_path: str | Path, storyboard: dict) -> dict:
    r"""Extract one verified rendered region for each stable semantic element ID.

    Beamer must define \MGElement{id}{TeX} with a hidden URI hyperlink.
    URI links survive text/math/image content and expose actual PDF rectangles.
    Reject fragments, wrong pages, unknown IDs or malformed rectangles.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise ElementGeometryError("Compiled PDF is missing")
    # Fail early before TTS or video: a valid element URI does not prove that
    # printed source-figure labels are separated from an adjacent text block.
    problems = audit_raster_image_text_clearance(pdf_path)
    if problems:
        first = problems[0]
        raise ElementGeometryError(
            "Figure/body text clearance failed on PDF page "
            f"{first['page']}: {first['gap_pt']} pt (requires "
            f"{first['required_gap_pt']} pt). Review layout and recompile; "
            "never crop original figure panels."
        )
    expected = _expected(storyboard)
    actual = {}
    page_sizes = []
    with pymupdf.open(pdf_path) as pdf:
        if len(pdf) != len(storyboard["slides"]):
            raise ElementGeometryError("Compiled page count does not match storyboard")
        for page_index, page in enumerate(pdf):
            rect = page.rect
            if not (rect.width > 0 and rect.height > 0):
                raise ElementGeometryError("Invalid compiled page dimensions")
            page_sizes.append({
                "slide_id": storyboard["slides"][page_index]["slide_id"],
                "page_index": page_index, "width_pt": round(rect.width, 3),
                "height_pt": round(rect.height, 3), "rotation": page.rotation,
            })
            for link in page.get_links():
                uri = link.get("uri", "")
                if link.get("kind") != pymupdf.LINK_URI or not uri.startswith(URI_PREFIX):
                    continue
                element_id = uri[len(URI_PREFIX):]
                if element_id not in expected:
                    raise ElementGeometryError(
                        f"Unknown element marker on PDF page {page_index+1}: {element_id}"
                    )
                if expected[element_id] != page_index:
                    raise ElementGeometryError(
                        f"Element {element_id} appears on wrong PDF page {page_index+1}"
                    )
                if element_id in actual:
                    raise ElementGeometryError(
                        f"Repeated or fragmented PDF marker for {element_id}; "
                        "wrap multiline content in a single LaTeX box"
                    )
                r = pymupdf.Rect(link["from"])
                vals = (r.x0, r.y0, r.x1, r.y1)
                if (not all(math.isfinite(v) for v in vals)
                        or r.is_empty or r.is_infinite
                        or r.width < 1.0 or r.height < 1.0):
                    raise ElementGeometryError(f"Invalid visual bounds for {element_id}")
                if not page.rect.contains(r):
                    raise ElementGeometryError(
                        f"Element {element_id} is clipped/outside its rendered page"
                    )
                if r.width * r.height > rect.width * rect.height * 0.85:
                    raise ElementGeometryError(
                        f"Element {element_id} occupies implausibly large slide region"
                    )
                actual[element_id] = {
                    "element_id": element_id,
                    "slide_id": storyboard["slides"][page_index]["slide_id"],
                    "page_index": page_index,
                    "rect_pt": [round(v, 3) for v in vals],
                    "rect_norm": [round(r.x0/rect.width, 7),
                                  round(r.y0/rect.height, 7),
                                  round(r.x1/rect.width, 7),
                                  round(r.y1/rect.height, 7)],
                }
    missing = sorted(set(expected).difference(actual))
    if missing:
        raise ElementGeometryError(f"Missing PDF element markers: {missing}")
    return {
        "schema_version": VERSION,
        "status": "rendered_geometry_verified_visual_content_unreviewed",
        "instrumented_pdf_sha256": _sha(pdf_path),
        "storyboard_sha256": canonical_sha256(storyboard),
        "pages": page_sizes,
        "elements": [actual[k] for k in sorted(actual)],
        "unverified": ["source_figure_panel_completeness",
                       "actual_narration_audio", "scientific_accuracy",
                       "audiovisual_synchronization"],
    }


def strip_instrumentation_links(pdf_path: str | Path, destination: str | Path,
                                geometry: dict) -> dict:
    """Rebuild a no-overwrite, visually identical PDF from instrumented pages.

    PyMuPDF cannot reliably delete pdfLaTeX hyperlink annotations whose xref=0.
    Use show_pdf_page to copy only rendered page CONTENT into fresh PDF pages,
    then compare low-resolution pixel buffers. All annotations/interactivity
    (not only MicroGen links) are intentionally discarded. This is suitable
    for static video slides; do not use for an interactive published PDF.
    """
    src, dest = Path(pdf_path), Path(destination)
    if src.resolve() == dest.resolve():
        raise ElementGeometryError("Cannot overwrite instrumented PDF in-place")
    if dest.exists():
        raise ElementGeometryError("Refusing to overwrite existing cleaned PDF")
    if _sha(src) != geometry.get("instrumented_pdf_sha256"):
        raise ElementGeometryError("Geometry was measured on a different PDF")
    if not dest.parent.is_dir():
        raise ElementGeometryError("Clean PDF output directory missing")
    tmp = dest.with_name(dest.name + ".microgen-temp")
    if tmp.exists():
        raise ElementGeometryError("Refusing to replace an existing temporary PDF")
    try:
        with pymupdf.open(src) as original, pymupdf.open() as rebuilt:
            if len(original) != len(geometry["pages"]):
                raise ElementGeometryError("Unexpected number of pages in source PDF")
            total = 0
            for index, page in enumerate(original):
                if page.rotation != 0:
                    raise ElementGeometryError("Rotated source pages require special geometry")
                total += sum(
                    link.get("kind") == pymupdf.LINK_URI
                    and str(link.get("uri", "")).startswith(URI_PREFIX)
                    for link in page.get_links()
                )
                new = rebuilt.new_page(width=page.rect.width, height=page.rect.height)
                new.show_pdf_page(new.rect, original, index)
            if total != len(geometry["elements"]):
                raise ElementGeometryError("Measured anchor count changed before cleaning")
            rebuilt.save(tmp, garbage=4, deflate=True)

        with pymupdf.open(src) as original, pymupdf.open(tmp) as clean:
            if len(clean) != len(original):
                raise ElementGeometryError("Cleaning changed page count")
            for index, (old, new) in enumerate(zip(original, clean)):
                if any(link.get("kind") == pymupdf.LINK_URI
                       and str(link.get("uri", "")).startswith(URI_PREFIX)
                       for link in new.get_links()):
                    raise ElementGeometryError("Private anchor links survived clean rebuild")
                # Exact pixels assure page visuals were not shifted during reconstruction.
                a = old.get_pixmap(matrix=pymupdf.Matrix(0.7, 0.7), alpha=False)
                b = new.get_pixmap(matrix=pymupdf.Matrix(0.7, 0.7), alpha=False)
                if a.width != b.width or a.height != b.height or a.samples != b.samples:
                    raise ElementGeometryError(
                        f"Clean PDF visual content differs from source page {index+1}"
                    )
        tmp.rename(dest)
    finally:
        tmp.unlink(missing_ok=True)
    return {
        "status": "clean_static_pdf_exact_pixel_match",
        "removed_instrumentation_links": total,
        "all_annotations_removed": True,
        "clean_pdf_sha256": _sha(dest),
    }
