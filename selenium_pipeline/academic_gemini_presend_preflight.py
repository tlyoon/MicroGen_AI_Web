"""No-Send Gemini model/capability preflight BEFORE academic review claims.

Used by the genuine changed-evidence source review queue. A source-bound
academic review job must not be globally claimed on a known unavailable
requested model. Only an OWNED browser tab which actually selects the
contracted model and Thinking level can pass. No prompt, files, API, Gemini
Send, TTS, or release. This handles the observed Hydrogen/Flash family drift
as a CAPABILITY issue rather than retrying model-picker DOM tricks.
"""
from __future__ import annotations

import os
from pathlib import Path

from .gemini_model import configured_ui_mode
from .gemini_stage_policy import browser_stage_needs_thinking
from .gemini_selenium_only_policy import presend_failure_code


class AcademicGeminiPreSendBlocked(ValueError):
    """Authenticated original Gemini model is not ready; no review claimed."""

    def __init__(self,reason: str):
        super().__init__(reason)
        self.failure_phase=reason


def inspect(*,port: int=9222) -> dict:
    if type(port) is not int or not 1<=port<=65535:
        raise AcademicGeminiPreSendBlocked("INVALID_GEMINI_DEBUG_PORT")
    from .series_gemini import _vendor_module
    from .three_pc_worker import LocalInstanceLock
    from .gemini_model import assert_owned_gemini_mode
    from .gemini_thinking import (
        configured_thinking_level,assert_owned_gemini_thinking_level)

    mode=configured_ui_mode()
    cache=Path(os.getenv("LOCALAPPDATA") or
               str(Path.home()/".cache"))/"Microvid"
    cache.mkdir(parents=True,exist_ok=True)
    vendor=_vendor_module()
    config=vendor.Config(
        root=cache,debug_port=port,
        use_persistent_chrome=True,force_kill_chrome_to_free_port=False)
    with LocalInstanceLock(f"gemini_port_{port}",cache/"browser_locks"):
        client=None
        try:
            client=vendor.GeminiSeleniumClient(config)
            client.start(ensure_gemini_on_launch=True)
            # The actual vendor-owned tab and NEW CHAT are both selected
            # with their original finite pre-Send picker/Thinking gates.
            # There is NO model prompt, file upload or submit operation.
            client.open_clean_gemini_chat()
            handle=getattr(client,"_automation_tab",None)
            assert_owned_gemini_mode(client.driver,handle,mode=mode,
                                     wait_seconds=4)
            level=None
            if browser_stage_needs_thinking(mode=mode):
                level=configured_thinking_level()
                assert_owned_gemini_thinking_level(
                    client.driver,handle,level=level)
            return {
                "status":"EXACT_OWNED_GEMINI_MODEL_AND_THINKING_READY_NO_SEND",
                "model_family":mode,
                "thinking_level":level,
                "gemini_requests_submitted":0,
                "files_uploaded":0,
                "model_prompt_typed":False,
                "academic_approval":False,
                "tts_authorized":False,
                "G2_approved":False,
                "student_publication_authorized":False,
            }
        except Exception as exc:
            # Safe normalized classes only. NEVER print browser source text,
            # user identifiers, prompts or arbitrary exception messages.
            phase=presend_failure_code(exc)
            raise AcademicGeminiPreSendBlocked(phase) from exc
        finally:
            if client is not None:
                try:
                    client.shutdown()
                except Exception:
                    pass


def select_ready_existing_session(*,primary_port: int=9222,
                                  allow_active_alternate: bool=True)->dict:
    """Try only already-running authorized profiles for EXACT same model.

    A missing contractual model on Account A may be available on the user's
    already-authenticated Account B. Never launch a login, switch to a
    different model family, or accept the parent tab's stale Flash label.
    The first *source-bound* model Send is still exclusively owned and
    independently checked by the existing per-job one-Send checkpoint.
    """
    from .launch_gemini import DEFAULT_PORT, ALT_PORT, ready
    try:
        evidence=inspect(port=primary_port)
        return {**evidence,"verified_port":primary_port,
                "alternate_account_used":False,
                "existing_profile_only":True}
    except AcademicGeminiPreSendBlocked as first:
        if (not allow_active_alternate or primary_port!=DEFAULT_PORT
                or first.failure_phase!=
                    "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE"
                or not ready(ALT_PORT)):
            raise
        try:
            second=inspect(port=ALT_PORT)
            return {**second,"verified_port":ALT_PORT,
                    "alternate_account_used":True,
                    "existing_profile_only":True}
        except AcademicGeminiPreSendBlocked as alternate:
            if alternate.failure_phase==(
                    "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE"):
                raise AcademicGeminiPreSendBlocked(
                    "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE"
                ) from alternate
            raise
