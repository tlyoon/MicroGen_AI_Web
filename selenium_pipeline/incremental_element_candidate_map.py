"""Extract independently addressable visible slide-element candidates for a queued lecture.

Ranks visible exact PDF text blocks against ORIGINAL utterances; lexical matches
are NOT speech/mathematical semantic approval. No OCR, paid TTS, or lecture edits.
"""
from __future__ import annotations
import math
from pathlib import Path
import pymupdf
from .figure_source_identity import require, _sha
from .incremental_lecture_sync_queue import inspect_folder
from .element_plan_autodraft import stable_recommendations

def candidate_map(*,folder:Path, queue:dict|None=None)->dict:
    folder=Path(folder).absolute()
    record=queue if queue is not None else inspect_folder(folder)
    slides=folder/"slides.pdf"
    require(record.get("status")=="INCREMENTAL_NARRATION_ELEMENT_EXECUTION_QUEUE_REVIEW_ONLY"
            and record.get("slides_sha256")==_sha(slides)
            and record.get("source_sha256")==_sha(folder/"source.pdf")
            and record.get("script_sha256")==_sha(folder/"script.txt"),
            "Queue must reference exact original complete lecture inputs")
    results=[]
    with pymupdf.open(slides) as deck:
        require(len(deck)==len(record["slides"]),"Slide count changed from source queue")
        for index,(page,row) in enumerate(zip(deck,record["slides"]),1):
            require(row["slide"]==index,"Out-of-order source-bound slide")
            targets=[]
            for block in page.get_text("blocks"):
                if len(block)<5 or not isinstance(block[4],str) or not block[4].strip():
                    continue
                x0,y0,x1,y1=(float(v) for v in block[:4])
                if not (all(math.isfinite(v) for v in (x0,y0,x1,y1))
                        and 0<=x0<x1<=page.rect.width+1
                        and 0<=y0<y1<=page.rect.height+1):
                    continue
                targets.append({
                    "draft_element_id":f"s{index:03d}.text.{len(targets)+1:03d}",
                    "kind":"text_block","visible_text":block[4].strip(),
                    "bbox_pdf_pt":[round(x0,3),round(y0,3),round(x1,3),round(y1,3)],
                    "panel_identity_review_required":False,
                    "anchor":{"type":"text_block","index":len(targets)},
                })
            refs=[]
            for utterance in row["original_verbatim_utterances"]:
                candidates=stable_recommendations(
                    utterance["original_text"],targets)
                selections=[]
                for suggestion in candidates:
                    match=next(x for x in targets
                               if x["draft_element_id"]==suggestion["draft_element_id"])
                    selections.append({
                        "target_id":match["draft_element_id"],
                        "original_visible_bbox_pdf_pt":match["bbox_pdf_pt"],
                        "visible_pdf_text":match["visible_text"],
                        "ranking_hint":suggestion["overlap_hint"],
                        "exactly_matched_visible_text":
                            utterance["original_text"].strip()==match["visible_text"],
                        "spoken_element_semantics_verified":False,
                    })
                refs.append({
                    "utterance_id":utterance["utterance_id"],
                    "original_text_sha256":utterance["original_text_sha256"],
                    "original_text":utterance["original_text"],
                    "candidate_visual_targets":selections,
                    "visual_element_review_required":True,
                    "source_mathematics_reviewed":False,
                    "element_tts_authorized":False,
                })
            results.append({"slide":index,
                            "original_slide_narration_sha256":
                                row["original_slide_narration_sha256"],
                            "candidate_visual_targets":targets,
                            "original_utterance_candidates":refs,
                            "all_utterances_source_semantics_verified":False})
    require(record["slides_sha256"]==_sha(slides)
            and record["source_sha256"]==_sha(folder/"source.pdf")
            and record["script_sha256"]==_sha(folder/"script.txt"),
            "Source assets changed while linking visible elements")
    return {"status":"PER_UTTERANCE_SLIDE_ELEMENT_CANDIDATES_REVIEW_REQUIRED",
            "source_sha256":record["source_sha256"],
            "slides_sha256":record["slides_sha256"],
            "script_sha256":record["script_sha256"],
            "slide_count":len(results),
            "utterance_count":sum(len(x["original_utterance_candidates"]) for x in results),
            "slides":results,
            "ready_for_paid_element_tts":False,
            "spoken_element_timing_verified":False,
            "student_publication_authorized":False}
