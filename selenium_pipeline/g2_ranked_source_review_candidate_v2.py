"""Prepare a distinct, correctly ranked G2 scientific review INPUT, no Send.

The legacy focused selector chooses the first eligible rendered element by
PDF traversal order, which can be a chapter heading instead of the physical
quantity being narrated. Preserve all previously reviewed V1 responses and
the original uncertain whole-slide requests. Pin the top physically verified
ranked rendered target in a NEW, SHA-distinct V2 candidate. Independent
scientific review, fresh provider health, a new legal finite budget and an
owned Selenium-only transport remain required in a separate later stage.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

from .ai_academic_web_review import build_review_job,review_instructions
from .figure_source_identity import _sha,require
from .g2_focused_source_target_preflight_v1 import (
    ROOT as V1_ROOT, STATUS_MISMATCH, stage as witness_original)
from .recovery_registry import lookup_mechanism

KIND="g2_ranked_source_review_candidate"
SIGNATURE="G2_LEGACY_TITLE_TARGET_MISMATCH_NEEDS_NEW_PHYSICAL_TARGET_REVIEW_INPUT"
MECHANISM="PIN_SEPARATE_RANKED_SOURCE_REVIEW_JOB_WITHOUT_REPLAY_OR_APPROVAL"
ROOT="G2_RANKED_SOURCE_REVIEW_CANDIDATES_V2"
STATUS="G2_RANKED_SOURCE_SCIENCE_INPUT_STAGED_UNAPPROVED_NO_SEND"
MAX_JOB=50000


def _canonical(data:dict)->bytes:
    return (json.dumps(data,ensure_ascii=False,sort_keys=True,
                       separators=(",",":"),allow_nan=False)+"\n").encode("utf8")


def _digest(data:dict)->str:
    return hashlib.sha256(_canonical(data)).hexdigest()


def stage(*,folder:Path,queue_root:Path,
          item:dict,source_preflight:dict)->dict:
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "Correctly ranked G2 science-input recovery not registered")
    folder,queue_root=Path(folder).absolute(),Path(queue_root).absolute()
    require(folder.is_dir() and queue_root.is_dir()
            and not folder.is_symlink() and not queue_root.is_symlink()
            and not queue_root.is_relative_to(folder)
            and item.get("status")==
                "DISTINCT_SINGLE_UTTERANCE_SOURCE_TASK_PREPARED_NO_SEND"
            and item.get("new_provider_requests")==0
            and item.get("old_send_replay_authorized") is False,
            "A genuine original one-utterance source review is required")
    source_preflight_file=Path(source_preflight["receipt"]).absolute()
    require(source_preflight_file.is_file()
            and not source_preflight_file.is_symlink()
            and source_preflight_file.parent==queue_root.parent/V1_ROOT
            and source_preflight_file.stem==source_preflight["scope_sha256"],
            "Original immutable target-mismatch preflight must be retained")
    old_source=witness_original(
        folder=folder,queue_root=queue_root,item=item)
    require(old_source==source_preflight
            and old_source["status"]==STATUS_MISMATCH,
            "Cannot turn an aligned or unverified V1 plan into a V2 repair")
    prior=json.loads(source_preflight_file.read_text("utf8"))
    require(prior["status"]==STATUS_MISMATCH
            and prior["scope_sha256"]==source_preflight["scope_sha256"]
            and prior["original_utterance_id"]==item["utterance_id"]
            and prior["original_slide"]==item["slide"],
            "G2 legacy source-target mismatch packet drift")
    shas={n:_sha(folder/n) for n in
          ("source.pdf","slides.pdf","script.txt")}
    require(prior["original_source_inputs_sha256"]==shas
            and shas["source.pdf"]==item["source_sha256"],
            "Original publisher/source slides changed")
    original=build_review_job(
        folder=folder,slide_numbers=[item["slide"]])
    require(original["source_sha256"]==shas["source.pdf"]
            and original["slides_sha256"]==shas["slides.pdf"]
            and original["script_sha256"]==shas["script.txt"],
            "Original source-backed slide target changed")
    target_id=prior["first_physically_backed_ranked_target_id"]
    originals=[t for t in original["slides"][0]["visual_targets"]
               if t["id"]==target_id]
    need_rows=[t for t in prior["original_ranked_physically_backed_targets"]
               if t["original_target_id"]==target_id]
    require(len(originals)==len(need_rows)==1
            and originals[0]["bbox_pdf_pt"] is not None
            and originals[0]["kind"]==need_rows[0]["original_target_kind"]
            and originals[0]["visible_text"]==need_rows[0]["original_rendered_text"]
            and originals[0]["bbox_pdf_pt"]==need_rows[0]["original_bbox_pdf_pt"],
            "Ranked G2 physical slide target identity is not original")
    legacy=item["job"]
    require(legacy["slides"][0]["visual_targets"][0]["id"]==
            prior["original_focused_selected_target_id"]
            and target_id!=prior["original_focused_selected_target_id"]
            and legacy["slides"][0]["utterances"][0]["id"]==
            prior["original_utterance_id"],
            "V2 claim must be distinct from original wrong target")
    job=copy.deepcopy(legacy)
    job["slides"][0]["visual_targets"]=[copy.deepcopy(originals[0])]
    job.pop("focused_source_review_v1",None)
    source_scope=_digest({
        "schema_version":2,"kind":"G2_DISTINCT_RANKED_SOURCE_SCIENCE_V2",
        "source":shas,"legacy_focused_scope":item["scope_sha256"],
        "original_claim_sha256":item["original_claim_sha256"],
        "preflight_scope":prior["scope_sha256"],
        "utterance_id":item["utterance_id"],
        "corrected_original_target_id":target_id,
        "original_target_text_sha256":need_rows[0]["original_rendered_sha256"],
        "original_quote_sha256":prior["physically_witnessed_quote_sha256"]})
    job["focused_source_review_v2"]={
        "status":"NEW_RANKED_PHYSICAL_TARGET_SOURCE_REVIEW_INPUT_NO_SEND",
        "scope_sha256":source_scope,
        "legacy_focused_scope_sha256":item["scope_sha256"],
        "original_prior_wrong_target_id":prior[
            "original_focused_selected_target_id"],
        "new_physical_target_id":target_id,
        "original_uncertain_claim_sha256":item["original_claim_sha256"],
        "source_passage_is_academic_proof":False,
        "independent_scientific_two_pass_QA_required":True,
        "student_publication_authorized":False}
    first=review_instructions(job,mode="INITIAL_REVIEW")
    second=review_instructions(job,mode="INDEPENDENT_CHALLENGE")
    require(first!=second
            and first!=review_instructions(legacy,mode="INITIAL_REVIEW")
            and job["academic_approval"] is False
            and job["student_publication_authorized"] is False
            and len(_canonical(job))<=MAX_JOB,
            "New G2 ranked review must have distinct bounded unapproved prompts")
    packet={
        "schema_version":2,"status":STATUS,
        "scope_sha256":source_scope,
        "original_preflight_scope_sha256":prior["scope_sha256"],
        "original_preflight_file_sha256":_sha(source_preflight_file),
        "original_source_inputs_sha256":shas,
        "original_historical_uncertain_claim_sha256":item["original_claim_sha256"],
        "original_focused_wrong_target_scope_sha256":item["scope_sha256"],
        "original_slide":item["slide"],
        "original_utterance_id":item["utterance_id"],
        "original_legacy_rendered_target_id":
            prior["original_focused_selected_target_id"],
        "corrected_ranked_physical_target_id":target_id,
        "new_initial_prompt_sha256":hashlib.sha256(first.encode()).hexdigest(),
        "new_challenge_prompt_sha256":hashlib.sha256(second.encode()).hexdigest(),
        "source_only_ranking_is_scientific_proof":False,
        "independent_browser_health_verified":False,
        "new_review_send_authorized":False,
        "independent_academic_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "student_publication_authorized":False,
        "new_browser_sends":0,"paid_gemini_API_calls":0,
        "source_science_review_job":job,
    }
    home=queue_root.parent/ROOT
    require(not home.is_symlink() and not home.is_relative_to(folder)
            and not home.is_relative_to(queue_root),
            "Redirected G2 ranked source-science task owner")
    home.mkdir(exist_ok=True)
    file=home/(source_scope+".json")
    require(not file.is_symlink(),"Linked G2 ranked source-input checkpoint")
    body=_canonical(packet)
    if file.exists():
        require(file.is_file() and file.read_bytes()==body,
                "Original G2 ranked source task changed on restart")
    else:
        with file.open("xb") as f:
            f.write(body);f.flush();os.fsync(f.fileno())
    return {
        "status":STATUS,"scope_sha256":source_scope,
        "receipt":str(file),"original_utterance_id":item["utterance_id"],
        "original_slide":item["slide"],
        "old_target_id":prior["original_focused_selected_target_id"],
        "new_target_id":target_id,
        "new_browser_sends":0,"paid_gemini_API_calls":0,
        "new_review_send_authorized":False,
        "independent_academic_QA_complete":False,
        "student_publication_authorized":False}
