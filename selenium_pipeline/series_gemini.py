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
    with LocalInstanceLock(f"gemini_port_{port}",cache/"browser_locks"):
        client=vendor.GeminiSeleniumClient(cfg)
        try:
            client.start(ensure_gemini_on_launch=True)
            selected=os.getenv("MICROGEN_GEMINI_UI_MODE","flash").strip().lower()
            ensure_mode(port,selected)
            client.open_clean_gemini_chat()
            # The new conversation may reset the selected UI mode. Re-check
            # AFTER changing tabs/chat, before sending source attachments.
            from .gemini_model import browser_model_evidence
            observed=ensure_mode(port,selected)
            browser_model_evidence(
                observed, requested_mode=selected,
                requested_model_id=os.getenv(
                    "MICROGEN_LLM_MODEL","gemini-3.8-flash"))
            if attachments:
                client.upload_files(attachments)
            if not client.type_prompt_text(instruction,retries=3):
                raise SeriesBridgeError("Could not type Gemini storyboard instruction")
            # A live Dell-115 test showed Quill can need ~3 seconds to
            # reveal the *ordinary* Send control after a large CDP insert.
            # Do not override hidden UI or submit if still hidden.
            from .gemini_response_recovery import await_owned_gemini_send_visible
            await_owned_gemini_send_visible(
                client.driver,getattr(client,"_automation_tab",None),
                wait_s=10,poll_s=0.5)
            if not client.click_send_with_fallbacks(retries=3):
                raise SeriesBridgeError("Could not submit Gemini storyboard instruction")
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
                )
                # The strict capture may fail while the same Gemini tab is
                # STILL generating. Observe only that owned tab for a bounded
                # grace period; do not submit an additional model request.
                # Completed text must pass the same JSON acceptance function.
                if snapshot.get("generating"):
                    owned = getattr(client, "_automation_tab", None)
                    def observe_owned_reply():
                        current = latest_owned_response(client.driver, owned)
                        if (not current.get("generating") and
                                current.get("capture_status") != "unavailable"):
                            return response_snapshot_with_scoped_copy(
                                client.driver, owned, copy_response=verified_copy)
                        return current
                    recovered, snapshot = poll_existing_owned_response(
                        observe_owned_reply, accept_fn=(accept_fn or _looks_complete),
                        wait_s=45, poll_s=3)
                    if recovered is not None:
                        return recovered
                reason = (
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
                raise SeriesBridgeError(
                    "No stable complete Gemini JSON; untrusted response "
                    f"quarantined at {receipt['raw_path']}. "
                    "Use offline recover-candidate after verifying content; "
                    "do not automatically resubmit source files."
                ) from capture_error
            return response
        finally:
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
