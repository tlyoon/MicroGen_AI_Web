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
    from .launch_gemini import ready
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
        use_persistent_chrome=True,existing_session_only=True,
        force_kill_chrome_to_free_port=False)
    with LocalInstanceLock(f"gemini_port_{port}",cache/"browser_locks"):
        if port==9225 and ready(port):
            from .gemini_existing_alternate_recovery import (
                enrolled_alternate_port_owned)
            if not enrolled_alternate_port_owned():
                raise AcademicGeminiPreSendBlocked(
                    "GEMINI_EXISTING_DEBUG_SESSION_UNAVAILABLE_NO_SEND")
        # Vendor used to launch a disposable Chrome when port disappeared.
        # Reopen only the previously initialized and authorized PRIMARY or
        # enrolled Account B profile through an exact registered no-Send
        # recovery. Neither route may create a new empty profile.
        if not ready(port):
            from .gemini_existing_primary_recovery import (
                recover_existing_primary_debug_session)
            from .gemini_existing_alternate_recovery import (
                recover_existing_alternate_debug_session)
            if not (recover_existing_primary_debug_session(port)
                    or recover_existing_alternate_debug_session(port)):
                raise AcademicGeminiPreSendBlocked(
                    "GEMINI_EXISTING_DEBUG_SESSION_UNAVAILABLE_NO_SEND")
        client=None
        try:
            client=vendor.GeminiSeleniumClient(config)
            client.start(ensure_gemini_on_launch=True)
            # The actual vendor-owned tab and NEW CHAT are both selected
            # with their original finite pre-Send picker/Thinking gates.
            # There is NO model prompt, file upload or submit operation.
            client.open_clean_gemini_chat()
            handle=getattr(client,"_automation_tab",None)
            observed_mode=configured_ui_mode()
            assert_owned_gemini_mode(client.driver,handle,mode=observed_mode,
                                     wait_seconds=4)
            level=None
            if browser_stage_needs_thinking(mode=observed_mode):
                level=configured_thinking_level()
                from .gemini_dynamic_task_router import task_policy,LEVELS
                academic_floor=task_policy("academic_review")["minimum_thinking"]
                if LEVELS.index(level)<LEVELS.index(academic_floor):
                    raise AcademicGeminiPreSendBlocked(
                        "GEMINI_ACADEMIC_THINKING_BELOW_REVIEW_FLOOR_NO_SEND")
                assert_owned_gemini_thinking_level(
                    client.driver,handle,level=level)
            if observed_mode!=mode:
                if (os.environ.get(
                        "MICROGEN_ACADEMIC_SOURCE_MODEL_REQUALIFICATION_PENDING")
                        != "1"):
                    raise AcademicGeminiPreSendBlocked(
                        "GEMINI_ACADEMIC_ALTERNATE_MODEL_NOT_SOURCE_QUALIFIED_NO_SEND")
                # A new model UI and checked HIGH reasoning are necessary
                # but not sufficient: the independent two-PDF response
                # capability is a distinct, original-source-bound gate.
                # Never permit original Pro source Sends to be reinterpreted.
                raise AcademicGeminiPreSendBlocked(
                    "GEMINI_ACADEMIC_ALTERNATE_AWAITS_NEW_TWO_PDF_PROOF_NO_SEND")
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
        except AcademicGeminiPreSendBlocked:
            raise
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
    """Try only enrolled, exact-verified owned profiles for the SAME model.

    A missing contractual model on Account A may be available on previously
    enrolled Account B. The finite normal presend recovery may reopen that
    one existing profile, but never create a profile, enter credentials,
    switch model family or trust the parent tab's stale Flash label.
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
                or first.failure_phase not in {
                    "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE",
                    "GEMINI_THINKING_CONTROL_UNAVAILABLE_OR_AMBIGUOUS",
                    "GEMINI_THINKING_LEVEL_UNAVAILABLE_NO_SEND",
                    "GEMINI_THINKING_SELECTION_UNVERIFIED_NO_SEND",
                    "GEMINI_EXISTING_DEBUG_SESSION_UNAVAILABLE_NO_SEND",
                }):
            raise
        # Avoid even inspecting an absent alternate unless an old, explicitly
        # enrolled Account B profile physically exists. Never create a new
        # profile as a side effect of choosing a fallback route.
        from .gemini_existing_alternate_recovery import (
            enrolled_alternate_profile_present)
        if not ready(ALT_PORT) and not enrolled_alternate_profile_present():
            raise
        if first.failure_phase!="GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE":
            from .recovery_registry import lookup_mechanism
            if first.failure_phase=="GEMINI_EXISTING_DEBUG_SESSION_UNAVAILABLE_NO_SEND":
                registered=lookup_mechanism(
                    "presend_capability_repair",
                    "PRIMARY_GEMINI_DEBUG_SESSION_DISAPPEARED_NO_SEND")
                if registered!=(
                    "VERIFY_ALREADY_RUNNING_ALTERNATE_WITHOUT_NEW_CHROME_NO_SEND"):
                    raise
            else:
                registered=lookup_mechanism(
                    "presend_capability_repair",
                    "EXACT_GEMINI_THINKING_CONTROL_UNAVAILABLE_NO_SEND")
                if registered!=(
                    "REVALIDATE_EXACT_MODEL_AND_THINKING_ON_OTHER_RUNNING_AUTHORIZED_PROFILE_NO_SEND"):
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
