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
    if ("requested_gemini_model_not_available" in detail
            or "model_not_available_no_send" in detail):
        return "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE"
    if any(x in detail for x in ("mode", "picker", "flash", "pro",
                                 "thinking", "level")):
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
        "requested_gemini_model_not_available_no_send",
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


# Read-only, prompt-free metadata from the EXACT owned Gemini tab. This
# restores the legacy new-user-turn evidence while keeping ONE Send maximum.
_OWNED_SEND_METADATA_JS = """
const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
const users=new Set();
for(const s of ['user-query','[data-message-author-role="user"]','[class*="user-query"]'])
  for(const e of document.querySelectorAll(s)) if(visible(e)) users.add(e);
const models=[...document.querySelectorAll('model-response')].filter(visible);
const editor=[...document.querySelectorAll(
  'div.ql-editor[contenteditable="true"],[contenteditable="true"][role="textbox"],textarea'
)].find(visible);
const txt=editor?String(editor.value||editor.innerText||editor.textContent||''):'';
return {users:users.size,models:models.length,editor_length:txt.trim().length,
        route:location.pathname,origin:location.origin};
"""


def owned_gemini_send_baseline(driver, owned_handle: str) -> dict:
    """Strict read-only baseline before the single possible model Send."""
    if not owned_handle or driver.current_window_handle != owned_handle:
        raise GeminiSeleniumPreSendBlocked(
            "Gemini source-owned browser tab changed before Send")
    if not str(driver.current_url).startswith("https://gemini.google.com/"):
        raise GeminiSeleniumPreSendBlocked(
            "Gemini owned tab is not on its authenticated model origin")
    try:
        result = driver.execute_script(_OWNED_SEND_METADATA_JS)
    except Exception as error:
        raise GeminiSeleniumPreSendBlocked(
            "Gemini owned-tab send baseline could not be read") from error
    if (not isinstance(result, dict)
            or result.get("origin") != "https://gemini.google.com"
            or any(type(result.get(k)) is not int or result[k] < 0
                   for k in ("users", "models", "editor_length"))
            or not isinstance(result.get("route"), str)
            or result["editor_length"] == 0):
        raise GeminiSeleniumPreSendBlocked(
            "Gemini owned-tab send baseline missing or editor empty")
    return {
        "users": result["users"],
        "models": result["models"],
        "editor_length": result["editor_length"],
        "route": result["route"],
    }


def observe_gemini_send_registration(
    driver, owned_handle: str, baseline: dict, *,
    wait_s: float = 8.0, poll_s: float = 0.25,
    clock=None, sleep=None,
) -> dict:
    """Confirm newly registered Gemini user turn after ONE possible click.

    No submit, Enter, force click, clipboard read, new tab or browser switch.
    If not confirmed, preserve the ambiguous Send and observe response only.
    """
    if (not isinstance(baseline, dict)
            or any(type(baseline.get(x)) is not int
                   for x in ("users", "models", "editor_length"))
            or not isinstance(baseline.get("route"), str)
            or not (0.5 <= wait_s <= 15)
            or not (0 < poll_s <= 2)):
        raise ValueError("Trusted no-resend Gemini observation required")
    clock = clock or time.monotonic
    sleep = sleep or time.sleep
    end = clock() + wait_s
    observed = 0
    while True:
        try:
            if (driver.current_window_handle != owned_handle
                    or not str(driver.current_url).startswith(
                        "https://gemini.google.com/")):
                return {"status": "OWNED_GEMINI_TAB_CHANGED",
                        "registered": False}
            data = driver.execute_script(_OWNED_SEND_METADATA_JS)
            if (isinstance(data, dict)
                    and data.get("origin") == "https://gemini.google.com"
                    and all(type(data.get(k)) is int and data[k] >= 0
                            for k in ("users", "models", "editor_length"))
                    and isinstance(data.get("route"), str)):
                observed += 1
                cleared = data["editor_length"] <= max(
                    8, int(baseline["editor_length"] * 0.15))
                if cleared:
                    if data["users"] > baseline["users"]:
                        return {"status": "NEW_USER_TURN_AND_COMPOSER_CLEARED",
                                "registered": True}
                    if data["models"] > baseline["models"]:
                        return {"status": "NEW_MODEL_RESPONSE_AND_COMPOSER_CLEARED",
                                "registered": True}
                    if (baseline["route"] in ("/app", "/app/")
                            and data["route"] != baseline["route"]
                            and data["route"].startswith("/app/")):
                        return {"status": "NEW_CONVERSATION_ROUTE_AND_COMPOSER_CLEARED",
                                "registered": True}
        except Exception:
            pass
        remaining = end - clock()
        if remaining <= 0:
            return {"status": (
                "NO_POSITIVE_NEW_USER_TURN_AFTER_CLICK"
                if observed else "OWNED_GEMINI_TAB_OBSERVATION_UNAVAILABLE"),
                "registered": False}
        sleep(min(poll_s, remaining))
