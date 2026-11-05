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
    """Canonical Windows containment without rejecting equivalent temp aliases.

    Resolve both sides consistently (unlike Path.absolute on a Windows CI
    workspace), while rejecting symlinked inputs and directory traversal.
    """
    base = Path(os.environ["LOCALAPPDATA"]).resolve(strict=True)
    requested = Path(path)
    if (".." in requested.parts or requested.is_symlink()
            or requested.parent.is_symlink()):
        raise ValueError("Unsafe local checkpoint path")
    root = requested.resolve(strict=False)
    if (sys.platform != "win32" or root == base
            or not root.is_relative_to(base)):
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


def _prompt_for_marker(marker: str) -> str:
    return ("This is a new, source-free MicroGen Selenium transport check. "
            "Reply with exactly this single line and nothing else: " + marker)


def prior_owned_draft(checkpoint: Path) -> str:
    """Only return exact text of an OWNED, terminal, non-click-confirmed canary.

    Does not claim a missing legacy send-intent proves no submission. It only
    authorizes replacing the identical self-authored text in a NEW owned tab;
    never resends the previous request or touches an unrelated draft.
    """
    import re
    previous = _local_root(checkpoint)
    if not previous.is_dir() or previous.is_symlink():
        raise ValueError("Previous owned checkpoint must already exist locally")
    claim = previous / "chatgpt_canary_claim.json"
    result = previous / "chatgpt_canary_result.json"
    for file in (claim, result):
        if file.is_symlink() or not file.is_file() or file.stat().st_size > 4096:
            raise ValueError("Owned canary receipt missing or unsafe")
    c = json.loads(claim.read_text(encoding="utf-8"))
    r = json.loads(result.read_text(encoding="utf-8"))
    marker = c.get("expected_response_marker")
    if (type(marker) is not str
            or not re.fullmatch(r"MICROGEN_CHATGPT_CANARY_[0-9A-F]{12}_OK", marker)):
        raise ValueError("Prior marker is not a canonical owned diagnostic")
    previous_prompt = _prompt_for_marker(marker)
    digest = hashlib.sha256(previous_prompt.encode("utf-8")).hexdigest()
    if not (c.get("schema_version") == 1
            and c.get("provider") == "chatgpt"
            and c.get("debug_port") == PORT
            and c.get("one_send_only") is True
            and c.get("source_files_attached") is False
            and c.get("prompt_sha256") == digest
            and r.get("status") == "CANARY_TERMINAL"
            and r.get("expected_response_marker") == marker
            and r.get("outcome") != "VALID_ATTRIBUTED_RESPONSE"
            and r.get("send_click_attempted") is not True
            and r.get("student_publication_authorized") is False):
        raise ValueError("Prior diagnostic was sent, accepted, or unverifiable")
    return previous_prompt


def _current_ui_exact_canary(main_text: str, marker: str) -> bool:
    """Fail-closed semantic fallback for current fresh-chat ChatGPT said UI."""
    if type(main_text) is not str or len(main_text) > 25000:
        return False
    prompt = _prompt_for_marker(marker)
    if main_text.count(prompt) != 1 or main_text.count(marker) != 2:
        return False
    start = main_text.find(prompt) + len(prompt)
    tag = main_text.find("ChatGPT said:", start)
    if tag < start:
        return False
    lines = [line.strip() for line in
             main_text[tag + len("ChatGPT said:"):].splitlines()
             if line.strip()]
    return (len(lines) >= 2 and lines[0] == marker
            and lines[1].startswith("ChatGPT can make mistakes."))


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
                if not messages or not observed["user_turn_confirmed"]:
                    # Current 2026 ChatGPT UI uses visible "ChatGPT said:"
                    # transcript labels, not old data-message-author-role.
                    # Accept only an exact, unique, owned prompt+assistant pair.
                    page = driver.execute_script(
                        "return (document.querySelector('main')?.innerText || '')"
                        ".slice(0, 25001);")
                    if (str(driver.current_url).startswith("https://chatgpt.com/c/")
                            and _current_ui_exact_canary(page, expected)):
                        observed["user_turn_confirmed"] = True
                        messages = [expected]
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
        timeout: int = WAIT_SECONDS, owned_draft_exact: str | None = None,
        prior_owned_checkpoint: Path | None = None) -> dict:
    root = _local_root(root)
    if owned_draft_exact is not None and prior_owned_checkpoint is not None:
        raise ValueError("Only one exact owned-draft source may be specified")
    if prior_owned_checkpoint is not None:
        previous = _local_root(prior_owned_checkpoint)
        if previous == root:
            raise ValueError("Cannot replay or self-reconcile the same checkpoint")
        owned_draft_exact = prior_owned_draft(previous)
    if owned_draft_exact is not None and prior_owned_checkpoint is None:
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
    prompt = _prompt_for_marker(expected)
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


def _existing_owned_chatgpt_snapshots(marker: str) -> list[dict]:
    """Read only existing port-9223 tabs containing this unique owned marker."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9223")
    driver = webdriver.Chrome(options=opts)
    found = []
    try:
        for handle in list(driver.window_handles)[:20]:
            try:
                driver.switch_to.window(handle)
                url = str(driver.current_url)
                if not url.startswith("https://chatgpt.com/c/"):
                    continue
                has_marker = driver.execute_script(
                    "return (document.querySelector('main')?.innerText || '')"
                    ".includes(arguments[0]);", marker)
                if not has_marker:
                    continue
                raw = driver.execute_script(
                    "return (document.querySelector('main')?.innerText || '')"
                    ".slice(0, 25001);")
                stop = bool(driver.execute_script(
                    "return [...document.querySelectorAll('button')]"
                    ".some(b => b.offsetWidth && "
                    "(/stop/i).test(b.getAttribute('aria-label') || ''));"))
                found.append({"url": url, "main_text": raw,
                              "stop_visible": stop})
            except Exception:
                continue
    finally:
        driver.service.stop()  # Do not close or navigate user Chrome
    return found


def reconcile_existing(*, root: Path, snapshots: list[dict] | None = None) -> dict:
    """Independent, zero-send certification of a prior ambiguous owned canary."""
    import re
    root = _local_root(root)
    claim = root / "chatgpt_canary_claim.json"
    result = root / "chatgpt_canary_result.json"
    intent = root / "chatgpt_send_click_intent.json"
    output = root / "chatgpt_canary_independent_reconciliation.json"
    def read_exact(file: Path) -> dict:
        if (file.is_symlink() or not file.is_file()
                or file.stat().st_size > 4096):
            raise ValueError("Missing or unsafe immutable owned canary proof")
        value = json.loads(file.read_text(encoding="utf-8"))
        if type(value) is not dict:
            raise ValueError("Owned canary proof must be a JSON object")
        return value
    c, r, click = read_exact(claim), read_exact(result), read_exact(intent)
    marker = c.get("expected_response_marker")
    if (type(marker) is not str
            or not re.fullmatch(r"MICROGEN_CHATGPT_CANARY_[0-9A-F]{12}_OK", marker)):
        raise ValueError("Unrecognized source-free marker")
    p = _prompt_for_marker(marker)
    if not (c.get("schema_version") == 1
            and c.get("provider") == "chatgpt"
            and c.get("debug_port") == PORT
            and c.get("one_send_only") is True
            and c.get("prompt_sha256") ==
                hashlib.sha256(p.encode("utf-8")).hexdigest()
            and c.get("source_files_attached") is False
            and r.get("status") == "CANARY_TERMINAL"
            and r.get("expected_response_marker") == marker
            and r.get("send_click_attempted") is True
            and r.get("outcome") == "TIMEOUT_RECONCILE_NO_RESEND"
            and click.get("status") == "SEND_CLICK_INTENT_NOT_DELIVERY_PROOF"
            and click.get("expected_response_marker") == marker
            and click.get("one_click_only") is True):
        raise ValueError("Not a matching immutable ambiguous one-send canary")
    if output.exists():
        prior = read_exact(output)
        if (prior.get("source_result_sha256") ==
                hashlib.sha256(result.read_bytes()).hexdigest()
                and prior.get("exact_marker_response_confirmed") is True):
            return {**prior, "status": "PRIOR_RECONCILIATION_REUSED_NO_SEND"}
        raise ValueError("Unexpected or changed reconciliation")
    rows = (snapshots if snapshots is not None
            else _existing_owned_chatgpt_snapshots(marker))
    matches = [s for s in rows if (
        type(s) is dict and type(s.get("url")) is str
        and s["url"].startswith("https://chatgpt.com/c/")
        and s.get("stop_visible") is False
        and _current_ui_exact_canary(s.get("main_text"), marker))]
    if len(matches) != 1:
        return {"status": "RESPONSE_NOT_INDEPENDENTLY_VERIFIED_NO_SEND",
                "matching_verified_conversations": len(matches),
                "model_submissions_this_call": 0,
                "student_publication_authorized": False}
    proof = {
        "schema_version": 1,
        "status": "CHATGPT_CANARY_EXACT_RESPONSE_INDEPENDENTLY_VERIFIED",
        "provider": "chatgpt", "debug_port": PORT,
        "source_claim_sha256": hashlib.sha256(claim.read_bytes()).hexdigest(),
        "source_result_sha256": hashlib.sha256(result.read_bytes()).hexdigest(),
        "source_click_intent_sha256": hashlib.sha256(intent.read_bytes()).hexdigest(),
        "conversation_url_sha256": hashlib.sha256(
            matches[0]["url"].encode("utf-8")).hexdigest(),
        "response_sha256": hashlib.sha256(marker.encode("utf-8")).hexdigest(),
        "response_characters": len(marker),
        "exact_marker_response_confirmed": True,
        "original_timeout_receipt_overwritten": False,
        "model_submissions_this_call": 0,
        "source_pdf_transmitted": False,
        "student_publication_authorized": False,
    }
    _create_json(output, proof)
    return proof


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--live", action="store_true",
                        help="One new source-free prompt, never replay an old claim")
    parser.add_argument("--replace-exact-owned-draft",
                        help="Only an exact previous MicroGen editor diagnostic text")
    parser.add_argument("--replace-owned-draft-from-checkpoint", type=Path,
                        help="Verify exact self-authored prior terminal canary draft")
    parser.add_argument("--reconcile-existing", action="store_true",
                        help="Read previous sent canary response, never submit another prompt")
    args = parser.parse_args(argv)
    try:
        if args.reconcile_existing:
            if args.live or args.replace_exact_owned_draft or args.replace_owned_draft_from_checkpoint:
                raise ValueError("Read-only reconciliation cannot request a model send")
            report = reconcile_existing(root=args.checkpoint)
        else:
            report = run(root=args.checkpoint, live=args.live,
                         owned_draft_exact=args.replace_exact_owned_draft,
                         prior_owned_checkpoint=args.replace_owned_draft_from_checkpoint)
    except (ValueError, OSError, KeyError) as exc:
        report = {"status": "CANARY_REJECTED_NO_SUBMISSION",
                  "error_type": type(exc).__name__}
    print(json.dumps(report, sort_keys=True, indent=2))
    if args.reconcile_existing:
        return 0 if report.get("status") in {
            "CHATGPT_CANARY_EXACT_RESPONSE_INDEPENDENTLY_VERIFIED",
            "PRIOR_RECONCILIATION_REUSED_NO_SEND",
        } else 2
    return 0 if report.get("outcome") == "VALID_ATTRIBUTED_RESPONSE" or not args.live else 2


if __name__ == "__main__":
    raise SystemExit(main())
