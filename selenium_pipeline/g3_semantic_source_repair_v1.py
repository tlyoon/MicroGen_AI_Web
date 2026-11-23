"""G3 science-safe automatic continuation after captured source-quote rejection.

A source-grounded lexical worklist is NOT scientific validation. Verify exact
original publisher/slide/script hashes and rejected model bytes, then
materialize one SOURCE-BOUNDED new semantic *review task* per original
narration unit. Admission requires substantive overlap with the SPOKEN
claim, rather than just slide text. A task is a genuinely narrower claim,
distinct from the rejected whole-slide mapping prompt, and does not send
Gemini requests, publish, alter old claims or auto-approve mathematics.

Existing academic one-Send, two-pass source model review and exact Neon/High
provenance are the ONLY allowed future scientific reviewer transport.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

from .g3_source_rejected_offline_repair_v1 import (
    rejected_packet, _canon, _sha, _terms, need)
from .rich_element_model_alignment import request_for_slide, prompt_for_request
from .pdf_text_source_span_witness import prove_source_quote_occurrence
from .ai_academic_web_review import review_instructions
from .recovery_registry import lookup_mechanism

KIND="g3_semantic_source_repair"
SIGNATURE="G3_REJECTED_QUOTE_WORKLIST_NEEDS_INDEPENDENT_SOURCE_SEMANTIC_QA"
MECHANISM="VERIFY_ORIGINAL_CLAIM_AND_STAGE_DISTINCT_SPOKEN_SOURCE_QA_TASK"
SCHEMA="G3_SINGLE_ORIGINAL_UTTERANCE_SCIENCE_REVIEW_TASK_V1"
ROOT="g3_distinct_semantic_science_tasks_v1"
_HEX=re.compile(r"[0-9a-f]{64}\Z")
MAX_TASKS=128
MAX_QUOTE_COUNT=3


def _read(path:Path,limit:int=100_000)->dict:
    need(path.is_file() and not path.is_symlink()
         and 0<path.stat().st_size<=limit,"Missing or unsafe original worklist")
    item=json.loads(path.read_text("utf8"))
    need(type(item) is dict,"Invalid source worklist structure")
    return item


def _write_once(path:Path,data:dict)->None:
    content=_canon(data)
    need(not path.is_symlink() and path.parent.is_dir()
         and not path.parent.is_symlink(),"Redirected source semantic task")
    temp=path.with_suffix(".stage")
    need(not temp.is_symlink(),"Redirected staged semantic task")
    if path.exists():
        need(path.is_file() and path.read_bytes()==content,
             "Prior semantic source-science task was modified")
        if temp.exists():
            need(temp.is_file() and temp.read_bytes()==content,
                 "Conflicting partial semantic task")
            temp.unlink()
        return
    if temp.exists():
        need(temp.is_file() and temp.read_bytes()==content,
             "Interrupted semantic task cannot be changed")
    else:
        with temp.open("xb") as writer:
            writer.write(content)
            writer.flush()
            os.fsync(writer.fileno())
    os.replace(temp,path)


def _verified_packet(*,spec:dict,worklist:Path)->tuple[dict,dict]:
    need(type(spec) is dict and all(k in spec for k in (
        "section","source_folder","checkpoint","review_root")),
        "Original G3 section is not pinned")
    need(worklist.parent.name==spec["section"],
         "G3 semantic task wrong textbook subsection")
    packet=_read(worklist)
    need(packet.get("schema_version")==2
         and packet.get("status")==
             "G3_REJECTED_CAPTURE_SOURCE_QUOTE_WORKLIST_NO_SEND_V2"
         and packet.get("quote_candidates_are_scientific_proof") is False
         and packet.get("student_publication_authorized") is False
         and packet.get("original_rejected_source_review_accepted") is False
         and packet.get("new_browser_sends")==0,
         "Cannot promote originally rejected source-mapping record")
    expected=rejected_packet(
        source_folder=spec["source_folder"],
        checkpoint=spec["checkpoint"],
        review_root=spec["review_root"],
        slide=packet["original_slide_number"])
    need(packet==expected and worklist.read_bytes()==_canon(expected),
         "Original model rejection or source worklist changed")
    from . import g3_rich_mapping_auto_continuation_v71 as reviewer
    files=reviewer._files(spec["review_root"],packet["original_slide_number"])
    need(packet["original_rejected_claim_sha256"]==_sha(files["claim"])
         and packet["original_rejected_raw_model_capture_sha256"]==
             _sha(files["capture"]),
         "Source-rejected original browser claim/capture identity changed")
    request=request_for_slide(
        source_folder=spec["source_folder"],checkpoint=spec["checkpoint"],
        slide_number=packet["original_slide_number"])
    need(request["source_inputs_sha256"]==packet["source_inputs_sha256"]
         and request["request_sha256"]==packet["original_request_sha256"],
         "Original G3 source/slide/script identity changed")
    return packet,request


def _one_unit(*,spec:dict,packet:dict,request:dict,row:dict,
              worklist_sha:str)->dict:
    need(type(row) is dict and _HEX.fullmatch(worklist_sha) is not None
         and row.get("original_model_source_selection_rejected") is True,
         "Source-quote suggestion is not historical rejected unit")
    uid=row["utterance_id"]
    original=[x for x in request["original_utterances"]
              if x["utterance_id"]==uid]
    targets=[x for x in request["visible_targets"]
             if x["target_id"]==row["original_selected_target_id"]]
    need(len(original)==1 and len(targets)==1
         and row["verbatim_utterance_sha256"]==
             hashlib.sha256(original[0]["verbatim_text"].encode("utf8")).hexdigest(),
         "Semantic task changed original narration or slide target")
    target=targets[0]
    need(row["original_selected_target_kind"]==target["kind"]
         and row["original_visible_text_sha256"]==
             hashlib.sha256(target["visible_text"].encode("utf8")).hexdigest(),
         "Semantic candidate uses different original slide evidence")
    text=original[0]["verbatim_text"]
    spoken_sha=hashlib.sha256(text.encode("utf8")).hexdigest()
    citations=[]
    # Unlike the first worklist, count overlap against ACTUAL NARRATION
    # rather than the union of spoken text and a previously guessed target.
    spoken_terms=_terms(text)
    for candidate in row["source_excerpt_candidates"]:
        overlap=sorted(spoken_terms&_terms(candidate["publisher_quote_verbatim"]))
        if len(overlap)<2:
            continue
        source=Path(spec["source_folder"])/"source.pdf"
        proof=prove_source_quote_occurrence(
            source_pdf=source,
            expected_sha256=request["source_inputs_sha256"]["source.pdf"],
            page_number=candidate["source_page"],
            verbatim_quote=candidate["publisher_quote_verbatim"])
        need(proof["status"]=="EXACT_ORIGINAL_PDF_PAGE_QUOTE_PRESENT"
             and proof["math_semantics_author_verified"] is False
             and candidate["quote_physically_present"] is True
             and candidate["publisher_quote_sha256"]==
                 hashlib.sha256(candidate["publisher_quote_verbatim"].encode("utf8")).hexdigest(),
             "Citation failed independent original-PDF physical validation")
        citations.append({
            "source_page":candidate["source_page"],
            "verbatim_source_quote":candidate["publisher_quote_verbatim"],
            "quote_sha256":proof["quote_sha256"],
            "publisher_raw_quote_sha256":candidate["publisher_quote_sha256"],
            "narration_term_overlap":overlap[:20],
            "narration_term_overlap_count":len(overlap),
            "quote_is_not_semantic_proof":True,
        })
    citations=sorted(citations,key=lambda c:(
        -c["narration_term_overlap_count"],c["source_page"],
        c["publisher_raw_quote_sha256"]))[:MAX_QUOTE_COUNT]
    eligible=bool(citations) and target["kind"] in {
        "text_block","text_group","math_row_group"}
    scope=hashlib.sha256(_canon({
        "kind":SCHEMA,"source_inputs_sha256":request["source_inputs_sha256"],
        "original_rejected_request_sha256":request["request_sha256"],
        "original_rejected_claim_sha256":packet["original_rejected_claim_sha256"],
        "original_model_capture_sha256":
            packet["original_rejected_raw_model_capture_sha256"],
        "source_worklist_sha256":worklist_sha,
        "original_utterance_id":uid,
        "original_selected_target_id":target["target_id"],
    })).hexdigest()
    job=None
    if eligible:
        job={
            "status":"SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED",
            "original_folder":str(Path(spec["source_folder"]).absolute()),
            "source_sha256":request["source_inputs_sha256"]["source.pdf"],
            "slides_sha256":request["source_inputs_sha256"]["slides.pdf"],
            "script_sha256":request["source_inputs_sha256"]["script.txt"],
            "selected_original_slides":[request["slide"]],
            "utterance_count":1,
            "source_only_pre_tts_review":True,
            "slides":[{
                "slide":request["slide"],
                "visual_targets":[{
                    "id":target["target_id"],
                    "bbox_pdf_pt":target["author_rect_pdf_pt"],
                    "visible_text":target["visible_text"],
                    "kind":target["kind"],
                }],
                "utterances":[{
                    "id":uid,"spoken_text":text,"spoken_sha256":spoken_sha,
                    "ranked_candidates":[target["target_id"]],
                }],
            }],
            "academic_approval":False,
            "student_publication_authorized":False,
            "verified_source_quote_candidates_v1":{
                "status":"PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1",
                **{k+"_sha256":request["source_inputs_sha256"][k+".pdf" if k!="script" else "script.txt"]
                   for k in ("source","slides","script")},
                "citations_are_scientific_proof":False,
                "all_mathematics_verified":False,
                "student_publication_authorized":False,
                "utterances":[{
                    "utterance_id":uid,"spoken_sha256":spoken_sha,
                    "allowed_citations":[
                        {k:v for k,v in c.items()
                         if k in ("source_page","verbatim_source_quote","quote_sha256")}
                        for c in citations],
                }],
            },
            "g3_distinct_source_science_v1":{
                "scope_sha256":scope,
                "original_rejected_request_sha256":request["request_sha256"],
                "original_rejected_claim_sha256":packet["original_rejected_claim_sha256"],
                "original_source_worklist_sha256":worklist_sha,
                "original_total_slide_utterances":len(request["original_utterances"]),
                "new_task_is_one_original_utterance":True,
                "independent_two_pass_verification_required":True,
                "human_academic_approval":False,
                "student_publication_authorized":False,
            },
        }
        new=review_instructions(job,mode="INITIAL_REVIEW")
        old=prompt_for_request(request)
        need(new!=old and len(new)>0
             and job["utterance_count"]<len(request["original_utterances"]),
             "Candidate science review cannot replay original whole-slide request")
    return {
        "schema_version":1,"status":(
            "G3_DISTINCT_SOURCE_SEMANTIC_QA_READY_NO_SEND"
            if eligible else
            "G3_SOURCE_EVIDENCE_INSUFFICIENT_NO_REVIEW_SEND"),
        "scope_sha256":scope,
        "section":spec["section"],
        "source_folder":str(spec["source_folder"]),
        "original_rejected_slide":request["slide"],
        "original_utterance_id":uid,
        "original_spoken_sha256":spoken_sha,
        "original_visible_target_id":target["target_id"],
        "source_worklist_sha256":worklist_sha,
        "original_rejected_claim_sha256":packet["original_rejected_claim_sha256"],
        "original_rejected_request_sha256":request["request_sha256"],
        "old_whole_slide_request_replayed":False,
        "exact_original_source_quote_candidates":citations,
        "original_spoken_terms":sorted(spoken_terms)[:45],
        "science_review_job":job,
        "new_source_review_send_allowed_without_fresh_neon_health":False,
        "g3_original_semantic_mapping_accepted":False,
        "independent_scientific_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "video_accepted":False,
        "student_publication_authorized":False,
        "new_gemini_browser_sends":0,
        "new_gemini_paid_API_calls":0,
    }


def materialize(*,specs:list,worklist_root:Path,output_root:Path)->dict:
    """Produce all distinct one-unit tasks with no external provider request."""
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "New G3 semantic source recovery is not in executable registry")
    worklist_root,output_root=(Path(worklist_root).absolute(),
                               Path(output_root).absolute())
    need(type(specs) is list and 1<=len(specs)<=8
         and worklist_root.is_dir() and not worklist_root.is_symlink()
         and output_root.parent.is_dir() and not output_root.is_symlink()
         and not output_root.is_relative_to(worklist_root)
         and not worklist_root.is_relative_to(output_root),
         "Semantic source repair requires separate immutable source owner")
    previous=[]
    for spec in specs:
        need(type(spec.get("section")) is str and
             not any(spec["section"]==s.get("section") for s in previous)
             and not output_root.is_relative_to(Path(spec["source_folder"])),
             "Semantic worklist cannot overwrite original source")
        previous.append(spec)
    source_files=[]
    for spec in specs:
        section=worklist_root/spec["section"]
        need(section.is_dir() and not section.is_symlink(),
             "Missing original source-worklist subsection")
        paths=sorted(section.glob("slide_*.json"))
        need(len(paths)<=MAX_TASKS and
             all(p.is_file() and not p.is_symlink() for p in paths),
             "Invalid original quotation worklist inventory")
        for path in paths:
            source_files.append((spec,path))
    need(len(source_files)<=MAX_TASKS,"Unbounded original G3 source worklists")
    items=[]
    for spec,path in source_files:
        packet,request=_verified_packet(spec=spec,worklist=path)
        sha=_sha(path)
        for row in packet["publisher_quote_worklist"]:
            items.append(_one_unit(
                spec=spec,packet=packet,request=request,row=row,
                worklist_sha=sha))
    need(len(items)<=MAX_TASKS,"Oversized source-grounded semantic review batch")
    output_root.mkdir(exist_ok=True)
    for item in items:
        home=output_root/item["section"]
        home.mkdir(exist_ok=True)
        need(home.is_dir() and not home.is_symlink(),
             "Redirected science review task subsection")
        _write_once(home/(item["scope_sha256"]+".json"),item)
    return {
        "status":"G3_SOURCE_SEMANTIC_REVIEW_TASKS_STAGED_NO_MODEL_SEND",
        "schema_version":1,
        "tasks":[{
            "section":item["section"],
            "slide":item["original_rejected_slide"],
            "utterance_id":item["original_utterance_id"],
            "scope_sha256":item["scope_sha256"],
            "task_status":item["status"],
            "physical_source_quote_candidates":len(
                item["exact_original_source_quote_candidates"]),
        } for item in items],
        "original_missing_source_quote_units":len(items),
        "new_distinct_science_review_tasks_ready":sum(
            x["science_review_job"] is not None for x in items),
        "unresolved_source_quote_units":sum(
            x["science_review_job"] is None for x in items),
        "old_uncertain_provider_claims_reset":False,
        "original_rejected_model_claims_accepted":0,
        "independent_scientific_QA_accepted":0,
        "new_browser_sends":0,
        "paid_gemini_API_calls":0,
        "student_publication_authorized":False,
    }
