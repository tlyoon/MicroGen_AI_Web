# MicroGen_AI Educational Automation Package
# Â© 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.
#
# This file is part of the MicroGen_AI package.
#
# Licensed under the MIT License (see LICENSE file in the project root).
# You may not use this file except in compliance with the License.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.


# MicroGen_AI Gemini UI Automation via Selenium
# Reusable Selenium communication layer extracted from map_and_rename_selenium_v7.py
#
# IMPORTANT NOTE ABOUT THE FILENAME:
# This file is intentionally named `selenium.py` per project convention.
# Because that name can shadow the upstream `selenium` package, this module
# imports the real upstream package using a guarded sys.path trick.

from __future__ import annotations

import os, sys, time, socket, subprocess, tempfile, re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

# ---------------- Logging ----------------
def log(msg: str, level: str = "INFO") -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)

DEFAULT_TIMEOUT = 6

# ---------------- Config ----------------
@dataclass
class Config:
    root: Path
    pages_dir: str = "pages"
    crops_dir: str = "crops"
    gemini_url: str = "https://gemini.google.com/app"
    debug_port: int = 9222
    wait_mapping_max: int = 120

    chrome_exe: str = os.getenv("CHROME_EXE", r"C:\Program Files\Google\Chrome\Application\chrome.exe")

    # Persistent profile inputs (kept for backwards compatibility)
    user_data_dir: str = os.getenv("GEMINI_USER_DATA_DIR", str(Path.home() / "AppData/Local/Google/Chrome/User Data"))
    profile_directory: str = os.getenv("GEMINI_PROFILE_DIRECTORY", "Default")

    fallback_user_data_dir: str = str(Path(tempfile.gettempdir()) / "gemini_selenium_fallback")
    fallback_profile_directory: str = "Default"

    # If True, attach to an existing remote-debug Chrome when the port is already in use.
    use_persistent_chrome: bool = True

    # If True, keep v7 behaviour of force-killing Chrome to free the debug port.
    # Set env SAFE_CHROME=1 to disable killing all Chrome.
    force_kill_chrome_to_free_port: bool = (os.getenv("SAFE_CHROME", "0") != "1")



# ---------------- Import real upstream selenium ----------------
def _import_upstream_selenium():
    """
    Import the *real* selenium package even though this module is named selenium.py.

    When this file is executed directly (for example via Spyder %runfile), Python may
    insert this module into sys.modules under the name 'selenium'. If we then try to
    import 'selenium.webdriver', Python can mistakenly treat THIS file as the selenium
    package, causing:
        ModuleNotFoundError: No module named 'selenium.webdriver'; 'selenium' is not a package

    To avoid that, we temporarily:
      1. remove this file's directory (and cwd) from sys.path
      2. remove any non-package 'selenium' entry from sys.modules
      3. import the real upstream selenium package/submodules
      4. restore sys.path and any prior sys.modules entry
    """
    import importlib

    this_dir = os.path.abspath(os.path.dirname(__file__))
    cwd_dir = os.path.abspath(os.getcwd())
    orig_path = list(sys.path)

    old_selenium = sys.modules.pop("selenium", None)
    restore_old_selenium = old_selenium is not None and not hasattr(old_selenium, "__path__")

    try:
        sys.path = [
            p for p in sys.path
            if os.path.abspath(p or os.getcwd()) not in {this_dir, cwd_dir}
        ]

        webdriver = importlib.import_module("selenium.webdriver")
        options_mod = importlib.import_module("selenium.webdriver.chrome.options")
        by_mod = importlib.import_module("selenium.webdriver.common.by")
        keys_mod = importlib.import_module("selenium.webdriver.common.keys")
        wait_mod = importlib.import_module("selenium.webdriver.support.ui")
        ec_mod = importlib.import_module("selenium.webdriver.support.expected_conditions")
        exc_mod = importlib.import_module("selenium.common.exceptions")
        return webdriver, options_mod, by_mod, keys_mod, wait_mod, ec_mod, exc_mod
    finally:
        sys.path = orig_path
        if restore_old_selenium:
            sys.modules["selenium"] = old_selenium

_webdriver, _options_mod, _by_mod, _keys_mod, _wait_mod, _ec_mod, _exc_mod = _import_upstream_selenium()

webdriver = _webdriver
Options = _options_mod.Options
By = _by_mod.By
Keys = _keys_mod.Keys
WebDriverWait = _wait_mod.WebDriverWait
EC = _ec_mod  # expected_conditions module aliased as EC
StaleElementReferenceException = _exc_mod.StaleElementReferenceException

# Optional clipboard
try:
    import pyperclip
except Exception:
    pyperclip = None

# Optional: pywinauto to close native file dialogs safely (Windows)
try:
    from pywinauto import Desktop
except Exception:
    Desktop = None

# Tunables (env overrides)
FAST_UI_WAIT              = float(os.getenv("FAST_UI_WAIT", "1.5"))
DEVTOOLS_MAX_WAIT         = int(os.getenv("DEVTOOLS_MAX_WAIT", "160"))
PROMPT_READY_WAIT         = int(os.getenv("PROMPT_READY_WAIT", "45"))
UPLOAD_SEARCH_CAP_SECONDS = float(os.getenv("UPLOAD_SEARCH_CAP_SECONDS", "45"))
UPLOAD_IFRAME_MAX         = int(os.getenv("UPLOAD_IFRAME_MAX", "16"))
UPLOAD_RESCAN_CYCLES      = int(os.getenv("UPLOAD_RESCAN_CYCLES", "3"))
UPLOAD_OPEN_ATTEMPTS      = int(os.getenv("UPLOAD_OPEN_ATTEMPTS", "4"))
OPEN_BACKOFF_BASE         = float(os.getenv("OPEN_BACKOFF_BASE", "0.4"))


# ---------------- Utilities ----------------
def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

def _wait_for_port(port: int, timeout: float = 18.0, poll: float = 0.25) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if _is_port_in_use(port):
            return True
        time.sleep(poll)
    return False

def kill_chrome_processes():
    """v7 compatibility: kills all Chrome instances to ensure remote-debugging port can open."""
    log("Force-closing existing Chrome processes to release remote-debug port...")
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True, check=False)
        else:
            subprocess.run(["pkill", "-f", "chrome"], capture_output=True, check=False)
        time.sleep(2)
    except Exception as e:
        log(f"Cleanup info: {e}", "DEBUG")

def dismiss_native_file_dialogs(timeout=3.0, interval=0.2):
    """
    Close OS file-open dialogs (e.g., 'Open', 'Choose File') spawned by Chrome.
    Safe: closes only the modal dialog (class '#32770'), not explorer.exe / desktop.
    """
    if Desktop is None:
        return
    end = time.time() + timeout
    while time.time() < end:
        try:
            for w in Desktop(backend="win32").windows(class_name="#32770"):
                title = (w.window_text() or "").lower()
                if "open" in title or "choose" in title or "file" in title:
                    try:
                        w.close()
                    except Exception:
                        try:
                            w.type_keys("%{F4}")  # Alt+F4
                        except Exception:
                            pass
        except Exception:
            pass
        time.sleep(interval)

# ---------------- Response wait/copy ----------------

def _looks_like_latex_doc(s: str) -> bool:
    if not s:
        return False
    return ("\\documentclass" in s) and ("\\end{document}" in s)

def _wait_until_generation_finishes(driver, timeout: float = 180.0, poll: float = 0.5) -> None:
    """
    Wait until Gemini is done generating.
    We use multiple signals:
      - absence/disablement of "Stop generating"/"Stop" button
      - presence of Send button enabled (or prompt is available)
      - last response text stable for a few polls
    This avoids capturing mid-stream.
    """
    t0 = time.time()

    # Track stability of last response
    last_text = ""
    stable = 0
    stable_needed = 3
    blank_since = None

    stop_xpaths = [
        "//button[contains(@aria-label,'Stop')]",
        "//button[contains(@title,'Stop')]",
        "//button[.//span[contains(normalize-space(.),'Stop')]]",
    ]
    send_xpaths = [
        "//button[@aria-label='Send message' or contains(@aria-label,'Send')]",
        "//button[contains(@aria-label,'Send')]",
        "//button[.//span[contains(normalize-space(.),'Send')]]",
    ]
    response_selectors = [
        "message-content",
        "div[role='article']",
        "div[class*='response']",
        "div[class*='model']",
    ]

    while time.time() - t0 < timeout:
        # 1) Check if Stop button exists (means still generating)
        stop_present = False
        try:
            for xp in stop_xpaths:
                btns = driver.find_elements(By.XPATH, xp)
                if btns:
                    # if any is displayed+enabled, consider it "generating"
                    for b in btns[-2:]:
                        try:
                            if b.is_displayed() and b.is_enabled():
                                stop_present = True
                                break
                        except Exception:
                            continue
                if stop_present:
                    break
        except Exception:
            pass

        # 2) Extract latest response text (best-effort)
        cur = ""
        try:
            for sel in response_selectors:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    cand = els[-1].get_attribute("innerText") or els[-1].text
                    cur = (cand or "").strip()
                    if cur:
                        break
        except Exception:
            pass

        # Fail fast if a previously submitted conversation has vanished
        # back to a blank composer state. This prevents narration from burning
        # the full response timeout after a transient/aborted submission.
        blank_conversation = False
        try:
            state = driver.execute_script(
                """
                const vis=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const userSelectors=['user-query','[data-message-author-role="user"]','[class*="user-query"]'];
                const users=new Set();
                for(const s of userSelectors) for(const e of document.querySelectorAll(s))
                  if(vis(e)) users.add(e);
                const models=[...document.querySelectorAll('model-response')].filter(vis).length;
                const editor=[...document.querySelectorAll(
                  'div.ql-editor[contenteditable="true"],[contenteditable="true"][role="textbox"],textarea'
                )].find(vis);
                const text=editor?((editor.value||editor.innerText||editor.textContent||'').trim()):'';
                return [users.size, models, text];
                """
            ) or [0, 0, ""]
            blank_conversation = (
                (not stop_present) and (not cur) and int(state[0]) == 0
                and int(state[1]) == 0 and not str(state[2] or "").strip()
            )
        except Exception:
            blank_conversation = False

        if blank_conversation:
            if blank_since is None:
                blank_since = time.time()
            elif time.time() - blank_since >= 3.0:
                log(
                    "Gemini conversation returned to a blank state after submission; "
                    "aborting response wait early.",
                    "WARN",
                )
                return
        else:
            blank_since = None

        # Stability heuristic
        if cur and cur == last_text:
            stable += 1
        else:
            stable = 0
            last_text = cur

        # 3) If no stop button AND stable enough, accept as finished
        if (not stop_present) and (stable >= stable_needed):
            return

        # 4) Additional: if Send is enabled and stable enough, accept
        try:
            send_enabled = False
            for xp in send_xpaths:
                btns = driver.find_elements(By.XPATH, xp)
                if btns:
                    try:
                        if btns[-1].is_enabled():
                            send_enabled = True
                            break
                    except Exception:
                        continue
            if send_enabled and stable >= stable_needed:
                return
        except Exception:
            pass

        time.sleep(poll)

    # timeout reached: return anyway (caller will validate via copy)
    return


def _try_click(driver, el) -> bool:
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    except Exception:
        pass
    try:
        el.click()
        return True
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", el)
            return True
        except Exception:
            return False

def _element_visible_text(el) -> str:
    try:
        txt = el.get_attribute("innerText") or el.text or ""
    except Exception:
        txt = ""
    return re.sub(r"\s+", " ", (txt or "")).strip()

def _normalize_textish(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()

def _page_text(driver) -> str:
    try:
        txt = driver.execute_script("return (document.body && document.body.innerText) || '';")
    except Exception:
        txt = ""
    return _normalize_textish(txt)

def _page_has_any_text(driver, phrases) -> bool:
    hay = _page_text(driver)
    return any((_normalize_textish(p) in hay) for p in (phrases or []))

def _response_container_candidates(driver):
    selectors = [
        "message-content",
        "div[role='article']",
        "div[class*='response']",
        "div[class*='model']",
    ]

    out = []
    seen = set()

    for sel in selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
        except Exception:
            els = []

        for el in els:
            try:
                key = el.id
            except Exception:
                key = str(id(el))

            if key in seen:
                continue
            seen.add(key)

            txt = _element_visible_text(el)
            if len(txt) < 20:
                continue

            try:
                if (el.get_attribute("contenteditable") or "").lower() == "true":
                    continue
            except Exception:
                pass

            try:
                if el.find_elements(By.CSS_SELECTOR, '[contenteditable="true"], textarea, input, div[role="textbox"]'):
                    continue
            except Exception:
                pass

            out.append(el)

    return out

def _latest_response_container(driver):
    cands = _response_container_candidates(driver)
    return cands[-1] if cands else None

def _response_action_scopes(driver, max_ancestors: int = 3):
    scope = _latest_response_container(driver)
    if scope is None:
        return []

    scopes = []
    seen = set()
    cur = scope

    for _ in range(max_ancestors + 1):
        try:
            key = cur.id
        except Exception:
            key = str(id(cur))

        if key not in seen:
            seen.add(key)
            scopes.append(cur)

        try:
            cur = driver.execute_script(
                "return arguments[0] ? arguments[0].parentElement : null;",
                cur
            )
        except Exception:
            cur = None

        if cur is None:
            break

    return scopes

def _find_copy_buttons_in_scope(scope):
    xpaths = [
        ".//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy response')]",
        ".//button[contains(translate(@title,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy response')]",
        ".//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy')]",
        ".//button[contains(translate(@title,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy')]",
        ".//*[@role='button' and contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy')]",
    ]

    out = []
    seen = set()

    for xp in xpaths:
        try:
            found = scope.find_elements(By.XPATH, xp)
        except Exception:
            found = []

        for el in found:
            try:
                key = el.id
            except Exception:
                key = str(id(el))

            if key in seen:
                continue
            seen.add(key)

            try:
                meta = " ".join([
                    el.get_attribute("aria-label") or "",
                    el.get_attribute("title") or "",
                    _element_visible_text(el),
                ]).lower()
            except Exception:
                meta = ""

            if "prompt" in meta:
                continue
            if "share" in meta:
                continue

            out.append(el)

    return out

def _find_more_buttons_in_scope(scope):
    xpaths = [
        ".//button[contains(@aria-label,'More') or contains(@title,'More')]",
        ".//button[contains(@aria-label,'Options') or contains(@title,'Options')]",
        ".//button[contains(@aria-label,'Menu') or contains(@title,'Menu')]",
        ".//*[@role='button' and (normalize-space(.)='⋯' or normalize-space(.)='...')]",
    ]

    out = []
    seen = set()

    for xp in xpaths:
        try:
            found = scope.find_elements(By.XPATH, xp)
        except Exception:
            found = []

        for el in found:
            try:
                key = el.id
            except Exception:
                key = str(id(el))

            if key in seen:
                continue
            seen.add(key)

            try:
                meta = " ".join([
                    el.get_attribute("aria-label") or "",
                    el.get_attribute("title") or "",
                    _element_visible_text(el),
                ]).lower()
            except Exception:
                meta = ""

            if "share" in meta:
                continue

            out.append(el)

    return out

def _copied_text_matches_latest_response(driver, copied_text: str) -> bool:
    copied = _normalize_textish(copied_text)
    if not copied:
        return False

    scope = _latest_response_container(driver)
    if scope is None:
        return True

    resp = _normalize_textish(_element_visible_text(scope))
    if not resp:
        return True

    if len(copied) <= 120:
        return copied in resp

    head = copied[:120]
    tail = copied[-120:]

    return (
        (head in resp) or
        (tail in resp) or
        (resp[:120] in copied)
    )

def _dismiss_open_menu_with_escape(driver):
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.ESCAPE)
        time.sleep(0.15)
    except Exception:
        pass



def _copy_via_toolbar_copy_button(driver) -> str:
    """
    Click ONLY a Copy button associated with the latest model response.
    Do NOT fall back to page-wide copy scanning, because that can hit
    prompt-copy controls instead of response-copy controls.
    """
    if pyperclip is None:
        return ""

    try:
        before = (pyperclip.paste() or "")
    except Exception:
        before = ""

    scopes = _response_action_scopes(driver, max_ancestors=3)
    if not scopes:
        return ""

    for scope in scopes:
        candidates = _find_copy_buttons_in_scope(scope)

        for el in reversed(candidates[-10:]):
            if not _try_click(driver, el):
                continue

            time.sleep(0.35)

            try:
                after = (pyperclip.paste() or "")
            except Exception:
                after = ""

            if not after or after == before:
                continue

            # Hard reject if Gemini explicitly says we copied the PROMPT.
            if _page_has_any_text(driver, ["prompt copied"]):
                before = after or before
                continue

            # Accept only if the clipboard content resembles the latest response.
            if _copied_text_matches_latest_response(driver, after):
                return after.strip()

            before = after or before

    return ""


def _copy_via_more_menu(driver) -> str:
    """
    Try a LOCAL More/Options menu near the latest model response only.
    Avoid page-wide menu probing because it can open unrelated controls
    such as share/prompt actions.
    """
    if pyperclip is None:
        return ""

    try:
        before = (pyperclip.paste() or "")
    except Exception:
        before = ""

    scopes = _response_action_scopes(driver, max_ancestors=3)
    if not scopes:
        return ""

    copy_item_xpaths = [
        "//*[self::button or self::div or self::li or self::span][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy')]",
        "//*[@role='menuitem'][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy')]",
    ]

    for scope in scopes:
        more_buttons = _find_more_buttons_in_scope(scope)

        for b in reversed(more_buttons[-6:]):
            _dismiss_open_menu_with_escape(driver)

            if not _try_click(driver, b):
                continue

            time.sleep(0.25)

            clicked_copy = False
            for cxp in copy_item_xpaths:
                try:
                    items = driver.find_elements(By.XPATH, cxp)
                except Exception:
                    items = []

                for it in reversed(items[-10:]):
                    try:
                        meta = " ".join([
                            it.get_attribute("aria-label") or "",
                            it.get_attribute("title") or "",
                            _element_visible_text(it),
                        ]).lower()
                    except Exception:
                        meta = ""

                    if "share" in meta:
                        continue
                    if "prompt" in meta:
                        continue

                    if _try_click(driver, it):
                        clicked_copy = True
                        break

                if clicked_copy:
                    break

            if not clicked_copy:
                _dismiss_open_menu_with_escape(driver)
                continue

            time.sleep(0.35)

            try:
                after = (pyperclip.paste() or "")
            except Exception:
                after = ""

            if not after or after == before:
                _dismiss_open_menu_with_escape(driver)
                continue

            if _page_has_any_text(driver, ["prompt copied"]):
                before = after or before
                _dismiss_open_menu_with_escape(driver)
                continue

            if _copied_text_matches_latest_response(driver, after):
                return after.strip()

            before = after or before
            _dismiss_open_menu_with_escape(driver)

    return ""


def capture_gemini_response_like_manual_copy(
    driver,
    wait_cap: int = 240,
    prefer_latex_doc: bool = True,
    retries: int = 8,
    min_chars: int = 0,
    accept_fn=None,
) -> str:
    """
    Robust capture:
      1) wait until generation finishes
      2) try toolbar Copy button
      3) try More-menu Copy
      4) fallback to DOM capture

    Extra guards:
      - min_chars: reject too-short text
      - accept_fn(text): custom completeness test

    Behavior:
      - If strict guards are requested (min_chars or accept_fn), return ""
        when no capture passes them.
      - Otherwise preserve old best-effort behavior.
    """

    def _passes_guards(txt: str) -> bool:
        txt = (txt or "").strip()
        if not txt:
            return False

        if prefer_latex_doc and not _looks_like_latex_doc(txt):
            return False

        if len(txt) < int(min_chars):
            return False

        if accept_fn is not None:
            try:
                if not accept_fn(txt):
                    return False
            except Exception:
                return False

        return True

    strict_mode = (int(min_chars) > 0) or (accept_fn is not None)

    _wait_until_generation_finishes(driver, timeout=float(wait_cap), poll=0.5)

    if strict_mode:
        try:
            state = driver.execute_script(
                """
                const vis=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const userSelectors=['user-query','[data-message-author-role="user"]','[class*="user-query"]'];
                const users=new Set();
                for(const s of userSelectors) for(const e of document.querySelectorAll(s))
                  if(vis(e)) users.add(e);
                const models=[...document.querySelectorAll('model-response')].filter(vis).length;
                const stop=[...document.querySelectorAll('button')].some(
                  b=>vis(b)&&((b.getAttribute('aria-label')||'').toLowerCase().includes('stop'))
                );
                const editor=[...document.querySelectorAll(
                  'div.ql-editor[contenteditable="true"],[contenteditable="true"][role="textbox"],textarea'
                )].find(vis);
                const text=editor?((editor.value||editor.innerText||editor.textContent||'').trim()):'';
                return [users.size, models, stop, text];
                """
            ) or [0, 0, False, ""]
            if int(state[0]) == 0 and int(state[1]) == 0 and not bool(state[2]) and not str(state[3] or "").strip():
                log("No active Gemini conversation remains after submission; skipping long capture fallback.", "WARN")
                return ""
        except Exception:
            pass

    best_effort_clip = ""
    for _ in range(max(1, retries)):
        clip = _copy_via_toolbar_copy_button(driver) or ""
        if not clip:
            clip = _copy_via_more_menu(driver) or ""

        clip = (clip or "").strip()
        if clip:
            best_effort_clip = clip
            if _passes_guards(clip):
                return clip

        time.sleep(0.8)

    dom = adaptive_wait_and_copy_full(
        driver,
        preset="short",
        overrides={
            "max_wait": 60,
            "min_chars": max(int(min_chars), 80),
            "stable_rounds": 4,
            "poll": 1.0,
        },
    )
    dom = (dom or "").strip()

    if dom and _passes_guards(dom):
        return dom

    if strict_mode:
        return ""

    return (best_effort_clip or dom or "").strip()

def adaptive_wait_and_copy(driver, preset="short", overrides=None):
    """
    Backward-compatible wrapper retained for callers that still use
    send_prompt_and_copy_response().
    """
    o = dict(overrides or {})
    o.setdefault("min_chars", 20)
    o.setdefault("stable_rounds", 3)
    o.setdefault("poll", 0.8)
    return adaptive_wait_and_copy_full(driver, preset=preset, overrides=o)

def adaptive_wait_and_copy_full(driver, preset="short", overrides=None):
    """
    Wait for the last response to stabilize with extra controls.
    overrides keys:
      - max_wait (seconds, default 240)
      - min_chars (default 200)
      - stable_rounds (default 3)
      - poll (seconds, default 0.8)
    """
    o = overrides or {}
    timeout = int(o.get("max_wait", 240))
    min_chars = int(o.get("min_chars", 200))
    stable_rounds = int(o.get("stable_rounds", 3))
    poll = float(o.get("poll", 0.8))

    t0 = time.time()
    last = ""
    stable = 0

    selectors = [
        "message-content",
        "div[role='article']",
        "div[class*='response']",
        "div[class*='model']",
    ]

    while time.time() - t0 < timeout:
        text = ""
        for sel in selectors:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    cand = els[-1].get_attribute("innerText") or els[-1].text
                    cand = (cand or "").strip()
                    if cand:
                        text = cand
                        break
            except Exception:
                pass

        if text and len(text) >= min_chars:
            if text == last:
                stable += 1
            else:
                last = text
                stable = 0

            if stable >= stable_rounds:
                return text

        time.sleep(poll)

    return (last or "").strip()


# =========================
# Gemini Selenium Client
# =========================

def _copy_last_gemini_response(driver) -> str:
    """
    Click Gemini's Copy button on the latest response and read clipboard.
    Mimics the manual 'copy' icon behavior.
    """
    if pyperclip is None:
        return ""

    selectors = [
        "//button[contains(@aria-label,'Copy')]",
        "//button[contains(@title,'Copy')]",
        "//button[.//*[contains(text(),'Copy')]]"
    ]

    try:
        before = pyperclip.paste()
    except Exception:
        before = ""

    for sel in selectors:
        try:
            btns = driver.find_elements(By.XPATH, sel)
            if not btns:
                continue

            btn = btns[-1]

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            btn.click()

            time.sleep(0.4)

            after = pyperclip.paste()

            if after and after != before:
                return after.strip()

        except Exception:
            pass

    return ""

class GeminiSeleniumClient:
    """
    Reusable Gemini UI automation layer:
    - Launches/attaches to a remote-debug Chrome session
    - Uploads local files through DOM file inputs (dialog-free)
    - Sends prompts & returns stabilized response text
    - Shuts down the Chrome session launched by this client (Windows safe)
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.driver: Optional[webdriver.Chrome] = None

        # Track ownership of the chrome instance we launched:
        self._launched_profile_dir: Optional[str] = None

    # ---------- Chrome lifecycle ----------
    def start(self, ensure_gemini_on_launch: bool = True) -> None:
        cfg = self.cfg

        port_in_use = _is_port_in_use(cfg.debug_port)
        if port_in_use and cfg.use_persistent_chrome:
            # Attach to existing session; do not "own" it.
            self._launched_profile_dir = None
        else:
            if not port_in_use:
                # v7 behaviour: if port not in use, optionally kill chrome to avoid zombies
                if cfg.force_kill_chrome_to_free_port:
                    kill_chrome_processes()

                # Unique profile per run (lets us close ONLY our automation Chrome on Windows)
                run_tag = time.strftime("%Y%m%d_%H%M%S")
                profile_dir = os.path.join(r"C:\gemini_automation_profile_runs", f"run_{run_tag}")
                os.makedirs(profile_dir, exist_ok=True)
                self._launched_profile_dir = profile_dir

                log(f"Launching Chrome on port {cfg.debug_port}...")
                args = [
                    cfg.chrome_exe,
                    f"--remote-debugging-port={cfg.debug_port}",
                    f"--user-data-dir={profile_dir}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    cfg.gemini_url if ensure_gemini_on_launch else "about:blank",
                ]
                popen_kwargs = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if sys.platform == "win32":
                    popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
                    subprocess.Popen(args, **popen_kwargs)
                else:
                    subprocess.Popen(args, start_new_session=True, **popen_kwargs)

                if not _wait_for_port(cfg.debug_port, timeout=15):
                    log("Chrome failed to expose remote-debug port. Check CHROME_EXE path.", "ERR")
                    raise RuntimeError("Remote-debug port not available.")
            else:
                # Port is in use and we are not allowed to attach => fail explicitly
                raise RuntimeError(f"Remote debug port {cfg.debug_port} already in use.")

        # Attach Selenium
        opts = Options()
        opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{cfg.debug_port}")
        self.driver = webdriver.Chrome(options=opts)
        log("Selenium attached successfully.")

        # A persistent debug browser can contain Google auth/helper tabs. ChromeDriver
        # does not guarantee which target is current on attach, so explicitly select
        # the real Gemini tab before login/composer detection.
        gemini_handle = None
        for handle in list(self.driver.window_handles):
            try:
                self.driver.switch_to.window(handle)
                if (self.driver.current_url or "").startswith("https://gemini.google.com/"):
                    gemini_handle = handle
                    break
            except Exception:
                continue
        if gemini_handle is None:
            self.driver.get(cfg.gemini_url)
        else:
            self.driver.switch_to.window(gemini_handle)

        # Smart login detection (kept from v7)
        log("Checking login status... (If browser is at Login screen, please sign in now)")
        t0 = time.time()
        logged_in = False
        while time.time() - t0 < 300:
            try:
                composer = self.driver.find_elements(By.CSS_SELECTOR, '[contenteditable="true"]')
                if composer:
                    log("Login detected. Proceeding to task...")
                    logged_in = True
                    break
            except Exception:
                pass
            time.sleep(2)

        if not logged_in:
            raise RuntimeError("Login timeout reached.")

    def ensure_driver_is_alive(self) -> None:
        if self.driver is None:
            self.start(ensure_gemini_on_launch=True)
            return
        try:
            _ = self.driver.current_url
        except Exception:
            log("Driver lost connection. Restarting Chrome...")
            self.start(ensure_gemini_on_launch=True)

    def shutdown(self) -> None:
        # Quit selenium driver
        try:
            if self.driver is not None:
                self.driver.quit()
        except Exception:
            pass
        self.driver = None

        # If we didn't launch a dedicated profile dir, we don't own the session => do nothing.
        if not self._launched_profile_dir:
            return

        # Windows: kill only chrome.exe instances that contain our unique user-data-dir + port
        try:
            if sys.platform == "win32":
                profile_dir = self._launched_profile_dir
                port = self.cfg.debug_port
                ps = rf"""
                $p = Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" |
                     Where-Object {{
                        ($_.CommandLine -like '*--remote-debugging-port={port}*') -and
                        ($_.CommandLine -like '*--user-data-dir={profile_dir}*')
                     }};
                foreach ($x in $p) {{
                    try {{ Stop-Process -Id $x.ProcessId -Force -ErrorAction SilentlyContinue }} catch {{}}
                }}
                """
                subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                    capture_output=True,
                    check=False,
                )
            else:
                # Linux/mac: best-effort kill by port token
                subprocess.run(["pkill", "-f", f"chrome.*remote-debugging-port={self.cfg.debug_port}"],
                               capture_output=True, check=False)
        except Exception:
            pass
        finally:
            self._launched_profile_dir = None

        # Ensure port released (best-effort)
        t0 = time.time()
        while time.time() - t0 < 8:
            if not _is_port_in_use(self.cfg.debug_port):
                break
            time.sleep(0.2)

    # ---------- Gemini UI helpers ----------
    def open_clean_gemini_chat(self) -> None:
        self.ensure_driver_is_alive()
        assert self.driver is not None
        # Development default is Flash; production returns to Pro after the
        # complete point-to-point package is stable. An explicit UI override
        # always wins, otherwise MICROGEN_MODEL_PHASE controls the target.
        phase = os.getenv("MICROGEN_MODEL_PHASE", "development").strip().lower()
        target_mode = os.getenv("MICROGEN_GEMINI_UI_MODE", "").strip().lower()
        if not target_mode:
            target_mode = "pro" if phase in {"production", "prod", "release"} else "flash"
        if target_mode not in {"flash", "pro"}:
            raise RuntimeError(f"Unsupported MICROGEN_GEMINI_UI_MODE={target_mode!r}")
        target_prefix = "3.8 Flash" if target_mode == "flash" else "3.1 Pro"

        # Reuse an authenticated Gemini tab identified by its real mode picker.
        # Then actively select the configured target inside that same tab.
        selected = False
        selected_mode = ""
        picker = None
        select_deadline = time.time() + 12.0
        while time.time() < select_deadline and not selected:
            for handle in list(self.driver.window_handles):
                try:
                    self.driver.switch_to.window(handle)
                    if not self.driver.current_url.startswith("https://gemini.google.com/"):
                        continue
                    pickers = self.driver.find_elements(By.CSS_SELECTOR, 'button[aria-label^="Open mode picker"]')
                    for candidate in pickers:
                        if candidate.is_displayed():
                            picker = candidate
                            selected = True
                            selected_mode = candidate.get_attribute("aria-label") or ""
                            break
                    if selected:
                        break
                except Exception:
                    continue
            if not selected:
                time.sleep(0.25)
        if not selected or picker is None:
            raise RuntimeError(
                "Authenticated Gemini tab with a mode picker was not found after 12s; "
                "refusing to use an unknown fallback tab."
            )

        def _mode_matches(label: str) -> bool:
            label_l = (label or "").lower()
            return "currently" in label_l and target_mode in label_l

        if not _mode_matches(selected_mode):
            try:
                picker.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", picker)

            target = None
            mode_deadline = time.time() + 8.0
            while time.time() < mode_deadline and target is None:
                for selector in ('[role="menuitem"]', 'gem-menu-item[role="menuitem"]'):
                    try:
                        items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    except Exception:
                        items = []
                    for item in items:
                        try:
                            if item.is_displayed() and (item.text or "").strip().startswith(target_prefix):
                                target = item
                                break
                        except Exception:
                            continue
                    if target is not None:
                        break
                if target is None:
                    time.sleep(0.20)
            if target is None:
                raise RuntimeError(f"Gemini {target_prefix} option was not available.")
            try:
                target.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", target)

            confirm_deadline = time.time() + 8.0
            while time.time() < confirm_deadline:
                try:
                    found = self.driver.find_elements(By.CSS_SELECTOR, 'button[aria-label^="Open mode picker"]')
                    for candidate in found:
                        if not candidate.is_displayed():
                            continue
                        selected_mode = candidate.get_attribute("aria-label") or ""
                        if _mode_matches(selected_mode):
                            picker = candidate
                            break
                    if _mode_matches(selected_mode):
                        break
                except Exception:
                    pass
                time.sleep(0.20)
            if not _mode_matches(selected_mode):
                raise RuntimeError(
                    f"Gemini {target_prefix} selection was not confirmed; UI reports {selected_mode!r}."
                )

        log(f"Selected Gemini tab via mode picker: {selected_mode} (phase={phase})")

        # Start a genuinely fresh conversation through Gemini's own New chat
        # control. Re-navigating to /app can reuse Angular conversation state
        # across pages even though the URL looks clean.
        started_fresh = False
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, 'a[aria-label="New chat"], [data-test-id="side-nav-sparkle-button"]')
            for link in reversed(links):
                if link.is_displayed():
                    try:
                        link.click()
                    except Exception:
                        self.driver.execute_script(
                            """
                            const e=arguments[0];
                            for (const t of ['pointerdown','mousedown','pointerup','mouseup','click']) {
                              const ev=t.startsWith('pointer')
                                ? new PointerEvent(t,{bubbles:true,cancelable:true,pointerType:'mouse',isPrimary:true})
                                : new MouseEvent(t,{bubbles:true,cancelable:true,view:window});
                              e.dispatchEvent(ev);
                            }
                            """,
                            link,
                        )
                    started_fresh = True
                    break
        except Exception:
            started_fresh = False
        if not started_fresh:
            self.driver.get(self.cfg.gemini_url)

        t0 = time.time()
        while time.time() - t0 < PROMPT_READY_WAIT:
            try:
                send_btn = self.driver.find_elements(By.XPATH, "//button[@aria-label='Send message' or contains(@aria-label,'Send')]")
                edt = self.driver.find_elements(By.CSS_SELECTOR, '[contenteditable="true"][role="textbox"]')
                if (send_btn and send_btn[-1].is_enabled()) or edt:
                    break
            except Exception:
                pass
            time.sleep(0.4)
        # Current Gemini sometimes finishes rendering the composer a moment
        # before Upload & tools becomes interactive. Probe the toggle and wait
        # briefly for its Angular handler to become live before returning.
        try:
            toggles = self.driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="Upload & tools"]')
            if toggles:
                toggle = toggles[-1]
                deadline = time.time() + 4.0
                while time.time() < deadline:
                    if (toggle.get_attribute("aria-expanded") or "").lower() == "true":
                        break
                    self.driver.execute_script(
                        """
                        const e=arguments[0];
                        for (const t of ['pointerdown','mousedown','pointerup','mouseup','click']) {
                          const ev=t.startsWith('pointer')
                            ? new PointerEvent(t,{bubbles:true,cancelable:true,pointerType:'mouse',isPrimary:true})
                            : new MouseEvent(t,{bubbles:true,cancelable:true,view:window});
                          e.dispatchEvent(ev);
                        }
                        """,
                        toggle,
                    )
                    time.sleep(0.18)
        except Exception:
            pass

        # Prove the new-chat composer is empty. Navigation to /app can preserve
        # draft text in Gemini; stale drafts must never be concatenated with a
        # new MicroGen mapping prompt.
        ed = self._get_prompt_editable()
        try:
            ed.click()
            ed.send_keys(Keys.CONTROL, "a")
            ed.send_keys(Keys.BACKSPACE)
            time.sleep(0.12)
        except Exception:
            pass
        if (ed.text or "").strip():
            try:
                self.driver.execute_script(
                    "arguments[0].innerHTML='<p><br></p>'; arguments[0].dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'deleteContentBackward'}));",
                    ed,
                )
                time.sleep(0.12)
            except Exception:
                pass
        if (ed.text or "").strip():
            raise RuntimeError("Gemini composer could not be cleared; refusing to continue with stale draft text.")
        log("Opened Gemini")

    def _get_prompt_editable(self):
        assert self.driver is not None
        candidates = [
            (By.CSS_SELECTOR, 'div[aria-label="Enter a prompt here"] [contenteditable="true"]'),
            (By.CSS_SELECTOR, 'div[aria-label="Enter a prompt here"]'),
            (By.CSS_SELECTOR, '[contenteditable="true"][role="textbox"]'),
            (By.XPATH, '//div[@role="textbox" and @contenteditable="true"]'),
            (By.XPATH, '//textarea'),
        ]
        for by, sel in candidates:
            try:
                el = WebDriverWait(self.driver, 4).until(EC.presence_of_element_located((by, sel)))
                return el
            except Exception:
                continue
        return self.driver.find_element(By.TAG_NAME, "body")

    def type_prompt_text(self, text: str, retries: int = 3) -> bool:
        """Enter Gemini prompt text through Chrome's input pipeline and verify it."""
        assert self.driver is not None

        def _norm(value: str) -> str:
            return " ".join((value or "").split())

        expected = _norm(text)
        for attempt in range(retries):
            try:
                ed = self._get_prompt_editable()
                if ed is None:
                    raise RuntimeError("Gemini prompt editor not found")
                ed.click()

                # Clear any stale draft through the editor command so Quill's
                # internal model stays synchronized with the DOM.
                try:
                    self.driver.execute_script(
                        """
                        const e=arguments[0]; e.focus();
                        const r=document.createRange(); r.selectNodeContents(e);
                        const s=window.getSelection(); s.removeAllRanges(); s.addRange(r);
                        document.execCommand('delete', false, null);
                        """,
                        ed,
                    )
                    time.sleep(0.05)
                except Exception:
                    pass

                # WebDriver send_keys/paste is silently ignored by the current
                # Gemini Quill editor on Dell-115. CDP Input.insertText is live-
                # verified and updates the editor's internal state.
                self.driver.execute_cdp_cmd("Input.insertText", {"text": text})
                time.sleep(0.18)

                actual = self.driver.execute_script(
                    "const e=arguments[0]; return (e.value||e.innerText||e.textContent||'').trim();",
                    ed,
                ) or ""
                actual_norm = _norm(actual)
                if expected and (actual_norm == expected or expected in actual_norm):
                    return True

                log(
                    f"Prompt verification failed after CDP input (attempt {attempt+1}); "
                    f"expected chars={len(expected)}, actual chars={len(actual_norm)}",
                    "WARN",
                )
            except StaleElementReferenceException:
                log("Prompt textbox went stale; retrying...", "WARN")
            except Exception as e:
                log(f"Typing prompt failed (attempt {attempt+1}): {e}", "WARN")
            time.sleep(0.25)
        return False

    def click_send_with_fallbacks(self, retries: int = 3) -> bool:
        """Submit only when Gemini shows positive evidence of a new user turn."""
        assert self.driver is not None

        def _snapshot_submission_state() -> tuple[int, int, bool, str]:
            try:
                values = self.driver.execute_script(
                    """
                    const vis=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                    const userSelectors=['user-query','[data-message-author-role="user"]','[class*="user-query"]'];
                    const users=new Set();
                    for(const s of userSelectors) for(const e of document.querySelectorAll(s))
                      if(vis(e)) users.add(e);
                    const models=[...document.querySelectorAll('model-response')].filter(vis).length;
                    const stop=[...document.querySelectorAll('button')].some(
                      b=>vis(b)&&((b.getAttribute('aria-label')||'').toLowerCase().includes('stop'))
                    );
                    const editor=[...document.querySelectorAll(
                      'div.ql-editor[contenteditable="true"],[contenteditable="true"][role="textbox"],textarea'
                    )].find(vis);
                    const text=editor?((editor.value||editor.innerText||editor.textContent||'').trim()):'';
                    return [users.size, models, stop, text];
                    """
                ) or [0, 0, False, ""]
                return int(values[0]), int(values[1]), bool(values[2]), str(values[3] or "")
            except Exception:
                return 0, 0, False, ""

        before_users, before_models, before_stop, before_text = _snapshot_submission_state()
        before_url = self.driver.current_url
        log(
            f"[SEND-VERIFY] baseline users={before_users} models={before_models} "
            f"stop={before_stop} composer_len={len(before_text.strip())} url={before_url}",
            "INFO",
        )

        def _registered() -> str:
            try:
                values = self.driver.execute_script(
                    """
                    const beforeUsers=Number(arguments[0]||0);
                    const beforeModels=Number(arguments[1]||0);
                    const beforeStop=Boolean(arguments[2]);
                    const beforeText=String(arguments[3]||'').trim();
                    const beforeUrl=String(arguments[4]||'');
                    const vis=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                    const userSelectors=['user-query','[data-message-author-role="user"]','[class*="user-query"]'];
                    const userSet=new Set();
                    for(const s of userSelectors) for(const e of document.querySelectorAll(s))
                      if(vis(e)) userSet.add(e);
                    const users=userSet.size;
                    const models=[...document.querySelectorAll('model-response')].filter(vis).length;
                    const stop=[...document.querySelectorAll('button')].some(
                      b=>vis(b)&&((b.getAttribute('aria-label')||'').toLowerCase().includes('stop'))
                    );
                    const editor=[...document.querySelectorAll(
                      'div.ql-editor[contenteditable="true"],[contenteditable="true"][role="textbox"],textarea'
                    )].find(vis);
                    const currentText=editor?((editor.value||editor.innerText||editor.textContent||'').trim()):'';
                    const clearLimit=Math.max(8, Math.floor(beforeText.length*0.15));
                    const composerCleared=beforeText.length===0 || currentText.length<=clearLimit;
                    if(!composerCleared) return '';
                    const nowUrl=String(location.href||'');
                    const baseApp=/^https:\/\/gemini\.google\.com\/app\/?(?:[?#].*)?$/i.test(beforeUrl);
                    const routed=/^https:\/\/gemini\.google\.com\/app\/[A-Za-z0-9_-]+/i.test(nowUrl);
                    if(baseApp && routed && nowUrl!==beforeUrl) return 'new-conversation-route+composer-cleared';
                    if(users>beforeUsers) return 'new-user-turn+composer-cleared';
                    if(models>beforeModels) return 'new-model-response+composer-cleared';
                    if(!beforeStop && stop) return 'new-stop-state+composer-cleared';
                    return '';
                    """,
                    before_users,
                    before_models,
                    before_stop,
                    before_text,
                    before_url,
                )
                return str(values or "")
            except Exception:
                return ""

        def _wait_registered(timeout: float = 4.5, stable_for: float = 0.40) -> bool:
            deadline = time.time() + timeout
            positive_since = None
            last_reason = ""
            while time.time() < deadline:
                reason = _registered()
                if reason:
                    # A newly materialized user turn or model response, together
                    # with the cleared composer enforced by _registered(), is
                    # authoritative submission evidence. Gemini can replace that
                    # DOM node quickly during route/render transitions, so do not
                    # require it to remain continuously visible for seconds.
                    if (
                        reason.startswith("new-user-turn")
                        or reason.startswith("new-model-response")
                        or reason.startswith("new-conversation-route")
                    ):
                        log(f"Gemini submission registered via {reason}.", "INFO")
                        return True

                    # A new Stop control is weaker evidence because upload/file
                    # processing can also expose Stop. Require it to persist
                    # briefly while the composer remains cleared.
                    last_reason = reason
                    if positive_since is None:
                        positive_since = time.time()
                    elif time.time() - positive_since >= stable_for:
                        log(f"Gemini submission registered via {last_reason}.", "INFO")
                        return True
                else:
                    positive_since = None
                    last_reason = ""
                time.sleep(0.05)
            return False

        selectors = [
            '//button[@aria-label="Send message"]',
            '//button[contains(@aria-label,"Send")]',
            '//button[contains(@aria-label,"Submit")]',
            '//button[contains(@aria-label,"Ask")]',
            '//button[normalize-space(.)="Submit"]',
            '//button[.//span[contains(normalize-space(.),"Send")]]',
            '//button[.//span[contains(normalize-space(.),"Submit")]]',
            '//button[.//span[contains(normalize-space(.),"Ask")]]',
        ]

        for attempt in range(retries):
            try:
                btn = None
                for sel in selectors:
                    btns = self.driver.find_elements(By.XPATH, sel)
                    visible = []
                    for candidate in btns:
                        try:
                            if candidate.is_displayed() and candidate.is_enabled():
                                visible.append(candidate)
                        except Exception:
                            pass
                    if visible:
                        btn = visible[-1]
                        break

                if btn is not None:
                    try:
                        btn.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", btn)
                    if _wait_registered(4.5):
                        return True
                    log(
                        f"Send control produced no new Gemini turn on attempt {attempt+1}; trying CDP Enter.",
                        "WARN",
                    )

                ed = self._get_prompt_editable()
                if ed is None:
                    raise RuntimeError("Gemini prompt editor unavailable for submit")
                ed.click()
                self.driver.execute_cdp_cmd("Input.dispatchKeyEvent", {
                    "type": "keyDown", "key": "Enter", "code": "Enter",
                    "windowsVirtualKeyCode": 13
                })
                self.driver.execute_cdp_cmd("Input.dispatchKeyEvent", {
                    "type": "keyUp", "key": "Enter", "code": "Enter",
                    "windowsVirtualKeyCode": 13
                })
                if _wait_registered(4.5):
                    return True

                log(
                    f"CDP Enter produced no new Gemini turn on attempt {attempt+1}.",
                    "WARN",
                )
            except StaleElementReferenceException:
                log("Send target went stale; retrying.", "WARN")
            except Exception as e:
                log(f"Send click failed (attempt {attempt+1}): {e}", "WARN")
            time.sleep(0.25)

        # Final trusted-input fallback. The figure mapper has proven on Dell-115
        # that Gemini sometimes ignores WebDriver/CDP activation but accepts a
        # real Windows Enter keystroke. Mark and focus the exact controlled
        # Chrome window before sending Enter, then require durable DOM evidence.
        marker = f"MICROGEN_AUTOMATION_TARGET_{os.getpid()}"
        old_title = ""
        try:
            from pywinauto import Desktop
            from pywinauto.keyboard import send_keys as native_send_keys

            ed = self._get_prompt_editable()
            if ed is None:
                raise RuntimeError("Gemini prompt editor unavailable for native submit")

            old_title = self.driver.title or "Google Gemini"
            self.driver.execute_script("document.title=arguments[0]", marker)
            time.sleep(0.25)

            wins = [w for w in Desktop(backend="uia").windows() if marker in w.window_text()]
            if len(wins) != 1:
                raise RuntimeError(f"Expected one marked Gemini Chrome window; found {len(wins)}")

            wins[0].set_focus()
            self.driver.execute_script("arguments[0].focus()", ed)
            time.sleep(0.10)
            native_send_keys("{ENTER}", pause=0.05)

            if _wait_registered(6.0, stable_for=2.50):
                log("[SEND-VERIFY] native Windows Enter achieved durable submission.", "INFO")
                return True

            log("[SEND-VERIFY] native Windows Enter did not achieve durable submission.", "WARN")
        except Exception as e:
            log(f"[SEND-VERIFY] native Windows Enter fallback failed: {e}", "WARN")
        finally:
            if old_title:
                try:
                    self.driver.execute_script("document.title=arguments[0]", old_title)
                except Exception:
                    pass

        log("[SEND-VERIFY] all send attempts ended without durable registration.", "WARN")
        return False

    # ---------- Upload helpers (DOM-first; dialog-free) ----------
    def _find_file_input_deep_js_current_frame(self):
        assert self.driver is not None
        js = r"""
        const isVisible = el => !!(el && el.offsetParent !== null &&
          getComputedStyle(el).visibility !== 'hidden' && getComputedStyle(el).display !== 'none');
        const out = []; const seen = new Set();
        const pushIf = el => { if (el && el.type === 'file' && !seen.has(el)) { seen.add(el); out.push(el); } };
        function walk(node) {
          if (!node) return;
          if (node.querySelectorAll) {
            node.querySelectorAll('input[type="file"]').forEach(pushIf);
            node.querySelectorAll('*').forEach(el => { if (el.shadowRoot) walk(el.shadowRoot); });
          }
          if (node.tagName && node.tagName.toLowerCase() === 'input' && node.type === 'file') pushIf(node);
        }
        walk(document);
        let visible = out.find(isVisible);
        return visible || out[0] || null;
        """
        try:
            return self.driver.execute_script(js)
        except Exception:
            return None

    def _switch_to_default(self):
        assert self.driver is not None
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

    def _click_attach_buttons_multi_probe(self, probes: int, base_backoff: float):
        assert self.driver is not None
        selectors = [
            (By.XPATH, '//button[@aria-label="Open upload file menu"]'),
            (By.XPATH, '//button[@aria-label="Attach"]'),
            (By.XPATH, '//button[contains(@aria-label,"Upload")]'),
            (By.XPATH, '//button[.//span[contains(normalize-space(.),"Upload")]]'),
            (By.XPATH, '//button[.//span[contains(normalize-space(.),"Attach")]]'),
            (By.XPATH, '//button[@title="Attach" or @title="Upload"]'),
        ]
        backoff = base_backoff
        for _ in range(probes):
            for (by, sel) in selectors:
                try:
                    els = self.driver.find_elements(by, sel)
                    if els:
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", els[-1])
                        except Exception:
                            pass
                        target = els[-1]
                        try:
                            target.click()
                            time.sleep(0.12)
                            if (target.get_attribute("aria-expanded") or "").lower() == "false":
                                self.driver.execute_script("arguments[0].click();", target)
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", target)
                        time.sleep(backoff)
                        backoff = min(backoff * 1.6 + 0.1, 1.2)
                        break
                except Exception:
                    continue

    def _ensure_file_input_any_frame_rescans(self) -> Optional[Tuple[object, Optional[int]]]:
        assert self.driver is not None
        deadline = time.time() + UPLOAD_SEARCH_CAP_SECONDS

        for _cycle in range(UPLOAD_RESCAN_CYCLES):
            if time.time() > deadline:
                break

            self._switch_to_default()
            el = self._find_file_input_deep_js_current_frame()
            if el:
                try:
                    self.driver.execute_script("""
                        arguments[0].style.display = 'block';
                        arguments[0].style.visibility = 'visible';
                        arguments[0].removeAttribute('hidden');
                        arguments[0].removeAttribute('aria-hidden');
                    """, el)
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                except Exception:
                    pass
                return el, None

            if UPLOAD_OPEN_ATTEMPTS:
                self._click_attach_buttons_multi_probe(UPLOAD_OPEN_ATTEMPTS, OPEN_BACKOFF_BASE)

            el = None
            try:
                el = WebDriverWait(self.driver, 1.5).until(
                    EC.presence_of_element_located((By.XPATH, '//input[@type="file"]'))
                )
            except Exception:
                el = self._find_file_input_deep_js_current_frame()
            if el:
                try:
                    self.driver.execute_script("""
                        arguments[0].style.display = 'block';
                        arguments[0].style.visibility = 'visible';
                        arguments[0].removeAttribute('hidden');
                        arguments[0].removeAttribute('aria-hidden');
                    """, el)
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                except Exception:
                    pass
                return el, None

            frames = self.driver.find_elements(By.TAG_NAME, "iframe")[:UPLOAD_IFRAME_MAX]
            for idx, f in enumerate(frames):
                if time.time() > deadline:
                    break
                try:
                    self.driver.switch_to.frame(f)
                except Exception:
                    self._switch_to_default()
                    continue

                if UPLOAD_OPEN_ATTEMPTS:
                    self._click_attach_buttons_multi_probe(UPLOAD_OPEN_ATTEMPTS, OPEN_BACKOFF_BASE)

                el = None
                try:
                    el = WebDriverWait(self.driver, 1.2).until(
                        EC.presence_of_element_located((By.XPATH, '//input[@type="file"]'))
                    )
                except Exception:
                    el = self._find_file_input_deep_js_current_frame()
                self._switch_to_default()
                if el:
                    return el, idx

            time.sleep(0.4)

        return None

    def upload_files(self, paths: List[Path], max_retries: int = 3) -> None:
        assert self.driver is not None
        paths = [Path(p).resolve() for p in paths]
        log(f"Uploading {len(paths)} file(s): " + ", ".join(p.name for p in paths))
        joined = "\n".join(str(p) for p in paths)
        all_images = all(p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"} for p in paths)

        for attempt in range(1, max_retries + 1):
            try:
                self._switch_to_default()
                # Current Gemini exposes separate document and image file inputs.
                # For image batches, select the image/* input explicitly instead
                # of accepting the first (document-only) input in DOM order.
                el = None
                if all_images:
                    image_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"][accept*="image"]')
                    if not image_inputs:
                        # Gemini 2026 UI creates the image input only while the
                        # Upload & tools menu is expanded. Avoid blind clicking:
                        # clicking an already-open toggle closes it.
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="Upload & tools"]')
                        if buttons:
                            toggle = buttons[-1]
                            deadline = time.time() + 3.0
                            while time.time() < deadline:
                                image_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"][accept*="image"]')
                                if image_inputs:
                                    break
                                if (toggle.get_attribute("aria-expanded") or "").lower() != "true":
                                    try:
                                        toggle.click()
                                    except Exception:
                                        pass
                                    time.sleep(0.08)
                                    if (toggle.get_attribute("aria-expanded") or "").lower() != "true":
                                        # Gemini's Angular menu can ignore WebDriver's
                                        # synthetic .click(); dispatch the complete
                                        # pointer/mouse activation sequence instead.
                                        self.driver.execute_script(
                                            """
                                            const e=arguments[0];
                                            for (const t of ['pointerdown','mousedown','pointerup','mouseup','click']) {
                                              const ev=t.startsWith('pointer')
                                                ? new PointerEvent(t,{bubbles:true,cancelable:true,pointerType:'mouse',isPrimary:true})
                                                : new MouseEvent(t,{bubbles:true,cancelable:true,view:window});
                                              e.dispatchEvent(ev);
                                            }
                                            """,
                                            toggle,
                                        )
                                time.sleep(0.15)
                    if image_inputs:
                        el = image_inputs[-1]

                # For documents/mixed batches, Gemini creates a generic
                # document/code input when Upload & tools is expanded. Target it
                # directly instead of repeatedly toggling the menu through the
                # legacy generic rescanner.
                if el is None and not all_images:
                    doc_inputs = []
                    try:
                        for candidate in self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]'):
                            accept = (candidate.get_attribute("accept") or "").lower()
                            if accept and "image/*" not in accept:
                                doc_inputs.append(candidate)
                    except Exception:
                        doc_inputs = []

                    if not doc_inputs:
                        toggles = self.driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="Upload & tools"]')
                        if toggles:
                            toggle = toggles[-1]
                            if (toggle.get_attribute("aria-expanded") or "").lower() != "true":
                                try:
                                    toggle.click()
                                except Exception:
                                    pass
                                time.sleep(0.12)
                                if (toggle.get_attribute("aria-expanded") or "").lower() != "true":
                                    self.driver.execute_script(
                                        """
                                        const e=arguments[0];
                                        for (const t of ['pointerdown','mousedown','pointerup','mouseup','click']) {
                                          const ev=t.startsWith('pointer')
                                            ? new PointerEvent(t,{bubbles:true,cancelable:true,pointerType:'mouse',isPrimary:true})
                                            : new MouseEvent(t,{bubbles:true,cancelable:true,view:window});
                                          e.dispatchEvent(ev);
                                        }
                                        """,
                                        toggle,
                                    )
                            deadline = time.time() + 2.5
                            while time.time() < deadline and not doc_inputs:
                                time.sleep(0.10)
                                try:
                                    for candidate in self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]'):
                                        accept = (candidate.get_attribute("accept") or "").lower()
                                        if accept and "image/*" not in accept:
                                            doc_inputs.append(candidate)
                                except Exception:
                                    pass
                    if doc_inputs:
                        el = doc_inputs[-1]

                frame_idx = None
                if el is None:
                    got = self._ensure_file_input_any_frame_rescans()
                    if not got:
                        raise RuntimeError("No compatible <input type=file> found in document or iframes.")
                    el, frame_idx = got

                if frame_idx is not None:
                    try:
                        self.driver.switch_to.frame(self.driver.find_elements(By.TAG_NAME, "iframe")[frame_idx])
                    except Exception:
                        pass

                try:
                    # The current image input advertises multiple=true and accepts
                    # a newline-separated WebDriver file list. Sending the whole
                    # batch atomically is important: sequential send_keys calls
                    # can replace/discard earlier image selections.
                    el.send_keys(joined)
                except Exception:
                    dismiss_native_file_dialogs(timeout=2.0)
                    raise

                self._switch_to_default()
                # Gemini attachment chips do not consistently expose filenames
                # as page text. The caller performs the authoritative attachment
                # count/progress/send-ready verification before submitting.
                time.sleep(0.8)
                dismiss_native_file_dialogs(timeout=0.3)
                return

            except Exception as e:
                log(f"Upload attempt {attempt}/{max_retries} failed: {e}", "WARN")
                try:
                    self.open_clean_gemini_chat()
                except Exception:
                    self.start(ensure_gemini_on_launch=True)

        raise RuntimeError("Could not upload files to Gemini after retries.")

    # ---------- Prompt / response ----------
    def send_prompt_and_copy_response(self, instruction_text: str, wait_cap: int) -> str:
        assert self.driver is not None
        if not self.type_prompt_text(instruction_text, retries=3):
            raise RuntimeError("Could not type into Gemini prompt field after retries.")
        if not self.click_send_with_fallbacks(retries=3):
            raise RuntimeError("Could not send the prompt after retries.")
        log(f"Waiting for model response to stabilize (adaptive, max_wait={wait_cap}) ÂÂ¦")
        return adaptive_wait_and_copy(self.driver, preset="short", overrides={"max_wait": wait_cap})
  
    #
    def send_prompt_and_copy_response_full(self, instruction_text: str, wait_cap: int, min_chars: int = 200) -> str:
        """
        Send prompt and capture response using Gemini's Copy icon behavior (clipboard),
        falling back to DOM only if needed.
        """
        assert self.driver is not None
    
        if not self.type_prompt_text(instruction_text, retries=3):
            raise RuntimeError("Could not type into Gemini prompt field after retries.")
        if not self.click_send_with_fallbacks(retries=3):
            raise RuntimeError("Could not send the prompt after retries.")
    
        log(f"Waiting for model response to stabilize (COPY-first, max_wait={wait_cap}) ...")
    
        # COPY-first capture (manual-copy mimic)
        copied = capture_gemini_response_like_manual_copy(
            self.driver,
            wait_cap=wait_cap,
            prefer_latex_doc=True,
            retries=6,
        )
        if copied:
            return copied
    
        # Final fallback: DOM stabilize
        log("COPY-first capture failed; falling back to DOM capture.", "WARN")
        return adaptive_wait_and_copy_full(
            self.driver,
            preset="short",
            overrides={
                "max_wait": wait_cap,
                "min_chars": min_chars,
                "stable_rounds": 3,
                "poll": 0.8,
            },
        )
    #


# =============================================================================
# ChatGPT additions (appended for compatibility; existing Gemini functions intact)
# =============================================================================

CHATGPT_URL = os.getenv("CHATGPT_URL", "https://chatgpt.com/")

def _chatgpt_page_text(driver) -> str:
    try:
        txt = driver.execute_script("return (document.body && document.body.innerText) || '';")
    except Exception:
        txt = ""
    return _normalize_textish(txt)

def _chatgpt_find_prompt_editable(driver):
    selectors = [
        (By.CSS_SELECTOR, "textarea#prompt-textarea"),
        (By.CSS_SELECTOR, "textarea[data-testid='composer-text-input']"),
        (By.CSS_SELECTOR, "div#prompt-textarea[contenteditable='true']"),
        (By.CSS_SELECTOR, "div[contenteditable='true'][role='textbox']"),
        (By.CSS_SELECTOR, "div[contenteditable='true']"),
        (By.CSS_SELECTOR, "textarea"),
    ]
    for by, sel in selectors:
        try:
            els = driver.find_elements(by, sel)
        except Exception:
            els = []
        for el in reversed(els):
            try:
                if el.is_displayed():
                    return el
            except Exception:
                pass
    return None

def _chatgpt_response_container_candidates(driver):
    selectors = [
        "article[data-testid^='conversation-turn-']",
        "[data-message-author-role='assistant']",
        "article",
        "div[class*='assistant']",
    ]
    out = []
    seen = set()
    for sel in selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
        except Exception:
            els = []
        for el in els:
            try:
                key = el.id
            except Exception:
                key = str(id(el))
            if key in seen:
                continue
            seen.add(key)
            try:
                txt = _element_visible_text(el)
            except Exception:
                txt = ""
            if len(txt) < 20:
                continue
            try:
                role = (el.get_attribute("data-message-author-role") or "").lower()
            except Exception:
                role = ""
            if role and role != "assistant":
                continue
            out.append(el)
    return out

def _latest_chatgpt_response_container(driver):
    cands = _chatgpt_response_container_candidates(driver)
    return cands[-1] if cands else None

def _chatgpt_response_action_scopes(driver, max_ancestors: int = 3):
    scope = _latest_chatgpt_response_container(driver)
    if scope is None:
        return []
    scopes = []
    seen = set()
    cur = scope
    for _ in range(max_ancestors + 1):
        try:
            key = cur.id
        except Exception:
            key = str(id(cur))
        if key not in seen:
            seen.add(key)
            scopes.append(cur)
        try:
            cur = driver.execute_script("return arguments[0] ? arguments[0].parentElement : null;", cur)
        except Exception:
            cur = None
        if cur is None:
            break
    return scopes

def _find_chatgpt_copy_buttons_in_scope(scope):
    xpaths = [
        ".//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy')]",
        ".//button[contains(translate(@data-testid,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy')]",
        ".//*[@role='button' and contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy')]",
    ]
    out = []
    seen = set()
    for xp in xpaths:
        try:
            found = scope.find_elements(By.XPATH, xp)
        except Exception:
            found = []
        for el in found:
            try:
                key = el.id
            except Exception:
                key = str(id(el))
            if key in seen:
                continue
            seen.add(key)
            out.append(el)
    return out

def _copy_last_chatgpt_response(driver) -> str:
    """
    Click ChatGPT's Copy button on the latest assistant response and read clipboard.
    This is appended in a way that leaves all Gemini copy helpers untouched.
    """
    if pyperclip is None:
        return ""

    try:
        before = (pyperclip.paste() or "")
    except Exception:
        before = ""

    scopes = _chatgpt_response_action_scopes(driver, max_ancestors=3)
    if not scopes:
        return ""

    for scope in scopes:
        candidates = _find_chatgpt_copy_buttons_in_scope(scope)
        for el in reversed(candidates[-10:]):
            if not _try_click(driver, el):
                continue
            time.sleep(0.35)
            try:
                after = (pyperclip.paste() or "")
            except Exception:
                after = ""
            if after and after != before:
                return after.strip()
            before = after or before

    return ""

def _chatgpt_generation_running(driver) -> bool:
    selectors = [
        "//button[contains(@aria-label,'Stop')]",
        "//button[contains(@data-testid,'stop')]",
        "//button[.//*[contains(normalize-space(.),'Stop')]]",
    ]
    for xp in selectors:
        try:
            btns = driver.find_elements(By.XPATH, xp)
        except Exception:
            btns = []
        for b in btns[-4:]:
            try:
                if b.is_displayed() and b.is_enabled():
                    return True
            except Exception:
                pass
    return False

def _wait_until_chatgpt_generation_finishes(driver, timeout: float = 180.0, poll: float = 0.5) -> None:
    t0 = time.time()
    last_text = ""
    stable = 0
    stable_needed = 3

    while time.time() - t0 < timeout:
        running = _chatgpt_generation_running(driver)

        cur = ""
        try:
            scope = _latest_chatgpt_response_container(driver)
            if scope is not None:
                cur = (_element_visible_text(scope) or "").strip()
        except Exception:
            cur = ""

        if cur and cur == last_text:
            stable += 1
        else:
            stable = 0
            last_text = cur

        if (not running) and stable >= stable_needed:
            return

        time.sleep(poll)

def adaptive_wait_and_copy_chatgpt(driver, max_wait: int = 240, min_chars: int = 200, stable_rounds: int = 3, poll: float = 0.8) -> str:
    t0 = time.time()
    last = ""
    stable = 0

    while time.time() - t0 < max_wait:
        text = ""
        try:
            scope = _latest_chatgpt_response_container(driver)
            if scope is not None:
                text = (_element_visible_text(scope) or "").strip()
        except Exception:
            text = ""

        if text and len(text) >= min_chars:
            if text == last:
                stable += 1
            else:
                last = text
                stable = 0

            if stable >= stable_rounds:
                return text

        time.sleep(poll)

    return (last or "").strip()

def capture_chatgpt_response_like_manual_copy(
    driver,
    wait_cap: int = 240,
    prefer_latex_doc: bool = True,
    retries: int = 8,
    min_chars: int = 0,
    accept_fn=None,
) -> str:
    def _passes_guards(txt: str) -> bool:
        txt = (txt or "").strip()
        if not txt:
            return False
        if prefer_latex_doc and not _looks_like_latex_doc(txt):
            return False
        if len(txt) < int(min_chars):
            return False
        if accept_fn is not None:
            try:
                if not accept_fn(txt):
                    return False
            except Exception:
                return False
        return True

    strict_mode = (int(min_chars) > 0) or (accept_fn is not None)

    _wait_until_chatgpt_generation_finishes(driver, timeout=float(wait_cap), poll=0.5)

    best_effort_clip = ""
    for _ in range(max(1, retries)):
        clip = (_copy_last_chatgpt_response(driver) or "").strip()
        if clip:
            best_effort_clip = clip
            if _passes_guards(clip):
                return clip
        time.sleep(0.8)

    dom = adaptive_wait_and_copy_chatgpt(
        driver,
        max_wait=min(int(wait_cap), 60),
        min_chars=max(int(min_chars), 80),
        stable_rounds=4,
        poll=1.0,
    ).strip()

    if dom and _passes_guards(dom):
        return dom

    if strict_mode:
        return ""

    return (best_effort_clip or dom or "").strip()

class ChatGPTSeleniumClient:
    """
    Reusable ChatGPT UI automation layer appended without changing Gemini logic.
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.driver: Optional[webdriver.Chrome] = None
        self._launched_profile_dir: Optional[str] = None

    def start(self, ensure_chatgpt_on_launch: bool = True) -> None:
        cfg = self.cfg

        port_in_use = _is_port_in_use(cfg.debug_port)
        if port_in_use and cfg.use_persistent_chrome:
            self._launched_profile_dir = None
        else:
            if not port_in_use:
                if cfg.force_kill_chrome_to_free_port:
                    kill_chrome_processes()

                run_tag = time.strftime("%Y%m%d_%H%M%S")
                if sys.platform == "win32":
                    profile_dir = os.path.join(r"C:\chatgpt_automation_profile_runs", f"run_{run_tag}")
                else:
                    profile_dir = os.path.join(tempfile.gettempdir(), f"chatgpt_automation_profile_runs_{run_tag}")
                os.makedirs(profile_dir, exist_ok=True)
                self._launched_profile_dir = profile_dir

                log(f"Launching Chrome on port {cfg.debug_port} for ChatGPT...")
                args = [
                    cfg.chrome_exe,
                    f"--remote-debugging-port={cfg.debug_port}",
                    f"--user-data-dir={profile_dir}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    CHATGPT_URL if ensure_chatgpt_on_launch else "about:blank",
                ]
                popen_kwargs = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if sys.platform == "win32":
                    popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
                    subprocess.Popen(args, **popen_kwargs)
                else:
                    subprocess.Popen(args, start_new_session=True, **popen_kwargs)

                if not _wait_for_port(cfg.debug_port, timeout=15):
                    log("Chrome failed to expose remote-debug port for ChatGPT. Check CHROME_EXE path.", "ERR")
                    raise RuntimeError("Remote-debug port not available.")
            else:
                raise RuntimeError(f"Remote debug port {cfg.debug_port} already in use.")

        opts = Options()
        opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{cfg.debug_port}")
        self.driver = webdriver.Chrome(options=opts)
        log("Selenium attached successfully (ChatGPT).")

        log("Checking ChatGPT login status... (If browser is at Login screen, please sign in now)")
        t0 = time.time()
        logged_in = False
        while time.time() - t0 < 300:
            try:
                composer = _chatgpt_find_prompt_editable(self.driver)
                if composer is not None:
                    log("ChatGPT composer detected. Proceeding to task...")
                    logged_in = True
                    break
            except Exception:
                pass
            time.sleep(2)

        if not logged_in:
            raise RuntimeError("ChatGPT login timeout reached.")

    def ensure_driver_is_alive(self) -> None:
        if self.driver is None:
            self.start(ensure_chatgpt_on_launch=True)
            return
        try:
            _ = self.driver.current_url
        except Exception:
            log("Driver lost connection. Restarting ChatGPT Chrome...")
            self.start(ensure_chatgpt_on_launch=True)

    def shutdown(self) -> None:
        try:
            if self.driver is not None:
                self.driver.quit()
        except Exception:
            pass
        self.driver = None

        if not self._launched_profile_dir:
            return

        try:
            if sys.platform == "win32":
                profile_dir = self._launched_profile_dir
                port = self.cfg.debug_port
                ps = rf"""
                $p = Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" |
                     Where-Object {{
                        ($_.CommandLine -like '*--remote-debugging-port={port}*') -and
                        ($_.CommandLine -like '*--user-data-dir={profile_dir}*')
                     }};
                foreach ($x in $p) {{
                    try {{ Stop-Process -Id $x.ProcessId -Force -ErrorAction SilentlyContinue }} catch {{}}
                }}
                """
                subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                    capture_output=True,
                    check=False,
                )
            else:
                subprocess.run(
                    ["pkill", "-f", f"chrome.*remote-debugging-port={self.cfg.debug_port}"],
                    capture_output=True,
                    check=False,
                )
        except Exception:
            pass
        finally:
            self._launched_profile_dir = None

    def open_clean_chatgpt_chat(self) -> None:
        self.ensure_driver_is_alive()
        assert self.driver is not None
        self.driver.get(CHATGPT_URL)

        t0 = time.time()
        while time.time() - t0 < PROMPT_READY_WAIT:
            try:
                edt = _chatgpt_find_prompt_editable(self.driver)
                if edt is not None:
                    break
            except Exception:
                pass
            time.sleep(0.4)
        log("Opened ChatGPT")

    def _get_prompt_editable(self):
        assert self.driver is not None
        found = _chatgpt_find_prompt_editable(self.driver)
        if found is not None:
            return found
        return self.driver.find_element(By.TAG_NAME, "body")

    def type_prompt_text(self, text: str, retries: int = 3) -> bool:
        assert self.driver is not None
        for attempt in range(retries):
            try:
                ed = self._get_prompt_editable()
                try:
                    ed.click()
                except Exception:
                    pass

                try:
                    self.driver.execute_script(
                        """
                        const el = arguments[0];
                        const txt = arguments[1];
                        if (!el) return false;
                        try { el.focus(); } catch(e) {}
                        if ('value' in el) {
                            el.value = txt;
                            el.dispatchEvent(new Event('input', {bubbles: true}));
                            el.dispatchEvent(new Event('change', {bubbles: true}));
                            return true;
                        }
                        try { el.textContent = txt; } catch(e) {}
                        try {
                            el.dispatchEvent(new InputEvent('input', {
                                bubbles: true,
                                data: txt,
                                inputType: 'insertText'
                            }));
                        } catch(e) {
                            try { el.dispatchEvent(new Event('input', {bubbles: true})); } catch(ee) {}
                        }
                        return true;
                        """,
                        ed,
                        text,
                    )
                    time.sleep(0.2)
                    cur = _normalize_textish(_element_visible_text(ed) or getattr(ed, "get_attribute", lambda x: "")("value") or "")
                    if not cur and pyperclip:
                        pyperclip.copy(text)
                        ed.send_keys(Keys.CONTROL, 'v')
                    return True
                except Exception:
                    if pyperclip:
                        pyperclip.copy(text)
                        ed.send_keys(Keys.CONTROL, 'v')
                    else:
                        ed.send_keys(text)
                    time.sleep(0.2)
                    return True
            except StaleElementReferenceException:
                log("ChatGPT prompt textbox went stale; retrying...", "WARN")
                time.sleep(0.3)
            except Exception as e:
                log(f"Typing ChatGPT prompt failed (attempt {attempt+1}): {e}", "WARN")
                time.sleep(0.3)
        return False

    def click_send_with_fallbacks(self, retries: int = 3) -> bool:
        assert self.driver is not None
        selectors = [
            (By.CSS_SELECTOR, "button[data-testid='send-button']"),
            (By.XPATH, "//button[contains(@aria-label,'Send')]"),
            (By.XPATH, "//button[contains(@data-testid,'send')]"),
            (By.XPATH, "//button[.//*[contains(normalize-space(.),'Send')]]"),
        ]
        for attempt in range(retries):
            try:
                if _chatgpt_generation_running(self.driver):
                    time.sleep(0.25)
                    continue

                for by, sel in selectors:
                    btns = self.driver.find_elements(by, sel)
                    if btns:
                        btn = btns[-1]
                        try:
                            WebDriverWait(self.driver, DEFAULT_TIMEOUT).until(EC.element_to_be_clickable((by, sel)))
                        except Exception:
                            pass
                        if _try_click(self.driver, btn):
                            time.sleep(0.25)
                            return True

                ed = self._get_prompt_editable()
                try:
                    ed.send_keys(Keys.CONTROL, Keys.ENTER)
                    time.sleep(0.25)
                    return True
                except Exception:
                    pass
                ed.send_keys(Keys.ENTER)
                time.sleep(0.25)
                return True
            except StaleElementReferenceException:
                log("ChatGPT send target went stale; retrying.", "WARN")
                time.sleep(0.3)
            except Exception as e:
                log(f"ChatGPT send click failed (attempt {attempt+1}): {e}", "WARN")
                time.sleep(0.3)
        return False

    def upload_files(self, paths: List[Path], max_retries: int = 3) -> None:
        assert self.driver is not None
        log(f"Uploading {len(paths)} file(s) to ChatGPT: " + ", ".join([Path(p).name for p in paths]))
        joined = "\n".join(str(Path(p).resolve()) for p in paths)

        for attempt in range(1, max_retries + 1):
            try:
                inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                if not inputs:
                    buttons = []
                    for by, sel in [
                        (By.CSS_SELECTOR, "button[aria-label*='Attach']"),
                        (By.CSS_SELECTOR, "button[aria-label*='Upload']"),
                        (By.XPATH, "//button[contains(@aria-label,'Attach')]"),
                        (By.XPATH, "//button[contains(@aria-label,'Upload')]"),
                    ]:
                        try:
                            buttons.extend(self.driver.find_elements(by, sel))
                        except Exception:
                            pass
                    for btn in reversed(buttons[-6:]):
                        try:
                            if btn.is_displayed():
                                _try_click(self.driver, btn)
                                time.sleep(0.5)
                                break
                        except Exception:
                            pass
                    inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")

                if not inputs:
                    raise RuntimeError("No <input type=file> found on ChatGPT page.")

                el = inputs[-1]
                try:
                    self.driver.execute_script(
                        """
                        arguments[0].style.display='block';
                        arguments[0].style.visibility='visible';
                        arguments[0].removeAttribute('hidden');
                        arguments[0].removeAttribute('aria-hidden');
                        """,
                        el,
                    )
                except Exception:
                    pass

                el.send_keys(joined)
                time.sleep(0.8)
                return

            except Exception as e:
                log(f"ChatGPT upload attempt {attempt}/{max_retries} failed: {e}", "WARN")
                try:
                    self.open_clean_chatgpt_chat()
                except Exception:
                    self.start(ensure_chatgpt_on_launch=True)

        raise RuntimeError("Could not initialize ChatGPT file upload path after retries.")

    def send_prompt_and_copy_response(self, instruction_text: str, wait_cap: int) -> str:
        assert self.driver is not None
        if not self.type_prompt_text(instruction_text, retries=3):
            raise RuntimeError("Could not type into ChatGPT prompt field after retries.")
        if not self.click_send_with_fallbacks(retries=3):
            raise RuntimeError("Could not send the ChatGPT prompt after retries.")
        log(f"Waiting for ChatGPT response to stabilize (COPY-first, max_wait={wait_cap}) ...")
        copied = capture_chatgpt_response_like_manual_copy(
            self.driver,
            wait_cap=wait_cap,
            prefer_latex_doc=False,
            retries=6,
        )
        if copied:
            return copied
        return adaptive_wait_and_copy_chatgpt(
            self.driver,
            max_wait=wait_cap,
            min_chars=200,
            stable_rounds=3,
            poll=0.8,
        )
