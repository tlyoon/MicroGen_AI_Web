"""Gemini Selenium-only original rich-mapping dispatch with durable one-Send.

An authenticated Gemini browser is the sole LLM route. The normal Gemini
transport performs bounded pre-Send preparation and same-owned-tab response
recovery. Any unknown post-Send outcome is never replayed. No ChatGPT or
Gemini API fallback, scientific self-approval, or student publication.
"""
from __future__ import annotations

import argparse
import json
import os
import threading
import sys
import time
from pathlib import Path
from typing import Callable

from .rich_mapping_provider_readiness import (
    inspect_provider,choose_provider,ProviderNotReady)
from .rich_unresolved_model_queue import verify_queue,merge_response
from .rich_element_model_alignment import (
    RichMappingError,require,parse_response,sha_bytes,stable_hash)
from .rich_unresolved_model_queue import prompt_partial
from .academic_source_microbatch import claimed_original_source_units


def _write_new(path:Path,payload:dict)->None:
    require(not path.exists() and not path.is_symlink()
            and path.parent.is_dir() and not path.parent.is_symlink(),
            "Cannot replace an existing source-bound job receipt")
    with path.open("x",encoding="utf8") as stream:
        json.dump(payload,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _update_claim(path:Path,payload:dict)->None:
    # Only an already created, owned single-job claim can be updated.
    require(path.is_file() and not path.is_symlink(),
            "Model request claim disappeared after submitting")
    pending=path.with_suffix(".pending.json")
    _write_new(pending,payload)
    os.replace(pending,path)


def _global_slide_claim(*, source_sha256: str, slide: int,
                        source_folder: Path, queue_folder: Path) -> Path:
    """Source-global one-Send identity across ALL attempt folders and runs.

    Academic source claims already use a global original-unit index. Rich
    source/figure mapping previously protected only a caller-owned directory;
    changing --attempt-root could silently resubmit the same original units.
    The permanent source-SHA+slide claim is placed in the machine's canonical
    Windows checkpoint root, not under any caller-controlled attempt folder.
    A newly edited script with the same publisher source does NOT bypass an
    original source slide claim; it requires distinct provenance review.
    """
    require(isinstance(source_sha256,str) and len(source_sha256)==64
            and all(c in "0123456789abcdef" for c in source_sha256)
            and type(slide) is int and 1<=slide<=500,
            "Untrusted original publisher SHA or slide identity")
    local=Path(os.environ.get("LOCALAPPDATA")
               or (Path.home()/"AppData"/"Local")).absolute()
    root=local/"MicroGen_AI_Web_Checkpoints"
    shared=root/".microgen_rich_mapping_once"
    per_source=shared/source_sha256
    for folder in (local,root,shared,per_source):
        require(not folder.is_symlink()
                and (not folder.exists() or folder.is_dir()),
                "Unsafe global original-slide claim index")
    require(not per_source.is_relative_to(source_folder)
            and not source_folder.is_relative_to(per_source)
            and not per_source.is_relative_to(queue_folder)
            and not queue_folder.is_relative_to(per_source),
            "Global original-source claim cannot overlap source or frozen queue")
    return per_source/f"slide_{slide:03d}.once.json"


_RICH_MAPPING_ENV_LOCK = threading.RLock()


def _real_transport(provider:str,prompt:str,port:int,wait_cap_s:int,
                    *,accept_fn=None)->str:
    if provider!="gemini":
        raise RichMappingError(
            "Gemini Selenium is the sole supported LLM generation route. "
            "ChatGPT and Gemini API fallback are disabled.")
    from .series_gemini import _browser_request
    from .rich_element_model_alignment import complete_json_response
    # A source-free transport canary may supply its OWN exact JSON acceptor,
    # but it shares every production rich model/Thinking/owned-tab guard.
    if accept_fn is not None and not callable(accept_fn):
        raise RichMappingError("Only a callable bounded response validator")
    # This is the NORMAL rich visual-mapping stage, distinct from strict
    # original academic-review and cheap figure-caption stages. The
    # existing owned-tab adaptive family policy is allowed to select a
    # POSITIVELY OBSERVED Pro family + independently verified Medium when
    # preferred Flash is NOT in the actual authenticated Gemini model menu.
    # Never guess a family from its order or use Flash-Lite for rich math.
    # Restore caller environment, including any in-worker adaptive route,
    # so another job cannot inherit a stale model picker preference.
    names=(
        "MICROGEN_ACTIVE_GENERATION_STAGE",
        "MICROGEN_GEMINI_THINKING_LEVEL",
        "MICROGEN_GEMINI_UI_MODE",
        "MICROGEN_LLM_MODEL",
        "MICROGEN_MODEL_ROUTE_REASON",
        "MICROGEN_MODEL_ROUTE_REQUESTED",
        "MICROGEN_MODEL_ROUTE_OFFERED",
    )
    # Browser stages communicate their verified picker through environment.
    # The owned browser port lock alone starts too late: protect this entire
    # stage-environment lifetime against concurrent rich-mapping threads.
    _RICH_MAPPING_ENV_LOCK.acquire()
    old={name:os.environ.get(name) for name in names}
    try:
        os.environ["MICROGEN_ACTIVE_GENERATION_STAGE"]="rich_mapping"
        # An inherited Low setting from a caption/previous job is NOT an
        # explicit preference for this new reasoning task.
        os.environ["MICROGEN_GEMINI_THINKING_LEVEL"]="medium"
        # Rich scientific mapping ALWAYS starts Flash-first, even when an
        # earlier stage left a Flash-Lite or Pro preference in the worker.
        # Only owned-tab menu evidence can choose a different safe family.
        os.environ["MICROGEN_GEMINI_UI_MODE"]="flash"
        os.environ["MICROGEN_LLM_MODEL"]="gemini-3.8-flash"
        for name in ("MICROGEN_MODEL_ROUTE_REASON",
                     "MICROGEN_MODEL_ROUTE_REQUESTED",
                     "MICROGEN_MODEL_ROUTE_OFFERED"):
            os.environ.pop(name,None)
        response=_browser_request(
            prompt,[],port=port,wait_cap_s=wait_cap_s,
            min_chars=8 if accept_fn is not None else 110,
            accept_fn=accept_fn or complete_json_response)
        # The underlying _browser_request verifies the exact selected
        # family AND Thinking radio immediately before its one Send. UI
        # family is verified; opaque server model version remains UNKNOWN.
        if getattr(response,"gemini_new_user_turn_verified",False) is True:
            response.rich_ui_family_verified=os.environ.get(
                "MICROGEN_GEMINI_UI_MODE","flash")
            response.rich_thinking_verified=os.environ.get(
                "MICROGEN_GEMINI_THINKING_LEVEL","medium")
            response.rich_fallback_reason=os.environ.get(
                "MICROGEN_MODEL_ROUTE_REASON")
        return response
    finally:
        for name,prior in old.items():
            if prior is None:
                os.environ.pop(name,None)
            else:
                os.environ[name]=prior
        _RICH_MAPPING_ENV_LOCK.release()


def _academic_unclaimed_scope(
        *, pending: dict, source_sha256: str,
        checkpoint_parent: Path) -> tuple[dict,list[str]]:
    """Never send old academic original units via the different rich route.

    The shared source-global academic claim index is authoritative for
    already claimed utterances, including unknown/corrupt model responses.
    Excluded units stay NULL and UNRESOLVED, never silently pass G2.
    """
    claimed=claimed_original_source_units(
        source_sha256=source_sha256,
        checkpoint_parent=checkpoint_parent)
    all_units=pending["only_unresolved_original_utterances"]
    ids=[u["utterance_id"] for u in all_units]
    require(len(set(ids))==len(ids),
            "Original rich source unit identity repeated")
    excluded=[uid for uid in ids if uid in claimed]
    if not excluded:
        return pending,[]
    eligible=[unit for unit in all_units
              if unit["utterance_id"] not in claimed]
    # A newly SHA-bound sub-request has a different identity from the
    # immutable full original queue. The model sees ONLY eligible speech.
    scoped={**pending,
        "only_unresolved_original_utterances":eligible,
        "full_original_partial_request_sha256":
            pending["partial_request_sha256"],
        "consumed_academic_source_units_excluded_not_approved":excluded,
        "academic_claim_inventory_sha256":stable_hash(sorted(claimed)),
    }
    scoped.pop("partial_request_sha256")
    scoped["partial_request_sha256"]=stable_hash(scoped)
    return scoped,excluded


def _merge_eligible_answer(
        *, proposed: dict, scoped: dict, full: dict,
        consumed: list[str]) -> dict:
    """Re-expand a limited response without changing old claimed units."""
    choices=proposed.get("associations")
    eligible=scoped["only_unresolved_original_utterances"]
    require(type(choices) is list and len(choices)==len(eligible)
            and proposed.get("slide")==full["slide"]
            and proposed.get("partial_request_sha256")==
                scoped["partial_request_sha256"]
            and proposed.get("paid_tts_authorized") in (None,False)
            and proposed.get("student_publication_authorized") in (None,False),
            "Gemini response contains unclaimed/claimed unit or wrong source")
    expected=[u["utterance_id"] for u in eligible]
    require([x.get("utterance_id") for x in choices
             if type(x) is dict]==expected
            and len(expected)==len(choices),
            "Gemini response contains old claimed or reordered source units")
    if not consumed:
        return proposed
    accepted={x["utterance_id"]:x for x in choices}
    claimed=set(consumed)
    expanded=[]
    for unit in full["only_unresolved_original_utterances"]:
        uid=unit["utterance_id"]
        if uid in claimed:
            expanded.append({
                "utterance_id":uid,
                "target_id":None,
                "source_page":None,
                "source_quote":None,
                "reason":"Prior source-global academic claim consumed; "
                         "hold unresolved; never repeat a model submission",
                "needs_review":True,
            })
        else:
            require(uid in accepted, "Unclaimed original utterance omitted")
            expanded.append(accepted[uid])
    require(len(expanded)==len(full["only_unresolved_original_utterances"]),
            "Prior claimed source unit was dropped from review outcome")
    return {
        "slide":full["slide"],
        "partial_request_sha256":full["partial_request_sha256"],
        "associations":expanded,
        "paid_tts_authorized":False,
        "student_publication_authorized":False,
    }


def dispatch_one(*,source_folder:Path,checkpoint:Path,fallback_dir:Path,
                 queue_folder:Path,slide:int,attempt_root:Path,
                 wait_cap_s:int=95,
                 provider_statuses:list[dict]|None=None,
                 transport:Callable[[str,str,int,int],str]|None=None)->dict:
    """Exactly one verified outbound request or a durable no-send blocker."""
    original=Path(source_folder).absolute()
    queue_folder=Path(queue_folder).absolute()
    attempt_root=Path(attempt_root).absolute()
    require(type(slide) is int and wait_cap_s>=10 and wait_cap_s<=180,
            "Bounded original slide number/model wait required")
    require(attempt_root.is_dir() and not attempt_root.is_symlink()
            and not attempt_root.is_relative_to(original)
            and not original.is_relative_to(attempt_root)
            and not attempt_root.is_relative_to(queue_folder),
            "Model receipts must be external and separate from frozen queue")
    manifest,_,requests=verify_queue(
        source_folder=original,checkpoint=checkpoint,
        fallback_dir=fallback_dir,queue_folder=queue_folder)
    require(1<=slide<=len(requests),"Slide absent from original source")
    pending=requests[slide-1]
    unsent=pending["only_unresolved_original_utterances"]
    if not unsent:
        return {
            "status":"ALREADY_INDEPENDENTLY_SOURCE_VERIFIED_NO_MODEL_NEEDED",
            "slide":slide,"model_submissions":0,
            "student_publication_authorized":False,
        }
    claim=attempt_root/f"slide_{slide:03d}.one_submission.json"
    source_sha=manifest["source_inputs_sha256"]["source.pdf"]
    global_claim=_global_slide_claim(
        source_sha256=source_sha,
        slide=slide,source_folder=original,queue_folder=queue_folder)
    scoped,excluded=_academic_unclaimed_scope(
        pending=pending,source_sha256=source_sha,
        checkpoint_parent=global_claim.parent.parent.parent)
    eligible=scoped["only_unresolved_original_utterances"]
    if not eligible:
        return {
            "status":"ALL_UNRESOLVED_SLIDE_UNITS_PREVIOUSLY_ACADEMIC_CLAIMED_NO_SEND",
            "slide":slide,"model_submissions":0,
            "source_sha256":source_sha,
            "original_unresolved_utterances_held":len(unsent),
            "academic_claimed_units_excluded":len(excluded),
            "new_eligible_utterances":0,
            "prior_academic_approvals_inferred":False,
            "student_publication_authorized":False,
        }
    # Global identity is authoritative even if caller names another attempt
    # folder. Verify BOTH before touching Gemini/Chrome or claiming a job.
    require(not claim.exists() and not claim.is_symlink(),
            "Original model job already claimed; reconcile before any retry")
    require(not global_claim.exists() and not global_claim.is_symlink(),
            "Source-global original slide already claimed across attempt roots; "
            "no Gemini Send replay")
    statuses=(provider_statuses if provider_statuses is not None
              else [inspect_provider("gemini")])
    selected=choose_provider(statuses)
    if selected["chosen_provider"] is None:
        from .gemini_selenium_only_policy import temporary_failure_message
        message=temporary_failure_message(
            selected["status"],may_have_submitted=False)
        print(message,file=sys.stderr,flush=True)
        return {"status":"GEMINI_SELENIUM_TEMPORARY_FAILURE_STOP",
                "slide":slide,"model_submissions":0,
                "stop_message":message,
                "student_publication_authorized":False,
                "provider_readiness":statuses}
    provider=selected["chosen_provider"]
    inspected=next(x for x in statuses if x["provider"]==provider)
    port=inspected["debug_port"]
    require(type(port) is int and 9222<=port<=9323
            and inspected["authenticated_ui_ready"] is True
            and inspected["model_submission_performed"] is False,
            "Selected model provider is not a safe authenticated browser")
    # The original author/source request is recomputed identically. Before
    # claiming another one-Send, require capacity evidence for its REAL length,
    # not merely a prior 2k source-free test. No source text is logged here.
    prompt=prompt_partial(scoped)
    if transport is None:
        from .windows_new_source_browser_admission import (
            inspect_new_source_browser_admission)
        from .windows_rich_mapping_capacity_admission import (
            inspect_rich_mapping_capacity)
        try:
            admission=inspect_new_source_browser_admission()
        except (ValueError,OSError,RuntimeError) as error:
            return {
                "status":"GEMINI_RICH_MAPPING_ROUTE_EVIDENCE_INVALID_NO_SEND",
                "slide":slide,"model_submissions":0,
                "evidence_error_type":type(error).__name__,
                "new_eligible_utterances_preserved":len(eligible),
                "student_publication_authorized":False,
            }
        if admission.get("new_source_stage_send_eligible") is not True:
            return {
                "status":"GEMINI_RICH_MAPPING_ROUTE_UNVERIFIED_NO_SEND",
                "slide":slide,"model_submissions":0,
                "new_eligible_utterances_preserved":len(eligible),
                "route_admission":admission,
                "student_publication_authorized":False,
            }
        try:
            capacity=inspect_rich_mapping_capacity(
                prompt_characters=len(prompt),base_admission=admission)
        except (ValueError,OSError,RuntimeError,KeyError,TypeError) as error:
            return {
                "status":"GEMINI_RICH_MAPPING_CAPACITY_EVIDENCE_INVALID_NO_SEND",
                "slide":slide,"model_submissions":0,
                "evidence_error_type":type(error).__name__,
                "new_eligible_utterances_preserved":len(eligible),
                "student_publication_authorized":False,
            }
        if capacity.get("rich_model_send_eligible") is not True:
            return {
                "status":"GEMINI_RICH_MAPPING_CAPACITY_UNVERIFIED_NO_SEND",
                "slide":slide,"model_submissions":0,
                "new_eligible_utterances_preserved":len(eligible),
                "capacity_admission":capacity,
                "student_publication_authorized":False,
            }
    initial={
        "schema_version":1,
        "status":"MAY_HAVE_SUBMITTED_RECONCILE_BEFORE_RESEND",
        "provider":provider,
        "browser_debug_port":port,
        "slide":slide,
        "partial_request_sha256":scoped["partial_request_sha256"],
        "original_frozen_full_request_sha256":pending["partial_request_sha256"],
        "source_inputs_sha256":manifest["source_inputs_sha256"],
        "requested_utterances":len(eligible),
        "prior_academic_claimed_original_units_excluded":len(excluded),
        "academic_claimed_utterance_ids":excluded,
        "prior_academic_claims_not_approved_by_this_route":True,
        "prior_accepted_prose_links_protected":len(
            pending["accepted_prose_links_already_sha_verified_do_not_resend"]),
        "original_prompt_sha256":sha_bytes(prompt.encode("utf8")),
        "created_unix":round(time.time(),3),
        "model_response_captured":False,
        "paid_tts_authorized":False,
        "student_publication_authorized":False,
    }
    # The academic ledger may have progressed while Gemini readiness
    # was inspected. Recheck fresh eligible source IDs immediately before
    # the exclusive Send claim. Once reserved, unknown provider outcome
    # remains non-retryable; no academic claim can be overwritten here.
    latest_academic=claimed_original_source_units(
        source_sha256=source_sha,
        checkpoint_parent=global_claim.parent.parent.parent)
    require(all(u["utterance_id"] not in latest_academic for u in eligible),
            "A pending academic original source unit was claimed while "
            "provider preflight ran; stop without a Gemini Send")
    # Create the permanent, SOURCE-GLOBAL claim atomically before any
    # local receipt or potential Send. In a concurrent new attempt root only
    # ONE exclusive create can succeed; the loser must fail before transport.
    for directory in (global_claim.parent.parent.parent,
                      global_claim.parent.parent,global_claim.parent):
        require(not directory.is_symlink(),
                "Symlinked global source claim root prohibited")
        directory.mkdir(exist_ok=True)
        require(directory.is_dir() and not directory.is_symlink(),
                "Global original claim root became unsafe")
    try:
        _write_new(global_claim,{**initial,
            "global_original_source_slide_once":True,
            "global_claim_scope":
                "ORIGINAL_PUBLISHER_SHA_AND_SLIDE_ACROSS_ATTEMPT_ROOTS",
        })
    except FileExistsError as exc:
        # Concurrent second attempt must never get as far as transport.
        raise RichMappingError(
            "Source-global original slide already claimed by another "
            "attempt; never submit the same original request twice") from exc
    _write_new(claim,initial)
    # A failure of an already owned submission is NEVER silently retried,
    # even if the other provider is available and has an active composer.
    raw_out=attempt_root/f"slide_{slide:03d}.raw_model_response.txt"
    result_out=attempt_root/f"slide_{slide:03d}.merged_response.json"
    audit_out=attempt_root/f"slide_{slide:03d}.source_audit.json"
    try:
        if transport is None:
            # The only real route is Gemini via authenticated Selenium. This
            # exact claimed original job may be submitted at most once.
            response=_real_transport(provider,prompt,port,wait_cap_s)
        else:
            response=transport(provider,prompt,port,wait_cap_s)
        require(isinstance(response,str) and bool(response.strip()),
                "Model returned no captured source-bound response")
        _write_new(raw_out,{"status":"RAW_PROVIDER_COPY_UNVERIFIED",
                             "provider":provider,"text":response})
        proposed=parse_response(response)
        # The model was never shown the 39 previous academic claims (for the
        # current Serway source). Before shared original audit, fill those
        # slots with explicit NULL unresolved results, NEVER invented passes.
        expanded=_merge_eligible_answer(
            proposed=proposed,scoped=scoped,full=pending,consumed=excluded)
        merged,audit=merge_response(
            source_folder=original,checkpoint=checkpoint,
            fallback_dir=fallback_dir,queue_folder=queue_folder,
            slide=slide,partial_response=expanded)
        # Recompute after provider interaction; source/previous accepted
        # text cannot be altered without invalidating the entire job.
        verify_queue(source_folder=original,checkpoint=checkpoint,
                     fallback_dir=fallback_dir,queue_folder=queue_folder)
        _write_new(result_out,merged)
        _write_new(audit_out,audit)
        final={**initial,
            "status":"CAPTURED_SOURCE_VERIFIED_REVIEW_ONLY",
            "model_response_captured":True,
            "raw_model_response_sha256":sha_bytes(raw_out.read_bytes()),
            "merged_result_sha256":sha_bytes(result_out.read_bytes()),
            "source_audit_sha256":sha_bytes(audit_out.read_bytes()),
            "remaining_utterances_requiring_independent_review":
                audit["remaining_review_items"],
            "independently_supported_text_links":
                audit["text_source_and_author_anchors_passed"],
            "owned_gemini_selected_ui_family_verified":getattr(
                response,"rich_ui_family_verified",None),
            "owned_gemini_selected_thinking_level_verified":getattr(
                response,"rich_thinking_verified",None),
            "owned_gemini_verified_adaptive_route_reason":getattr(
                response,"rich_fallback_reason",None),
            "opaque_server_model_version_verified":False,
        }
        _update_claim(claim,final)
        _update_claim(global_claim,{**final,
            "global_original_source_slide_once":True,
            "global_claim_scope":
                "ORIGINAL_PUBLISHER_SHA_AND_SLIDE_ACROSS_ATTEMPT_ROOTS",
        })
        return final
    except Exception as error:
        # The one-Send claim was already durably written. A callback can fail
        # after a Gemini browser click, so do not reset/reissue it or change
        # model provider. The Selenium transport prints its own STOP reminder.
        if transport is not None:
            from .gemini_selenium_only_policy import emit_temporary_failure
            emit_temporary_failure(type(error).__name__,
                                   may_have_submitted=True)
        raise


def main(argv=None)->None:
    p=argparse.ArgumentParser(description=__doc__)
    for opt in ("source-folder","checkpoint","fallback-dir","queue-folder",
                "attempt-root"):
        p.add_argument("--"+opt,type=Path,required=True)
    p.add_argument("--slide",type=int,required=True)
    p.add_argument("--wait-s",type=int,default=95)
    args=p.parse_args(argv)
    report=dispatch_one(source_folder=args.source_folder,
         checkpoint=args.checkpoint,fallback_dir=args.fallback_dir,
         queue_folder=args.queue_folder,slide=args.slide,
         attempt_root=args.attempt_root,wait_cap_s=args.wait_s)
    print(json.dumps(report,indent=2))
if __name__=="__main__":
    main()
