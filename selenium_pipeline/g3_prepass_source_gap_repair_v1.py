"""Pre-review G3 source-gap repair from ORIGINAL rejected publisher captures.

A narration *transition* is not a physics assertion. Don't invent a
scientific quotation for one. The rendered review-question slide still
requires independently verified scientific and visual QA. For substantive
claims, search the actual full original subsection (rather than a few
top lexical lines), pin exact physically witnessed contiguous source text,
and stage a genuinely new one-utterance two-pass review with NO browser Send.

Original academic response, source and previously issued worklist immutable.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from .g3_semantic_source_repair_v1 import (
    _verified_packet, _one_unit, _write_once, _read, _canon, _sha, need)
from .g3_semantic_context_recovery_v2 import _context
from .g3_source_rejected_offline_repair_v1 import _terms
from .ai_academic_web_review import review_instructions
from .rich_element_model_alignment import prompt_for_request
from .recovery_registry import lookup_mechanism

KIND="g3_prepass_source_gap_repair"
SIGNATURE="G3_MISSING_QUOTE_MIXES_NARRATION_TRANSITION_AND_SUBSTANTIVE_CLAIM"
MECHANISM="CLASSIFY_NAVIGATION_OR_STAGE_PHYSICALLY_WITNESSED_NEW_SOURCE_SCIENCE"
STATUS_NAV="G3_NAVIGATIONAL_UTTERANCE_NO_SOURCE_CLAIM_VISUAL_QA_REQUIRED"
STATUS_SCI="G3_REPAIRED_SOURCE_CLAIM_REQUIRES_TWO_PASS_SCIENCE_NO_SEND"
ROOT="g3_prepass_source_gap_repair_v2"
SCI_ROOT="g3_prepass_source_science_reviews_v1"
MAX_FILES=20
NAV_TEXT={
    "finally, we will review the key concepts with summary points and conceptual questions.":
        "summary and review questions",
    "to conclude, consider these two review questions.":
        "in example 8.3",
}


def _nav_type(text:str,target:str)->bool:
    # Narrow, deterministic evidence for these source-pin derived sentences.
    # Do not broadly classify physics or numeric claims as transitions.
    normalized_target=" ".join(target.strip().lower().split())
    return NAV_TEXT.get(" ".join(text.strip().lower().split())) in (
        normalized_target, "in example 8.3"
    ) and (normalized_target.startswith("summary and review questions")
           or "in example 8.3" in normalized_target)


def _missing(*,spec:dict,original_root:Path,file:Path):
    worklist_root=Path(original_root).absolute()
    need(file.is_file() and not file.is_symlink()
         and file.parent==worklist_root/spec["section"],
         "Only original immutable publisher worklists are allowed")
    packet,request=_verified_packet(spec=spec,worklist=file)
    source_sha=_sha(file)
    missing=[]
    for row in packet["publisher_quote_worklist"]:
        old=_one_unit(spec=spec,packet=packet,request=request,
                      row=row,worklist_sha=source_sha)
        if old["science_review_job"] is None:
            missing.append((row,old))
    return packet,request,source_sha,missing


def _repair_unit(*,spec:dict,packet:dict,request:dict,
                 worklist_sha:str,row:dict,old:dict)->dict:
    spoken=next(x for x in request["original_utterances"]
                if x["utterance_id"]==row["utterance_id"])
    target=next(x for x in request["visible_targets"]
                if x["target_id"]==row["original_selected_target_id"])
    is_navigation=_nav_type(spoken["verbatim_text"],target["visible_text"])
    eligible_quotes=[]
    if not is_navigation:
        excerpt_job={
            "source_sha256":request["source_inputs_sha256"]["source.pdf"],
            "slides":[{
                "utterances":[{"spoken_text":spoken["verbatim_text"]}],
                "visual_targets":[{"visible_text":target["visible_text"]}],
            }],
        }
        old_quotes={
            (x["source_page"],x["publisher_quote_sha256"])
            for x in row["source_excerpt_candidates"]}
        candidates=_context(folder=Path(spec["source_folder"]),
                            job=excerpt_job,previous_quotes=old_quotes)
        for c in candidates[:4]:
            overlap=sorted(_terms(c["verbatim_source_quote"]) &
                           _terms(spoken["verbatim_text"]))
            need(len(overlap)>=2
                 and c["physically_witnessed_original_PDF"] is True
                 and c["source_semantic_support_verified"] is False,
                 "Original PDF context cannot certify scientific meaning")
            eligible_quotes.append({
                "source_page":c["source_page"],
                "publisher_quote_verbatim":c["verbatim_source_quote"],
                "publisher_quote_sha256":c["original_source_quote_sha256"],
                "quote_physically_present":True,
                "meaning_or_target_mapping_verified":False,
                "independent_scientific_QA_approved":False,
            })
    scope=hashlib.sha256(_canon({
        "new_recovery":"G3_PREPASS_SOURCE_GAP_CONTEXT_V2",
        "worklist_sha256":worklist_sha,
        "old_rejected_claim_sha256":packet["original_rejected_claim_sha256"],
        "old_rejected_capture_sha256":
            packet["original_rejected_raw_model_capture_sha256"],
        "source_inputs_sha256":request["source_inputs_sha256"],
        "utterance_sha256":row["verbatim_utterance_sha256"],
        "visual_target_sha256":row["original_visible_text_sha256"],
        "source_quotes":eligible_quotes,
        "navigation_only":is_navigation,
    })).hexdigest()
    status=(STATUS_NAV if is_navigation else
            STATUS_SCI if eligible_quotes else
            "G3_SOURCE_GAP_STILL_UNSUPPORTED_NO_MODEL_SEND")
    job=None
    if eligible_quotes:
        # Build the existing validated one-unit academic job from the same
        # SOURCE-PINNED rejection; only new physically witnessed quotations
        # differ. Never edit the original worklist or its parent request.
        rerow=copy.deepcopy(row)
        rerow["source_excerpt_candidates"]=eligible_quotes
        proposal=_one_unit(spec=spec,packet=packet,request=request,
                           row=rerow,worklist_sha=worklist_sha)
        job=proposal["science_review_job"]
        need(job is not None
             and job["academic_approval"] is False
             and job["student_publication_authorized"] is False,
             "No automatic source-science approval")
        job.pop("g3_distinct_source_science_v1")
        job["g3_prepass_source_science_v1"]={
            "new_scope_sha256":scope,
            "original_rejected_claim_sha256":
                packet["original_rejected_claim_sha256"],
            "original_rejected_model_capture_sha256":
                packet["original_rejected_raw_model_capture_sha256"],
            "original_utterance_id":row["utterance_id"],
            "parent_no_quote_task_scope_sha256":old["scope_sha256"],
            "old_worklist_sha256":worklist_sha,
            "source_context_is_not_semantic_proof":True,
            "two_independent_passes_required":True,
            "student_publication_authorized":False,
        }
        need(review_instructions(job,mode="INITIAL_REVIEW")!=
             prompt_for_request(request)
             and len(request["original_utterances"])>1,
             "Cannot repeat original whole-slide browser request")
    return {
        "schema_version":2,"status":status,
        "scope_sha256":scope,
        "section":spec["section"],
        "original_slide":request["slide"],
        "original_utterance_id":row["utterance_id"],
        "original_narration_sha256":row["verbatim_utterance_sha256"],
        "original_visual_target_sha256":row["original_visible_text_sha256"],
        "original_rejected_claim_sha256":
            packet["original_rejected_claim_sha256"],
        "original_rejected_raw_model_capture_sha256":
            packet["original_rejected_raw_model_capture_sha256"],
        "original_request_sha256":request["request_sha256"],
        "original_worklist_sha256":worklist_sha,
        "source_worklist_sha256":worklist_sha,
        "original_source_inputs_sha256":request["source_inputs_sha256"],
        "navigation_only_no_physics_utterance":is_navigation,
        "rendered_visual_question_science_QA_required":True,
        "physically_witnessed_new_quote_count":len(eligible_quotes),
        "new_scientific_source_review_job":job,
        "publisher_quotes_are_semantic_proof":False,
        "original_model_rejection_promoted":False,
        "independent_scientific_QA_complete":False,
        "independent_visual_QA_complete":False,
        "independent_acoustic_video_QA_complete":False,
        "student_publication_authorized":False,
        "new_browser_sends":0,
        "paid_gemini_API_calls":0,
    }


def materialize(*,specs:list,worklist_root:Path,state_root:Path)->dict:
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "Source-gap recovery is not registered in the executable workflow")
    root=Path(state_root).absolute()
    original=Path(worklist_root).absolute()
    need(root.is_dir() and not root.is_symlink()
         and original.is_dir() and not original.is_symlink()
         and original.is_relative_to(root),
         "Missing separate persistent original G3 source worklists")
    items=[]
    for spec in specs:
        source_files=sorted((original/spec["section"]).glob("slide_*.json"))
        need(len(source_files)<=MAX_FILES,"Unbounded source-gap inventory")
        for file in source_files:
            packet,request,src_sha,missing=_missing(
                spec=spec,original_root=original,file=file)
            for row,old in missing:
                items.append(_repair_unit(
                    spec=spec,packet=packet,request=request,row=row,
                    old=old,worklist_sha=src_sha))
    output=root/ROOT
    need(not output.is_symlink(),"Unsafe source-gap recovery root")
    output.mkdir(exist_ok=True)
    for item in items:
        section=output/item["section"]
        need(not section.is_symlink(),"Unsafe original source subsection")
        section.mkdir(exist_ok=True)
        _write_once(section/(item["scope_sha256"]+".json"),item)
    return {
        "schema_version":2,
        "status":"G3_PREPASS_SOURCE_GAPS_CLASSIFIED_NO_PROVIDER_SEND",
        "original_insufficient_quote_statements":len(items),
        "navigation_only_with_visual_QA_pending":sum(
            x["status"]==STATUS_NAV for x in items),
        "genuine_source_derived_review_jobs":sum(
            x["status"]==STATUS_SCI for x in items),
        "genuine_source_still_unsupported":sum(
            "STILL_UNSUPPORTED" in x["status"] for x in items),
        "tasks":[{"section":x["section"],
                  "original_slide":x["original_slide"],
                  "original_utterance_id":x["original_utterance_id"],
                  "status":x["status"],
                  "scope_sha256":x["scope_sha256"],
                  "source_quotes":x["physically_witnessed_new_quote_count"]}
                 for x in items],
        "academic_source_acceptances_added":0,
        "new_browser_sends":0,
        "paid_gemini_API_calls":0,
        "student_publication_authorized":False,
    }


def pinned(*,spec:dict,state_root:Path,task_file:Path)->dict:
    state_root=Path(state_root).absolute()
    f=Path(task_file).absolute()
    need(f.parent==state_root/ROOT/spec["section"]
         and f.is_file() and not f.is_symlink(),
         "No existing immutable G3 prepass task")
    row=_read(f)
    original=state_root/"offline_source_quote_worklists_v2"/spec["section"]
    source_files=sorted(original.glob("slide_*.json"))
    matched=[]
    for source in source_files:
        packet,request,src_sha,missing=_missing(
            spec=spec,original_root=original.parent,file=source)
        for unit,old in missing:
            if unit["utterance_id"]==row.get("original_utterance_id"):
                expected=_repair_unit(
                    spec=spec,packet=packet,request=request,
                    worklist_sha=src_sha,row=unit,old=old)
                if expected["scope_sha256"]==row.get("scope_sha256"):
                    matched.append(expected)
    need(len(matched)==1 and row==matched[0]
         and f.read_bytes()==_canon(matched[0]),
         "Prepass source science task failed original PDF identity")
    return row
