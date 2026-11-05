"""Windows ChatGPT Selenium login preparation in an existing dedicated profile.

Only port 9223 is reserved for ChatGPT. A guest composer MUST NOT count
as authentication. Can optionally focus an EXISTING ChatGPT tab for the user
to sign in manually; never types passwords, sends a prompt, closes Chrome,
moves cookies between profiles, or republishes a source.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable

CHATGPT_DEBUG_PORT = 9223
GEMINI_DEBUG_PORTS = frozenset((9222, 9225))


def inspect_login(*, port: int = CHATGPT_DEBUG_PORT,
                  browser_check: Callable | None = None) -> dict:
    if sys.platform != "win32":
        raise ValueError("Native Windows only")
    if type(port) is not int or port != CHATGPT_DEBUG_PORT:
        raise ValueError("ChatGPT must use dedicated port 9223, not Gemini ports")
    from .rich_mapping_provider_readiness import inspect_provider
    health = (inspect_provider("chatgpt", port) if browser_check is None
              else browser_check("chatgpt", port))
    if (type(health) is not dict
            or health.get("provider") != "chatgpt"
            or health.get("debug_port") != port):
        raise ValueError("No trusted ChatGPT-specific browser evidence")
    ready = (health.get("status") == "AUTHENTICATED_COMPOSER_READY"
             and health.get("authenticated_ui_ready") is True
             and health.get("model_submission_performed") is False)
    login = health.get("status") == "LOGIN_REQUIRED"
    status = (
        "CHATGPT_AUTHENTICATED_FOR_A_NEW_UNSENT_JOB_ONLY" if ready
        else "CHATGPT_MANUAL_LOGIN_REQUIRED_IN_EXISTING_PROFILE" if login
        else "CHATGPT_EXISTING_PROFILE_NOT_READY"
    )
    return {
        "schema_version": 1,
        "status": status,
        "chatgpt_debug_port": port,
        "authenticated_chatgpt_session": ready,
        "manual_login_required": bool(login),
        "existing_browser_status": health.get("status"),
        "gemini_reserved_ports_untouched": True,
        "user_owned_chrome_tabs_closed": False,
        "browser_prompt_submitted": False,
        "password_or_cookies_read_or_transferred": False,
        "automatic_existing_source_resubmission_authorized": False,
        "new_model_or_tts_calls": False,
        "student_publication_authorized": False,
    }


def focus_existing_login_tab(*, port: int = CHATGPT_DEBUG_PORT,
                             browser_factory=None) -> bool:
    """Focus a previously open ChatGPT tab ONLY. No tab or URL is created."""
    if sys.platform != "win32" or port != CHATGPT_DEBUG_PORT:
        raise ValueError("Only dedicated Windows ChatGPT port 9223")
    if browser_factory is None:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        opts = Options()
        opts.add_experimental_option("debuggerAddress", "127.0.0.1:9223")
        driver = webdriver.Chrome(options=opts)
    else:
        driver = browser_factory(port)
    managed = browser_factory is None
    try:
        for handle in list(driver.window_handles):
            try:
                driver.switch_to.window(handle)
                if not str(driver.current_url).startswith("https://chatgpt.com/"):
                    continue
                try:
                    driver.execute_cdp_cmd("Page.bringToFront", {})
                except Exception:
                    pass
                return True
            except Exception:
                continue
        return False
    finally:
        if managed:
            # Chrome is a USER profile. Stop the automation driver only.
            # driver.quit() may close the user's authenticated browser.
            try:
                driver.service.stop()
            except Exception:
                pass


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--focus-existing-login-tab", action="store_true",
                   help="Only focus an existing 9223 ChatGPT tab; do not navigate or sign in")
    args = p.parse_args(argv)
    try:
        data = inspect_login()
        if args.focus_existing_login_tab and data["manual_login_required"]:
            data["existing_login_tab_focused"] = focus_existing_login_tab()
    except (ValueError, OSError, ImportError) as exc:
        data = {
            "status": "CHATGPT_SELENIUM_SESSION_INSPECTION_REJECTED",
            "error_type": type(exc).__name__,
            "password_or_cookies_read_or_transferred": False,
            "browser_prompt_submitted": False,
            "student_publication_authorized": False,
        }
    print(json.dumps(data, indent=2))
    return 0 if data.get("authenticated_chatgpt_session") else 2


if __name__ == "__main__":
    raise SystemExit(main())
