"""Gemini Selenium is the sole generation route: finite, safe pre-Send recovery.

Retries here are ONLY for preparation known to precede the first Send
(client attach, mode check, fresh owned chat, upload, editor and visible
Send readiness). This module does not submit prompts, switch models/providers,
or permit a second Send after a browser click with unknown outcome.
"""
from __future__ import annotations

import sys
import time
from typing import Callable, TypeVar

MAX_PRESEND_RECOVERY_ATTEMPTS = 3
T = TypeVar("T")


class GeminiSeleniumTemporaryFailure(RuntimeError):
    """Finite Gemini browser recovery exhausted; no alternative LLM."""

    def __init__(self, message: str, *, attempts_used: int = 0,
                 failure_phase: str = "PRE_SEND"):
        super().__init__(message)
        self.gemini_prepare_attempts_used = attempts_used
        self.gemini_failure_phase = failure_phase
        self.gemini_send_boundary_entered = False


class GeminiSeleniumPreSendBlocked(GeminiSeleniumTemporaryFailure):
    """No click occurred; the exact owned-tab Send preflight failed."""


def presend_failure_code(error: BaseException) -> str:
    """Safe failure classification; never copy the prompt or browser page."""
    detail = (type(error).__name__ + " " + str(error)).casefold()
    if any(x in detail for x in ("login", "sign in", "authentication",
                                 "captcha", "challenge", "just a moment")):
        return "AUTHENTICATION_OR_BROWSER_VERIFICATION_REQUIRED"
    if any(x in detail for x in ("send control", "send button", "composer",
                                 "editor", "typing")):
        return "GEMINI_COMPOSER_OR_SEND_CONTROL_NOT_READY"
    if any(x in detail for x in ("mode", "picker", "flash", "pro")):
        return "GEMINI_MODEL_PICKER_NOT_READY"
    if any(x in detail for x in ("connection", "chromedriver", "browser", "tab")):
        return "GEMINI_BROWSER_OR_WEBDRIVER_NOT_READY"
    return "PRE_SEND_PREPARATION_FAILED_UNCLASSIFIED"


def temporary_failure_message(reason: str, *, may_have_submitted: bool) -> str:
    note = (
        "An earlier Send may have been accepted. Bounded observation of the "
        "owned Gemini tab is complete; inspect the SHA-bound attempt claim "
        "and any saved response quarantine. Do not resend this job."
        if may_have_submitted else
        "No Gemini model Send was established. Browser preparation or "
        "authentication failed before submission."
    )
    return (
        "[MicroGen] Gemini Selenium temporary failure. "
        "The generation procedure has STOPPED after bounded recovery. "
        + note + " No ChatGPT or Gemini API fallback will be attempted. "
        "Please retry only a demonstrably unsent/new authorized job once "
        "Gemini Selenium is working. "
        "Cause: " + reason[:240]
    )


def emit_temporary_failure(reason: str, *, may_have_submitted: bool) -> None:
    print(temporary_failure_message(
        reason, may_have_submitted=may_have_submitted), file=sys.stderr,
        flush=True)


def _nonretryable_presend(error: Exception) -> bool:
    # Never auto-work around identity/security issues, wrong source or rights.
    desc = (type(error).__name__ + ": " + str(error)).casefold()
    return any(term in desc for term in (
        "sign in", "login required", "authentication required",
        "browser verification", "just a moment", "challenge",
        "captcha", "source mismatch", "source changed", "unauthorized",
        "permission denied", "different source", "invalid source",
    ))


def prepare_with_bounded_retries(
    *, make_client: Callable[[], T], prepare_without_send: Callable[[T], None],
    dispose: Callable[[T], None],
    attempts: int = MAX_PRESEND_RECOVERY_ATTEMPTS,
    sleeper: Callable[[float], None] = time.sleep,
) -> T:
    """Return a prepared client; never repeat even one *possible* Send.

    Only a callback that does not click Send may be passed as prepare_without_send.
    Dispose failed owned clients before trying another clean preparation.
    All model submission and same-tab response capture are OUTSIDE this loop.
    """
    if type(attempts) is not int or not 1 <= attempts <= 3:
        raise ValueError("Bounded Gemini preparation limit must be 1-3")
    if not all(callable(x) for x in (
            make_client, prepare_without_send, dispose, sleeper)):
        raise ValueError("Required trustworthy Gemini preparation callbacks")
    last: Exception | None = None
    for index in range(attempts):
        client = None
        try:
            client = make_client()
            prepare_without_send(client)
            try:
                setattr(client, "_microgen_presend_attempts_used", index + 1)
            except (AttributeError, TypeError):
                pass
            return client
        except Exception as error:
            last = error
            if client is not None:
                try:
                    dispose(client)
                except Exception:
                    pass
            if _nonretryable_presend(error) or index + 1 == attempts:
                break
            sleeper(min(2.0, 0.5 * 2 ** index))
    used = index + 1
    code = presend_failure_code(last) if last else "UNKNOWN_PRE_SEND_FAILURE"
    raise GeminiSeleniumTemporaryFailure(
        "Gemini Selenium pre-Send preparation stopped after at most "
        f"{attempts} attempts; actually used={used}; cause={code}",
        attempts_used=used, failure_phase=code
    ) from last


def click_one_owned_gemini_send(driver, owned_handle: str) -> bool:
    """One normal Selenium click, NEVER a second Enter/JS/provider fallback.

    The caller owns the already prepared, source-claimed job and must observe
    only the same tab afterward. A click exception can mean submission, so it
    is treated as uncertain and must not be retried.
    """
    if (not owned_handle
            or driver.current_window_handle != owned_handle
            or not str(driver.current_url).startswith(
                "https://gemini.google.com/")):
        raise GeminiSeleniumPreSendBlocked(
            "Gemini source-owned browser tab changed before Send")
    from selenium.webdriver.common.by import By
    candidates = [
        item for item in driver.find_elements(
            By.CSS_SELECTOR, 'button[aria-label="Send message"]')
        if item.is_displayed() and item.is_enabled()
    ]
    if len(candidates) > 1:
        raise GeminiSeleniumPreSendBlocked(
            "Gemini exact visible Send control is not unique")
    if not candidates:
        # Current Angular Gemini may expose a valid exact Send control to
        # querySelectorAll while Selenium's legacy locator returns none.
        # This is ONE guarded DOM click, not an Enter/hidden-button bypass.
        try:
            return bool(driver.execute_script("""
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||
                                     e.getClientRects().length));
                const eligible=e=>{
                    if(!visible(e)||e.disabled||
                       e.getAttribute('aria-disabled')==='true')return false;
                    for(let node=e;node&&node.nodeType===1;node=node.parentElement){
                        const s=getComputedStyle(node);
                        if(s.display==='none'||s.visibility==='hidden'||
                           Number(s.opacity)<=0.01)return false;
                    }
                    return true;
                };
                const exact=[...document.querySelectorAll(
                    'button[aria-label="Send message"]')].filter(eligible);
                if(exact.length!==1)return false;
                exact[0].click();
                return true;
            """))
        except Exception:
            return False  # A DOM click may have submitted; no other attempt.
    # Never force-click hidden controls or send a synthetic Enter.
    # This is the only physical submit action in this production request.
    try:
        candidates[0].click()
    except Exception:
        return False  # Click may have succeeded: observe the SAME tab only.
    return True
