"""Captionless source graphics: bounded recovery from Gemini review marker.

Never invent a textbook figure number. An EXACT source-response
MAPPING_REVIEW_REQUIRED can be resolved to a generic, explicitly
uncaptioned source crop only if the same ORIGINAL PDF page contains enough
extractable text to rule out an image-only/scanned page, NO printed figure
number anywhere, ONE original Docling crop, a SHA-bound original PDF,
page PNG and crop with valid source-space geometry, and no prose-heavy
crop. Uncertain PDF/crop/figure identity remains unaccepted.

Normal caller remains responsible for non-destructive copy/checkpoint and
never retries a claimed Gemini Send. This is source-only evidence, not proof
of figure semantics, pixel correspondence, science or release readiness.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

class UncaptionedSourceNotProven(ValueError):
    pass


_FIGURE_REF = re.compile(r"(?i)\b(?:figure|fig\.?)\s*\d+(?:[.\-]\d+)?")
_CROP_NAME = re.compile(r"^fig_[1-9][0-9]*\.png$")
_PAGE_NAME = re.compile(r"^page_([1-9][0-9]*)\.png$")


def _digest(path: Path, max_bytes: int) -> str:
    if (not path.is_file() or path.is_symlink()
            or path.stat().st_size <= 0 or path.stat().st_size > max_bytes):
        raise UncaptionedSourceNotProven("Original source asset missing/unsafe")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recover_source_uncaptioned_crop(*, response: str,
                                  source_pdf: Path, page_png: Path,
                                  crops_dir: Path, geometry_manifest: Path
                                  ) -> tuple[list[tuple[str, str, str]], dict]:
    """Return one transparent generic mapping and SHA evidence, or reject."""
    if type(response) is not str or response.strip() != "MAPPING_REVIEW_REQUIRED":
        raise UncaptionedSourceNotProven("Only exact unresolvable-caption marker qualifies")
    source_pdf, page_png, crops_dir, geometry_manifest = (
        Path(source_pdf), Path(page_png), Path(crops_dir), Path(geometry_manifest))
    page = _PAGE_NAME.fullmatch(page_png.name)
    if (page is None or not crops_dir.is_dir() or crops_dir.is_symlink()
            or geometry_manifest.parent != crops_dir
            or geometry_manifest.name != page_png.stem + "_crop_geometry.json"):
        raise UncaptionedSourceNotProven("Unexpected page/crop source paths")
    page_num = int(page[1])
    source_sha = _digest(source_pdf, 25_000_000)
    image_sha = _digest(page_png, 25_000_000)
    manifest_sha = _digest(geometry_manifest, 2_000_000)
    try:
        manifest = json.loads(geometry_manifest.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, OSError) as exc:
        raise UncaptionedSourceNotProven("Unreadable source crop geometry") from exc
    if (not isinstance(manifest, dict)
            or manifest.get("schema_version") != 1
            or manifest.get("status") !=
               "SOURCE_DECLARED_CROP_GEOMETRY_CANDIDATES_NOT_VERIFIED"
            or manifest.get("page_number") != page_num
            or manifest.get("original_source_pdf_sha256") != source_sha
            or manifest.get("page_image_sha256") != image_sha
            or manifest.get("crop_count") != 1
            or manifest.get("source_crop_pixel_correspondence_verified") is not False
            or manifest.get("figure_composite_layout_certified") is not False
            or manifest.get("student_publication_authorized") is not False
            or not isinstance(manifest.get("crops"), list)
            or len(manifest["crops"]) != 1):
        raise UncaptionedSourceNotProven("Source/crop provenance not unique and exact")
    item = manifest["crops"][0]
    if not isinstance(item, dict):
        raise UncaptionedSourceNotProven("Invalid source crop declaration")
    crop_name = item.get("crop_file")
    if (type(crop_name) is not str or not _CROP_NAME.fullmatch(crop_name)
            or set(p.name for p in crops_dir.glob("fig_*.png")) != {crop_name}
            or item.get("source_pdf_sha256") != source_sha
            or item.get("page_image_sha256") != image_sha
            or item.get("source_page") != page_num
            or item.get("status") != "DOCLING_SINGLE_SOURCE_RECT_CANDIDATE"
            or item.get("source_crop_pixel_correspondence_verified") is not False
            or item.get("original_caption_and_panel_semantics_verified") is not False
            or item.get("automatic_composite_or_publication_authorized") is not False
            or item.get("crop_sha256") != _digest(crops_dir / crop_name, 25_000_000)):
        raise UncaptionedSourceNotProven("Source crop file/hash is not independently bound")
    rect = item.get("bbox_source_pdf_top_left_pt")
    size = item.get("source_page_size_pt")
    if (not isinstance(rect, list) or len(rect) != 4
            or not isinstance(size, list) or len(size) != 2
            or not all(type(v) in (int, float) and math.isfinite(v)
                       for v in rect + size)
            or not (0 <= rect[0] < rect[2] <= size[0]
                    and 0 <= rect[1] < rect[3] <= size[1])):
        raise UncaptionedSourceNotProven("Invalid source-space crop rectangle")
    try:
        import fitz
    except ImportError as exc:
        raise UncaptionedSourceNotProven("PyMuPDF source text inspection unavailable") from exc
    try:
        with fitz.open(str(source_pdf)) as pdf:
            if page_num > len(pdf):
                raise UncaptionedSourceNotProven("Original page number beyond PDF")
            original = pdf[page_num - 1]
            if (abs(original.rect.width - size[0]) > 0.1
                    or abs(original.rect.height - size[1]) > 0.1):
                raise UncaptionedSourceNotProven("Original PDF page geometry changed")
            text = original.get_text("text", sort=True)
            words = original.get_text("words")
            # High text coverage proves a selectable-text source, reducing
            # the risk of silently labeling a scanned/undecodable caption.
            if len(words) < 100 or len(text) < 500:
                raise UncaptionedSourceNotProven("Page text coverage too low")
            if _FIGURE_REF.search(text):
                raise UncaptionedSourceNotProven(
                    "Original page mentions numbered figures: cannot infer which caption")
            inner = [
                w for w in words
                if (w[0] < rect[2]+1.5 and w[2] > rect[0]-1.5
                    and w[1] < rect[3]+1.5 and w[3] > rect[1]-1.5)]
            if len(inner) > 12 or sum(len(str(w[4])) for w in inner) > 35:
                raise UncaptionedSourceNotProven(
                    "Crop has substantial original prose/math text, not clearly a graphic")
    except UncaptionedSourceNotProven:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise UncaptionedSourceNotProven("Could not verify original PDF text") from exc

    # No generic content/physics inference, just an explicit source-only
    # identifier. Never treat this as a printed numbered figure caption.
    label = "Unlabeled source graphic"
    target = f"Unlabeled source graphic page_{page_num} {crop_name}"
    rows = [(crop_name, label, target)]
    evidence = {
        "schema_version": 1,
        "status": "UNCAPTIONED_SOURCE_CROP_VERIFIED_NOT_SEMANTIC_QA",
        "original_model_response_sha256": hashlib.sha256(
            response.encode("utf-8")).hexdigest(),
        "source_pdf_sha256": source_sha,
        "source_page_number": page_num,
        "source_page_png_sha256": image_sha,
        "source_crop_manifest_sha256": manifest_sha,
        "source_crop_name": crop_name,
        "source_crop_sha256": item["crop_sha256"],
        "source_crop_pdf_rect_top_left_pt": rect,
        "observed_source_pdf_word_count": len(words),
        "observed_words_in_source_crop": len(inner),
        "numbered_figure_caption_observed_on_page": False,
        "generic_label_explicitly_not_printed": True,
        "resolution": [list(row) for row in rows],
        "new_model_sends": 0,
        "source_crop_pixel_correspondence_verified": False,
        "independent_scientific_and_diagram_semantics_verified": False,
        "full_figure_composite_certified": False,
        "student_publication_authorized": False,
    }
    return rows, evidence
