"""Restart-safe G3 next-step task after two source-AI UNRESOLVED verdicts.

A saved textbook context candidate is only source text, not evidence that
the statement is scientifically true. Reconcile original independent model
replies, reject the previous irrelevant quote, physically witness a new
Example-specific source context, and stage a genuinely different 1-utterance
two-pass academic review. The production dispatcher can immediately advance
that task within its explicit one-run Send budget. No old claim is replayed.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from .g3_semantic_source_repair_v1 import _canon, _sha, _read, _write_once, need
from .g3_semantic_context_recovery_v2 import recover
from .g3_distinct_semantic_science_v1 import _pinned_task as _verify_original
from .pdf_text_source_span_witness import prove_source_quote_occurrence
from .ai_academic_web_review import review_instructions
from .recovery_registry import lookup_mechanism

KIND="g3_source_context_autoforward"
SIGNATURE="TWO_G3_SCIENCE_REVIEWERS_UNRESOLVED_BUT_NEW_PUBLISHER_CONTEXT_FOUND"
MECHANISM="BIND_CONTEXT_AND_OLD_DISPUTE_CREATE_DISTINCT_REVIEW_THEN_AUTO_ADVANCE"
READY="G3_DISTINCT_EXAMPLE_CONTEXT_SCIENCE_REVIEW_READY_NO_SEND"
TASK_ROOT="g3_distinct_example_context_tasks_v1"
REVIEW_ROOT="g3_distinct_example_context_reviews_v1"


def _source_context_for_original(*,spec:dict,state_root:Path,
                                 original_task:Path)->tuple[dict,dict]:
    state_root=Path(state_root).absolute()
    old=_verify_original(
        spec=spec,worklist_root=state_root/"offline_source_quote_worklists_v2",
        task_file=original_task)
    folder=state_root/"g3_distinct_semantic_science_reviews_v1"/old["scope_sha256"]
    need(folder.is_dir() and not folder.is_symlink(),
         "No independent G3 academic reviewer history")
    v3=recover(
        folder=Path(spec["source_folder"]),
        task=old,review_root=folder)
    saved=folder/"semantic_context_recovery_v3.json"
    need(saved.is_file() and not saved.is_symlink()
         and saved.read_bytes()==_canon(v3)
         and v3["status"]==
             "G3_BOTH_INDEPENDENT_SCIENCE_REVIEWERS_UNRESOLVED_SOURCE_REPAIR_V3"
         and v3["original_two_model_verdicts"]==["UNRESOLVED","UNRESOLVED"]
         and v3["new_distinct_recovery_action"]==
             "NEW_DISTINCT_EXAMPLE_CONTEXT_REVIEW_TASK_REQUIRED"
         and v3["original_source_task_scope_sha256"]==old["scope_sha256"]
         and v3["new_gemini_browser_sends"]==0
         and v3["student_publication_authorized"] is False,
         "No source-backed independent double-UNRESOLVED context")
    return old,v3


def _select_new_quotes(*,source_pdf:Path,source_sha:str,
                       parent:dict,evidence:dict)->list[dict]:
    """At most two neighboring publisher pages, distinct contiguous quotes."""
    candidates=evidence["source_context_alternative_candidates"]
    need(type(candidates) is list and 1<=len(candidates)<=16,
         "Unbounded source-derived textbook context")
    first=candidates[0]
    pages=sorted({c["source_page"] for c in candidates
                  if abs(c["source_page"]-first["source_page"])<=1},
                 key=lambda n:(abs(n-first["source_page"]),n))[:2]
    need(first["source_page"] in pages,"No primary source page")
    old={(c["source_page"],c["verbatim_source_quote"])
         for c in parent["exact_original_source_quote_candidates"]}
    selected=[]
    for page in pages:
        rows=[c for c in candidates if c["source_page"]==page]
        rows.sort(key=lambda c:(-c["source_lexical_score"],
                                c["original_source_quote_sha256"]))
        chosen=0
        for c in rows:
            quote=c["verbatim_source_quote"]
            if (page,quote) in old:
                continue
            proof=prove_source_quote_occurrence(
                source_pdf=source_pdf,expected_sha256=source_sha,
                page_number=page,verbatim_quote=quote)
            need(c.get("original_source_quote_sha256")==
                     hashlib.sha256(quote.encode("utf8")).hexdigest()
                 and c.get("witnessed_quote_sha256")==proof["quote_sha256"]
                 and c.get("physically_witnessed_original_PDF") is True
                 and c.get("source_semantic_support_verified") is False
                 and len(c.get("original_spoken_overlap",[]))>=2
                 and bool(c.get("rendered_target_overlap"))
                 and proof["math_semantics_author_verified"] is False,
                 "Context quote not from the original publisher/narration")
            selected.append({
                "source_page":page,
                "verbatim_source_quote":quote,
                "quote_sha256":proof["quote_sha256"],
            })
            chosen+=1
            if chosen>=2:
                break
    need(1<=len(selected)<=4
         and any(q["source_page"]==first["source_page"] for q in selected),
         "No independently verified new source-context evidence")
    return selected


def build(*,spec:dict,state_root:Path,original_task:Path)->dict:
    old,evidence=_source_context_for_original(
        spec=spec,state_root=state_root,original_task=original_task)
    original=old["science_review_job"]
    source=Path(spec["source_folder"]).absolute()
    need(all(_sha(source/f)==original[f.split(".")[0]+"_sha256"]
             for f in ("source.pdf","slides.pdf","script.txt")),
         "Original textbook/narration/slide changed")
    quotes=_select_new_quotes(
        source_pdf=source/"source.pdf",source_sha=original["source_sha256"],
        parent=old,evidence=evidence)
    job=copy.deepcopy(original)
    utterance=job["slides"][0]["utterances"][0]
    packet=job["verified_source_quote_candidates_v1"]
    need(len(packet["utterances"])==1
         and utterance["id"]==old["original_utterance_id"]
         and packet["utterances"][0]["utterance_id"]==utterance["id"],
         "Source context changed original spoken identity")
    packet["utterances"][0]["allowed_citations"]=quotes
    scope=hashlib.sha256(_canon({
        "schema":"G3_DISTINCT_CONTEXT_SOURCE_SCIENCE_20261124",
        "parent_scope":old["scope_sha256"],
        "previous_two_model_receipt_sha":evidence[
            "original_two_pass_receipt_sha256"],
        "context_evidence_sha":hashlib.sha256(_canon(evidence)).hexdigest(),
        "chosen_publisher_quotes":quotes,
        "source_sha":original["source_sha256"],
        "spoken_sha":utterance["spoken_sha256"],
    })).hexdigest()
    job.pop("g3_distinct_source_science_v1",None)
    job["g3_source_context_science_v1"]={
        "new_context_review_scope_sha256":scope,
        "parent_source_review_scope_sha256":old["scope_sha256"],
        "previous_two_model_verdicts":["UNRESOLVED","UNRESOLVED"],
        "parent_model_result_is_NOT_source_semantic_acceptance":True,
        "original_context_quote_was_mathematically_irrelevant":True,
        "publisher_context_receipt_sha256":
            hashlib.sha256(_canon(evidence)).hexdigest(),
        "candidate_quotations_do_not_prove_math":True,
        "independent_source_first_pass_and_challenge_required":True,
        "automatic_audited_G3_mapping_approval":False,
        "student_publication_authorized":False,
    }
    # Both review prompts must be new and distinct from original rejected
    # first/challenge source model tasks, never an old Send replay.
    old_job=old["science_review_job"]
    need(review_instructions(job,mode="INITIAL_REVIEW")!=
             review_instructions(old_job,mode="INITIAL_REVIEW")
         and review_instructions(job,mode="INDEPENDENT_CHALLENGE")!=
             review_instructions(old_job,mode="INDEPENDENT_CHALLENGE"),
         "Original rejected Gemini model prompt cannot be replayed")
    return {
        "schema_version":1,"status":READY,
        "scope_sha256":scope,
        "section":spec["section"],
        "original_utterance_id":utterance["id"],
        "parent_original_task_scope_sha256":old["scope_sha256"],
        "parent_double_unresolved_source_receipt_sha256":
            evidence["original_two_pass_receipt_sha256"],
        "parent_context_recovery_sha256":
            hashlib.sha256(_canon(evidence)).hexdigest(),
        "source_worklist_sha256":old["source_worklist_sha256"],
        "source_sha256":original["source_sha256"],
        "original_spoken_sha256":utterance["spoken_sha256"],
        "new_source_quote_count":len(quotes),
        "review_job":job,
        "old_source_review_prompts_replayed":False,
        "new_provider_requests":0,
        "new_paid_gemini_API_requests":0,
        "new_context_scientific_support_approved":False,
        "original_G3_semantic_mappings_promoted":0,
        "independent_acoustic_video_QA_complete":False,
        "student_publication_authorized":False,
    }


def stage(*,spec:dict,state_root:Path,original_task:Path)->tuple[Path,dict]:
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "Source-context continuation not registered for normal deployment")
    root=Path(state_root).absolute()
    task=build(spec=spec,state_root=root,original_task=original_task)
    home=root/TASK_ROOT/spec["section"]
    need(not home.is_symlink()
         and not home.is_relative_to(Path(spec["source_folder"]).absolute()),
         "Unsafe context review checkpoint")
    home.mkdir(parents=True,exist_ok=True)
    path=home/(task["scope_sha256"]+".json")
    _write_once(path,task)
    return path,task


def pinned(*,spec:dict,state_root:Path,task_file:Path)->dict:
    root=Path(state_root).absolute()
    f=Path(task_file).absolute()
    original_root=root/"g3_distinct_semantic_science_tasks_v1"/spec["section"]
    need(f.parent==root/TASK_ROOT/spec["section"]
         and f.is_file() and not f.is_symlink()
         and original_root.is_dir() and not original_root.is_symlink(),
         "Only existing genuine separate source-context task is admissible")
    candidate=_read(f)
    old_file=original_root/(candidate.get("parent_original_task_scope_sha256","")+".json")
    new=build(spec=spec,state_root=root,original_task=old_file)
    need(candidate==new and f.read_bytes()==_canon(new)
         and f.name==new["scope_sha256"]+".json",
         "Saved source-context review was modified or disconnected")
    return new
