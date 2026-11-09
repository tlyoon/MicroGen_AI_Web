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
import sys
import time
from pathlib import Path
from typing import Callable

from .rich_mapping_provider_readiness import (
    inspect_provider,choose_provider,ProviderNotReady)
from .rich_unresolved_model_queue import verify_queue,merge_response
from .rich_element_model_alignment import (
    RichMappingError,require,parse_response,sha_bytes)
from .rich_unresolved_model_queue import prompt_partial


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


def _real_transport(provider:str,prompt:str,port:int,wait_cap_s:int)->str:
    if provider=="gemini":
        from .series_gemini import _browser_request
        from .rich_element_model_alignment import complete_json_response
        return _browser_request(prompt,[],port=port,
            wait_cap_s=wait_cap_s,min_chars=110,
            accept_fn=complete_json_response)
    raise RichMappingError(
        "Gemini Selenium is the sole supported LLM generation route. "
        "ChatGPT and Gemini API fallback are disabled.")


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
    require(not claim.exists() and not claim.is_symlink(),
            "Original model job already claimed; reconcile before any retry")
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
    prompt=prompt_partial(pending)
    initial={
        "schema_version":1,
        "status":"MAY_HAVE_SUBMITTED_RECONCILE_BEFORE_RESEND",
        "provider":provider,
        "browser_debug_port":port,
        "slide":slide,
        "partial_request_sha256":pending["partial_request_sha256"],
        "source_inputs_sha256":manifest["source_inputs_sha256"],
        "requested_utterances":len(unsent),
        "prior_accepted_prose_links_protected":len(
            pending["accepted_prose_links_already_sha_verified_do_not_resend"]),
        "original_prompt_sha256":sha_bytes(prompt.encode("utf8")),
        "created_unix":round(time.time(),3),
        "model_response_captured":False,
        "paid_tts_authorized":False,
        "student_publication_authorized":False,
    }
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
        merged,audit=merge_response(
            source_folder=original,checkpoint=checkpoint,
            fallback_dir=fallback_dir,queue_folder=queue_folder,
            slide=slide,partial_response=proposed)
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
        }
        _update_claim(claim,final)
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
