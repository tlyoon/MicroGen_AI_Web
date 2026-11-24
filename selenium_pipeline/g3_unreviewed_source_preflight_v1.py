"""Source-only immutable G3 review readiness for untouched original slides.

The historical two-uncertain-Send breaker forbids new original whole-slide
Gemini browser dispatch. This preflight can still pin each untouched slide's
EXACT original textbook/slide/script/mapping and original visible/narrated
identities for later independently qualified source review.

No copied model reply, fabricated source quotation, academic acceptance,
Gemini browser/API Send, TTS, media publication or unbounded retry.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .g3_semantic_source_repair_v1 import _canon, _write_once, _read, need
from .g3_rich_mapping_auto_continuation_v71 import (
    prepare as prepare_owner, _inspect_one)
from .rich_element_model_alignment import request_for_slide
from .recovery_registry import lookup_mechanism

KIND="g3_unreviewed_source_preflight"
SIGNATURE="G3_UNTOUCHED_SLIDES_STALLED_BEHIND_TWO_HISTORICAL_UNKNOWN_SENDS"
MECHANISM="PIN_ORIGINAL_UNTOUCHED_SOURCE_TASKS_WITH_ZERO_MODEL_SENDS"
ROOT="g3_original_unreviewed_source_preflight_v1"
STATUS="G3_UNTOUCHED_ORIGINAL_SLIDE_SOURCE_PREPARED_NO_SEND"
MAX_ORIGINAL_SLIDES=60
MAX_NARRATIONS_PER_SLIDE=96
MAX_VISUAL_TARGETS_PER_SLIDE=192


def _original_task(*,spec:dict,slide:int,existing_owner:dict)->dict:
    need(type(slide) is int and 1<=slide<=existing_owner["original_slides"],
         "Original slide must exist in saved source mapping")
    folder=Path(spec["source_folder"]).absolute()
    checkpoint=Path(spec["checkpoint"]).absolute()
    review_root=Path(spec["review_root"]).absolute()
    status=_inspect_one(
        source_folder=folder,checkpoint=checkpoint,root=review_root,n=slide,
        reconcile=False)
    need(status["status"]=="ELIGIBLE_FRESH_SOURCE_REVIEW_NO_SEND_YET",
         "Original slide has claimed or existing model review; never replay")
    req=request_for_slide(source_folder=folder,checkpoint=checkpoint,
                          slide_number=slide)
    need(req["slide"]==slide
         and req["source_inputs_sha256"]==existing_owner["source_inputs_sha256"],
         "Original textbook slide/script fingerprint changed")
    units=req["original_utterances"]
    targets=req["visible_targets"]
    need(type(units) is list and 0<len(units)<=MAX_NARRATIONS_PER_SLIDE
         and type(targets) is list
         and 0<len(targets)<=MAX_VISUAL_TARGETS_PER_SLIDE,
         "Unbounded or empty original slide and script")
    source_inputs=req["source_inputs_sha256"]
    pinned_units=[{
        "original_utterance_id":u["utterance_id"],
        "original_spoken_text_sha256":
            hashlib.sha256(u["verbatim_text"].encode("utf8")).hexdigest(),
    } for u in units]
    pinned_visual=[{
        "original_target_id":t["target_id"],
        "original_target_kind":t["kind"],
        "original_visible_text_sha256":
            hashlib.sha256(t["visible_text"].encode("utf8")).hexdigest(),
    } for t in targets]
    need(len({u["original_utterance_id"] for u in pinned_units})==len(units)
         and len({t["original_target_id"] for t in pinned_visual})==len(targets),
         "Duplicate original G3 source mapping items")
    scope=hashlib.sha256(_canon({
        "schema_version":1,"status":STATUS,
        "section":spec["section"],"original_slide":slide,
        "source_inputs_sha256":source_inputs,
        "original_mapping_request_sha256":req["request_sha256"],
        "original_mapping_checkpoint_sha256":
            existing_owner["mapping_checkpoint_sha256"],
        "original_units":pinned_units,
        "original_visual_targets":pinned_visual,
    })).hexdigest()
    return {
        "schema_version":1,
        "status":STATUS,
        "scope_sha256":scope,
        "section":spec["section"],
        "original_slide":slide,
        "source_inputs_sha256":source_inputs,
        "original_mapping_checkpoint_sha256":
            existing_owner["mapping_checkpoint_sha256"],
        "original_mapping_request_sha256":req["request_sha256"],
        "original_utterances":pinned_units,
        "original_visible_targets":pinned_visual,
        "original_utterance_count":len(units),
        "original_visual_target_count":len(targets),
        "original_model_claim_observed":False,
        "existing_historical_request_replayed":False,
        "new_source_science_review_ready_without_fresh_health":False,
        "independent_scientific_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "independent_video_QA_complete":False,
        "student_publication_authorized":False,
        "new_browser_sends":0,
        "paid_gemini_API_calls":0,
    }


def materialize(*,specs:list,state_root:Path)->dict:
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "G3 original untouched-slide recovery not executable")
    root=Path(state_root).absolute()
    need(root.is_dir() and not root.is_symlink()
         and type(specs) is list and 1<=len(specs)<=6,
         "Original G3 source-only state is missing")
    tasks=[]
    for spec in specs:
        need(type(spec) is dict
             and all(k in spec for k in (
                 "section","source_folder","checkpoint","review_root"))
             and type(spec["section"]) is str
             and spec["section"].startswith("Serway_"),
             "Original subsection may not be substituted")
        owner=prepare_owner(
            source_folder=spec["source_folder"],
            checkpoint=spec["checkpoint"],review_root=spec["review_root"])
        count=owner["original_slides"]
        need(type(count) is int and 1<=count<=MAX_ORIGINAL_SLIDES,
             "Unbounded original publisher subsection slide count")
        for slide in range(1,count+1):
            status=_inspect_one(
                source_folder=Path(spec["source_folder"]).absolute(),
                checkpoint=Path(spec["checkpoint"]).absolute(),
                root=Path(spec["review_root"]).absolute(),
                n=slide,reconcile=False)
            if status["status"]!="ELIGIBLE_FRESH_SOURCE_REVIEW_NO_SEND_YET":
                continue
            tasks.append(_original_task(
                spec=spec,slide=slide,existing_owner=owner))
    output=root/ROOT
    need(not output.is_symlink(),"Redirected untouched original slide worklist")
    output.mkdir(exist_ok=True)
    for task in tasks:
        home=output/task["section"]
        need(not home.is_symlink(),"Redirected original source section")
        home.mkdir(exist_ok=True)
        _write_once(home/(task["scope_sha256"]+".json"),task)
    return {
        "schema_version":1,
        "status":"G3_ORIGINAL_UNREVIEWED_SLIDES_SOURCE_PINNED_NO_SEND",
        "original_untouched_slides_prepared":len(tasks),
        "section_counts":[{"section":s["section"],
                           "prepared_original_slides":sum(
                               t["section"]==s["section"] for t in tasks)}
                           for s in specs],
        "tasks":[{"section":x["section"],
                  "slide":x["original_slide"],
                  "scope_sha256":x["scope_sha256"],
                  "utterances":x["original_utterance_count"],
                  "visible_targets":x["original_visual_target_count"]}
                 for x in tasks],
        "original_science_approvals":0,
        "new_browser_sends":0,
        "paid_gemini_API_calls":0,
        "student_publication_authorized":False,
    }


def pinned(*,spec:dict,state_root:Path,task_file:Path)->dict:
    root=Path(state_root).absolute()
    file=Path(task_file).absolute()
    need(file.is_file() and not file.is_symlink()
         and file.parent==root/ROOT/spec["section"],
         "Not an original untouched slide review task")
    saved=_read(file)
    owner=prepare_owner(
        source_folder=spec["source_folder"],
        checkpoint=spec["checkpoint"],review_root=spec["review_root"])
    expected=_original_task(
        spec=spec,slide=saved["original_slide"],existing_owner=owner)
    need(expected==saved and file.read_bytes()==_canon(expected),
         "Original unreviewed slide source proof changed")
    return saved
