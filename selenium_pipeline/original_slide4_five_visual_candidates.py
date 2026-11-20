"""Complete five original Slide4 review-only visual *candidates* from real slide.

Three geometry/source pixel-bound triangle candidates already exist. The
introduction and absolute-value narration have distinct source-slide *text*
targets; their exact PDF text and boxes can be proposed without false timing,
independent mathematical approval or proof of an audible, highlighted MP4.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .ai_academic_web_review import build_review_job
from .figure_source_identity import _sha,require
from .original_slide4_figure_highlight_candidates import (
    inspect_original_slide4_highlight_candidates,
)


def complete_review_only_visual_candidates(*,job:dict, prior:dict)->dict:
    require(job.get("status")=="SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED"
            and len(job.get("slides",[]))==1
            and job["slides"][0]["slide"]==4
            and job.get("utterance_count")==5
            and prior.get("status")=="ORIGINAL_SLIDE4_THREE_RASTER_REGION_CANDIDATES_REVIEW_ONLY"
            and prior.get("proposed_figure_region_utterance_count")==3
            and prior.get("unmapped_original_utterance_count")==2
            and all(prior.get(f"original_{a}_sha256")==job.get(f"{a}_sha256")
                    for a in ("source","slides","script")),
            "Genuine prior candidate report and exact same original source required")
    units=job["slides"][0]["utterances"]
    base=prior["utterance_candidates"]
    require(len(base)==len(units)==5
            and all(base[i].get("utterance_id")==units[i].get("id")
                    and base[i].get("original_spoken_sha256")==units[i].get("spoken_sha256")
                    for i in range(5)),
            "Exact original narration/SHA candidate coverage required")
    require(base[0].get("candidate_panel_id") is None
            and base[4].get("candidate_panel_id") is None
            and all(base[i].get("candidate_panel_id") is not None for i in (1,2,3)),
            "Cannot overwrite previously approved geometry or fabricate missing speech")
    targets=job["slides"][0]["visual_targets"]
    require(type(targets) is list and len(targets)==6
            and [t.get("id") for t in targets]
            ==[f"s004.text.{i:03d}" for i in range(1,7)],
            "Expected real original Slide4 text layout changed")
    def verify(i:int,required:list[str])->list[float]:
        t=targets[i-1]
        require(t.get("kind")=="text_block" and type(t.get("visible_text")) is str
                and all(x in t["visible_text"] for x in required),
                f"Original Slide4 text target {i} changed or does not cite narrated topic")
        rect=t.get("bbox_pdf_pt")
        require(type(rect) is list and len(rect)==4
                and all(type(v) in (int,float) and math.isfinite(v) for v in rect)
                and 0<=rect[0]<rect[2]<=420
                and 0<=rect[1]<rect[3]<=300,
                "Original source Slide4 text rectangle is not valid")
        return list(rect)
    verify(1,["Geometric Reference Triangles"])
    intro=verify(2,["Each substitution corresponds","right triangle","angle u"])
    root_glyph=verify(3,["√"])
    expr1=verify(4,["a2 + x2","a| sec u|","√"])
    expr2=verify(5,["a2 −x2","a| cos u|","√"])
    expr3=verify(6,["x2 −a2","a| tan u|"])
    intro_speech=units[0]["spoken_text"].lower()
    root_speech=units[4]["spoken_text"].lower()
    require("right triangles" in intro_speech
            and "acute angle" in intro_speech
            and "principal square root" in root_speech
            and "absolute values" in root_speech
            and "secant" in root_speech,
            "Original introduction or principal-root narration scope changed")
    union=[
        round(min(r[0] for r in (root_glyph,expr1,expr2,expr3)),4),
        round(min(r[1] for r in (root_glyph,expr1,expr2,expr3)),4),
        round(max(r[2] for r in (root_glyph,expr1,expr2,expr3)),4),
        round(max(r[3] for r in (root_glyph,expr1,expr2,expr3)),4),
    ]
    require(union[2]-union[0]>=70 and union[3]-union[1]>=40
            and intro[3]<union[1]-50
            and all(r[0]>=union[0] and r[2]<=union[2]
                    and r[1]>=union[1] and r[3]<=union[3]
                    for r in (root_glyph,expr1,expr2,expr3)),
            "Original radical equation geometry overlaps intro or is incomplete")
    rows=[]
    for idx,(unit,previous) in enumerate(zip(units,base)):
        row={
            **previous,
            "utterance_id":unit["id"],
            "original_spoken_sha256":unit["spoken_sha256"],
            "actual_audio_start_s":None,
            "actual_audio_end_s":None,
            "source_math_independently_agreed":False,
            "source_figure_semantics_independently_approved":False,
            "actual_highlighted_video_frames_verified":False,
        }
        if idx==0:
            row.update({
                "review_target_id":"s004.text.002",
                "candidate_highlight_bbox_pdf_pt":intro,
                "candidate_kind":"VISIBLE_SLIDE_TEXT_REGION",
                "review_reason":"SOURCE_SLIDE_RIGHT_TRIANGLE_INTRO_TEXT_CANDIDATE_ONLY",
            })
        elif idx==4:
            row.update({
                "review_target_id":"s004.text.003-through-s004.text.006",
                "candidate_highlight_bbox_pdf_pt":union,
                "candidate_kind":"MULTILINE_RADICAL_AND_ABSOLUTE_VALUE_TEXT_REGION",
                "review_reason":"SOURCE_SLIDE_ABSOLUTE_VALUE_EQUATIONS_CANDIDATE_ONLY",
                "radical_operator_pdf_text_academically_verified":False,
            })
        else:
            require(row["candidate_highlight_bbox_pdf_pt"] is not None,
                    "Previously grounded triangle candidate lost")
            row.update({"review_target_id":previous["candidate_panel_id"],
                        "candidate_kind":"SOURCE_MATCHED_TRIANGLE_RASTER_STRIP"})
        require(row["speaking_start_s"] is None and row["speaking_end_s"] is None
                and row["speech_to_visual_sync_verified"] is False,
                "Visual candidate is not an observed audio/visual synchronization")
        rows.append(row)
    require(len(rows)==5 and all(x["candidate_highlight_bbox_pdf_pt"] is not None
                                  for x in rows),
            "Five original narration units must have bounded REVIEW candidates")
    return {
        "status":"FIVE_ORIGINAL_SLIDE4_VISUAL_CANDIDATES_NOT_TIMED_OR_APPROVED",
        "source_sha256":job["source_sha256"],
        "slides_sha256":job["slides_sha256"],
        "script_sha256":job["script_sha256"],
        "original_slide_number":4,
        "utterance_candidate_count":5,
        "source_matched_figure_region_candidate_count":3,
        "original_slide_text_region_candidate_count":2,
        "unmapped_visual_candidate_count":0,
        "utterance_candidates":rows,
        "narration_timing_verified":False,
        "source_mathematical_review_approved":False,
        "highlighted_video_verified":False,
        "voice_provenance_verified":False,
        "genuine_Kore_TTS_authorized":False,
        "student_publication_authorized":False,
        "new_Gemini_request_sent":False,
    }


def inspect_original_slide4_five_visual_candidates(*,folder:Path)->dict:
    root=Path(folder).absolute()
    names=("source.pdf","slides.pdf","script.txt")
    hashes=tuple(_sha(root/name) for name in names)
    job=build_review_job(folder=root,slide_numbers=[4])
    prior=inspect_original_slide4_highlight_candidates(folder=root)
    result=complete_review_only_visual_candidates(job=job,prior=prior)
    require(tuple(_sha(root/name) for name in names)==hashes,
            "Original teaching materials changed during source text mapping")
    require((result["source_sha256"],result["slides_sha256"],
             result["script_sha256"])==hashes,
            "Source text/narration/page SHA identities do not agree")
    return result


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    args=p.parse_args(argv)
    print(json.dumps(inspect_original_slide4_five_visual_candidates(folder=args.folder),
                     indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
