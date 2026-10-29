"""Source-bound, review-only Slide4 reference-triangle highlight candidates.

No timecodes, audio alignment, semantic approval, or publication. Candidates
are three geometrically verified source-matched raster strips from Figure 8.2
paired with exact original narration *mentions*, not a verified lesson scene.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

import pymupdf

from .ai_academic_web_review import build_review_job
from .figure_source_identity import require,_sha
from .original_figure82_side_word_positions import inspect_original_figure82_side_word_positions
from .original_figure82_pixel_registration import inspect_original_figure82_pixel_registration
from .original_figure82_source_label_order import inspect_original_figure82_label_order
from .original_composite_gutter_proposals import inspect_original_composite_gutters

# A deliberately small, original-source-specific vertical slice. Unverified
# mathematical/lexical inference NEVER becomes an encoded-video timing cue.
_MENTION = (
    ("s004.utterance.002","tangent","x = a tan u"),
    ("s004.utterance.003","sine","x = a sin u"),
    ("s004.utterance.004","secant","x = a sec u"),
)
_UNMAPPED = ("s004.utterance.001","s004.utterance.005")


def propose_original_triangle_mentions(*,utterances:list,rectangles:list,
                                       source_formulas:list, slide_size:tuple)->dict:
    """Reject inferred, shifted, duplicated or missing original panel identity."""
    require(type(utterances) is list and len(utterances)==5,
            "Expected all five immutable original Slide4 utterances")
    require(type(rectangles) is list and len(rectangles)==3
            and type(source_formulas) is list and len(source_formulas)==3,
            "Three independently sourced Figure8.2 regions required")
    require(type(slide_size) is tuple and len(slide_size)==2
            and all(type(v) in (int,float) and math.isfinite(v) and v>0
                    for v in slide_size),
            "Original slide PDF boundaries required")
    ids=[u.get("id") for u in utterances if isinstance(u,dict)]
    require(len(ids)==5 and ids==[f"s004.utterance.{i:03d}" for i in range(1,6)],
            "Original narration units missing, duplicated or reordered")
    require(all(type(u.get("spoken_text")) is str
                and type(u.get("spoken_sha256")) is str
                and len(u["spoken_sha256"])==64
                and re.fullmatch("[0-9a-f]{64}",u["spoken_sha256"])
                for u in utterances),
            "Immutable verbatim source utterance hash required")
    # Validate location evidence before proposing any pairing.
    bounds=[]
    for idx,(row,name) in enumerate(zip(rectangles,source_formulas),1):
        require(type(row) is dict and row.get("candidate_index")==idx
                and type(row.get("panel_native_pixel_sha256")) is str
                and re.fullmatch("[0-9a-f]{64}",row["panel_native_pixel_sha256"])
                and name==_MENTION[idx-1][2],
                "Original Figure8.2 candidate order/hash/formula changed")
        rect=row.get("candidate_slide_bbox_pdf_pt")
        require(type(rect) is list and len(rect)==4
                and all(type(v) in (int,float) and math.isfinite(v) for v in rect)
                and 0<=rect[0]<rect[2]<=slide_size[0]
                and 0<=rect[1]<rect[3]<=slide_size[1]
                and rect[2]-rect[0]>50 and rect[3]-rect[1]>40,
                "Original Figure8.2 candidate outside slide or too small")
        bounds.append(rect)
    require(all(abs(a[2]-b[0])<0.25
                and abs(a[1]-b[1])<0.25 and abs(a[3]-b[3])<0.25
                for a,b in zip(bounds,bounds[1:])),
            "Slide4 panel candidate regions overlap or are not contiguous")
    mappings=[]
    for i,u in enumerate(utterances):
        if u["id"] in _UNMAPPED:
            mappings.append({
                "utterance_id":u["id"],
                "original_spoken_sha256":u["spoken_sha256"],
                "candidate_panel_id":None,
                "candidate_highlight_bbox_pdf_pt":None,
                "review_reason":"GENERAL_INTRO_OR_ABSOLUTE_ROOT_REQUIRES_SEPARATE_SCENE_REVIEW",
                "speaking_start_s":None,"speaking_end_s":None,
                "source_figure_math_semantics_approved":False,
                "speech_to_visual_sync_verified":False,
            })
            continue
        expected_id,word,formula=_MENTION[i-1]
        spoken=u["spoken_text"]
        require(u["id"]==expected_id
                and len(re.findall(r"(?<![a-z])"+word+r"(?![a-z])",
                                   spoken.casefold()))==1,
                "Narration phrase does not uniquely support Figure8.2 candidate")
        require(not any(
            re.search(r"(?<![a-z])"+other+r"(?![a-z])",spoken.casefold())
            for other in ("tangent","sine","secant") if other!=word),
            "Narration has competing triangle-substitution labels")
        target=rectangles[i-1]
        mappings.append({
            "utterance_id":u["id"],
            "original_spoken_sha256":u["spoken_sha256"],
            "candidate_panel_id":f"s004.figure82.strip.{i:03d}",
            "original_source_formula_label":formula,
            "candidate_highlight_bbox_pdf_pt":target["candidate_slide_bbox_pdf_pt"],
            "original_source_strip_sha256":target["panel_native_pixel_sha256"],
            "review_reason":"LEXICAL_AND_SOURCE_PIXEL_PANEL_ORDER_HINT_NOT_SEMANTIC_APPROVAL",
            "speaking_start_s":None,"speaking_end_s":None,
            "source_figure_math_semantics_approved":False,
            "speech_to_visual_sync_verified":False,
        })
    require(sum(x["candidate_panel_id"] is not None for x in mappings)==3
            and sum(x["candidate_panel_id"] is None for x in mappings)==2,
            "Cannot silently drop utterances or invent full coverage")
    return {
        "status":"ORIGINAL_SLIDE4_THREE_RASTER_REGION_CANDIDATES_REVIEW_ONLY",
        "original_utterance_count":5,
        "proposed_figure_region_utterance_count":3,
        "unmapped_original_utterance_count":2,
        "utterance_candidates":mappings,
        "original_utterance_sequence_preserved":True,
        "all_utterances_highlightable":False,
        "original_audio_or_word_timestamps_verified":False,
        "video_element_highlight_synchronization_verified":False,
        "mathematical_and_academic_semantics_verified":False,
        "student_publication_authorized":False,
    }


def inspect_original_slide4_highlight_candidates(*,folder:Path)->dict:
    root=Path(folder).absolute()
    source,slides,script=(root/n for n in ("source.pdf","slides.pdf","script.txt"))
    hashes=tuple(_sha(p) for p in (source,slides,script))
    job=build_review_job(folder=root,slide_numbers=[4])
    sides=inspect_original_figure82_side_word_positions(folder=root)
    pixels=inspect_original_figure82_pixel_registration(folder=root)
    labels=inspect_original_figure82_label_order(folder=root)
    gutters=inspect_original_composite_gutters(folder=root,slide=4)
    require((job["source_sha256"],job["slides_sha256"],job["script_sha256"])==hashes
            and (sides["source_sha256"],sides["slides_sha256"],sides["script_sha256"])==hashes
            and (pixels["source_sha256"],pixels["slides_sha256"],pixels["script_sha256"])==hashes
            and (labels["source_sha256"],labels["slides_sha256"],labels["script_sha256"])==hashes
            and (gutters["original_source_sha256"],gutters["original_slides_sha256"],
                 gutters["original_script_sha256"])==hashes,
            "Original narration, printed source, bitmap and geometry SHA mismatch")
    require(sides["printed_side_position_candidate_count"]==3
            and pixels["original_source_to_slide_pixel_similarity_accepted"] is True
            and pixels["individual_strip_count"]==3
            and labels["printed_label_count"]==3,
            "Real Figure8.2 prerequisite not verified")
    require(job["utterance_count"]==5
            and job["slides"][0]["slide"]==4,
            "Not the original complete Slide4 speech")
    ordered=[x["source_printed_label"] for x in labels["ordered_review_candidates"]]
    with pymupdf.open(slides) as deck:
        require(len(deck)>=4,"Original Slide4 missing")
        size=(float(deck[3].rect.width),float(deck[3].rect.height))
    report=propose_original_triangle_mentions(
        utterances=job["slides"][0]["utterances"],
        rectangles=gutters["candidate_strips"],
        source_formulas=ordered,slide_size=size)
    require(tuple(_sha(p) for p in (source,slides,script))==hashes,
            "Original sources changed during speech/element review")
    return {
        **report,
        "original_source_sha256":hashes[0],
        "original_slides_sha256":hashes[1],
        "original_script_sha256":hashes[2],
        "original_slide_number":4,
        "printed_figure_source_page":1,
        "figure82_source_to_slide_pixel_similarity_verified":True,
        "source_triangle_printed_side_positions_technically_verified":True,
        "independent_two_pass_original_math_agreements_added":0,
        "real_Kore_audio_accepted":False,
        "original_encoded_highlighted_mp4_verified":False,
        "new_Gemini_request_sent":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    args=p.parse_args(argv)
    print(json.dumps(inspect_original_slide4_highlight_candidates(folder=args.folder),
                     indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
