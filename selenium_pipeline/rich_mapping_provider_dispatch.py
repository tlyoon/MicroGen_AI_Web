"""One-shot source-grounded rich mapping dispatch with no duplicate model jobs.

Only an existing authenticated Gemini/ChatGPT UI may receive an original
unresolved-only request. An attempt receipt is durably written BEFORE sending.
A browser timeout or invalid reply is reconciliation-required, not permission
to resend through a second provider. New ChatGPT tabs are isolated to the
preconfigured Chrome debugging profile; user-owned tabs are not rewritten.

No paid API or TTS, no local LLM, no original PDF/author asset modifications,
no human/scientific/academic/student publication approval is conferred.
"""
from __future__ import annotations

import argparse
import json
import os
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


def _chatgpt_browser_once(prompt:str,*,port:int,wait_cap_s:int)->str:
    """Use the existing vendor client in a new owned tab, never guest mode."""
    from .series_gemini import _vendor_module
    from .rich_mapping_provider_readiness import inspect_provider
    health=inspect_provider("chatgpt",port)
    require(health["authenticated_ui_ready"],
            "Authenticated ChatGPT browser unavailable; do not send")
    vendor=_vendor_module()
    cache=Path(os.getenv("LOCALAPPDATA") or str(Path.home()/
               "AppData"/"Local"))/"Microvid"/"RichModelProposals"
    cache.mkdir(parents=True,exist_ok=True)
    cfg=vendor.Config(root=cache,debug_port=port,
                      use_persistent_chrome=True,
                      force_kill_chrome_to_free_port=False)
    client=vendor.ChatGPTSeleniumClient(cfg)
    owned=None
    previous=None
    try:
        client.start(ensure_chatgpt_on_launch=False)
        driver=client.driver
        require(driver is not None,"ChatGPT remote browser driver unavailable")
        previous=driver.current_window_handle
        driver.switch_to.new_window("tab")
        owned=driver.current_window_handle
        driver.get("https://chatgpt.com/")
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        WebDriverWait(driver,15).until(
            lambda d: bool(d.find_elements(By.CSS_SELECTOR,
                               "#prompt-textarea")))
        require(not any((x.text or "").strip().lower()=="log in"
                   for x in driver.find_elements(By.CSS_SELECTOR,"button")
                   if x.is_displayed()),
                "ChatGPT tab is guest; must not send model prompt")
        raw=client.send_prompt_and_copy_response(
            prompt,wait_cap=wait_cap_s)
        require(isinstance(raw,str) and bool(raw.strip()),
                "ChatGPT did not provide a complete copied response")
        return raw
    finally:
        try:
            if owned and client.driver:
                driver=client.driver
                if owned in driver.window_handles:
                    driver.switch_to.window(owned)
                    driver.close()  # Only tab opened by this request
                if previous in driver.window_handles:
                    driver.switch_to.window(previous)
        except Exception:
            pass
        try:
            # Do not call client.shutdown(): that may terminate the existing
            # authenticated Chrome instance rather than only our driver.
            if client.driver:
                client.driver.service.stop()
        except Exception:
            pass


def _real_transport(provider:str,prompt:str,port:int,wait_cap_s:int)->str:
    if provider=="gemini":
        from .series_gemini import _browser_request
        from .rich_element_model_alignment import complete_json_response
        return _browser_request(prompt,[],port=port,
            wait_cap_s=wait_cap_s,min_chars=110,
            accept_fn=complete_json_response)
    if provider=="chatgpt":
        return _chatgpt_browser_once(prompt,
            port=port,wait_cap_s=wait_cap_s)
    raise RichMappingError("Unsupported provider, no local LLM allowed")


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
              else [inspect_provider("gemini"),
                    inspect_provider("chatgpt")])
    selected=choose_provider(statuses)
    if selected["chosen_provider"] is None:
        return {"status":"NO_AUTHENTICATED_PROVIDER_READY_NO_SUBMISSION",
                "slide":slide,"model_submissions":0,
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
        call=transport or _real_transport
        response=call(provider,prompt,port,wait_cap_s)
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
    except Exception:
        # Preserve the original MAY_HAVE_SUBMITTED receipt, and any original
        # response bytes if captured; never auto-switch to ChatGPT or retry.
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
