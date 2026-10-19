"""Strict rendered-figure equivalence preflight, stacked after exact identity.

An embedded PDF xref is not proof of what a reader actually sees. A clipping
path, transparency, foreground text, annotations or external graphics may
hide the bitmap while leaving its MD5 and geometric placement unchanged.

Render each PDF page's selected rectangle independently and compare it to
an image-only PDF page built from that SAME source bitmap. Require exact RGB
pixel equivalence with no tolerance; uncertain profiles and antialiasing are
rejected rather than guessed. This is proof of a bounded rendered comparison,
NOT semantic/panel approval or authorization to synthesize narrated video.
"""
from __future__ import annotations

from pathlib import Path
import pymupdf

from .figure_source_identity import (
    FigureIdentityReviewRequired, inspect_whole_raster_candidate,
    require, _sha, _one_image,
)

def _rendered_equivalence(doc, page_number: int, caption: str, label: str,
                          *, scale: int = 2) -> dict:
    """Compare *visible* page pixels to an independent image-only reference."""
    require(type(scale) is int and 2 <= scale <= 4,
            "Unsupported bounded raster comparison resolution")
    item, rect, xref = _one_image(doc, page_number, caption, label)
    page = doc[page_number - 1]
    image = doc.extract_image(xref)
    require(isinstance(image, dict)
            and isinstance(image.get("image"), bytes)
            and bool(image["image"]),
            f"{label}: unable to independently extract referenced raster")
    # Place exactly the original embedded image on an otherwise blank page.
    # A byte-identical rendering of the actual PDF rect implies that *at
    # this resolution* no intervening drawing/annotation/clip has changed
    # the expected on-screen RGB pixels. Page captions are outside rect.
    with pymupdf.open() as reference:
        blank = reference.new_page(
            width=page.rect.width, height=page.rect.height)
        blank.insert_image(rect, stream=image["image"], keep_proportion=False)
        matrix = pymupdf.Matrix(scale, scale)
        actual = page.get_pixmap(
            matrix=matrix, clip=rect, colorspace=pymupdf.csRGB,
            alpha=False, annots=True)
        expected = blank.get_pixmap(
            matrix=matrix, clip=rect, colorspace=pymupdf.csRGB,
            alpha=False, annots=False)
        require(actual.n == 3 and expected.n == 3
                and actual.width == expected.width
                and actual.height == expected.height
                and actual.width >= 100 and actual.height >= 75,
                f"{label}: image render comparison dimensions invalid")
        require(bytes(actual.samples) == bytes(expected.samples),
                f"{label}: PDF image visible pixels differ from an "
                "unclipped, unobstructed image-only reference")
        return {
            "page": page_number,
            "bbox": [round(v, 2) for v in rect],
            "render_scale": scale,
            "comparison_width": actual.width,
            "comparison_height": actual.height,
            "source_xref": xref,
            "independent_reference_pixels_equal": True,
        }


def inspect_rendered_whole_raster_candidate(
    *, source: Path, slides: Path, source_page: int, slide_page: int,
    caption: str, scale: int = 2,
) -> dict:
    """Require PR140 identity and independent PDF raster visibility evidence.

    This result is intentionally NOT a figure-semantic or multi-panel
    correctness certificate, nor a substitute for a publication gate.
    """
    # The underlying preflight checks lexical symlinks/junctions, exact
    # source identities/captions, one raster placement, and no vector paths.
    candidate=inspect_whole_raster_candidate(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,caption=caption)
    source=Path(source).resolve(strict=True)
    slides=Path(slides).resolve(strict=True)
    require(candidate["source_sha256"]==_sha(source)
            and candidate["slides_sha256"]==_sha(slides),
            "PDF mutated after original source identity inspection")
    with pymupdf.open(source) as textbook,pymupdf.open(slides) as deck:
        original=_rendered_equivalence(
            textbook,source_page,caption,"source",scale=scale)
        slide=_rendered_equivalence(
            deck,slide_page,caption,"slide",scale=scale)
    require(candidate["source_sha256"]==_sha(source)
            and candidate["slides_sha256"]==_sha(slides),
            "PDF mutated during independent rendered-image inspection")
    return {
        **candidate,
        "status":"RENDER_EQUIVALENT_WHOLE_RASTER_CANDIDATE_REVIEW_REQUIRED",
        "rendered_raster_equivalence_verified":True,
        "source_render":original,
        "slide_render":slide,
        # Rendering tests pixel equivalence at a defined resolution.
        # They do NOT prove correctness of original embedded source crop,
        # identify all subpanels or establish correct physics semantics.
        "image_visible_completeness_certified":False,
        "figure_panel_completeness_certified":False,
        "figure_semantics_certified":False,
        "tts_or_video_authorized":False,
        "human_review_claimed":False,
    }
