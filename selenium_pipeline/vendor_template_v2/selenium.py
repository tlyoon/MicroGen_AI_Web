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
        assert self.driver is not None
        for attempt in range(retries):
            try:
                ed = self._get_prompt_editable()
                try:
                    ed.click()
                except Exception:
                    pass
                try:
                    if pyperclip:
                        pyperclip.copy(text)
                        ed.send_keys(Keys.CONTROL, 'v')
                    else:
                        ed.send_keys(text)
                except Exception:
                    ed.send_keys(text)
                time.sleep(0.2)
                return True
            except StaleElementReferenceException:
                log("Prompt textbox went stale; retrying...", "WARN")
                time.sleep(0.3)
            except Exception as e:
                log(f"Typing prompt failed (attempt {attempt+1}): {e}", "WARN")
                time.sleep(0.3)
        return False

    def click_send_with_fallbacks(self, retries: int = 3) -> bool:
        assert self.driver is not None
        selectors = [
            '//button[@aria-label="Send message"]',
            '//button[contains(@aria-label,"Send")]',
            '//button[contains(@aria-label,"Ask")]',
            '//button[.//span[contains(normalize-space(.),"Send")]]',
            '//button[.//span[contains(normalize-space(.),"Ask")]]',
        ]
        for attempt in range(retries):
            try:
                for sel in selectors:
                    btns = self.driver.find_elements(By.XPATH, sel)
                    if btns:
                        try:
                            WebDriverWait(self.driver, DEFAULT_TIMEOUT).until(EC.element_to_be_clickable(btns[-1]))
                        except Exception:
                            pass
                        btns[-1].click()
                        time.sleep(0.25)
                        return True
                ed = self._get_prompt_editable()
                ed.send_keys(Keys.CONTROL, Keys.ENTER)
                time.sleep(0.25)
                return True
            except StaleElementReferenceException:
                log("Send target went stale; retrying.", "WARN")
                time.sleep(0.3)
            except Exception as e:
                log(f"Send click failed (attempt {attempt+1}): {e}", "WARN")
                time.sleep(0.3)
        try:
            ed = self._get_prompt_editable()
            ed.send_keys(Keys.RETURN)
            time.sleep(0.25)
            return True
        except Exception:
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
                        els[-1].click()
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
        log(f"Uploading {len(paths)} file(s): " + ", ".join([Path(p).name for p in paths]))
        joined = "\n".join(str(Path(p).resolve()) for p in paths)

        for attempt in range(1, max_retries + 1):
            try:
                got = self._ensure_file_input_any_frame_rescans()
                if not got:
                    raise RuntimeError("No <input type=file> found in document or iframes.")

                el, frame_idx = got
                if frame_idx is not None:
                    try:
                        self.driver.switch_to.frame(self.driver.find_elements(By.TAG_NAME, "iframe")[frame_idx])
                    except Exception:
                        pass

                try:
                    el.send_keys(joined)
                except Exception:
                    dismiss_native_file_dialogs(timeout=2.0)
                    time.sleep(0.2)
                    try:
                        self.driver.execute_script(
                            "arguments[0].style.display='block'; arguments[0].removeAttribute('hidden');", el
                        )
                    except Exception:
                        pass
                    el.send_keys(joined)

                self._switch_to_default()
                time.sleep(0.8)
                dismiss_native_file_dialogs(timeout=1.0)
                return

            except Exception as e:
                log(f"Upload attempt {attempt}/{max_retries} failed: {e}", "WARN")
                try:
                    self.open_clean_gemini_chat()
                except Exception:
                    self.start(ensure_gemini_on_launch=True)

        raise RuntimeError("Could not initialize file upload path after retries.")

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
