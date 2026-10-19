"""Read-only, fail-closed PDF whole-raster-figure source identity preflight.

This deliberately DOES NOT authorize narrated figure TTS, panel selection,
mathematical correctness, production video, or YouTube publication.
Pixel identity is necessary but not sufficient for visible completeness:
PDF clipping paths, masks, annotations and source panel semantics require
independent validation. Candidate records are never academic approvals.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pymupdf


class FigureIdentityReviewRequired(ValueError):
    """Evidence cannot establish an unambiguous whole-image candidate."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise FigureIdentityReviewRequired(reason)


def _sha(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), "Missing regular PDF")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def _caption_boxes(page, caption: str) -> list[pymupdf.Rect]:
    return [
        pymupdf.Rect(block[:4])
        for block in page.get_text("blocks")
        if len(block) > 4 and isinstance(block[4], str)
        and _norm(block[4]) == _norm(caption)
    ]


def _one_image(doc, page_no: int, caption: str, label: str):
    require(type(page_no) is int and 1 <= page_no <= len(doc),
            f"{label}: invalid PDF page")
    page = doc[page_no - 1]
    require(not page.get_drawings(),
            f"{label}: vector figure/path present; raster identity incomplete")
    info = page.get_image_info(xrefs=True, hashes=True)
    require(len(info) == 1,
            f"{label}: needs exactly one raster image on specified page")
    item = info[0]
    xref = item.get("xref")
    require(type(xref) is int and xref > 0,
            f"{label}: inline image has no verifiable embedded source xref")
    entries = [entry for entry in page.get_images(full=True)
               if entry[0] == xref]
    require(len(entries) == 1 and entries[0][1] == 0,
            f"{label}: masked, reused or ambiguous image xref")
    rects = page.get_image_rects(xref)
    require(len(rects) == 1,
            f"{label}: missing or repeated image placement")
    rect = rects[0]
    require(not rect.is_infinite and not rect.is_empty
            and page.rect.contains(rect)
            and rect.width >= 60 and rect.height >= 40,
            f"{label}: clipped, off-page or illegibly small image")
    require(abs(rect.width / rect.height
                - item["width"] / item["height"])
            <= .025 * item["width"] / item["height"],
            f"{label}: placement distorts full-image aspect ratio")
    caption_boxes = _caption_boxes(page, caption)
    require(len(caption_boxes) == 1,
            f"{label}: caption absent, altered or repeated")
    box = caption_boxes[0]
    require(box.y0 >= rect.y1 - 2 and box.y0 - rect.y1 < 130,
            f"{label}: caption is not unambiguously below figure")
    require(box.x1 >= rect.x0 and box.x0 <= rect.x1,
            f"{label}: caption and figure do not align horizontally")
    require(isinstance(item.get("digest"), bytes)
            and len(item["digest"]) == 16,
            f"{label}: decoded raster fingerprint missing")
    return item, rect, xref


def inspect_whole_raster_candidate(
    *, source: Path, slides: Path, source_page: int,
    slide_page: int, caption: str
) -> dict:
    """Return a candidate only when all exact technical identity gates pass.

    The caller must NOT convert this candidate into a production-approved
    image_whole anchor: actual panel completeness, clipping masks, text and
    figure semantics have not been independently certified.
    """
    # Inspect the original lexical paths BEFORE resolution: resolve() follows
    # links and would hide a symlinked PDF (or symlinked parent directory).
    def checked_path(raw: Path) -> Path:
        candidate = Path(raw).absolute()
        for component in (candidate, *candidate.parents):
            require(not component.is_symlink()
                    and not getattr(component, "is_junction", lambda: False)(),
                    "Symlinked or junction PDF path is not permitted")
        require(candidate.is_file(), "Missing regular PDF")
        return candidate.resolve(strict=True)

    source, slides = checked_path(source), checked_path(slides)
    require(source != slides, "Source and slide PDFs must be different files")
    source_hash, slide_hash = _sha(source), _sha(slides)
    require(isinstance(caption, str) and 9 <= len(caption) <= 500,
            "A complete explicit figure caption is required")
    require(re.search(r"(?i)\bfig(?:ure)?[\s.]*\d", caption) is not None,
            "Caption must identify a numbered source figure")
    require(not re.search(r"\([a-f]\)", caption, re.I),
            "Panel-labelled caption needs a separate panel completeness audit")
    with pymupdf.open(source) as textbook, pymupdf.open(slides) as deck:
        require(0 < len(textbook) <= 250 and 0 < len(deck) <= 500,
                "Empty or oversized PDF")
        a, source_rect, sxref = _one_image(
            textbook, source_page, caption, "source")
        b, slide_rect, dxref = _one_image(
            deck, slide_page, caption, "slide")
        require(a["digest"] == b["digest"]
                and a["width"] == b["width"]
                and a["height"] == b["height"],
                "Decoded source and slide raster image identity differs")
        require(slide_rect.width >= 100 and slide_rect.height >= 75,
                "Slide image too small for figure narration")
        # Same pixels on a different page may refer to a reused logo, inset
        # or duplicate diagram: require unique provenance across both PDFs.
        for label, doc, wanted in (
            ("source", textbook, source_page),
            ("slide", deck, slide_page),
        ):
            for index, page in enumerate(doc, 1):
                if index == wanted:
                    continue
                require(not any(img.get("digest") == a["digest"]
                                for img in page.get_image_info(hashes=True)),
                        f"{label}: image reused on another PDF page")
        return {
            "schema_version": 1,
            "status": "EXACT_WHOLE_RASTER_CANDIDATE_REVIEW_REQUIRED",
            "source_sha256": source_hash,
            "slides_sha256": slide_hash,
            "source_page": source_page,
            "slide_page": slide_page,
            "source_xref": sxref,
            "slide_xref": dxref,
            "decoded_image_md5": a["digest"].hex(),
            "pixel_dimensions": [a["width"], a["height"]],
            "source_bbox": [round(v, 2) for v in source_rect],
            "slide_bbox": [round(v, 2) for v in slide_rect],
            "caption_evidence": caption,
            "image_pixel_identity_verified": True,
            "caption_text_identity_verified": True,
            "image_visible_completeness_certified": False,
            "figure_semantics_certified": False,
            "figure_panel_completeness_certified": False,
            "tts_or_video_authorized": False,
            "human_review_claimed": False,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--slides", required=True, type=Path)
    parser.add_argument("--source-page", required=True, type=int)
    parser.add_argument("--slide-page", required=True, type=int)
    parser.add_argument("--caption", required=True)
    args = parser.parse_args()
    result = inspect_whole_raster_candidate(
        source=args.source, slides=args.slides,
        source_page=args.source_page, slide_page=args.slide_page,
        caption=args.caption)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
