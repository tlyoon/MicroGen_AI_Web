"""Fail-closed Figure 8.3 source/math/narration publication decision.

This contract gate deliberately cannot authorize a paid element-TTS job,
a final MP4 replacement or student publication from visual source/slide
candidate matches. Such release requires an independent later contract and
genuine clip-level acoustically proven speech alignment evidence.
"""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from .figure_source_identity import require
from .math_aware_slide5_figure_candidates import audit

def _review_box(box)->bool:
    return (type(box) is list and len(box)==4
            and all(type(x) is int and 0<=x<=3000 for x in box)
            and box[0]<box[2] and box[1]<box[3])

def evaluate_candidate_release(evidence:dict)->dict:
    require(type(evidence) is dict and evidence.get("figure_id")=="8.3",
            "Original Figure 8.3 review evidence required")
    for name in ("source_sha256","slides_sha256","script_sha256"):
        h=evidence.get(name)
        require(type(h) is str and bool(re.fullmatch("[0-9a-f]{64}",h)),
                "Missing exact original source/slide/script evidence fingerprint")
    utterances=evidence.get("utterances")
    require(type(utterances) is list and 0<len(utterances)<=100
            and type(evidence.get("unique_single_function_hint_count")) is int
            and type(evidence.get("unresolved_hint_count")) is int
            and evidence.get("original_slide_inverse_operator_glyph_correspondence_verified") is True
            and evidence.get("full_equation_operator_anchor_registration_consistent") is True
            and evidence.get("original_fraction_x_over_a_positions_independently_disambiguated") is True,
            "Source-bound independent equation and narration candidate evidence missing")
    require(evidence.get("figure_element_tts_authorized") is False
            and evidence.get("student_publication_authorized") is False,
            "Untrusted evidence attempts to grant media-release permissions")
    seen=set()
    named=0;ambiguous=0
    review=[]
    for entry in utterances:
        require(type(entry) is dict and type(entry.get("utterance_id")) is str
                and bool(entry["utterance_id"]) and entry["utterance_id"] not in seen,
                "Duplicate or malformed original narration segment identity")
        seen.add(entry["utterance_id"])
        require(entry.get("paid_tts_authorized") is False
                and entry.get("narration_to_panel_semantics_verified") is False
                and entry.get("complete_equation_label_and_axis_mathematics_verified") is False,
                "Premature TTS or semantic approval in merely pixel-reviewed utterance")
        panel=entry.get("candidate_ordered_graph_panel")
        branches=entry.get("function_names_explicitly_spoken")
        require(type(branches) is list
                and all(b in ("tangent","sine","secant") for b in branches),
                "Untrusted named mathematical function cues")
        if len(branches)==1:
            require(type(panel) is int and 1<=panel<=3
                    and entry.get("source_x_over_a_fraction_position_disambiguated") is True
                    and entry.get("source_full_expression_to_slide_operator_registration_consistent") is True
                    and _review_box(entry.get("candidate_matched_operator_pixel_bbox_for_review"))
                    and _review_box(entry.get("candidate_full_expression_bitmap_bbox_for_review")),
                    "Named-panel source/fraction/slide equation candidate not independently located")
            named+=1
            status="NAMED_SOURCE_EXPRESSION_REVIEW_ANCHOR_ONLY"
        else:
            require(panel is None
                    and entry.get("candidate_matched_operator_pixel_bbox_for_review") is None
                    and entry.get("candidate_full_expression_bitmap_bbox_for_review") is None,
                    "Ambiguous utterance incorrectly given a mathematical review target")
            ambiguous+=1
            status="MULTIPLE_OR_NO_FUNCTION_NAMES_REVIEW_REQUIRED"
        review.append({"utterance_id":entry["utterance_id"],"status":status,
                       "potential_review_panel":panel,
                       "element_level_audio_job_authorized":False})
    require(named==evidence["unique_single_function_hint_count"]
            and ambiguous==evidence["unresolved_hint_count"]
            and named+ambiguous==len(utterances),
            "Real source narration candidate counts do not reconcile")
    blockers=["COMPLETE_DISPLAYED_EQUATION_MATHEMATICAL_EQUIVALENCE_NOT_VERIFIED",
              "ALL_FIGURE_AXES_TICKS_AND_GRAPH_SEMANTICS_NOT_VERIFIED",
              "SPOKEN_ELEMENT_TIMING_AND_SEGMENT_LEVEL_TTS_AUDIO_NOT_VERIFIED",
              "HUMAN_ACADEMIC_LISTENING_QA_NOT_VERIFIED"]
    if evidence.get("full_equation_bitmap_pixel_uniqueness_verified") is not True:
        blockers.insert(0,"FULL_EXPRESSION_PIXEL_TEMPLATE_NOT_UNIQUELY_CORROBORATED")
    if ambiguous:
        blockers.append("UNRESOLVED_MULTI_OR_NO_FUNCTION_UTTERANCES")
    return {"schema_version":1,
            "status":"SOURCE_BOUND_FIGURE83_REVIEW_CANDIDATES_PRODUCTION_BLOCKED",
            "original_source_sha256":evidence["source_sha256"],
            "original_slides_sha256":evidence["slides_sha256"],
            "original_script_sha256":evidence["script_sha256"],
            "utterance_count":len(review),
            "named_review_anchor_count":named,
            "unresolved_utterance_count":ambiguous,
            "utterance_dispositions":review,
            "release_blockers":blockers,
            "verified_spoken_element_audio_jobs":0,
            "authorized_paid_tts_jobs":[],
            "genuine_element_level_spoken_timing_verified":False,
            "production_media_accepted":False,
            "student_publication_authorized":False}

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    for f in ("source","slides","script"):
        p.add_argument("--"+f,type=Path,required=True)
    a=p.parse_args(argv)
    r=audit(source=a.source,slides=a.slides,script=a.script)
    result=evaluate_candidate_release(r)
    print(json.dumps(result,ensure_ascii=True,indent=2,sort_keys=True))
    return 2  # review-only state is an intentionally blocked release

if __name__=="__main__":
    raise SystemExit(main())
