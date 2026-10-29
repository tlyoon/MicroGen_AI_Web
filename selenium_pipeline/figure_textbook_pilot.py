"""Read-only real-textbook vector/slide figure pilot and fail-closed QA report.

Never generates/overwrites teaching outputs; never authorizes narrated figure
highlights, paid TTS, publication, or human academic review. The discovery
path explains precisely why source attribution remains unverified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pymupdf

from .figure_source_identity import require, _sha
from .figure_vector_provenance import _checked_pdf
from .figure_vector_panel_seams import inspect_vector_panel_seams


def inspect_textbook_figure_pilot(
    *, source: Path, slides: Path, source_page: int, slide_page: int,
    figure_id: str, declared: dict | None = None,
) -> dict:
    """Audit actual existing textbook/lecture PDFs without writing files.

    An explicit geometrical receipt can advance to an *unapproved* candidate,
    but no result certifies the scientific meaning or complete author figure.
    """
    source, slides = _checked_pdf(source), _checked_pdf(slides)
    require(source != slides, "Source and slide PDFs must be distinct")
    require(type(source_page) is int and type(slide_page) is int,
            "Pages must be one-based integer indices")
    require(isinstance(figure_id,str)
            and re.fullmatch(r"[1-9][0-9]*\.[0-9]+",figure_id),
            "Figure id must be a numeric chapter.figure token")
    before={"source_sha256":_sha(source),"slides_sha256":_sha(slides)}
    with pymupdf.open(source) as textbook,pymupdf.open(slides) as deck:
        require(1 <= source_page <= len(textbook)
                and 1 <= slide_page <= len(deck),
                "Actual source/slide pages out of range")
        original=textbook[source_page-1]
        lecture=deck[slide_page-1]
        source_drawings=original.get_drawings()
        src_images=original.get_image_info(xrefs=True)
        slide_drawings=lecture.get_drawings()
        slide_images=lecture.get_image_info(xrefs=True)
        rx=re.compile(r"(?i)\bfig(?:ure)?[\s.]*"
                      +re.escape(figure_id)+r"\b")
        caption_source=[b[4].strip() for b in original.get_text("blocks")
                        if len(b)>4 and isinstance(b[4],str)
                        and rx.search(b[4])]
        caption_slide=[b[4].strip() for b in lecture.get_text("blocks")
                       if len(b)>4 and isinstance(b[4],str)
                       and rx.search(b[4])]
        source_text_label_matches=re.findall(
            r"\([a-f]\)",original.get_text(),re.I)
        report={
            "schema_version":1,
            "figure_id":figure_id,
            "source_page":source_page,
            "slide_page":slide_page,
            **before,
            "source_page_count":len(textbook),
            "slide_page_count":len(deck),
            "source_vector_paths":len(source_drawings),
            "source_raster_images":len(src_images),
            "slide_vector_paths":len(slide_drawings),
            "slide_raster_images":len(slide_images),
            "source_figure_id_mentions":len(caption_source),
            "slide_figure_id_mentions":len(caption_slide),
            "source_pdf_extractable_panel_label_tokens":len(
                source_text_label_matches),
            "original_source_and_slides_modified":False,
            "academic_review_claimed":False,
            "scientific_semantics_certified":False,
            "figure_panel_completeness_certified":False,
            "tts_or_video_authorized":False,
            "student_publication_authorized":False,
        }
    require(all(_sha(original)==before[name] for original,name
                in ((source,"source_sha256"),(slides,"slides_sha256"))),
            "Original PDF changed during discovery")

    if declared is None:
        report.update({
            "status":"PILOT_BLOCKED_MISSING_INDEPENDENT_FIGURE_GEOMETRY",
            "figure_region_mapping_verified":False,
            "reason":"Figure identifier, path/image counts and PDF text do not "
                     "independently establish all original source figure/panel "
                     "rectangles, labels and rendered slide matches",
            "next_action":"Supply independently grounded source/slide figure "
                          "regions and all panel boxes; re-run strict "
                          "vector/slide equivalence without writing inputs",
        })
        return report

    require(isinstance(declared,dict)
            and set(declared)=={"source_bbox","slide_bbox","panel_boxes",
                                "panel_ids","caption"},
            "Explicit caption and complete source/slide panel geometry required")
    try:
        candidate=inspect_vector_panel_seams(
            source=source,slides=slides,
            source_page=source_page,slide_page=slide_page,
            **declared)
    except Exception as exc:
        # Expected technical gate failures are results, not forged acceptance.
        from .figure_source_identity import FigureIdentityReviewRequired
        if not isinstance(exc,FigureIdentityReviewRequired):
            raise
        report.update({
            "status":"PILOT_BLOCKED_SOURCE_PANEL_PROOF",
            "figure_region_mapping_verified":False,
            "reason":str(exc),
        })
    else:
        report.update({
            "status":"PILOT_TECHNICAL_CANDIDATE_SEMANTIC_QA_BLOCKED",
            "figure_region_mapping_verified":True,
            "candidate_receipt_status":candidate["status"],
            "candidate_source_sha256":candidate["source_sha256"],
            "candidate_rendered_sha256":candidate["rendered_rgb_sha256"],
            "source_original_labels_checked":True,
            "true_panel_boundary_semantics_certified":False,
            "reason":"A strict visual source-to-slide proof exists but does "
                     "not establish all author-intended panel boundaries, "
                     "scientific figure meaning, or production approval",
        })
    require(_sha(source)==before["source_sha256"]
            and _sha(slides)==before["slides_sha256"],
            "Original PDFs changed during explicit candidate verification")
    return report


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--slides",type=Path,required=True)
    parser.add_argument("--source-page",type=int,required=True)
    parser.add_argument("--slide-page",type=int,required=True)
    parser.add_argument("--figure-id",required=True)
    parser.add_argument("--declared-json",type=Path,default=None)
    args=parser.parse_args()
    declared=None
    if args.declared_json:
        require(args.declared_json.is_file()
                and not args.declared_json.is_symlink(),
                "Must use existing trusted explicit mapping JSON")
        declared=json.loads(args.declared_json.read_text(encoding="utf-8"))
    report=inspect_textbook_figure_pilot(
        source=args.source,slides=args.slides,source_page=args.source_page,
        slide_page=args.slide_page,figure_id=args.figure_id,
        declared=declared)
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
