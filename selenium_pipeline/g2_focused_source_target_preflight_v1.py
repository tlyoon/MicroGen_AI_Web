"""Immutable offline G2 focused-source target audit, before any new Send.

A physically witnessed textbook quote and a rendered slide target are not
proof that the target matches the narrator. Preserve original G2 claims and
existing accepted focused reviews. For new tasks, flag if the legacy chosen
visual element is not the first physically backed, source-ranked candidate.
No provider calls or academic acceptance occur here.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

from .ai_academic_web_review import build_review_job
from .figure_source_identity import _sha, require
from .pdf_text_source_span_witness import prove_source_quote_occurrence
from .recovery_registry import lookup_mechanism

KIND="g2_focused_source_target_preflight"
SIGNATURE="G2_DISTINCT_FOCUSED_SOURCE_TARGET_CAN_DIFFER_FROM_NARRATION_RANK"
MECHANISM="IMMUTABLY_WITNESS_ORIGINAL_SOURCE_AND_FLAG_TARGET_MISMATCH_NO_SEND"
ROOT="G2_FOCUSED_SOURCE_TARGET_PREFLIGHT_V1"
STATUS_MISMATCH="G2_FOCUSED_RENDERED_TARGET_RANK_MISMATCH_NO_SEND"
STATUS_READY="G2_FOCUSED_SOURCE_TARGET_READY_FOR_INDEPENDENT_QA_NO_SEND"
MAX_TARGETS=64


def _digest(data:dict)->str:
    return hashlib.sha256(json.dumps(
        data,sort_keys=True,ensure_ascii=False,separators=(",",":")
        ).encode("utf8")).hexdigest()


def stage(*,folder:Path,queue_root:Path,item:dict)->dict:
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "G2 focused source-target preflight missing from executable registry")
    folder,queue_root=Path(folder).absolute(),Path(queue_root).absolute()
    require(folder.is_dir() and queue_root.is_dir()
            and not folder.is_symlink() and not queue_root.is_symlink()
            and not queue_root.is_relative_to(folder),
            "Original source and external original academic queue required")
    require(type(item) is dict
            and item.get("status")==
                "DISTINCT_SINGLE_UTTERANCE_SOURCE_TASK_PREPARED_NO_SEND"
            and item.get("new_provider_requests")==0
            and item.get("old_send_replay_authorized") is False
            and item.get("student_publication_authorized") is False
            and item.get("focused_utterance_count")==1,
            "Only original source-focused zero-Send review plans accepted")
    job=item["job"]
    sha={name:_sha(folder/name) for name in
         ("source.pdf","slides.pdf","script.txt")}
    require(job["source_sha256"]==item["source_sha256"]==sha["source.pdf"]
            and job["slides_sha256"]==sha["slides.pdf"]
            and job["script_sha256"]==sha["script.txt"]
            and job["academic_approval"] is False
            and job["student_publication_authorized"] is False,
            "Original G2 source/slides/script fingerprint drift")
    original=build_review_job(folder=folder,slide_numbers=[item["slide"]])
    require(original["source_sha256"]==sha["source.pdf"]
            and original["slides_sha256"]==sha["slides.pdf"]
            and original["script_sha256"]==sha["script.txt"],
            "Original source-backed rendered slide changed")
    units=[x for x in original["slides"][0]["utterances"]
           if x["id"]==item["utterance_id"]]
    require(len(units)==1,"Original narration identity not unique")
    unit=units[0]
    focused=job["slides"][0]["utterances"][0]
    require(focused["id"]==unit["id"]
            and focused["spoken_text"]==unit["spoken_text"]
            and focused["spoken_sha256"]==unit["spoken_sha256"],
            "Focused narration cannot diverge from original slide")
    require(len(job["slides"][0]["visual_targets"])==1,
            "Focused task must select precisely one rendered visual target")
    chosen=job["slides"][0]["visual_targets"][0]
    all_targets={t["id"]:t for t in
                 original["slides"][0]["visual_targets"]
                 if t.get("bbox_pdf_pt") is not None}
    require(1<=len(all_targets)<=MAX_TARGETS
            and len(all_targets)==len(
                [t for t in original["slides"][0]["visual_targets"]
                 if t.get("bbox_pdf_pt") is not None]),
            "Duplicate or unbounded original rendered slide targets")
    ranked=[x for x in unit["ranked_candidates"] if x in all_targets]
    require(bool(ranked) and len(set(ranked))==len(ranked)
            and chosen["id"] in all_targets
            and chosen==all_targets[chosen["id"]],
            "Original focused visual selection lacks physical slide witness")
    rows=[{
        "original_target_id":id,
        "original_target_kind":all_targets[id]["kind"],
        "original_rendered_text":all_targets[id]["visible_text"],
        "original_rendered_sha256":hashlib.sha256(
            all_targets[id]["visible_text"].encode("utf8")).hexdigest(),
        "original_bbox_pdf_pt":all_targets[id]["bbox_pdf_pt"],
    } for id in ranked]
    focus=job["verified_source_quote_candidates_v1"]["utterances"]
    require(len(focus)==1
            and focus[0]["utterance_id"]==unit["id"]
            and focus[0]["spoken_sha256"]==unit["spoken_sha256"]
            and len(focus[0]["allowed_citations"])==1,
            "Only one exact physically witnessed original quotation allowed")
    quote=focus[0]["allowed_citations"][0]
    proof=prove_source_quote_occurrence(
        source_pdf=folder/"source.pdf",
        expected_sha256=sha["source.pdf"],page_number=quote["source_page"],
        verbatim_quote=quote["verbatim_source_quote"])
    require(proof["quote_sha256"]==quote["quote_sha256"]
            and proof["math_semantics_author_verified"] is False,
            "Textbook passage witness changed or claims science approval")
    old_claim=queue_root/f"slide_{item['slide']:03d}_initial_review_attempt_01_request"/"dispatch_attempted.claim"
    require(old_claim.is_file() and not old_claim.is_symlink()
            and _sha(old_claim)==item["original_claim_sha256"],
            "Original uncertain G2 Send claim changed before new task")
    aligned=(chosen["id"]==ranked[0])
    source_scope=_digest({
        "schema_version":1,"focused_scope":item["scope_sha256"],
        "source_inputs_sha256":sha,
        "original_claim_sha256":_sha(old_claim),
        "ranked_original_targets_sha256":_digest({"targets":rows}),
        "quote_sha256":quote["quote_sha256"],
        "legacy_target_id":chosen["id"]})
    record={
        "schema_version":1,
        "status":STATUS_READY if aligned else STATUS_MISMATCH,
        "scope_sha256":source_scope,
        "focused_task_scope_sha256":item["scope_sha256"],
        "original_source_inputs_sha256":sha,
        "original_historical_claim_sha256":_sha(old_claim),
        "original_slide":item["slide"],
        "original_utterance_id":unit["id"],
        "exact_original_narration":unit["spoken_text"],
        "original_spoken_sha256":unit["spoken_sha256"],
        "original_focused_selected_target_id":chosen["id"],
        "original_focused_selected_target_text":chosen["visible_text"],
        "first_physically_backed_ranked_target_id":ranked[0],
        "original_ranked_physically_backed_targets":rows,
        "focused_target_is_first_ranked_physical_candidate":aligned,
        "original_publisher_pdf_page":quote["source_page"],
        "exact_original_publisher_quote":quote["verbatim_source_quote"],
        "physically_witnessed_quote_sha256":proof["quote_sha256"],
        "publisher_quote_is_scientific_proof":False,
        "best_ranked_target_is_academically_verified":False,
        "original_G2_reviews_modified":False,
        "independent_academic_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "new_browser_sends":0,"new_paid_gemini_API_calls":0,
        "student_publication_authorized":False,
    }
    path=queue_root.parent/ROOT
    require(not path.is_symlink() and not path.is_relative_to(folder)
            and not path.is_relative_to(queue_root),
            "Redirected original source-only preflight directory")
    path.mkdir(exist_ok=True)
    dest=path/(source_scope+".json")
    require(not dest.is_symlink(),"Redirected G2 target preflight")
    body=json.dumps(record,sort_keys=True,ensure_ascii=False,
                    indent=2)+"\n"
    if dest.exists():
        require(dest.is_file() and dest.read_text("utf8")==body,
                "Original G2 source-target evidence changed after checkpoint")
    else:
        with dest.open("x",encoding="utf8") as f:
            f.write(body)
            f.flush();os.fsync(f.fileno())
    return {"status":record["status"],"scope_sha256":source_scope,
            "receipt":str(dest),
            "original_utterance_id":unit["id"],
            "original_slide":item["slide"],
            "legacy_target_id":chosen["id"],
            "first_physically_backed_ranked_target_id":ranked[0],
            "new_browser_sends":0,"new_paid_gemini_API_calls":0,
            "independent_academic_QA_complete":False,
            "student_publication_authorized":False}
