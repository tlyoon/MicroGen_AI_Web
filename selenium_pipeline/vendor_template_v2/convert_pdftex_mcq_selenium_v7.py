#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_pdftex_mcq_selenium_v5.py

TEX + PDF (+ prompt file) -> Gemini -> Moodle MCQ XML

This version keeps Gemini UI communication exclusively inside the local
selenium.py used by MicroGen_AI, and improves the XML extraction path to
prefer explicit output markers from the prompt:

    <<<BEGIN_QUIZ_XML>>>
    <quiz> ... </quiz>
    <<<END_QUIZ_XML>>>

Key improvements from v3:
- marker-based extraction is now the primary response parsing path
- fallback extraction still supports raw <quiz> blocks and fenced xml
- Gemini repair stage also accepts marked output
- corrected error-file repair submission path
- prompt default updated to pdftex_mcq_sel_v4.txt
- clearer helper structure and logging around extraction

Retained functionality:
- discover *_problemset.tex / *_problemset.pdf pairs
- upload PDF + TEX + prompt file to Gemini
- request Moodle MCQ XML generation
- extract <quiz>...</quiz>
- inject Base64 images for %%FIGURE: ...%% placeholders
- sanitize XML
- convert XML to HTML
- submit failed XML back to Gemini for repair
"""

from __future__ import annotations

import argparse
import base64
import glob
import html
import importlib.util
import io
import os
import re
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple


EXTRA_WAIT = int(os.environ["GEMINI_EXTRA_WAIT"]) if os.environ.get("GEMINI_EXTRA_WAIT") else None
PROMPT_BASENAME = "pdftex_mcq_sel_v4.txt"

def find_missing_problemset_pairs(directory="."):
    """
    Scan directory for *_problemset.tex and *_problemset.pdf pairs
    and detect which pairs do not yet have corresponding
    *_problemset_mcq.xml and *_problemset_mcq.html outputs.

    Returns:
        FILES_TO_CONVERT : list[str]
    """

    directory = Path(directory)
    files = set(os.listdir(directory))

    bases = set()

    # Identify valid problemset bases
    for f in files:
        if f.endswith("_problemset.tex"):
            base = f[:-4]  # remove .tex
            if f"{base}.pdf" in files:
                bases.add(base)

    FILES_TO_CONVERT = []

    for base in sorted(bases):

        xml_file = f"{base}_mcq.xml"
        html_file = f"{base}_mcq.html"

        if xml_file not in files or html_file not in files:
            FILES_TO_CONVERT.append(base)

    return FILES_TO_CONVERT


# Option 1: hard-coded filter for selected basename pairs.
#
# Example:
# FILES_TO_CONVERT = [
#     'SECTION_22-1_problemset',
#     'SECTION_22-2_problemset',
# ]
#
# This will process only:
#   SECTION_22-1_problemset.tex + SECTION_22-1_problemset.pdf
#   SECTION_22-2_problemset.tex + SECTION_22-2_problemset.pdf
#
# and generate:
#   SECTION_22-1_problemset_mcq.xml
#   SECTION_22-2_problemset_mcq.xml
#
# Option 2: 
# Leave as [] to process all discovered *_problemset.tex / *_problemset.pdf pairs.
#FILES_TO_CONVERT: List[str] = []
#
# Option 3: 
# Auto detecting *_problemset.tex / *_problemset.pdf pairs that are not yet converted into *.xml
#
FILES_TO_CONVERT = find_missing_problemset_pairs()
#FILES_TO_CONVERT = ['SECTION_24-5_problemset','SECTION_24-6_problemset']
print("FILES_TO_CONVERT =", FILES_TO_CONVERT)

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def log(msg: str, level: str = "INFO") -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)

def save_debug_capture(debug_dir: Path | None, stem: str, label: str, text: str) -> None:
    """
    Save raw Gemini capture text for debugging, before validation rejects it.
    """
    try:
        if debug_dir is None:
            return
        if not text:
            return

        debug_dir = Path(debug_dir)
        debug_dir.mkdir(parents=True, exist_ok=True)

        out = debug_dir / f"{stem}__{label}.txt"
        out.write_text(text, encoding="utf-8", errors="replace")

        log(f"[DEBUG] Saved raw capture: {out}", "INFO")
    except Exception as e:
        log(f"[DEBUG] Failed to save raw capture ({label}): {e}", "WARN")
        
def import_local_module(module_filename: str, module_name: str):
    candidates = [
        Path(__file__).resolve().with_name(module_filename),
        Path.cwd().resolve() / module_filename,
    ]

    for mod_path in candidates:
        if mod_path.exists():
            spec = importlib.util.spec_from_file_location(module_name, mod_path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module

    raise ImportError(
        f"Could not locate the local {module_filename} required by MicroGen_AI. "
        f"Expected it beside this script or in the current working directory."
    )


_local_selenium = import_local_module("selenium.py", "microgen_local_selenium")
SeleniumConfig = _local_selenium.Config
GeminiSeleniumClient = _local_selenium.GeminiSeleniumClient
_wait_until_generation_finishes = _local_selenium._wait_until_generation_finishes
_copy_via_toolbar_copy_button = _local_selenium._copy_via_toolbar_copy_button
_copy_via_more_menu = _local_selenium._copy_via_more_menu
capture_gemini_response_like_manual_copy = getattr(
    _local_selenium,
    'capture_gemini_response_like_manual_copy',
    None,
)
adaptive_wait_and_copy_full = getattr(
    _local_selenium,
    'adaptive_wait_and_copy_full',
    None,
)

# Compatibility fallback for older selenium.py variants.
if capture_gemini_response_like_manual_copy is None:
    def capture_gemini_response_like_manual_copy(
        driver,
        wait_cap: int = 240,
        prefer_latex_doc: bool = True,
        retries: int = 8,
        min_chars: int = 0,
        accept_fn=None,
    ) -> str:
        _wait_until_generation_finishes(driver, timeout=float(wait_cap), poll=0.5)
        txt = ''
        ###
        _local_selenium = import_local_module("selenium.py", "microgen_local_selenium")
        SeleniumConfig = _local_selenium.Config
        GeminiSeleniumClient = _local_selenium.GeminiSeleniumClient
        ###
        return ''

def has_xml_signal(text: str) -> bool:
    if not text:
        return False

    s = (text or "").strip().lower()
    if not s:
        return False

    return (
        BEGIN.lower() in s
        or END.lower() in s
        or "<quiz" in s
        or "</quiz>" in s
        or "<?xml" in s
        or "<question" in s
        or "<name>" in s
    )

def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _page_text(driver) -> str:
    try:
        txt = driver.execute_script("return (document.body && document.body.innerText) || '';")
    except Exception:
        txt = ""
    return _norm_text(txt)


def _page_has_phrase(driver, phrases) -> bool:
    hay = _page_text(driver)
    return any(_norm_text(p) in hay for p in (phrases or []))


def _element_text(el) -> str:
    try:
        txt = el.get_attribute("innerText") or el.text or ""
    except Exception:
        txt = ""
    return re.sub(r"\s+", " ", (txt or "")).strip()


def _js_click(driver, el) -> bool:
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


def _hover_reveal(driver, el) -> None:
    try:
        driver.execute_script("""
            const el = arguments[0];
            if (!el) return;
            try { el.scrollIntoView({block:'center'}); } catch (e) {}
            const r = el.getBoundingClientRect();
            const opts = {
                bubbles: true,
                cancelable: true,
                clientX: r.left + Math.min(20, Math.max(1, r.width / 2)),
                clientY: r.top + Math.min(20, Math.max(1, r.height / 2))
            };
            ['pointerover','mouseover','mouseenter','mousemove'].forEach(t => {
                try { el.dispatchEvent(new MouseEvent(t, opts)); } catch (e) {}
            });
        """, el)
    except Exception:
        pass


def _latest_response_scopes_local(driver, max_ancestors: int = 4):
    selectors = [
        "message-content",
        "div[role='article']",
        "div[class*='response']",
        "div[class*='model']",
    ]

    candidates = []
    seen = set()

    for sel in selectors:
        try:
            els = driver.find_elements("css selector", sel)
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

            txt = _element_text(el)
            if len(txt) < 20:
                continue

            try:
                meta = " ".join([
                    el.get_attribute("aria-label") or "",
                    el.get_attribute("title") or "",
                    txt,
                ]).lower()
            except Exception:
                meta = txt.lower()

            if "enter a prompt here" in meta:
                continue

            candidates.append(el)

    if not candidates:
        return []

    scope = candidates[-1]
    scopes = []
    cur = scope
    seen = set()

    for _ in range(max_ancestors + 1):
        if cur is None:
            break

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

    return scopes


def _copy_button_candidates_local(scope):
    xpaths = [
        ".//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy response')]",
        ".//button[contains(translate(@title,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy response')]",
        ".//*[@role='button' and contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy response')]",
        ".//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy')]",
        ".//button[contains(translate(@title,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy')]",
        ".//*[@role='button' and contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy')]",
    ]

    out = []
    seen = set()

    for xp in xpaths:
        try:
            found = scope.find_elements("xpath", xp)
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
                    _element_text(el),
                ]).lower()
            except Exception:
                meta = ""

            if "prompt" in meta:
                continue
            if "share" in meta:
                continue

            out.append(el)

    return out


def _more_button_candidates_local(scope):
    xpaths = [
        ".//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'more')]",
        ".//button[contains(translate(@title,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'more')]",
        ".//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'options')]",
        ".//button[contains(translate(@title,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'options')]",
        ".//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'menu')]",
        ".//button[contains(translate(@title,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'menu')]",
        ".//*[@role='button' and (normalize-space(.)='⋯' or normalize-space(.)='...')]",
    ]

    out = []
    seen = set()

    for xp in xpaths:
        try:
            found = scope.find_elements("xpath", xp)
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


def _dismiss_menu(driver):
    try:
        body = driver.find_element("tag name", "body")
        body.send_keys("\uE00C")  # ESC
        time.sleep(0.15)
    except Exception:
        pass


def _try_local_response_copy(driver, retries: int = 4) -> str:
    if pyperclip is None:
        return ""

    best = ""

    for _ in range(max(1, retries)):
        scopes = _latest_response_scopes_local(driver, max_ancestors=4)
        if not scopes:
            time.sleep(0.4)
            continue

        for scope in scopes:
            _hover_reveal(driver, scope)
            time.sleep(0.2)

            # direct response-copy buttons
            for btn in reversed(_copy_button_candidates_local(scope)[-12:]):
                try:
                    before = pyperclip.paste() or ""
                except Exception:
                    before = ""

                if not _js_click(driver, btn):
                    continue

                time.sleep(0.45)

                try:
                    after = pyperclip.paste() or ""
                except Exception:
                    after = ""

                if not after or after == before:
                    continue

                # Reject prompt copy
                if _page_has_phrase(driver, ["prompt copied"]):
                    if len(after) > len(best):
                        best = after
                    continue

                low = after.lower()
                if (
                    "</quiz>" in low
                    or (BEGIN.lower() in low and END.lower() in low)
                    or ("<quiz" in low and len(after) > 200)
                ):
                    return after.strip()

                if len(after) > len(best):
                    best = after

            # more-menu route near latest response
            for more_btn in reversed(_more_button_candidates_local(scope)[-8:]):
                _dismiss_menu(driver)

                if not _js_click(driver, more_btn):
                    continue

                time.sleep(0.25)

                menu_xpaths = [
                    "//*[self::button or self::div or self::li or self::span][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy response')]",
                    "//*[@role='menuitem'][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy response')]",
                    "//*[self::button or self::div or self::li or self::span][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy')]",
                    "//*[@role='menuitem'][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'copy')]",
                ]

                clicked_copy = False
                for xp in menu_xpaths:
                    try:
                        items = driver.find_elements("xpath", xp)
                    except Exception:
                        items = []

                    for it in reversed(items[-12:]):
                        try:
                            meta = " ".join([
                                it.get_attribute("aria-label") or "",
                                it.get_attribute("title") or "",
                                _element_text(it),
                            ]).lower()
                        except Exception:
                            meta = ""

                        if "prompt" in meta:
                            continue
                        if "share" in meta:
                            continue

                        try:
                            before = pyperclip.paste() or ""
                        except Exception:
                            before = ""

                        if not _js_click(driver, it):
                            continue

                        clicked_copy = True
                        time.sleep(0.45)

                        try:
                            after = pyperclip.paste() or ""
                        except Exception:
                            after = ""

                        if not after or after == before:
                            continue

                        if _page_has_phrase(driver, ["prompt copied"]):
                            if len(after) > len(best):
                                best = after
                            continue

                        low = after.lower()
                        if (
                            "</quiz>" in low
                            or (BEGIN.lower() in low and END.lower() in low)
                            or ("<quiz" in low and len(after) > 200)
                        ):
                            _dismiss_menu(driver)
                            return after.strip()

                        if len(after) > len(best):
                            best = after

                    if clicked_copy:
                        break

                _dismiss_menu(driver)

        time.sleep(0.6)

    return best.strip()

import sanitize_xml
import xml_to_html_v2
import shutil

try:
    import pyperclip  # noqa: F401
except Exception:
    pyperclip = None


CHROME_DEBUG_PORT = int(os.environ.get("CHROME_DEBUG_PORT", os.environ.get("GEMINI_DEVTOOLS_PORT", "9222")))
WAIT_RESPONSE_MAX = int(os.environ.get("WAIT_RESPONSE_MAX", "420"))

MCQ_PROMPT_TEMPLATE = f"""
Follow the instructions exactly as written in the attached prompt file {PROMPT_BASENAME}.
"""

BEGIN = "<<<BEGIN_QUIZ_XML>>>"
END = "<<<END_QUIZ_XML>>>"
BEGIN_RE = re.compile(re.escape(BEGIN) + r"(.*?)" + re.escape(END), re.S)

PROMPT_TEXT_CACHE: dict[str, str] = {}

PROMPT_SUFFIX = (
    "\n\n"
    f"Return ONLY the final quiz XML wrapped exactly between {BEGIN} and {END}. "
    "Do not include explanations before or after the markers."
)


def read_prompt_file_text(prompt_path: Path) -> str:
    key = str(prompt_path.resolve())

    cached = PROMPT_TEXT_CACHE.get(key)
    if cached is not None:
        return cached

    try:
        text = prompt_path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception as e:
        raise RuntimeError(f"Failed to read prompt file {prompt_path}: {e}") from e

    if not text:
        raise RuntimeError(f"Prompt file is empty: {prompt_path}")

    PROMPT_TEXT_CACHE[key] = text
    return text


def build_prompt(pdf_path: Path, prompt_path: Path) -> str:
    _ = pdf_path  # reserved for future prompt interpolation
    prompt_body = read_prompt_file_text(prompt_path)
    return prompt_body.rstrip() + PROMPT_SUFFIX



def clear_composer(client: GeminiSeleniumClient) -> None:
    if client.driver is None:
        return

    try:
        ed = _fast_find_prompt_editable(client)
    except Exception:
        return

    try:
        client.driver.execute_script("""
            const el = arguments[0];
            if (!el) return;
            el.focus();

            const clearOne = (node) => {
                if (!node) return;
                try {
                    if ('value' in node) node.value = '';
                } catch (e) {}
                try { node.innerHTML = ''; } catch (e) {}
                try { node.textContent = ''; } catch (e) {}
                try { node.innerText = ''; } catch (e) {}
                try { node.dispatchEvent(new Event('input', {bubbles: true})); } catch (e) {}
                try { node.dispatchEvent(new Event('change', {bubbles: true})); } catch (e) {}
            };

            clearOne(el);

            try {
                el.querySelectorAll('[contenteditable="true"], div[role="textbox"], textarea, p, span')
                  .forEach(clearOne);
            } catch (e) {}
        """, ed)
    except Exception:
        pass

    time.sleep(0.02)

def _page_text_lower(driver) -> str:
    try:
        txt = driver.execute_script("return (document.body && document.body.innerText) || '';")
    except Exception:
        txt = ""
    return re.sub(r"\s+", " ", (txt or "")).strip().lower()


def _count_visible_matches(driver, selectors) -> int:
    total = 0
    for sel in selectors:
        try:
            els = driver.find_elements("css selector", sel)
            total += sum(1 for e in els if e.is_displayed())
        except Exception:
            pass
    return total



# -------- Fast local helpers (script-local only; do not modify selenium.py) --------
def _fast_find_prompt_editable(client: GeminiSeleniumClient):
    """
    Faster local prompt-box finder to avoid repeated slow fallback waits in
    client._get_prompt_editable().
    """
    if client.driver is None:
        return None

    cache = getattr(client, "_mcq_prompt_cache", None)
    if cache is not None:
        try:
            if cache.is_displayed():
                return cache
        except Exception:
            pass

    selectors = [
        ("css selector", 'div[aria-label="Enter a prompt here"] [contenteditable="true"]'),
        ("css selector", '[contenteditable="true"][role="textbox"]'),
        ("css selector", 'div[role="textbox"][contenteditable="true"]'),
        ("css selector", 'textarea'),
        ("css selector", 'div[aria-label="Enter a prompt here"]'),
    ]

    for by, sel in selectors:
        try:
            els = client.driver.find_elements(by, sel)
        except Exception:
            els = []
        for el in reversed(els):
            try:
                if el.is_displayed():
                    setattr(client, "_mcq_prompt_cache", el)
                    return el
            except Exception:
                pass

    try:
        el = client.driver.execute_script(
            """
            const sels = [
              'div[aria-label="Enter a prompt here"] [contenteditable="true"]',
              '[contenteditable="true"][role="textbox"]',
              'div[role="textbox"][contenteditable="true"]',
              'textarea',
              'div[aria-label="Enter a prompt here"]'
            ];
            const isVisible = (el) => {
              if (!el) return false;
              const cs = getComputedStyle(el);
              const r = el.getBoundingClientRect();
              return cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && r.height > 0;
            };
            for (const sel of sels) {
              for (const node of document.querySelectorAll(sel)) {
                if (isVisible(node)) return node;
              }
            }
            return null;
            """
        )
        if el is not None:
            setattr(client, "_mcq_prompt_cache", el)
            return el
    except Exception:
        pass

    return None


def _attachment_probe_strict(driver) -> tuple[int, list[str]]:
    """
    Count only explicit attachment/remove affordances and filenames.
    Avoid broad selectors like [class*='file'] or [class*='chip'] that inflate
    counts with unrelated Gemini UI elements.
    """
    strict_selectors = [
        "[aria-label*='Remove file']",
        "[aria-label*='Remove attachment']",
        "[aria-label^='Remove '][role='button']",
        "button[aria-label*='Remove file']",
        "button[aria-label*='Remove attachment']",
    ]

    count = 0
    names = []

    try:
        info = driver.execute_script(
            """
            const sels = arguments[0];
            const isVisible = (el) => {
                if (!el) return false;
                const cs = getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return cs.display !== 'none' &&
                       cs.visibility !== 'hidden' &&
                       rect.width > 0 &&
                       rect.height > 0;
            };

            const out = [];
            const seen = new Set();

            for (const sel of sels) {
                for (const el of document.querySelectorAll(sel)) {
                    if (!isVisible(el)) continue;
                    const key = (el.outerHTML || '').slice(0, 180) + '|' + (el.getAttribute('aria-label') || '');
                    if (seen.has(key)) continue;
                    seen.add(key);

                    const aria = (el.getAttribute('aria-label') || '').trim();
                    let name = aria.replace(/^Remove\s+/i, '').trim();
                    if (/\.(png|jpg|jpeg|pdf|docx?|tex|txt)$/i.test(name)) {
                        out.push(name);
                    } else {
                        out.push('');
                    }
                }
            }
            return out;
            """,
            strict_selectors,
        ) or []
        count = len(info)
        names = [x.strip().lower() for x in info if isinstance(x, str) and x.strip()]
    except Exception:
        count = _count_visible_matches(driver, strict_selectors)
        names = []

    return count, names


BUSY_SELECTORS = [
    "[role='progressbar']",
    "mat-progress-bar",
    ".upload-progress",
    "[aria-label*='Uploading']",
    "[aria-label*='uploading']",
    "[aria-label*='Processing']",
    "[aria-label*='processing']",
    "[class*='progress']",
    "[class*='uploading']",
]

def get_visible_attachment_count(driver) -> int:
    count, _ = _attachment_probe_strict(driver)
    return count


def get_visible_attachment_names(driver) -> list[str]:
    _, names = _attachment_probe_strict(driver)
    return names


def wait_for_upload_to_settle(
    client: GeminiSeleniumClient,
    expected_names=None,
    timeout: float = 6.0,
    quiet_window: float = 0.25,
    poll: float = 0.08,
    baseline_attachment_count: int = 0,
    min_new_attachments: int = 0,
) -> bool:
    """
    Proceed only when upload stabilization is genuinely achieved.

    Stable criteria:
      1. no visible upload/progress indicator
      2. composer exists
      3. EITHER expected filenames are visible
         OR the visible attachment count has increased enough over baseline
      4. the above remains true for quiet_window seconds
    """
    if client.driver is None:
        return False

    expected_names = [str(x).strip().lower() for x in (expected_names or []) if str(x).strip()]

    t0 = time.time()
    good_since = None
    last_report = 0.0

    while time.time() - t0 < timeout:
        page_txt = _page_text_lower(client.driver)

        busy_count = _count_visible_matches(client.driver, BUSY_SELECTORS)
        busy_text = any(tok in page_txt for tok in ["uploading", "processing", "preparing"])

        composer_ready = False
        try:
            ed = _fast_find_prompt_editable(client)
            composer_ready = ed is not None
        except Exception:
            composer_ready = False

        attachment_count, attachment_names = _attachment_probe_strict(client.driver)
        new_attachments = max(0, attachment_count - baseline_attachment_count)

        names_seen = 0
        if expected_names:
            page_name_hits = sum(1 for name in expected_names if name in page_txt)
            chip_name_hits = sum(1 for name in expected_names if name in attachment_names)
            names_seen = max(page_name_hits, chip_name_hits)

        names_ready = bool(expected_names) and (names_seen >= len(expected_names))
        attachment_ready = (min_new_attachments > 0) and (new_attachments >= min_new_attachments)
        send_ready = get_safe_send_button(client) is not None

        files_ready = names_ready or attachment_ready or (attachment_count > baseline_attachment_count)

        signature = (busy_count, busy_text, composer_ready, names_seen, attachment_count, send_ready)
        stable_now = (busy_count == 0) and (not busy_text) and composer_ready and files_ready and send_ready

        if stable_now and signature == locals().get("_last_signature_upload_mcq"):
            if good_since is None:
                good_since = time.time()
            elif time.time() - good_since >= quiet_window:
                log(
                    f"Upload settled after {time.time() - t0:.1f}s "
                    f"(names_seen={names_seen}/{len(expected_names) if expected_names else 0}, "
                    f"attachment_count={attachment_count}, "
                    f"baseline_attachment_count={baseline_attachment_count}, "
                    f"new_attachments={new_attachments}).",
                    "INFO",
                )
                return True
        else:
            good_since = None

        _last_signature_upload_mcq = signature

        if time.time() - last_report >= 2.0:
            log(
                f"[upload-settle] busy_count={busy_count}, busy_text={busy_text}, "
                f"composer_ready={composer_ready}, "
                f"names_seen={names_seen}/{len(expected_names) if expected_names else 0}, "
                f"attachment_count={attachment_count}, "
                f"baseline_attachment_count={baseline_attachment_count}, "
                f"new_attachments={new_attachments}, "
                f"min_new_attachments={min_new_attachments}",
                "DEBUG",
            )
            last_report = time.time()

        time.sleep(poll)

    log(
        f"Upload settle timed out after {timeout:.1f}s "
        f"(names_seen={names_seen}/{len(expected_names) if expected_names else 0}, "
        f"attachment_count={attachment_count}, "
        f"baseline_attachment_count={baseline_attachment_count}, "
        f"new_attachments={new_attachments}).",
        "WARN",
    )
    return False


def stop_generation_if_present(client: GeminiSeleniumClient) -> bool:
    if client.driver is None:
        return False

    selectors = [
        "//button[contains(@aria-label,'Stop')]",
        "//button[contains(@title,'Stop')]",
        "//button[.//span[contains(normalize-space(.),'Stop')]]",
    ]

    for sel in selectors:
        try:
            btns = client.driver.find_elements('xpath', sel)
        except Exception:
            btns = []

        for btn in reversed(btns[-4:]):
            try:
                if btn.is_displayed() and btn.is_enabled():
                    try:
                        client.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    except Exception:
                        pass
                    try:
                        btn.click()
                    except Exception:
                        client.driver.execute_script('arguments[0].click();', btn)
                    time.sleep(0.40)
                    return True
            except Exception:
                pass

    return False

def get_composer_text(client: GeminiSeleniumClient) -> str:
    if client.driver is None:
        return ''

    try:
        ed = _fast_find_prompt_editable(client)
    except Exception:
        return ''

    try:
        txt = client.driver.execute_script("""
            const root = arguments[0];
            if (!root) return '';

            const vals = [];

            const harvest = (node) => {
                if (!node) return;
                try {
                    if ('value' in node && node.value && String(node.value).trim()) {
                        vals.push(String(node.value).trim());
                    }
                } catch (e) {}
                try {
                    if (node.innerText && String(node.innerText).trim()) {
                        vals.push(String(node.innerText).trim());
                    }
                } catch (e) {}
                try {
                    if (node.textContent && String(node.textContent).trim()) {
                        vals.push(String(node.textContent).trim());
                    }
                } catch (e) {}
            };

            harvest(root);

            try {
                root.querySelectorAll('[contenteditable=\"true\"], div[role=\"textbox\"], textarea, p, span')
                    .forEach(harvest);
            } catch (e) {}

            vals.sort((a, b) => b.length - a.length);
            return vals.length ? vals[0] : '';
        """, ed)

        return (txt or '').strip()
    except Exception:
        return ''


def inject_prompt_text(
    client: GeminiSeleniumClient,
    text: str,
    verify_timeout: float = 0.45,
    poll: float = 0.03,
) -> bool:
    if client.driver is None:
        return False

    try:
        ed = _fast_find_prompt_editable(client)
    except Exception:
        return False

    try:
        ok = client.driver.execute_script("""
            const root = arguments[0];
            const txt  = arguments[1];
            if (!root) return false;

            const targets = [];
            targets.push(root);

            try {
                root.querySelectorAll('[contenteditable="true"], div[role="textbox"], textarea')
                    .forEach(x => targets.push(x));
            } catch (e) {}

            const uniq = [];
            const seen = new Set();
            for (const t of targets) {
                if (t && !seen.has(t)) {
                    seen.add(t);
                    uniq.push(t);
                }
            }

            const fill = (el) => {
                try { el.focus(); } catch (e) {}

                try {
                    if ('value' in el) {
                        el.value = txt;
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                        return true;
                    }
                } catch (e) {}

                try { el.innerHTML = ''; } catch (e) {}
                try { el.textContent = txt; } catch (e) {}
                try {
                    el.dispatchEvent(new InputEvent('input', {
                        bubbles: true,
                        inputType: 'insertText',
                        data: txt
                    }));
                } catch (e) {
                    try { el.dispatchEvent(new Event('input', {bubbles: true})); } catch (ee) {}
                }
                try { el.dispatchEvent(new Event('change', {bubbles: true})); } catch (e) {}

                return true;
            };

            for (const el of uniq) {
                if (fill(el)) return true;
            }
            return false;
        """, ed, text)

        if not ok:
            return False

        t0 = time.time()
        while time.time() - t0 < verify_timeout:
            if prompt_verified_in_composer(client, text):
                return True
            time.sleep(poll)

        return prompt_verified_in_composer(client, text)
    except Exception:
        return False

def prompt_verified_in_composer(client: GeminiSeleniumClient, prompt_text: str) -> bool:
    current = ' '.join(get_composer_text(client).split())
    if not current:
        return False

    prompt_norm = ' '.join(prompt_text.split())
    probe = prompt_norm[:60].strip()
    if probe and probe in current:
        return True

    lead = prompt_norm[:220]
    tokens = [
        tok for tok in re.findall(r'[A-Za-z0-9_.:/\\-]{4,}', lead)
        if tok.lower() not in {'your', 'with', 'that', 'this', 'have', 'from', 'only', 'must'}
    ]
    hits = sum(1 for tok in tokens[:12] if tok in current)

    return len(current) >= 40 and hits >= 3


def get_safe_send_button(client: GeminiSeleniumClient):
    if client.driver is None:
        return None

    stop_selectors = [
        "//button[contains(@aria-label,'Stop')]",
        "//button[contains(@title,'Stop')]",
        "//button[.//span[contains(normalize-space(.),'Stop')]]",
    ]
    for sel in stop_selectors:
        try:
            btns = client.driver.find_elements('xpath', sel)
        except Exception:
            btns = []
        for b in btns[-3:]:
            try:
                if b.is_displayed() and b.is_enabled():
                    return None
            except Exception:
                pass

    send_selectors = [
        '//button[@aria-label=\"Send message\"]',
        '//button[contains(@aria-label,\"Send\")]',
        '//button[contains(@aria-label,\"Ask\")]',
        '//button[.//span[contains(normalize-space(.),\"Send\")]]',
        '//button[.//span[contains(normalize-space(.),\"Ask\")]]',
    ]
    for sel in send_selectors:
        try:
            btns = client.driver.find_elements('xpath', sel)
        except Exception:
            btns = []
        for b in reversed(btns[-4:]):
            try:
                if b.is_displayed() and b.is_enabled():
                    return b
            except Exception:
                pass

    return None


def click_safe_send_button(client: GeminiSeleniumClient) -> bool:
    btn = get_safe_send_button(client)
    if btn is None:
        return False

    try:
        client.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    except Exception:
        pass

    try:
        btn.click()
        time.sleep(0.05)
        return True
    except Exception:
        try:
            client.driver.execute_script('arguments[0].click();', btn)
            time.sleep(0.05)
            return True
        except Exception:
            return False

def _send_registered(client: GeminiSeleniumClient, before_text: str = "") -> bool:
    """
    Accept any of these as proof that Gemini accepted the prompt:
      - composer is empty
      - stop button appears
      - send button disappears / is disabled
      - composer text changed substantially from the pre-send snapshot
    """
    if client.driver is None:
        return False

    try:
        stop_selectors = [
            "//button[contains(@aria-label,'Stop')]",
            "//button[contains(@title,'Stop')]",
            "//button[.//span[contains(normalize-space(.),'Stop')]]",
        ]
        for sel in stop_selectors:
            btns = client.driver.find_elements('xpath', sel)
            for b in btns[-3:]:
                try:
                    if b.is_displayed() and b.is_enabled():
                        return True
                except Exception:
                    pass
    except Exception:
        pass

    cur = " ".join(get_composer_text(client).split())
    before = " ".join((before_text or "").split())

    if not cur:
        return True

    if before and cur != before and len(cur) < max(20, len(before) // 3):
        return True

    try:
        btn = get_safe_send_button(client)
        if btn is None:
            return True
    except Exception:
        pass

    return False

def wait_for_prompt_to_leave_composer(
    client: GeminiSeleniumClient,
    before_text: str = '',
    timeout: float = 3.0,
    poll: float = 0.1,
) -> bool:
    t0 = time.time()

    while time.time() - t0 < timeout:
        if _send_registered(client, before_text=before_text):
            return True
        time.sleep(poll)

    return False

def response_looks_complete(response_text: str) -> bool:
    if not response_text:
        return False

    payload = extract_xml(response_text)
    if not payload:
        return False

    payload = deverbatim(payload)
    payload = html.unescape(payload)
    payload = clean_xml_content(payload)

    s = payload.find('<quiz')
    e = payload.rfind('</quiz>')
    if s == -1 or e == -1 or e <= s:
        return False

    candidate = payload[s:e + len('</quiz>')]
    try:
        ET.fromstring(candidate)
        return True
    except Exception:
        return (BEGIN in response_text and END in response_text and '<quiz' in candidate and '</quiz>' in candidate)


def send_prompt_and_copy_response_via_copy_icon(
    client: GeminiSeleniumClient,
    instruction_text: str,
    wait_cap: int,
    retries: int = 8,
    debug_dir: Path | None = None,
    debug_stem: str = "gemini_response",
) -> str:
    if client.driver is None:
        raise RuntimeError("Selenium client driver is not available.")

    send_ok = False

    for attempt in range(3):
        if stop_generation_if_present(client):
            log(f"Stopped premature Gemini generation before prompt attempt {attempt+1}.", "WARN")
            time.sleep(0.4)

        clear_composer(client)
        time.sleep(0.1)

        injected = inject_prompt_text(client, instruction_text, verify_timeout=1.2, poll=0.1)
        if not injected:
            log(f"Prompt injection failed on attempt {attempt+1}.", "WARN")
            time.sleep(0.2)
            continue

        composer_before_send = get_composer_text(client)

        if not prompt_verified_in_composer(client, instruction_text):
            log(
                f"Prompt not confirmed in composer on attempt {attempt+1}. "
                f"Snapshot: {repr(composer_before_send[:160])}",
                "WARN",
            )
            time.sleep(0.2)
            continue

        if not click_safe_send_button(client):
            log(f"Safe Send button not available on attempt {attempt+1}.", "WARN")
            time.sleep(0.2)
            continue

        if wait_for_prompt_to_leave_composer(
            client,
            before_text=composer_before_send,
            timeout=1.2,
            poll=0.04,
        ):
            send_ok = True
            break

        log(f"Prompt did not register after Send on attempt {attempt+1}.", "WARN")
        time.sleep(0.3)

    if not send_ok:
        raise RuntimeError("Prompt could not be reliably submitted to Gemini.")

    log(f"Waiting for Gemini response to finish (max_wait={wait_cap}) ...", "INFO")
    _wait_until_generation_finishes(client.driver, timeout=float(wait_cap), poll=0.5)

    copied_text = (_try_local_response_copy(client.driver, retries=2) or "").strip()
    save_debug_capture(debug_dir, debug_stem, "local_xml_copy", copied_text)

    if copied_text and response_looks_complete(copied_text):
        return copied_text

    if copied_text and has_xml_signal(copied_text):
        log("Captured XML-like response, but completeness check was not fully satisfied.", "WARN")
        return copied_text

    raise RuntimeError("Failed to copy a complete XML response from Gemini.")

def extract_between_markers(text: str) -> str:
    if not text:
        return ""
    m = BEGIN_RE.search(text)
    return m.group(1).strip() if m else ""


def extract_code_fence_payload(s: str) -> str:
    if not s:
        return s
    blocks = re.findall(r"```(?:\s*xml)?\s*(.*?)```", s, flags=re.S | re.I)
    if not blocks:
        return s
    with_quiz = [b for b in blocks if "<quiz" in b]
    return (max(with_quiz, key=len) if with_quiz else max(blocks, key=len)).strip()


def find_best_quiz_block(s: str) -> str:
    if not s:
        return ""
    candidates = []
    for m in re.finditer(r"<quiz\b", s, flags=re.I):
        start = m.start()
        end = s.find("</quiz>", start)
        if end != -1:
            end += len("</quiz>")
            candidates.append(s[start:end])
    return max(candidates, key=len).strip() if candidates else ""


def extract_xml(raw: str) -> str:
    if not raw:
        return ""

    # 1) Explicit marker contract from pdftex_mcq_sel_v4.txt.
    marked = extract_between_markers(raw)
    if marked:
        return marked

    # 2) Fenced XML fallback.
    fenced = extract_code_fence_payload(raw)
    best = find_best_quiz_block(fenced)
    if best:
        return best

    # 3) Raw quiz block fallback on the original text.
    best = find_best_quiz_block(raw)
    if best:
        return best

    # 4) As a final fallback, return stripped raw text.
    return raw.strip()


def deverbatim(s: str) -> str:
    if not s:
        return s
    s = (
        s.replace("\\<", "<")
         .replace("\\>", ">")
         .replace("\\/", "/")
         .replace("\\!", "!")
         .replace("\\?", "?")
         .replace("\\[", "[")
         .replace("\\]", "]")
    )
    s = s.replace("\\<![CDATA[", "<![CDATA[").replace("\\]]>", "]]>")
    s = s.replace("\\_", "_").replace("\\％", "％").replace("\\%", "%")
    s = s.replace("\\\\", "\\")
    return s


_ILLEGAL_XML_CHARS = r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]"
_BARE_AMP = re.compile(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9A-Fa-f]+;)")


def clean_xml_content(xml_string: str) -> str:
    s = xml_string or ""
    s = s.replace("\ufeff", "").replace("\u2028", "")
    s = s.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    s = re.sub(_ILLEGAL_XML_CHARS, "", s)
    s = re.sub(r"<\?xml[^>]*\?>", "", s)
    s = _BARE_AMP.sub("&amp;", s)
    return s


class CDATA(str):
    pass


_CDATA_START_VAR = re.compile(r"<\s*!\s*\[\s*CDATA\s*\[", re.IGNORECASE)
_CDATA_END_VAR = re.compile(r"\]\s*\]\s*>", re.IGNORECASE)
_FENCE_LINE = re.compile(r"^\s*(```+|~~~+).*$", re.M)


def _strip_outer_lonely_angle_brackets(payload: str) -> str:
    if not payload:
        return payload
    s = payload.strip()
    if s.startswith("<") and s.endswith(">"):
        inner = s[1:-1].strip()
        if "<" not in inner and ">" not in inner and "/" not in inner:
            return inner
    return payload


def _remove_cdata_tokens_variants(s: str) -> tuple[str, int]:
    if not s:
        return s, 0
    count_before = len(_CDATA_START_VAR.findall(s)) + len(_CDATA_END_VAR.findall(s))
    s = _CDATA_START_VAR.sub("", s)
    s = _CDATA_END_VAR.sub("", s)
    count_before += s.count("<![CDATA[") + s.count("]]>")
    s = s.replace("<![CDATA[", "").replace("]]>", "")
    return s, count_before


def sanitize_text_payload(payload: str) -> tuple[str, int]:
    if payload is None:
        payload = ""
    tokens_removed = 0
    payload, removed = _remove_cdata_tokens_variants(payload)
    tokens_removed += removed
    payload = _strip_outer_lonely_angle_brackets(payload)
    payload = _FENCE_LINE.sub("", payload)
    return payload, tokens_removed


def _escape_cdata(text):
    try:
        text_str = str(text) if text is not None else ""
        return text_str.replace("]]>", "]]]]><![CDATA[>")
    except Exception:
        return ""


def _write_element_recursive(writer_func, element, encoding, level=0, indent="  "):
    if indent:
        writer_func((indent * level).encode(encoding))
    writer_func(f"<{element.tag}".encode(encoding))
    for key, value in element.attrib.items():
        writer_func(f' {key}="{html.escape(value, quote=True)}"'.encode(encoding))
    has_text = element.text and element.text.strip()
    has_children = len(element) > 0
    if not has_text and not has_children:
        writer_func("/>".encode(encoding))
    else:
        writer_func(">".encode(encoding))
        if has_text:
            if isinstance(element.text, CDATA):
                writer_func(f"<![CDATA[{_escape_cdata(element.text)}]]>".encode(encoding))
            else:
                writer_func(html.escape(element.text).encode(encoding))
        if has_children:
            if indent:
                writer_func("\n".encode(encoding))
            for child in element:
                _write_element_recursive(writer_func, child, encoding, level + 1, indent)
            if indent and has_children:
                writer_func((indent * level).encode(encoding))
        writer_func(f"</{element.tag}>".encode(encoding))
    if indent or level > 0:
        writer_func("\n".encode(encoding))


def write_xml_with_cdata(tree, filename, encoding="utf-8", xml_declaration=True, indent=None):
    filename_str = str(filename)
    if not filename_str:
        print("❌ [ERROR] Attempted write with empty filename.")
        return
    try:
        outdir = os.path.dirname(filename_str)
        if outdir:
            os.makedirs(outdir, exist_ok=True)
        with open(filename_str, "wb") as f:
            if xml_declaration:
                f.write(f'<?xml version="1.0" encoding="{encoding}"?>\n'.encode(encoding))
            _write_element_recursive(f.write, tree.getroot(), encoding, indent=indent or "")
    except Exception as e:
        print(f"❌ [ERROR] Failed XML write '{os.path.basename(filename_str)}': {e}")
        traceback.print_exc()


def post_sanitize_mcq_text(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    if root.tag != "quiz":
        q = root.find(".//quiz")
        if q is None:
            return xml_text
        root = q
    for t in root.iter("text"):
        payload = t.text or ""
        cleaned, _ = sanitize_text_payload(payload)
        t.text = CDATA(cleaned)
    buf = io.BytesIO()

    def _w(b: bytes):
        buf.write(b)

    _write_element_recursive(_w, root, "utf-8", level=0, indent="  ")
    return buf.getvalue().decode("utf-8")


def inject_base64_images(xml_content: str, search_path: Path) -> str:
    pat = re.compile(r"%%FIGURE:\s*(.*?)%%")

    def _repl(m):
        cap_name = m.group(1).strip()
        img_fname = f"{cap_name}.png"
        img_path = search_path / img_fname

        if not img_path.exists():
            log(f"  [IMG] Warning: Image file not found: {img_path.name} in {search_path}", "WARN")
            return ""

        try:
            raw_bytes = img_path.read_bytes()
            b64_str = base64.b64encode(raw_bytes).decode("ascii")
            log(f"  [IMG] Embedding {img_path.name} ({len(raw_bytes)} bytes)", "INFO")
            return (
                f'<img src="data:image/png;base64,{b64_str}" '
                f'alt="{cap_name}" '
                f'class="img-fluid" '
                f'style="max-width: 600px; height: auto; display: block; margin: 0.5em auto;" />'
            )
        except Exception as e:
            log(f"  [IMG] Failed to encode {img_path.name}: {e}", "ERR")
            return ""

    return pat.sub(_repl, xml_content)


def gemini_sanitize_mcq(mcq_error_files, client: GeminiSeleniumClient, wait_cap: int):
    if not mcq_error_files:
        log("No *_problemset_mcq__error.xml files to sanitize.", "INFO")
        return

    log(f"Gemini XML sanitize: {len(mcq_error_files)} error file(s) queued.", "INFO")

    total = 0
    errors = 0
    t0 = time.time()

    for err_path in sorted(mcq_error_files):
        err_path = Path(err_path)
        log(f"=== Gemini sanitize MCQ: {err_path.name} ===", "INFO")

        fixed_name = err_path.name.replace("__error", "") if "__error" in err_path.name else err_path.name
        fixed_path = err_path.with_name(fixed_name)

        payload = ""
        raw = ""

        try:
            client.open_clean_gemini_chat()
            client.upload_files([err_path])

            instruction = f"""
You are an expert Technical XML Editor specialized in Moodle Question Bank formats.

I have uploaded ONE file:
- {err_path.name}

This file is intended to be a valid Moodle quiz XML file but currently contains syntax errors, malformed tags, or formatting leakage.

YOUR TASK:

1. REPAIR XML SYNTAX:
   - Ensure exactly one top-level <quiz> ... </quiz> element.
   - Verify every opening tag has a matching closing tag.
   - Ensure every <text> node is wrapped exactly once in <![CDATA[ ... ]]>.
   - Fix broken CDATA sequences.

2. REMOVE NON-XML CONTENT:
   - Remove any explanation, comments, chain-of-thought, or stray text.
   - Keep only the final repaired Moodle XML.

3. PRESERVE CONTENT LOGIC:
   - Do not change the intended physics or mathematics meaning.
   - Repair formatting only.

4. OUTPUT CONTRACT:
   - Wrap the repaired XML exactly as:
     {BEGIN}
     <quiz> ... </quiz>
     {END}
   - Output nothing before {BEGIN}
   - Output nothing after {END}
"""

            raw = send_prompt_and_copy_response_via_copy_icon(
                client=client,
                instruction_text=instruction,
                wait_cap=(EXTRA_WAIT if EXTRA_WAIT else wait_cap),
            )

            if not raw.strip():
                raise RuntimeError("Gemini returned empty response during sanitize.")

            payload = extract_xml(raw)
            payload = deverbatim(payload)
            payload = html.unescape(payload)
            payload = clean_xml_content(payload)
            payload = payload.replace("]]></</text>", "]]></text>")
            payload = payload.replace("</</text>", "</text>")

            def _try_parse(text: str) -> str:
                txt = clean_xml_content(text or "")
                s = txt.find("<quiz")
                e = txt.rfind("</quiz>")
                if s != -1 and e != -1 and e > s:
                    txt = txt[s:e + len("</quiz>")]
                ET.fromstring(txt)
                return txt

            parseable = _try_parse(payload)
            pre_sanitized = post_sanitize_mcq_text(parseable)
            root = ET.fromstring(pre_sanitized)
            tree = ET.ElementTree(root)

            write_xml_with_cdata(
                tree,
                fixed_path,
                encoding="utf-8",
                xml_declaration=True,
                indent="  ",
            )

            log(f"✅ Gemini-sanitized MCQ XML -> {fixed_path.name}", "OK")
            total += 1

        except Exception as e:
            errors += 1
            warn_path = err_path.with_suffix(".sanitized_fallback.xml")
            warn = f"<!-- Gemini sanitize failed: {e} -->\n"
            fallback = payload if payload else raw
            warn_path.write_text(warn + (fallback or ""), encoding="utf-8")
            log(f"⚠️ Gemini sanitize failed for {err_path.name}, wrote fallback {warn_path.name}", "WARN")
            continue

        time.sleep(3)

    dt = time.time() - t0
    log(f"Gemini sanitize completed: fixed={total}, errors={errors}, elapsed={dt:.1f}s", "INFO")


def process_pair(
    tex_path: Path,
    pdf_path: Path,
    prompt_path: Path,
    outdir: Path,
    wait_cap: int,
    client: GeminiSeleniumClient,
):
    out_name = re.sub(r"_problemset$", "_problemset_mcq", tex_path.stem) + ".xml"
    out_path = outdir / out_name

    log("=== Processing Pair ===", "INFO")
    log(f"TEX: {tex_path.name}", "INFO")
    log(f"PDF: {pdf_path.name}", "INFO")
    log(f"PROMPT: {prompt_path.name} (read locally; not uploaded)", "INFO")
    log(f"OUT: {out_path.name}", "INFO")

    prompt = build_prompt(pdf_path, prompt_path)

    last_error = None
    raw = None

    max_rounds = 2

    for round_idx in range(1, max_rounds + 1):
        try:
            client.open_clean_gemini_chat()

            baseline_attachment_count = 0
            if client.driver is not None:
                baseline_attachment_count = get_visible_attachment_count(client.driver)

            log(
                f"Round {round_idx}/{max_rounds}: uploading 2 file(s): "
                f"{pdf_path.name}, {tex_path.name}",
                "INFO",
            )

            client.upload_files([pdf_path, tex_path])

            log("Waiting for upload to settle...", "INFO")
            settled = wait_for_upload_to_settle(
                client,
                expected_names=[pdf_path.name, tex_path.name],
                timeout=6.0,
                quiet_window=0.25,
                poll=0.08,
                baseline_attachment_count=baseline_attachment_count,
                min_new_attachments=2,
            )

            if not settled:
                raise RuntimeError("Upload did not settle reliably.")

            raw = send_prompt_and_copy_response_via_copy_icon(
                client=client,
                instruction_text=prompt,
                wait_cap=wait_cap,
                debug_dir=outdir / "_gemini_debug",
                debug_stem=tex_path.stem,
            )

            # success
            last_error = None
            break

        except Exception as e:
            last_error = e
            log(
                f"Round {round_idx}/{max_rounds} failed for {tex_path.name}: {e}",
                "WARN",
            )
            time.sleep(1.0)

    if raw is None:
        raise RuntimeError(
            f"Failed to process {tex_path.name} after {max_rounds} clean-chat round(s): {last_error}"
        )

    xml = extract_xml(raw)
    xml = deverbatim(xml)

    if not xml:
        log("No XML detected — saving raw output instead.", "WARN")
        xml = raw

    if "%%FIGURE:" in xml:
        log("Detected figure placeholders. Attempting to inject images...", "INFO")
        xml = inject_base64_images(xml, tex_path.parent)

    outdir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(xml, encoding="utf-8")
    log(f"Saved {out_path}", "INFO")

    log(f"To sanitize_xml.main() {str(out_path)}", "INFO")
    sanitize_xml.main(str(out_path))

    out_path_str = str(out_path)
    mcq_html = out_path_str.split(".xml")[0] + ".html"
    mcq_error = out_path_str.split(".xml")[0] + "__error.xml"

    xml_source_for_next_step = out_path_str
    if not os.path.isfile(xml_source_for_next_step) and os.path.isfile(mcq_error):
        log(f"sanitize_xml moved/rewrote output to {mcq_error}; using that as source.", "WARN")
        xml_source_for_next_step = mcq_error

    try:
        os.remove(mcq_html)
        log(f"Existing {mcq_html} is removed", "INFO")
    except Exception:
        log(f"No existing {mcq_html} is found", "INFO")

    try:
        log(f"Attempt to generate {mcq_html} from {xml_source_for_next_step}", "INFO")
        xml_to_html_v2.convert_single_xml(xml_source_for_next_step)
        log(f"Finish generating {mcq_html} from {xml_source_for_next_step}", "INFO")
    except Exception:
        log("xml_to_html_v2.convert_single_xml(out_path) failed to execute", "WARN")

    if os.path.isfile(mcq_html):
        log(
            f"{xml_source_for_next_step} is successfully converted into {mcq_html}. "
            f"Will not submit for correction",
            "INFO",
        )
    else:
        log(f"Do not find {mcq_html}. Will submit {xml_source_for_next_step} for correction", "WARN")

        if os.path.isfile(mcq_error):
            correction_source = mcq_error
        else:
            correction_source = mcq_error
            shutil.copy(xml_source_for_next_step, correction_source)

        gemini_sanitize_mcq([correction_source], client=client, wait_cap=wait_cap)



def normalize_requested_basenames(items: List[str] | None) -> List[str]:
    """Normalize requested file basenames by stripping quotes and extensions."""
    if not items:
        return []

    normalized: List[str] = []
    for item in items:
        if item is None:
            continue
        name = str(item).strip().strip("\"'")
        if not name:
            continue
        if name.endswith('.tex'):
            name = name[:-4]
        elif name.endswith('.pdf'):
            name = name[:-4]
        normalized.append(name)

    # preserve order while removing duplicates
    seen = set()
    ordered: List[str] = []
    for name in normalized:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def parse_files_to_convert_arg(raw: str | None) -> List[str]:
    """Parse --files into a basename list.

    Accepts forms such as:
      --files SECTION_25-1_problemset,SECTION_25-3_problemset
      --files "SECTION_25-1_problemset SECTION_25-3_problemset"
      --files "['SECTION_25-1_problemset','SECTION_25-3_problemset']"
    """
    if not raw:
        return []

    text = raw.strip()
    if not text:
        return []

    # Try Python-literal list/tuple first.
    try:
        import ast
        obj = ast.literal_eval(text)
        if isinstance(obj, (list, tuple, set)):
            return normalize_requested_basenames([str(x) for x in obj])
        if isinstance(obj, str):
            text = obj
    except Exception:
        pass

    text = text.strip().strip('[]()')
    parts = re.split(r'[\s,]+', text)
    return normalize_requested_basenames(parts)


def find_requested_pairs(root: Path, requested_basenames: List[str]) -> List[Tuple[Path, Path]]:
    """Resolve requested basenames into existing TEX/PDF pairs under root."""
    pairs: List[Tuple[Path, Path]] = []
    missing: List[str] = []

    for base in requested_basenames:
        tex_path = (root / f'{base}.tex').resolve()
        pdf_path = (root / f'{base}.pdf').resolve()

        if not tex_path.exists():
            missing.append(f'{base}.tex')
            continue
        if not pdf_path.exists():
            missing.append(f'{base}.pdf')
            continue

        pairs.append((tex_path, pdf_path))

    if missing:
        missing_str = ', '.join(missing)
        raise FileNotFoundError(f'Requested file(s) not found under {root}: {missing_str}')

    return pairs


def discover_pairs(root: Path, requested_basenames: List[str] | None = None) -> List[Tuple[Path, Path]]:
    """Discover all or selected *_problemset TEX/PDF pairs."""
    requested = normalize_requested_basenames(requested_basenames)
    if requested:
        return find_requested_pairs(root, requested)

    pattern = glob.glob(str(root / '*_problemset.tex'))
    pairs: List[Tuple[Path, Path]] = []

    for tex in pattern:
        tex_path = Path(tex)
        pdf_path = tex_path.with_suffix('.pdf')
        if pdf_path.exists():
            pairs.append((tex_path.resolve(), pdf_path.resolve()))
        else:
            log(f'Missing PDF for {tex_path.name}', 'WARN')

    return pairs

def find_prompt_file(script_dir: Path, root: Path, explicit: str = None) -> Path:
    if explicit:
        cand = root / explicit
        if cand.exists():
            return cand.resolve()
        raise FileNotFoundError(f"Explicit prompt file not found: {cand}")

    candidates = [
        script_dir / PROMPT_BASENAME,
        root / PROMPT_BASENAME,
        Path.cwd() / PROMPT_BASENAME,
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    raise FileNotFoundError(
        f"{PROMPT_BASENAME} not found next to script, in root, or in CWD."
    )


def main():
    import subprocess
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--outdir", default=None)
    parser.add_argument(
        "--wait_cap",
        type=int,
        default=WAIT_RESPONSE_MAX,
        help="Maximum seconds to wait for Gemini response per pair.",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help=f"Optional prompt filename relative to --root (default: {PROMPT_BASENAME}).",
    )
    parser.add_argument(
        "--files",
        default=None,
        help=(
            "Optional selected basenames to process only. Accepts comma-separated, "
            "space-separated, or Python-list syntax, e.g. "
            '"SECTION_25-1_problemset,SECTION_25-3_problemset" or '
            '"[\"SECTION_25-1_problemset\", \"SECTION_25-3_problemset\"]".'
        ),
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    root = Path(args.root).resolve()
    outdir_global = Path(args.outdir).resolve() if args.outdir else None

    try:
        prompt_path = find_prompt_file(script_dir, root, args.prompt)
        log(f"Using prompt file: {prompt_path}", "INFO")
    except FileNotFoundError as e:
        log(str(e), "ERR")
        raise

    cli_requested = parse_files_to_convert_arg(args.files)
    configured_requested = normalize_requested_basenames(FILES_TO_CONVERT)
    requested_basenames = cli_requested if cli_requested else configured_requested

    if requested_basenames:
        log(f"Restricted processing to selected basenames: {requested_basenames}", "INFO")
    else:
        log("No specific files requested; processing all discovered *_problemset pairs.", "INFO")

    pairs = discover_pairs(root, requested_basenames)
    log(f"Found {len(pairs)} TEX/PDF pair(s).", "INFO")

    if not pairs:
        log("No valid TEX/PDF pairs found to process.", "WARN")
        return

    selenium_cfg = SeleniumConfig(
        root=root,
        debug_port=CHROME_DEBUG_PORT,
        wait_mapping_max=args.wait_cap,
    )
    client = GeminiSeleniumClient(selenium_cfg)

    try:
        client.start(ensure_gemini_on_launch=True)
        
        ###
        for tex_path, pdf_path in pairs:
            outdir = outdir_global if outdir_global else tex_path.parent
        
            # --------------------------------------------------
            # 🔒 SKIP if BOTH XML and HTML already exist
            # --------------------------------------------------
            stem = tex_path.stem
        
            # Match the same naming logic as process_pair()
            out_xml = re.sub(r"_problemset$", "_problemset_mcq", stem) + ".xml"
            out_html = out_xml.replace(".xml", ".html")
        
            xml_path = outdir / out_xml
            html_path = outdir / out_html
        
            if xml_path.exists() and html_path.exists():
                log(f"⏭️ Skipping {stem} — outputs already exist ({out_xml}, {out_html})", "INFO")
                continue
            # --------------------------------------------------
        
            try:
                #subprocess.run([sys.executable, "launch_gemini_chrome.py"], check=True)        
                process_pair(
                    tex_path=tex_path,
                    pdf_path=pdf_path,
                    prompt_path=prompt_path,
                    outdir=outdir,
                    wait_cap=args.wait_cap,
                    client=client,
                )
                ###
                time.sleep(1.5)
                xmlname = pdf_path.name.split('.pdf')[0] + '_mcq.xml'
                log(f"Slept for 1.5 seconds after converting {pdf_path.name} into {xmlname}")
                ###
        
            except Exception as e:
                log(f"Error processing {tex_path.name}: {e}", "ERR")
        ###
        
        '''
        for tex_path, pdf_path in pairs:
            outdir = outdir_global if outdir_global else tex_path.parent
            try:                
                #subprocess.run([sys.executable, "launch_gemini_chrome.py"], check=True)
                process_pair(
                    tex_path=tex_path,
                    pdf_path=pdf_path,
                    prompt_path=prompt_path,
                    outdir=outdir,
                    wait_cap=args.wait_cap,
                    client=client,
                )
                time.sleep(10)
                xmlname = pdf_path.name.split('.pdf')[0]+'_mcq.xml'
                log(f"Slept for 10 seconds after converting {pdf_path.name} into {xmlname}")
            except Exception as e:
                log(f"Error processing {tex_path.name}: {e}", "ERR")
        '''    

    finally:
        try:
            client.shutdown()
        except Exception:
            pass

from correct_xml_abcde import fix_answernumbering
def run_pass() -> None:
    """Run one full MCQ-generation pass, then normalize answernumbering tags."""
    main()
    fix_answernumbering()


if __name__ == "__main__":
    # First pass
    run_pass()

    # Second pass: catch any *_problemset.tex / *_problemset.pdf pairs
    # that failed to generate in the first round. Already-generated
    # *_problemset_mcq.xml / *_problemset_mcq.html outputs will be skipped
    # by find_missing_problemset_pairs().
    #run_pass()
