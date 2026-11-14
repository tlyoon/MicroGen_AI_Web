"""Normal lecture visual candidate router for verified captioned source panels.

Reuses physically published caption labels, vector marker/underline anchors,
historical ORB+AKAZE detectors, and whole-slide embedded image provenance.
This is an on-the-fly SELECTABLE PANEL TARGET repair, not an academic proof
or permission for new paid audio.
"""
from __future__ import annotations

from pathlib import Path
import re

import pymupdf

from .figure_source_identity import require, FigureIdentityReviewRequired, _sha
from .source_caption_panel_registration import inspect_panel_correspondence


def _source_figure_candidates(source: Path, requested: list[str]) -> list[tuple]:
    """Discover captioned figures without guessing figure IDs from slide titles."""
    anchors=[]
    with pymupdf.open(source) as pdf:
        for page_number,page in enumerate(pdf,1):
            for block in page.get_text("blocks"):
                if len(block)<5 or not isinstance(block[4],str):
                    continue
                value=" ".join(block[4].split())
                match=re.match(
                    r"(?i)^Figure\s+(\d{1,2}\.\d{1,3})\b",value)
                if match and all(re.search(
                        rf"\({re.escape(marker)}\)",value,re.I)
                        for marker in requested):
                    anchors.append((page_number,match[1]))
                    if len(anchors)>12:
                        # A huge ambiguous textbook extract should not
                        # prevent other lecture stages from advancing. The
                        # whole-image candidate remains review-only.
                        return []
    return anchors


def panel_targets_for_slide(*,source: Path,slides: Path,
                            slide_number: int,
                            rendered_text: str | None = None) -> list[dict]:
    """Return only unique, independently source-to-slide matched panel targets.

    A visual target can be supplied to Gemini automatically without forcing
    a human to manually crop it, but utterance-level academic mathematical
    semantics remain independently unapproved. No unrelated layout guessed.
    """
    source,slides=Path(source).absolute(),Path(slides).absolute()
    require(type(slide_number) is int and 1<=slide_number<=500
            and source.is_file() and slides.is_file()
            and not source.is_symlink() and not slides.is_symlink(),
            "Real original source+slide PDF required")
    src_hash,dst_hash=_sha(source),_sha(slides)
    with pymupdf.open(slides) as deck:
        require(slide_number<=len(deck),"Slide outside original PDF")
        text=(deck[slide_number-1].get_text()
              if rendered_text is None else rendered_text)
    letters=sorted(set(x.lower() for x in
        re.findall(r"\(([a-f])\)",text,re.I)))
    if not 2<=len(letters)<=5 or letters!=list("abcde"[:len(letters)]):
        return []
    candidates=_source_figure_candidates(source,letters)
    matching=[]
    for page_number,figure in candidates:
        try:
            record=inspect_panel_correspondence(
                source=source,slides=slides,
                source_page=page_number,slide_page=slide_number,
                figure_id=figure)
        except (FigureIdentityReviewRequired,ValueError,RuntimeError,
                OSError,TypeError):
            # No semantic bypass: a figure without sufficient independent
            # visual evidence remains a whole-image pending target.
            continue
        if [p["panel"] for p in record["panels"]]!=letters:
            continue
        matching.append(record)
        require(len(matching)<=1,
                "More than one physically matched source figure; ambiguous")
    require(_sha(source)==src_hash and _sha(slides)==dst_hash,
            "Source PDF changed during automatic panel recovery")
    if not matching:
        return []
    record=matching[0]
    out=[]
    for p in record["panels"]:
        letter=p["panel"]
        out.append({
            "draft_element_id":f"s{slide_number:03d}.panel.{letter}",
            "kind":"image_caption_panel",
            "visible_text":f"({letter}) {p['caption_meaning']}",
            "bbox_pdf_pt":p["slide_page_bbox_pdf_pt"],
            "panel_identity_review_required":False,
            "source_caption_panel_meaning_verified":True,
            "independent_visual_registration_verified":True,
            "mathematical_semantics_verified":False,
            "audio_alignment_verified":False,
            "anchor":{
                "type":"original_pdf_panel_visual_provenance",
                "source_sha256":record["source_sha256"],
                "slides_sha256":record["slides_sha256"],
                "source_page":record["source_page"],
                "figure_id":record["figure_id"],
                "panel":letter,
                "source_caption_sha256":record["caption_sha256"],
                "slide_image_md5":record["embedded_figure_decoded_md5"],
                "original_marker":p["printed_marker_source"],
                "native_bitmap_bbox":p["slide_native_pixel_bbox"],
                "actual_pdf_bbox":p["slide_page_bbox_pdf_pt"],
            },
        })
    require(len(out)==record["panel_count"]
            and len(set(x["draft_element_id"] for x in out))==len(out),
            "Incomplete or duplicate exact source panel target")
    return out
