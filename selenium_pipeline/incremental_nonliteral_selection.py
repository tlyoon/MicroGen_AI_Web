"""Validate explicit nonliteral narration element reviews against immutable original PDFs.

A reviewer choice is a declared decision, not mathematical proof supplied by
this software. Verify source quote/page and exact candidate visual geometry;
do not silently approve other utterances.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha
from .incremental_element_candidate_map import candidate_map

def validate_explicit_element_choices(*,folder:Path,choices:list[dict],
                                      candidates:dict|None=None)->dict:
    folder=Path(folder).absolute()
    mapping=candidates if candidates is not None else candidate_map(folder=folder)
    require(type(mapping) is dict
            and mapping.get("status")=="PER_UTTERANCE_SLIDE_ELEMENT_CANDIDATES_REVIEW_REQUIRED"
            and type(choices) is list and len(choices)<=mapping.get("utterance_count",0),
            "Original candidate mapping and bounded independent choices required")
    known={u["utterance_id"]:(slide,u)
           for slide in mapping["slides"]
           for u in slide["original_utterance_candidates"]}
    require(len(known)==mapping["utterance_count"],
            "Duplicate or missing original narration identities")
    approved=[];seen=set();claimed_visual=set()
    before={key:_sha(folder/name) for key,name in [
        ("source_sha256","source.pdf"),("slides_sha256","slides.pdf"),
        ("script_sha256","script.txt")]}
    require(all(mapping.get(k)==before[k] for k in before),
            "Stale original teaching assets or choice map")
    with pymupdf.open(folder/"source.pdf") as source,pymupdf.open(folder/"slides.pdf") as deck:
        for decision in choices:
            require(type(decision) is dict
                    and set(decision)=={
                        "utterance_id","spoken_text_sha256","target_id",
                        "source_page","verbatim_source_quote",
                        "reviewer_attestation","reviewer_id"}
                    and type(decision["utterance_id"]) is str
                    and decision["utterance_id"] in known
                    and decision["utterance_id"] not in seen,
                    "Selections must identify one original utterance exactly")
            uid=decision["utterance_id"]
            seen.add(uid)
            row,u=known[uid]
            require(u["original_text_sha256"]==decision["spoken_text_sha256"]
                    and decision["reviewer_attestation"] is True
                    and type(decision["reviewer_id"]) is str
                    and 3<=len(decision["reviewer_id"].strip())<=120,
                    "Explicit accountable reviewer acknowledgement required")
            targets=[t for t in u["candidate_visual_targets"]
                     if t["target_id"]==decision["target_id"]]
            require(len(targets)==1,"Reviewer selection not from original PDF")
            visual=targets[0]
            source_page=decision["source_page"]
            quote=decision["verbatim_source_quote"]
            require(type(source_page) is int and 1<=source_page<=len(source)
                    and type(quote) is str and 12<=len(quote)<=800
                    and quote in source[source_page-1].get_text(),
                    "Original exact textbook citation missing or not at claimed page")
            page=deck[row["slide"]-1]
            box=visual["original_visible_bbox_pdf_pt"]
            require(type(box) is list and len(box)==4
                    and 0<=box[0]<box[2]<=page.rect.width+1
                    and 0<=box[1]<box[3]<=page.rect.height+1,
                    "Visual element escapes actual original slide")
            visual_key=(row["slide"],visual["target_id"])
            require(visual_key not in claimed_visual,
                    "A reviewed visual cannot be assigned to conflicting spoken segments")
            claimed_visual.add(visual_key)
            approved.append({
                "utterance_id":uid,"slide":row["slide"],
                "spoken_text":u["original_text"],
                "spoken_text_sha256":decision["spoken_text_sha256"],
                "target_id":decision["target_id"],
                "bbox_pdf_pt":box,
                "original_source_page":source_page,
                "original_quote_sha256":hashlib.sha256(quote.encode()).hexdigest(),
                "reviewer_id":decision["reviewer_id"].strip(),
                "reviewer_attestation_present":True,
                "independently_proven_spoken_audio_fidelity":False,
                "audio_duration_or_spoken_word_timing_verified":False,
            })
    require(all(before[k]==_sha(folder/name) for k,name in [
        ("source_sha256","source.pdf"),("slides_sha256","slides.pdf"),
        ("script_sha256","script.txt")]),"Original inputs mutated while reviewing")
    return {"status":"EXPLICIT_NONLITERAL_ELEMENT_SELECTIONS_SOURCE_BOUND",
            **before,
            "original_utterance_count":mapping["utterance_count"],
            "reviewed_utterance_count":len(approved),
            "unreviewed_utterance_count":mapping["utterance_count"]-len(approved),
            "selected_segments":approved,
            "mathematics_semantics_independently_machine_verified":False,
            "tts_billing_authorized":False,
            "whole_lecture_spoken_element_sync_verified":False,
            "student_publication_authorized":False}
