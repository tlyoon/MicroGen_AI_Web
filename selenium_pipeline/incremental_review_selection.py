"""Promote only independently corroborated exact source-text / PDF-text utterance matches.

This is NOT an automatic math equivalence reviewer: ambiguous utterances keep
their own review slot; unaffected literal source text continues independently.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import pymupdf
from .figure_source_identity import require,_sha
from .incremental_element_candidate_map import candidate_map
from .incremental_lecture_sync_queue import inspect_folder
from .automatic_element_narration import normalize

def exact_source_text_selections(*,folder:Path,candidates:dict|None=None)->dict:
    folder=Path(folder).absolute()
    q=inspect_folder(folder)
    c=candidates if candidates is not None else candidate_map(folder=folder,queue=q)
    require(c.get("status")=="PER_UTTERANCE_SLIDE_ELEMENT_CANDIDATES_REVIEW_REQUIRED"
            and all(c.get(k)==q[k] for k in ("source_sha256","slides_sha256","script_sha256"))
            and c.get("slide_count")==len(q["slides"])
            and c.get("utterance_count")==sum(
                len(x["original_verbatim_utterances"]) for x in q["slides"]),
            "Candidate map source drift or coverage gap")
    before=[q[x] for x in ("source_sha256","slides_sha256","script_sha256")]
    selections=[]
    with pymupdf.open(folder/"source.pdf") as source,pymupdf.open(folder/"slides.pdf") as deck:
        source_pages=[normalize(p.get_text()) for p in source]
        require(len(deck)==len(c["slides"]),"Original slide PDF mismatch")
        for row,original in zip(c["slides"],q["slides"]):
            require(row["slide"]==original["slide"],
                    "Utterance candidate page differs from source worklist")
            page=deck[row["slide"]-1]
            visible=page.get_text("blocks")
            seen=set()
            selections_for_slide=[]
            for unit,mapped in zip(original["original_verbatim_utterances"],
                                   row["original_utterance_candidates"]):
                require(unit["utterance_id"]==mapped["utterance_id"]
                        and unit["original_text_sha256"]==mapped["original_text_sha256"]
                        and len(mapped["candidate_visual_targets"])<=3,
                        "Candidate ID/text SHA changed or contains too many targets")
                actual=normalize(unit["original_text"])
                matches=[]
                for target in mapped["candidate_visual_targets"]:
                    if normalize(target["visible_pdf_text"])!=actual:
                        continue
                    block_name=target["target_id"]
                    candidate=next((x for x in row["candidate_visual_targets"]
                                    if x["draft_element_id"]==block_name),None)
                    if candidate is None or candidate["bbox_pdf_pt"]!=target["original_visible_bbox_pdf_pt"]:
                        continue
                    require(type(candidate["anchor"]["index"]) is int,
                            "Missing real PDF text block index")
                    index=candidate["anchor"]["index"]
                    if not (0<=index<len(visible) and
                            normalize(visible[index][4])==actual):
                        continue
                    pages=[n+1 for n,s in enumerate(source_pages) if actual in s]
                    if len(pages)!=1:continue
                    matches.append((target,pages[0]))
                unique=len(matches)==1 and matches[0][0]["target_id"] not in seen if matches else False
                if unique:
                    target,pagenumber=matches[0]
                    seen.add(target["target_id"])
                else:
                    target,pagenumber=None,None
                selections_for_slide.append({
                    "utterance_id":unit["utterance_id"],
                    "spoken_text":unit["original_text"],
                    "spoken_text_sha256":unit["original_text_sha256"],
                    "exact_source_pdf_text_match_verified":bool(unique),
                    "original_source_pdf_page":pagenumber,
                    "visible_element_id":target["target_id"] if target else None,
                    "element_bbox_pdf_pt":target["original_visible_bbox_pdf_pt"] if target else None,
                    "needs_semantic_or_source_review":not unique,
                    "math_semantic_approval_assumed":False,
                    "wordlevel_speech_timing_verified":False,
                })
            selections.append({"slide":row["slide"],"utterances":selections_for_slide})
    require([_sha(folder/n) for n in ("source.pdf","slides.pdf","script.txt")]==before,
            "Original assets changed during exact matching")
    matched=sum(x["exact_source_pdf_text_match_verified"]
                for s in selections for x in s["utterances"])
    return {"status":"EXACT_SOURCE_LITERAL_ELEMENT_FAST_LANE_PARTIAL",
            "source_sha256":before[0],"slides_sha256":before[1],"script_sha256":before[2],
            "utterances_total":c["utterance_count"],
            "source_literal_matches":matched,
            "review_required":c["utterance_count"]-matched,
            "slides":selections,
            "whole_lecture_math_semantics_verified":False,
            "ready_for_paid_tts":False,
            "production_release_authorized":False}
