"""Safe, bounded, source-agnostic ChatGPT Selenium response transport.

This handles only a NEW, previously claimed single job, not retries of a
source-bound prompt. Treat a click with uncertain result as in-flight forever
until an existing tab is reconciled. Native Windows Dell-115 Chrome port 9223.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time

from .windows_chatgpt_sourcefree_canary import (
    SEND_BUTTON_CSS, prior_owned_draft,
)

CHATGPT_PORT = 9223
UI_DISCLAIMER = "ChatGPT can make mistakes. Check important info."
MAX_TRANSCRIPT = 500_000
MAX_DRAFT_SCAN = 60


class ChatGPTPreSendBlocked(RuntimeError):
    """No Send click occurred; do not automatically replay this claimed job."""


class ChatGPTUncertainSubmission(RuntimeError):
    """One click may have submitted; preserve its tab and never resend."""


def extract_current_chatgpt_reply(text: str, exact_prompt: str) -> str | None:
    """Attribute exactly one user prompt and one complete assistant response.

    Works with current visible 'You said:' / 'ChatGPT said:' transcripts.
    Deliberately rejects extra turns, missing footer, spurious prompt echoes,
    partial/streaming content, and ambiguous layouts rather than guessing.
    """
    if (type(text) is not str or type(exact_prompt) is not str
            or not exact_prompt.strip() or len(text) > MAX_TRANSCRIPT
            or text.count(exact_prompt.strip()) != 1):
        return None
    anchor = "\nYou said:\n"
    start = text.find(anchor)
    if start < 0 and text.startswith("You said:\n"):
        start, anchor = 0, "You said:\n"
    if start < 0 or text.find(anchor, start + len(anchor)) >= 0:
        return None
    prompt_start = start + len(anchor)
    label = "\nChatGPT said:\n"
    assistant_start = text.find(label, prompt_start)
    if assistant_start < 0:
        return None
    user_text = text[prompt_start:assistant_start].strip()
    if user_text != exact_prompt.strip():
        return None
    body_start = assistant_start + len(label)
    footer = "\n" + UI_DISCLAIMER
    footer_at = text.find(footer, body_start)
    if footer_at < 0:
        return None
    response = text[body_start:footer_at].strip()
    if not response or "\nYou said:\n" in response or "\nChatGPT said:\n" in response:
        return None
    if text.find(label, footer_at) >= 0 or text.find(anchor, footer_at) >= 0:
        return None
    return response


def find_exact_self_authored_draft(text: str, checkpoints_root: Path | None) -> bool:
    """Only a previously owned *non-clicked* canary may be replaced.

    Never infer that arbitrary nonempty user input belongs to MicroGen. An
    uncertain/pending source job must never be used as an overwrite permit.
    """
    if not text or checkpoints_root is None:
        return False
    root = Path(checkpoints_root)
    if not root.is_dir() or root.is_symlink():
        return False
    try:
        directories = sorted(
            (p for p in root.iterdir() if p.is_dir() and not p.is_symlink()),
            key=lambda p: p.name, reverse=True,
        )[:MAX_DRAFT_SCAN]
    except OSError:
        return False
    for folder in directories:
        if not (folder / "chatgpt_canary_claim.json").is_file():
            continue
        try:
            candidate = prior_owned_draft(folder)
            if candidate != text:
                continue
            # A new click-intent journal always makes a send ambiguous.
            # The older V3 attempt is separately audited as pre-click.
            if (folder / "chatgpt_send_click_intent.json").exists():
                continue
            return True
        except (ValueError, OSError, KeyError, TypeError):
            continue
    return False


def write_click_intent(path: Path, exact_prompt: str) -> None:
    """Durably record the sole intended click before touching the Send control."""
    path = Path(path)
    if (path.is_symlink() or path.exists() or not path.parent.is_dir()
            or path.parent.is_symlink()):
        raise ChatGPTPreSendBlocked("CLICK_INTENT_PATH_UNSAFE_OR_ALREADY_CLAIMED")
    record = {
        "schema_version": 1,
        "status": "CHATGPT_CLICK_INTENT_NOT_DELIVERY_PROOF",
        "provider": "chatgpt",
        "debug_port": CHATGPT_PORT,
        "one_click_only": True,
        "prompt_sha256": hashlib.sha256(exact_prompt.encode("utf-8")).hexdigest(),
        "created_unix": time.time(),
        "source_pdf_saved_in_receipt": False,
        "automatic_retry_authorized": False,
    }
    with path.open("x", encoding="utf-8") as fp:
        json.dump(record, fp, sort_keys=True, indent=2)
        fp.write("\n")
        fp.flush()
        os.fsync(fp.fileno())


def _read_composer(driver, el) -> str:
    return driver.execute_script(
        "return (arguments[0].innerText || '').trim();", el)


def _read_main(driver) -> str:
    return driver.execute_script(
        "return (document.querySelector('main')?.innerText || '')"
        ".slice(0, 500001);"
    ) or ""


def submit_one_in_owned_tab(
    driver, prompt: str, *,
    wait_cap_s: int,
    click_intent_path: Path,
    checkpoint_root: Path | None = None,
    clock=time.monotonic,
    sleeper=time.sleep,
) -> str:
    """Operate only an already opened owned, authenticated ChatGPT new tab.

    One exact text insertion and at most one Send click. No Enter fallback,
    no model/API retry, no clipboard, no user tab closing.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    if (type(prompt) is not str or not prompt.strip() or len(prompt) > 120_000
            or type(wait_cap_s) is not int or not 10 <= wait_cap_s <= 180):
        raise ChatGPTPreSendBlocked("UNSAFE_OR_UNBOUNDED_PROMPT")
    if not str(driver.current_url).startswith("https://chatgpt.com/"):
        raise ChatGPTPreSendBlocked("WRONG_PROVIDER_DOMAIN")
    def composer(d):
        for css in ("#prompt-textarea",
                    "[data-testid='composer-text-input']",
                    "div[contenteditable='true'][role='textbox']"):
            for el in d.find_elements(By.CSS_SELECTOR, css):
                if el.is_displayed() and el.is_enabled():
                    return el
        return False
    try:
        editor = WebDriverWait(driver, 18).until(composer)
    except Exception as exc:
        raise ChatGPTPreSendBlocked("COMPOSER_NOT_READY_NO_SEND") from exc
    login_buttons = driver.find_elements(By.CSS_SELECTOR, "button[data-testid='login-button']")
    if any(b.is_displayed() for b in login_buttons):
        raise ChatGPTPreSendBlocked("MANUAL_LOGIN_REQUIRED_NO_SEND")
    previous_text = (_read_composer(driver, editor) or "").strip()
    if previous_text and not find_exact_self_authored_draft(previous_text, checkpoint_root):
        raise ChatGPTPreSendBlocked("UNOWNED_OR_UNCERTAIN_DRAFT_NO_OVERWRITE")
    editor.click()
    # Real 2026 ProseMirror ignored normal Selenium send_keys in Dell-115 V1.
    driver.execute_script(
        "document.execCommand('selectAll',false,null);"
        "document.execCommand('insertText',false,arguments[0]);", prompt)
    if _read_composer(driver, editor) != prompt.strip():
        raise ChatGPTPreSendBlocked("PROMPT_READBACK_MISMATCH_NO_SEND")

    def send_ready(d):
        for button in d.find_elements(By.CSS_SELECTOR, SEND_BUTTON_CSS):
            if button.is_displayed() and button.is_enabled():
                return button
        return False
    try:
        send = WebDriverWait(driver, 15).until(send_ready)
    except Exception as exc:
        raise ChatGPTPreSendBlocked("SEND_CONTROL_NOT_FOUND_NO_SEND") from exc
    write_click_intent(click_intent_path, prompt)
    try:
        send.click()  # One and only one attempt.
    except Exception as exc:
        raise ChatGPTUncertainSubmission("CLICK_DELIVERY_UNCERTAIN_NO_RESEND") from exc

    deadline = clock() + wait_cap_s
    previous = None
    stable = 0
    while clock() < deadline:
        try:
            url = str(driver.current_url)
            if not url.startswith("https://chatgpt.com/c/"):
                sleeper(0.75)
                continue
            text = _read_main(driver)
            response = extract_current_chatgpt_reply(text, prompt)
            if response:
                stopped = any(
                    b.is_displayed() for b in driver.find_elements(
                        By.CSS_SELECTOR,
                        'button[data-testid="stop-button"],'
                        'button[aria-label="Stop"],button[aria-label^="Stop "]'))
                if stopped:
                    stable = 0
                else:
                    stable = stable + 1 if response == previous else 1
                    previous = response
                    if stable >= 3:
                        return response
        except Exception:
            # A transient/unknown DOM state is not permission to click again.
            stable = 0
        sleeper(0.75)
    raise ChatGPTUncertainSubmission("RESPONSE_CAPTURE_PENDING_RECONCILE_NO_RESEND")


def chatgpt_once(
    prompt: str, *, port: int, wait_cap_s: int,
    click_intent_path: Path, checkpoint_root: Path | None = None,
    driver_factory=None,
) -> str:
    """Attach to existing Chrome, create one owned tab, preserve uncertain tab."""
    if port != CHATGPT_PORT:
        raise ChatGPTPreSendBlocked("CHATGPT_PORT_ISOLATION_VIOLATION")
    from .rich_mapping_provider_readiness import inspect_provider
    readiness = inspect_provider("chatgpt", port)
    if readiness.get("status") != "AUTHENTICATED_COMPOSER_READY":
        raise ChatGPTPreSendBlocked("AUTHENTICATION_REQUIRED_NO_SEND")
    if driver_factory is None:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9223")
        driver = webdriver.Chrome(options=options)
    else:
        driver = driver_factory()
    owned = None
    previous = None
    success = False
    try:
        previous = driver.current_window_handle
        driver.switch_to.new_window("tab")
        owned = driver.current_window_handle
        driver.get("https://chatgpt.com/")
        response = submit_one_in_owned_tab(
            driver, prompt, wait_cap_s=wait_cap_s,
            click_intent_path=click_intent_path, checkpoint_root=checkpoint_root)
        success = True
        return response
    finally:
        try:
            # Retain a potentially in-flight tab for source-bound reconciliation.
            if success and owned and owned in driver.window_handles:
                driver.switch_to.window(owned)
                driver.close()
                if previous in driver.window_handles:
                    driver.switch_to.window(previous)
        except Exception:
            pass
        try:
            if driver_factory is None:
                driver.service.stop()  # Never quit the user's Chrome process
        except Exception:
            pass
