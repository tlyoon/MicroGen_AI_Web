"""G3 original rendered review questions: physics source evidence, no acceptance.

A narration transition is not a physics claim, but the accompanying
rendered slide can contain independent physics questions. Recover each
real question from the original rendered slides.pdf, witness exact
relevant passages in the SAME original textbook source.pdf, and create
a separate immutable visual/scientific audit task. No model Send, no
change to originally rejected source mapping, and no academic acceptance.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

from .g3_prepass_source_gap_repair_v1 import (
    ROOT as PREPASS_ROOT, STATUS_NAV, pinned as pinned_transition)
from .g3_semantic_source_repair_v1 import (
    _verified_packet, _read, _sha, _canon, _write_once, need)
from .g3_semantic_context_recovery_v2 import _context
from .pdf_text_source_span_witness import prove_source_quote_occurrence
from .rich_element_model_alignment import request_for_slide
from .recovery_registry import lookup_mechanism

KIND="g3_original_visual_question_audit"
SIGNATURE="G3_NARRATION_TRANSITION_HIDE_RENDERED_SCIENTIFIC_REVIEW_QUESTIONS"
MECHANISM="EXTRACT_RENDERED_QUESTIONS_WITNESS_PUBLISHER_CONTEXT_AND_REQUIRE_SCIENCE_QA"
ROOT="g3_original_visual_question_source_audit_v1"
STATUS="G3_ORIGINAL_RENDERED_QUESTIONS_SOURCE_EVIDENCE_UNAPPROVED"
MAX_QUOTE=4
MAX_TASKS=24
_Q=re.compile(r"\s*1\s+(.*?)\s+2\s+(.*?)\s*\Z",re.S)


def _questions(target:str)->list[str]:
    need(type(target) is str and len(target)<=5000,
         "Invalid original rendered slide question text")
    m=_Q.fullmatch(target)
    if m is None:
        return []
    items=[x.strip() for x in m.groups()]
    need(len(items)==2 and all(len(v)>=45 and "?" in v for v in items),
         "Source-derived numbered review question text changed")
    return items


def _proof(*,folder:Path,source_sha:str,question:str)->list[dict]:
    # Validate original publisher source independently even when ZERO
    # matching quotes are returned. Otherwise a changed PDF could look
    # like simply insufficient support and conceal a source-drift error.
    source=Path(folder)/"source.pdf"
    need(source.is_file() and not source.is_symlink()
         and _sha(source)==source_sha,
         "Original textbook source drift before visual question evidence")
    # This is SOURCE-ONLY search evidence for a VISIBLE question. We
    # explicitly do not pretend it was the narrator's original utterance.
    review={
        "source_sha256":source_sha,
        "slides":[{
            "utterances":[{"spoken_text":question}],
            "visual_targets":[{"visible_text":question}],
        }],
    }
    found=_context(folder=folder,job=review,previous_quotes=set())
    selected=[]
    for c in found[:MAX_QUOTE]:
        proof=prove_source_quote_occurrence(
            source_pdf=folder/"source.pdf",expected_sha256=source_sha,
            page_number=c["source_page"],
            verbatim_quote=c["verbatim_source_quote"])
        need(c["witnessed_quote_sha256"]==proof["quote_sha256"]
             and proof["math_semantics_author_verified"] is False
             and c["physically_witnessed_original_PDF"] is True
             and c["source_semantic_support_verified"] is False,
             "A source snippet cannot prove the answer to a review question")
        selected.append({
            "original_publisher_page":c["source_page"],
            "exact_original_source_quote":c["verbatim_source_quote"],
            "quote_sha256":proof["quote_sha256"],
            "is_a_physical_source_witness":True,
            "is_a_verified_scientific_answer":False,
        })
    return selected


def _one(*,spec:dict,nav_task:dict,worklist_root:Path)->dict:
    scope=nav_task["scope_sha256"]
    folder=Path(spec["source_folder"]).absolute()
    worklist_dir=Path(worklist_root).absolute()/spec["section"]
    original=[]
    for file in sorted(worklist_dir.glob("slide_*.json")):
        p=_read(file)
        if (p["original_slide_number"]==nav_task["original_slide"]
            and any(x["utterance_id"]==nav_task["original_utterance_id"]
                    for x in p["publisher_quote_worklist"])):
            original.append(file)
    need(len(original)==1,"Original rejected source reply ambiguous")
    packet,request=_verified_packet(spec=spec,worklist=original[0])
    old=next(x for x in packet["publisher_quote_worklist"]
             if x["utterance_id"]==nav_task["original_utterance_id"])
    target=next(x for x in request["visible_targets"]
                if x["target_id"]==old["original_selected_target_id"])
    need(_sha(original[0])==nav_task["original_worklist_sha256"]
         and old["original_visible_text_sha256"]==
             hashlib.sha256(target["visible_text"].encode("utf8")).hexdigest()
         and nav_task["original_narration_sha256"]==
             old["verbatim_utterance_sha256"]
         and packet["original_rejected_claim_sha256"]==
             nav_task["original_rejected_claim_sha256"],
         "Original visual/source mapping or source-review capture changed")
    source_shas=request["source_inputs_sha256"]
    question_texts=_questions(target["visible_text"])
    questions=[]
    for i,text in enumerate(question_texts,1):
        selected=_proof(
            folder=folder,source_sha=source_shas["source.pdf"],
            question=text)
        questions.append({
            "original_question_number":i,
            "original_rendered_question":text,
            "original_rendered_question_sha256":
                hashlib.sha256(text.encode("utf8")).hexdigest(),
            "physically_witnessed_publisher_context":selected,
            "publisher_context_can_prove_answer":False,
            "independent_source_science_QA_required":True,
            "independent_rendered_visual_QA_required":True,
            "human_academic_approval":False,
        })
    context_kind=(
        "ORIGINAL_TWO_RENDERED_PHYSICS_QUESTIONS"
        if questions else "ORIGINAL_REVIEW_SECTION_TITLE_ONLY")
    new_scope=hashlib.sha256(_canon({
        "schema":"G3_RENDERED_VISUAL_QUESTION_WITNESS_V1",
        "original_navigation_scope_sha256":scope,
        "original_source_inputs_sha256":source_shas,
        "original_rejected_request_sha256":request["request_sha256"],
        "original_rejected_claim_sha256":
            packet["original_rejected_claim_sha256"],
        "original_selected_target_id":target["target_id"],
        "original_target_sha256":old["original_visible_text_sha256"],
        "questions":[x["original_rendered_question_sha256"]
                     for x in questions],
    })).hexdigest()
    return {
        "schema_version":1,
        "status":STATUS,
        "scope_sha256":new_scope,
        "section":spec["section"],
        "original_slide":request["slide"],
        "original_narration_transition_unit":nav_task["original_utterance_id"],
        "original_narration_is_no_physics_claim":True,
        "original_selected_visible_target_id":target["target_id"],
        "original_visible_target_sha256":old["original_visible_text_sha256"],
        "original_navigation_source_task_scope_sha256":scope,
        "original_source_inputs_sha256":source_shas,
        "original_source_worklist_sha256":_sha(original[0]),
        "original_rejected_model_claim_sha256":
            packet["original_rejected_claim_sha256"],
        "visual_content_kind":context_kind,
        "original_rendered_questions":questions,
        "rendered_scientific_questions_count":len(questions),
        "source_question_evidence_is_not_academic_approval":True,
        "original_G3_semantic_mapping_promoted":False,
        "source_scientific_QA_complete":False,
        "rendered_visual_QA_complete":False,
        "audio_QA_complete":False,
        "video_QA_complete":False,
        "student_publication_authorized":False,
        "new_provider_sends":0,
        "paid_gemini_API_calls":0,
    }


def materialize(*,specs:list,state_root:Path)->dict:
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "Original question source audit not in executable registry")
    root=Path(state_root).absolute()
    need(root.is_dir() and not root.is_symlink(),
         "Original G3 academic state required")
    outputs=[]
    for spec in specs:
        home=root/PREPASS_ROOT/spec["section"]
        if not home.exists():
            continue
        need(home.is_dir() and not home.is_symlink(),
             "Unsafe original narration transition folder")
        files=sorted(home.glob("*.json"))
        need(len(files)<=MAX_TASKS,"Unbounded narration audit")
        for file in files:
            task=_read(file)
            if task.get("status")!=STATUS_NAV:
                continue
            valid=pinned_transition(
                spec=spec,state_root=root,task_file=file)
            need(valid==task
                 and valid["independent_visual_QA_complete"] is False,
                 "Previously approved navigation cannot satisfy science review")
            item=_one(
                spec=spec,nav_task=task,
                worklist_root=root/"offline_source_quote_worklists_v2")
            output=root/ROOT/spec["section"]
            need(not output.is_symlink(),"Redirected visual question audit")
            output.mkdir(parents=True,exist_ok=True)
            _write_once(output/(item["scope_sha256"]+".json"),item)
            outputs.append(item)
    return {
        "schema_version":1,
        "status":"G3_RENDERED_QUESTION_SOURCE_WORKLISTS_STAGED_UNAPPROVED",
        "nav_slide_worklists":len(outputs),
        "rendered_scientific_questions":sum(
            len(v["original_rendered_questions"]) for v in outputs),
        "physically_witnessed_quote_candidates":sum(
            len(q["physically_witnessed_publisher_context"])
            for v in outputs for q in v["original_rendered_questions"]),
        "tasks":[{
            "section":v["section"],"slide":v["original_slide"],
            "scope_sha256":v["scope_sha256"],
            "visible_questions":v["rendered_scientific_questions_count"],
            "worklist_status":v["visual_content_kind"]}
            for v in outputs],
        "independent_scientific_QA_approved":0,
        "independent_visual_QA_approved":0,
        "new_provider_sends":0,
        "paid_gemini_API_calls":0,
        "student_publication_authorized":False,
    }
