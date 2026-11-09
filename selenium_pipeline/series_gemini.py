"""Opt-in Gemini web-UI storyboard candidate transport through existing Selenium.

Candidates undergo structural verification and still require scientific review.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Callable

from .series_bridge import SeriesBridgeError,check_selected_inputs,read_json,write_json_new
from .storyboard_gate import inspect_storyboard,canonical_sha256


def decode_storyboard_response(raw: str) -> dict:
    """Reject commentary, duplicate keys and truncated JSON."""
    if not isinstance(raw,str) or len(raw)>1_800_000:
        raise SeriesBridgeError("Gemini response missing or exceeds size cap")
    raw=raw.strip()
    fence=chr(96)*3
    if raw.startswith(fence):
        lines=raw.splitlines()
        if len(lines)<3 or lines[0].strip().lower() not in (
                fence+"json",fence):
            raise SeriesBridgeError("Expected a single JSON response")
        if lines[-1].strip()!=fence:
            raise SeriesBridgeError("JSON code fence is incomplete")
        raw="\n".join(lines[1:-1])
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise SeriesBridgeError(f"Duplicate Gemini JSON key: {key}")
            result[key]=value
        return result
    try:
        result=json.loads(raw,object_pairs_hook=unique)
    except json.JSONDecodeError as exc:
        raise SeriesBridgeError("Gemini did not return valid complete JSON") from exc
    if not isinstance(result,dict):
        raise SeriesBridgeError("Storyboard JSON must be an object")
    return result


def _looks_complete(raw: str) -> bool:
    try:
        decode_storyboard_response(raw)
        return True
    except SeriesBridgeError:
        return False


def _vendor_module():
    path=Path(__file__).resolve().parent/"vendor_template_v2"/"selenium.py"
    spec=importlib.util.spec_from_file_location("_microgen_series_gemini",path)
    if spec is None or spec.loader is None:
        raise SeriesBridgeError("Vendored Gemini Selenium client unavailable")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def _browser_request(instruction: str,attachments: list[Path],
                     *,port: int,wait_cap_s: int,
                     min_chars: int=200,accept_fn=None) -> str:
    from .three_pc_worker import LocalInstanceLock
    from .gemini_model import ensure_mode

    vendor=_vendor_module()
    cache=Path(os.getenv("LOCALAPPDATA") or (Path.home()/".cache"))/"Microvid"
    # Explicit text-only Gemini request mode: original-source evidence may be
    # embedded directly in a bounded prompt when document upload stalls.
    # No surrogate attachment, no unrelated Chrome tab, no new paid API.
    if type(attachments) is not list or any(not isinstance(p,Path) for p in attachments):
        raise SeriesBridgeError("Browser request attachments must be paths")
    request_root=Path(attachments[0]).parent if attachments else cache
    cfg=vendor.Config(
        root=request_root,debug_port=port,
        use_persistent_chrome=True,force_kill_chrome_to_free_port=False,
    )
    from .gemini_selenium_only_policy import (
        prepare_with_bounded_retries, emit_temporary_failure,
        click_one_owned_gemini_send)
    with LocalInstanceLock(f"gemini_port_{port}",cache/"browser_locks"):
        client=None
        send_boundary_entered=False
        try:
            def prepare_without_send(owned):
                owned.start(ensure_gemini_on_launch=True)
                selected=os.getenv("MICROGEN_GEMINI_UI_MODE","flash").strip().lower()
                ensure_mode(port,selected)
                owned.open_clean_gemini_chat()
                # New chats may reset Gemini's mode: independently recheck.
                from .gemini_model import browser_model_evidence
                observed=ensure_mode(port,selected)
                browser_model_evidence(
                    observed,requested_mode=selected,
                    requested_model_id=os.getenv(
                        "MICROGEN_LLM_MODEL","gemini-3.8-flash"))
                if attachments:
                    owned.upload_files(attachments)
                if not owned.type_prompt_text(instruction,retries=3):
                    raise SeriesBridgeError("Gemini editor did not accept prompt")
                from .gemini_response_recovery import await_owned_gemini_send_visible
                if not await_owned_gemini_send_visible(
                        owned.driver,getattr(owned,"_automation_tab",None),
                        wait_s=10,poll_s=0.5):
                    raise SeriesBridgeError(
                        "Gemini ordinary Send control not visible before submission")
            client=prepare_with_bounded_retries(
                make_client=lambda:vendor.GeminiSeleniumClient(cfg),
                prepare_without_send=prepare_without_send,
                dispose=lambda owned:owned.shutdown())
            # This is the ONE possible model Send; no keyboard/DOM/LLM
            # fallback clicks. An exception may mean delivery, so never
            # restart this source claim after crossing this boundary.
            send_boundary_entered=True
            clicked=click_one_owned_gemini_send(
                client.driver,getattr(client,"_automation_tab",None))
            if not clicked:
                print("[MicroGen] Gemini Selenium Send click outcome uncertain; "
                      "observing only the existing owned model tab without "
                      "another submission.",file=sys.stderr,flush=True)
            # Long Gemini replies may time out or raise before the strict
            # JSON acceptance callback runs. Capture even exception paths.
            capture_error = None
            response = ""
            try:
                response = vendor.capture_gemini_response_like_manual_copy(
                    client.driver,wait_cap=wait_cap_s,prefer_latex_doc=False,
                    min_chars=min_chars,retries=4,
                    accept_fn=(accept_fn or _looks_complete),
                )
            except (TimeoutError, RuntimeError) as exc:
                capture_error = exc
            if not response:
                from .gemini_response_recovery import (
                    latest_owned_response, response_snapshot_with_scoped_copy,
                    quarantine_snapshot, poll_existing_owned_response,
                )
                # This vendor helper verifies the Copy button belongs
                # to the latest MODEL response, not a user prompt.
                # Never use unrestricted clipboard or another Chrome tab.
                verified_copy = getattr(
                    vendor, "_copy_via_toolbar_copy_button", None
                )
                snapshot = response_snapshot_with_scoped_copy(
                    client.driver, getattr(client, "_automation_tab", None),
                    copy_response=verified_copy,
                    accept_fn=(accept_fn or _looks_complete),
                )
                # The strict capture may fail while the same Gemini tab is
                # STILL generating. Observe only that owned tab for a bounded
                # grace period; do not submit an additional model request.
                # Completed text must pass the same JSON acceptance function.
                if snapshot.get("capture_status") != "unavailable":
                    owned = getattr(client, "_automation_tab", None)
                    def observe_owned_reply():
                        current = latest_owned_response(client.driver, owned)
                        if (not current.get("generating") and
                                current.get("capture_status") != "unavailable"):
                            return response_snapshot_with_scoped_copy(
                                client.driver, owned, copy_response=verified_copy,
                                accept_fn=(accept_fn or _looks_complete))
                        return current
                    # Real original 8.4 diagnostic preserved the short
                    # non-generating "Gemini said" placeholder after 149 s.
                    # Give this owned tab a *short* no-resend observation
                    # window even when no Stop button is visible. Continuing
                    # generation retains the longer existing 45 s grace.
                    recovered, snapshot = poll_existing_owned_response(
                        observe_owned_reply, accept_fn=(accept_fn or _looks_complete),
                        wait_s=(45 if snapshot.get("generating") else 12),
                        poll_s=2)
                    if recovered is not None:
                        return recovered
                from .gemini_provider_ui_terminal_error import (
                    classify_visible_reply,
                )
                ui_error = classify_visible_reply(
                    text=snapshot.get("text", ""),
                    capture_status=snapshot.get("capture_status", ""),
                    generating=bool(snapshot.get("generating")))
                reason = (
                    "owned_gemini_ui_error_text" if
                    ui_error["known_gemini_ui_error_text_observed"] else
                    "strict_json_capture_exception" if capture_error is not None
                    else "strict_json_capture_timeout"
                )
                try:
                    receipt = quarantine_snapshot(snapshot, reason=reason)
                except OSError as exc:
                    raise SeriesBridgeError(
                        "Gemini JSON capture failed and recovery quarantine "
                        "could not be written; inspect the owned browser tab"
                    ) from exc
                if ui_error["known_gemini_ui_error_text_observed"]:
                    raise SeriesBridgeError(
                        "Gemini browser returned a visible owned-model UI error "
                        "without the requested JSON answer; captured and "
                        "quarantined. This is not proof of an API outage; "
                        "do not automatically resubmit."
                    ) from capture_error
                raise SeriesBridgeError(
                    "No stable complete Gemini JSON; untrusted response "
                    f"quarantined at {receipt['raw_path']}. "
                    "Use offline recover-candidate after verifying content; "
                    "do not automatically resubmit source files."
                ) from capture_error
            return response
        except Exception as error:
            emit_temporary_failure(
                type(error).__name__,
                may_have_submitted=send_boundary_entered)
            raise
        finally:
            if client is not None:
                try:
                    client.shutdown()
                except Exception:
                    pass


def request_storyboard_candidate(
    *,source_root: Path,source_pdf: Path,outline: dict,plan: dict,
    domain: str,part_id: str,authoring_folder: Path,
    candidate_path: Path,profile_file: Path | None=None,
    transport: Callable[[str,list[Path]],str] | None=None,
    chrome_port: int=9222,wait_cap_s: int=420,
) -> dict:
    """Explicit request, then strict structural gate; never auto-approves."""
    scan,profile,part=check_selected_inputs(
        source_root=source_root,source_pdf=source_pdf,
        outline=outline,plan=plan,domain=domain,part_id=part_id,
        profile_file=profile_file,
    )
    bundle=read_json(authoring_folder/"part_authoring_manifest.json")
    if bundle.get("status")!="prepared_not_generated" or (
            bundle.get("source_sha256")!=scan["source_sha256"] or
            bundle.get("plan_sha256")!=canonical_sha256(plan) or
            bundle.get("part_id")!=part_id):
        raise SeriesBridgeError("Prepared authoring bundle is stale")
    attached_pdf=authoring_folder/"source.pdf"
    attached_brief=authoring_folder/"storyboard_authoring_brief.txt"
    if not attached_pdf.is_file() or not attached_brief.is_file() or (
            attached_pdf.read_bytes()!=source_pdf.read_bytes()):
        raise SeriesBridgeError("Prepared source PDF/brief missing or stale")
    if (candidate_path.exists() or not candidate_path.parent.is_dir()
            or candidate_path.resolve().is_relative_to(source_root.resolve())):
        raise SeriesBridgeError("Candidate must be new and outside source tree")
    if not 60<=wait_cap_s<=1200 or not 1<=chrome_port<=65535:
        raise SeriesBridgeError("Invalid browser port or wait deadline")
    instruction=(
        f"Produce EXACTLY one joint source-grounded JSON storyboard for "
        f"Part {part['index']} of {part['part_count']}. Read attached complete "
        "authoring brief and source PDF. Preserve all planned scientific "
        "concepts, figures, slide IDs, visual elements and narration segments. "
        "Output one JSON object with no other commentary, no unsupported claims, "
        "no placeholders. This is a candidate requiring independent review."
    )
    call=transport or (lambda prompt,files:_browser_request(
        prompt,files,port=chrome_port,wait_cap_s=wait_cap_s
    ))
    obj=decode_storyboard_response(call(instruction,[attached_pdf,attached_brief]))
    report=inspect_storyboard(
        obj,plan,outline,profile,scan=scan,source_pdf=source_pdf,
    )
    write_json_new(candidate_path,obj)
    return {
        "status":"candidate_structurally_valid_scientific_review_required",
        "part_id":part_id,
        "storyboard_sha256":report["storyboard_sha256"],
        "structural_status":report["status"],
        "unverified":report["unverified"],
    }
