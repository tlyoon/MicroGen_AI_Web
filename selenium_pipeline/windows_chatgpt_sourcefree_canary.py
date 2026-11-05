"""Single-send, source-free ChatGPT Selenium transport diagnostic on Dell-115.

Requires explicit --live and a fresh LOCALAPPDATA checkpoint. Claim is fsynced
before any possible browser submission. Never retry a prior claim, send source
files, use paid API/TTS, or close pre-existing user tabs. The newly created
canary tab is kept for reconciliation if a response is not verified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time

PORT = 9223
WAIT_SECONDS = 90
SEND_BUTTON_CSS = (
    "button[data-testid='send-button'],"
    "button[aria-label='Send'],"
    "button[aria-label='Send prompt']"
)


def _local_root(path: Path) -> Path:
    base = Path(os.environ["LOCALAPPDATA"]).resolve(strict=True)
    root = Path(path).absolute()
    if (sys.platform != "win32" or root == base
            or not root.is_relative_to(base)
            or root.is_symlink() or root.parent.is_symlink()):
        raise ValueError("Use a fresh local Windows checkpoint, not a shared source")
    return root


def _create_json(path: Path, obj: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(obj, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _replace_json(path: Path, obj: dict) -> None:
    temp = path.with_suffix(".tmp")
    _create_json(temp, obj)
    os.replace(temp, path)


def expected_text(token: str) -> str:
    return "MICROGEN_CHATGPT_CANARY_" + token + "_OK"


def _real_browser_once(prompt: str, expected: str, timeout: int,
                       owned_draft_exact: str | None = None,
                       on_send_intent=None) -> dict:
    """Exactly one click on an owned tab; never overwrite an unrelated draft."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    opts = Options()
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9223")
    driver = webdriver.Chrome(options=opts)
    owned = None
    initial = None
    keep_for_reconciliation = True
    observed = {
        "outcome": "NO_VERIFIED_RESPONSE", "send_click_attempted": False,
        "user_turn_confirmed": False, "assistant_response_seen": False,
        "response_character_count": 0, "response_sha256": None,
    }
    try:
        initial = driver.current_window_handle
        driver.switch_to.new_window("tab")
        owned = driver.current_window_handle
        driver.get("https://chatgpt.com/")
        def composer(d):
            for css in ("#prompt-textarea", "[data-testid='composer-text-input']",
                        "div[contenteditable='true'][role='textbox']"):
                for el in d.find_elements(By.CSS_SELECTOR, css):
                    if el.is_displayed() and el.is_enabled():
                        return el
            return False
        ed = WebDriverWait(driver, 18).until(composer)
        login_buttons = driver.find_elements(By.CSS_SELECTOR, "button[data-testid='login-button']")
        if any(b.is_displayed() for b in login_buttons):
            observed["outcome"] = "LOGIN_REQUIRED_ON_NEW_TAB_NO_SEND"
            return observed
        if not str(driver.current_url).startswith("https://chatgpt.com/"):
            observed["outcome"] = "WRONG_DOMAIN_NO_SEND"
            return observed
        existing = driver.execute_script(
            "return (arguments[0].innerText || '').trim();", ed)
        if existing and existing != owned_draft_exact:
            observed["outcome"] = "COMPOSER_NOT_EMPTY_NO_SEND"
            return observed
        # Only a known exact self-authored diagnostic draft may be replaced.
        # The caller must explicitly supply the complete marker; no broad clear.
        # Current ChatGPT ProseMirror on Dell-115 ignores Selenium send_keys()
        # despite returning normally. Verified alternative: insertText on the
        # focused editable and read back the DOM before any send attempt.
        ed.click()
        driver.execute_script(
            "document.execCommand('selectAll',false,null);"
            "document.execCommand('insertText',false,arguments[0]);", prompt)
        current = driver.execute_script(
            "return (arguments[0].innerText || '').trim();", ed)
        if current != prompt:
            observed["outcome"] = "PROMPT_NOT_CONFIRMED_NO_SEND"
            return observed

        # No fallback Enter, no send retry: one click or an uncertain receipt.
        send = WebDriverWait(driver, 15).until(
            lambda d: next(
                (x for x in d.find_elements(By.CSS_SELECTOR, SEND_BUTTON_CSS)
                 if x.is_displayed() and x.is_enabled()), False))
        # Fsync the exact point of no return before one and only one click.
        if on_send_intent is not None:
            on_send_intent()
        observed["send_click_attempted"] = True
        send.click()
        end = time.monotonic() + timeout
        previous = None
        steady = 0
        while time.monotonic() < end:
            try:
                user = driver.find_elements(By.CSS_SELECTOR,
                    '[data-message-author-role="user"]')
                observed["user_turn_confirmed"] = any(
                    expected in (x.text or "") for x in user)
                assistants = driver.find_elements(By.CSS_SELECTOR,
                    '[data-message-author-role="assistant"]')
                messages = [(x.text or "").strip() for x in assistants
                            if (x.text or "").strip()]
                if messages:
                    value = messages[-1]
                    observed["assistant_response_seen"] = True
                    observed["response_character_count"] = len(value)
                    observed["response_sha256"] = hashlib.sha256(
                        value.encode("utf-8")).hexdigest()
                    if value == previous:
                        steady += 1
                    else:
                        previous, steady = value, 0
                    stop = any(
                        x.is_displayed() for x in driver.find_elements(
                            By.CSS_SELECTOR, 'button[data-testid="stop-button"]'))
                    if observed["user_turn_confirmed"] and steady >= 3 and not stop:
                        observed["outcome"] = (
                            "VALID_ATTRIBUTED_RESPONSE" if value == expected
                            else "RESPONSE_RETURNED_NONCONFORMING")
                        keep_for_reconciliation = False
                        return observed
            except Exception:
                pass
            time.sleep(1)
        observed["outcome"] = "TIMEOUT_RECONCILE_NO_RESEND"
        return observed
    finally:
        try:
            # Do not destroy uncertain evidence or close any pre-existing tab.
            if owned and not keep_for_reconciliation and owned in driver.window_handles:
                driver.switch_to.window(owned)
                driver.close()
                if initial in driver.window_handles:
                    driver.switch_to.window(initial)
        except Exception:
            pass
        try:
            driver.service.stop()  # Never driver.quit() on user Chrome profile
        except Exception:
            pass


def run(*, root: Path, live: bool = False, browser=None, readiness=None,
        timeout: int = WAIT_SECONDS, owned_draft_exact: str | None = None) -> dict:
    root = _local_root(root)
    if owned_draft_exact is not None:
        import re
        if (type(owned_draft_exact) is not str
                or not re.fullmatch(r"MICROGEN_EDITOR_TYPING_DIAGNOSTIC_[A-Z0-9]{4,32}",
                                    owned_draft_exact)):
            raise ValueError("Only exact self-authored editor diagnostics may be replaced")
    if timeout < 15 or timeout > 120:
        raise ValueError("Only bounded response waits are supported")
    claim, result = root / "chatgpt_canary_claim.json", root / "chatgpt_canary_result.json"
    intent = root / "chatgpt_send_click_intent.json"
    if claim.exists():
        if result.is_file():
            return {**json.loads(result.read_text(encoding="utf-8")),
                    "status": "EXISTING_CLAIM_REUSED_NO_NEW_SEND"}
        return {"status": "PRIOR_CLAIM_UNRESOLVED_NO_RESEND",
                "model_submissions_this_call": 0}
    if result.exists() or intent.exists():
        raise ValueError("Orphan result or send intent without an owned claim")
    if not live:
        return {"status": "DRY_RUN_NO_SUBMISSION", "model_submissions_this_call": 0}
    from .rich_mapping_provider_readiness import inspect_provider
    check = readiness or (lambda: inspect_provider("chatgpt", PORT))
    health = check()
    if (health.get("provider") != "chatgpt"
            or health.get("debug_port") != PORT
            or health.get("authenticated_ui_ready") is not True
            or health.get("status") != "AUTHENTICATED_COMPOSER_READY"):
        return {"status": "CHATGPT_NOT_AUTHENTICATED_NO_SEND",
                "model_submissions_this_call": 0}
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink() or claim.exists():
        raise ValueError("Checkpoint changed during preflight")
    token = secrets.token_hex(6).upper()
    expected = expected_text(token)
    prompt = ("This is a new, source-free MicroGen Selenium transport check. "
              "Reply with exactly this single line and nothing else: " + expected)
    initial = {
        "schema_version": 1, "status": "MAY_HAVE_SUBMITTED_NO_RESEND",
        "provider": "chatgpt", "debug_port": PORT,
        "expected_response_marker": expected,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "claim_created_unix": time.time(),
        "one_send_only": True, "source_files_attached": False,
        "known_owned_draft_replacement": owned_draft_exact is not None,
        "api_generation_or_tts_billed": False,
        "student_publication_authorized": False,
    }
    _create_json(claim, initial)
    final = {**initial, "status": "CANARY_TERMINAL",
             "outcome": "NO_VERIFIED_RESPONSE", "error_type": None,
             "model_submissions_this_call": 1}
    try:
        if browser is not None:
            observation = browser(prompt, expected, timeout)
        else:
            def pre_click():
                _create_json(intent, {
                    "schema_version": 1, "status": "SEND_CLICK_INTENT_NOT_DELIVERY_PROOF",
                    "provider": "chatgpt", "debug_port": PORT,
                    "expected_response_marker": expected,
                    "one_click_only": True, "created_unix": time.time(),
                })
            observation = _real_browser_once(
                prompt, expected, timeout, owned_draft_exact=owned_draft_exact,
                on_send_intent=pre_click)
        if not isinstance(observation, dict):
            raise TypeError("Malformed browser observation")
        allowed = ("outcome", "send_click_attempted", "user_turn_confirmed",
                   "assistant_response_seen", "response_character_count",
                   "response_sha256")
        final.update({k: observation[k] for k in allowed if k in observation})
        # A verified no-click preflight is not a model submission; unknown
        # exceptions stay conservative as MAY_HAVE_SUBMITTED.
        if observation.get("send_click_attempted") is False:
            final["model_submissions_this_call"] = 0
    except Exception as exc:
        # Never serialize exception messages, browser text, or credentials.
        final["error_type"] = type(exc).__name__
        if browser is None and not intent.exists():
            # Exact fsynced send-click intent was not created: no send attempted.
            final["outcome"] = "PRE_CLICK_FAILURE_CONFIRMED_NO_SEND"
            final["send_click_attempted"] = False
            final["model_submissions_this_call"] = 0
    _create_json(result, final)
    return final


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--live", action="store_true",
                        help="One new source-free prompt, never replay an old claim")
    parser.add_argument("--replace-exact-owned-draft",
                        help="Only an exact previous MicroGen editor diagnostic text")
    args = parser.parse_args(argv)
    try:
        report = run(root=args.checkpoint, live=args.live,
                     owned_draft_exact=args.replace_exact_owned_draft)
    except (ValueError, OSError, KeyError) as exc:
        report = {"status": "CANARY_REJECTED_NO_SUBMISSION",
                  "error_type": type(exc).__name__}
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report.get("outcome") == "VALID_ATTRIBUTED_RESPONSE" or not args.live else 2


if __name__ == "__main__":
    raise SystemExit(main())
