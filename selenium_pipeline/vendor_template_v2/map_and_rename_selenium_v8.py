# MicroGen_AI Educational Automation Package
# (c) 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.
# This file is part of the MicroGen_AI package.
#
# Licensed under the MIT License (see LICENSE file in the project root).
#
# You may not use this file except in compliance with the License.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
# -*- coding: utf-8 -*-

from __future__ import annotations
import os, re, sys, time, json, socket, shutil, tempfile, subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

# Console encoding (Windows)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# -------- Logging --------
def log(msg: str, level: str = "INFO") -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)

def natural_sort_key(s: str):
    import re as _re
    return [int(t) if t.isdigit() else t.lower() for t in _re.split(r"(\d+)", s)]


# -------- Timing helpers --------
def _ts_now() -> float:
    return time.perf_counter()


def _fmt_dt(dt: float) -> str:
    return f"{dt:.3f}s"


def log_timing(stage: str, started_at: float, detail: str = "", level: str = "INFO") -> None:
    msg = f"[TIMING] {stage}: {_fmt_dt(_ts_now() - started_at)}"
    if detail:
        msg += f" | {detail}"
    log(msg, level)


class GeminiGenerationStalled(RuntimeError):
    """Gemini accepted the prompt but remained generating without a response node."""
    pass

# ==========================================================
# Selenium/Gemini communication layer (reusable)
#   - implemented in ./selenium.py (local file)
# ==========================================================
import importlib.util
# Force-load the LOCAL selenium.py (Gemini UI automation module), not the pip selenium package
_SEL_PATH = Path(__file__).with_name("selenium.py")
spec = importlib.util.spec_from_file_location("gemini_selenium", str(_SEL_PATH))
gemsel = importlib.util.module_from_spec(spec)
assert spec and spec.loader, f"Failed to load local selenium.py from {_SEL_PATH}"
import sys as _sys
# dataclasses needs the module registered in sys.modules during exec_module
_sys.modules[spec.name] = gemsel
spec.loader.exec_module(gemsel)

# -------- Config --------
# Keep your original Config for this script's CLI ergonomics.
# The Selenium client accepts an instance of gemsel.Config, so we mirror fields.
@dataclass
class Config:
    root: Path
    pages_dir: str = "pages"
    crops_dir: str = "crops"
    gemini_url: str = "https://gemini.google.com/app"
    debug_port: int = 9222
    wait_mapping_max: int = 120
    chrome_exe: str = os.getenv("CHROME_EXE", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    user_data_dir: str = os.getenv("GEMINI_USER_DATA_DIR", str(Path.home() / "AppData/Local/Google/Chrome/User Data"))
    profile_directory: str = os.getenv("GEMINI_PROFILE_DIRECTORY", "Default")
    fallback_user_data_dir: str = str(Path(tempfile.gettempdir()) / "gemini_selenium_fallback")
    fallback_profile_directory: str = "Default"
    use_persistent_chrome: bool = True
    force_kill_chrome_to_free_port: bool = (os.getenv("SAFE_CHROME", "0") != "1")


# -------- Prompt, parsing, cleaning --------
COMBINED_MAPPING_PROMPT = (
    "You are given:\n"
    " A full textbook PAGE IMAGE (png) that may contain multiple figure captions/numbers.\n"
    " Several FIGURE CROPS (png) clipped from that same page.\n\n"
    "TASK (plain text only): For EACH crop file, determine the most appropriate caption label as it appears on the page, "
    "then propose a target filename.\n\n"
    "OUTPUT RULES (no extra commentary, no markdown):\n"
    "  One line per crop, exactly in the format:\n"
    '  fig_2.png : "Figure 21-5" : Figure 21-5.png\n'
    '  fig_1.png : "Fig. 41.3"   : Fig. 41.3.png\n'
    '  fig_5.png : "Figure TP41.3" : Figure TP41.3.png\n'
    "  Use ASCII quotes (\") around the caption label.\n"
    "  If a crop has no explicit label on the page, use \"Unlabeled image\" and a short, 2-6 word description for the target filename.\n"
    "  Do not include bullets, code fences, or extra lines."
)

SMART_TO_ASCII = str.maketrans({
    "\u201c": '"', "\u201d": '"', "\u2019": "'", "\u2018": "'",
    "\u2010": "-", "\u2013": "-", "\u2014": "-",
})

CODEFENCE_RE = re.compile(r"```(?:[a-zA-Z0-9_-]*)?\s*([\s\S]*?)```", re.MULTILINE)


def clean_model_text(txt: str) -> str:
    if not txt:
        return ""
    blocks = CODEFENCE_RE.findall(txt)
    if blocks:
        txt = "\n".join(blocks)
    lines = []
    for line in txt.splitlines():
        line = line.translate(SMART_TO_ASCII)
        line = re.sub(r'^\s*(?:[-*\u2022]\s+)', '', line)
        lines.append(line.rstrip())
    return "\n".join(lines).strip()

# SAFE PARSER v7 -- prevents mixed filenames completely
MAP_PATTERN = re.compile(
    r"""
    ^\s*
    (?P<src>[A-Za-z0-9_.-]+\.png)       # source figure file
    \s*(?::|->|-)+\s*                  # separator: colon, dash, or ASCII arrow
    (?P<name>.+?)                        # human-readable name
    \s*(?::|->|-)+\s*                  # separator: colon, dash, or ASCII arrow
    (?P<dst>[A-Za-z0-9_. -]+\.png)      # output figure filename
    \s*$
    """,
    re.VERBOSE,
)

def parse_mapping_lines(text: str) -> List[Tuple[str, str, str]]:
    """
    Parse mapping lines like:
      fig_2.png : "Figure 22.1 (a)" : Figure 22.1 (a).png
      input_file_1.png : "Figure 22.4" : Figure 22.4.png
      crop_2.png : "Figure 22.5" : Figure 22.5.png

    Returns list of (returned_name, label, target_png).
    The returned_name is parsed for completeness but should not be trusted.
    """
    if not text:
        return []

    smart = {
        "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
        "\u2019": "'", "\u2018": "'", "\u201b": "'", "\u2032": "'",
        "\uff1a": ":",
        "\u2013": "-", "\u2014": "-", "\u2010": "-",
    }
    for a, b in smart.items():
        text = text.replace(a, b)

    triples: List[Tuple[str, str, str]] = []
    lines = text.splitlines()

    pat = re.compile(
        r"""^\s*
            (?:[-*\u2022]\s*)?
            `?
            (?P<crop>[A-Za-z0-9_.-]+\.png)
            `?\s*:\s*
            (?P<label>"[^"]*"|[^:]*?)
            \s*:\s*
            (?P<target>[^#\r\n]*?\.png)
            \s*$""",
        re.IGNORECASE | re.VERBOSE,
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue

        line = line.strip("`")
        m = pat.match(line)
        if not m:
            continue

        crop = m.group("crop").strip()
        label = m.group("label").strip()
        target = m.group("target").strip()

        if len(label) >= 2 and label[0] == '"' and label[-1] == '"':
            label = label[1:-1].strip()

        target = re.sub(r"[.,;:\s]+$", "", target)

        triples.append((crop, label, target))

    return triples


# -------- Merge helpers --------
try:
    from PIL import Image
except Exception:
    Image = None

MIN_PNG_KB       = float(os.getenv("MIN_PNG_KB", "2.55"))
OVERWRITE_ALWAYS = True  # set False to suffix __1, __2, ...

def _file_kb(p: Path) -> float:
    try: return p.stat().st_size / 1024.0
    except Exception: return 0.0

def merge_images_horizontally(image_paths: List[Path], output_path: Path):
    if Image is None:
        log("Pillow not installed; skip merging.", "WARN")
        return
    imgs = [Image.open(p) for p in image_paths if p.exists() and _file_kb(p) >= MIN_PNG_KB]
    if not imgs:
        return
    widths, heights = zip(*(im.size for im in imgs))
    total_w, max_h = sum(widths), max(heights)
    merged = Image.new("RGB", (total_w, max_h), (255, 255, 255))
    x = 0
    for im in imgs:
        merged.paste(im, (x, 0)); x += im.width
    merged.save(output_path)
    for im in imgs: im.close()
    log(f"[MERGE] {len(imgs)} parts -> {output_path.name}")




# -------- Thick Gemini UI guards / capture (aligned with fix_latex_selenium_v4.py) --------

# -------- Fast local composer helpers (avoid repeated slow _get_prompt_editable calls) --------
def _fast_find_prompt_editable(client):
    """
    Faster local prompt-box finder for this script only.
    We avoid repeated calls to client._get_prompt_editable(), which can spend
    multiple 4-second waits across selector fallbacks inside selenium.py.
    """
    if client.driver is None:
        return None

    cache = getattr(client, "_map_prompt_cache", None)
    if cache is not None:
        try:
            if cache.is_displayed():
                return cache
        except Exception:
            pass

    selectors = [
        ('css selector', 'div[aria-label="Enter a prompt here"] [contenteditable="true"]'),
        ('css selector', '[contenteditable="true"][role="textbox"]'),
        ('css selector', 'div[role="textbox"][contenteditable="true"]'),
        ('css selector', 'textarea'),
        ('css selector', 'div[aria-label="Enter a prompt here"]'),
    ]

    for by, sel in selectors:
        try:
            els = client.driver.find_elements(by, sel)
        except Exception:
            els = []
        for el in reversed(els):
            try:
                if el.is_displayed():
                    setattr(client, "_map_prompt_cache", el)
                    return el
            except Exception:
                pass

    # lightweight JS fallback
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
              const nodes = Array.from(document.querySelectorAll(sel));
              for (const el of nodes) {
                if (isVisible(el)) return el;
              }
            }
            return null;
            """
        )
        if el is not None:
            setattr(client, "_map_prompt_cache", el)
            return el
    except Exception:
        pass

    return None


def clear_composer(client) -> None:
    if client.driver is None:
        return

    try:
        ed = _fast_find_prompt_editable(client)
    except Exception:
        return
    if ed is None:
        return

    # Gemini currently uses a Quill editor. Select its contents and invoke the
    # browser editing command so Quill receives a real editor deletion and keeps
    # its internal model synchronized with the DOM.
    try:
        client.driver.execute_script(
            """
            const e=arguments[0];
            e.focus();
            const r=document.createRange();
            r.selectNodeContents(e);
            const s=window.getSelection();
            s.removeAllRanges();
            s.addRange(r);
            document.execCommand('delete', false, null);
            """,
            ed,
        )
        time.sleep(0.08)
        if not get_composer_text(client).strip():
            return
    except Exception:
        pass

    # Last-resort cleanup for an already-corrupt/stale draft.
    try:
        client.driver.execute_script(
            "arguments[0].innerHTML='<p><br></p>'; arguments[0].dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'deleteContentBackward'}));",
            ed,
        )
    except Exception:
        pass
    time.sleep(0.05)


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


def _attachment_probe(driver) -> tuple[int, list[str]]:
    """
    Count attachment indicators conservatively.

    We intentionally avoid broad selectors such as [class*='file'] because they
    can match unrelated UI elements and make the script wait much longer than
    necessary. We prefer explicit "remove attachment/file" affordances and
    filename chips when available.
    """
    strict_selectors = [
        "gem-media-attachment",
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
                    let name = aria.replace(/^Remove\\s+/i, '').trim();
                    if (/\\.(png|jpg|jpeg|pdf|docx?|tex|txt)$/i.test(name)) {
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

    # Gemini's current image attachment UI can expose only the status text
    # "Image uploaded" rather than filename/remove chips. Treat each visible
    # status as a confirmed attachment signal.
    try:
        body = (driver.find_element("tag name", "body").text or "")
        uploaded = body.lower().count("image uploaded")
        if uploaded > count:
            count = uploaded
    except Exception:
        pass

    return count, names


def get_visible_attachment_count(driver) -> int:
    count, _ = _attachment_probe(driver)
    return count


def get_visible_attachment_names(driver) -> list[str]:
    _, names = _attachment_probe(driver)
    return names


def get_latest_response_text(driver) -> str:
    # Prefer the concrete current Gemini response containers. Broad class
    # selectors are retained only as fallbacks because they can match thinking
    # chrome or unrelated UI and hide the actual completed answer.
    selectors = [
        "model-response message-content",
        "model-response .model-response-text",
        "model-response",
        "message-content",
        "div[role='article']",
        "div[class*='response']",
        "div[class*='model']",
    ]
    for sel in selectors:
        try:
            els = driver.find_elements("css selector", sel)
        except Exception:
            els = []
        if not els:
            continue
        for el in reversed(els[-4:]):
            try:
                txt = (el.get_attribute("innerText") or el.text or "").strip()
            except Exception:
                txt = ""
            if len(txt) >= 10:
                return txt
    return ""


def wait_for_mapping_response_ready(client, baseline_text: str = "", timeout: float = 120.0, poll: float = 0.30) -> str:
    """
    End the response wait as soon as the latest response contains parseable
    mapping lines. Also fail fast when Gemini is visibly generating but never
    creates a model-response node, which is the observed Pro stall mode.
    """
    if client.driver is None:
        return ""

    last = ""
    stable = 0
    t0 = time.time()
    stall_started = None
    stall_limit = float(os.getenv("GEMINI_MAPPING_STALL_SECONDS", "25"))

    while time.time() - t0 < timeout:
        cur = clean_model_text(get_latest_response_text(client.driver))

        generating = False
        try:
            for sel in [
                "//button[contains(@aria-label,'Stop')]",
                "//button[contains(@title,'Stop')]",
                "//button[.//span[contains(normalize-space(.),'Stop')]]",
            ]:
                btns = client.driver.find_elements("xpath", sel)
                for b in btns[-3:]:
                    try:
                        if b.is_displayed() and b.is_enabled():
                            generating = True
                            break
                    except Exception:
                        pass
                if generating:
                    break
        except Exception:
            generating = False

        try:
            model_count = len([
                e for e in client.driver.find_elements("css selector", "model-response")
                if e.is_displayed()
            ])
        except Exception:
            model_count = 0

        if generating and model_count == 0:
            if stall_started is None:
                stall_started = time.time()
            elif time.time() - stall_started >= stall_limit:
                elapsed = time.time() - stall_started
                log(
                    f"Gemini generation stall detected: Stop response persisted {elapsed:.1f}s "
                    f"with zero model-response nodes.",
                    "WARN",
                )
                raise GeminiGenerationStalled(
                    f"Gemini generation stalled for {elapsed:.1f}s with no model-response node."
                )
        else:
            stall_started = None

        if cur:
            parsed = parse_mapping_lines(cur)
            if parsed:
                if cur == last:
                    stable += 1
                else:
                    last = cur
                    stable = 0
                if stable >= 1 and not generating:
                    log(
                        f"Mapping response confirmed early after {time.time() - t0:.1f}s "
                        f"with {len(parsed)} parseable line(s).",
                        "INFO",
                    )
                    return cur

        time.sleep(poll)

    return ""


def wait_for_upload_to_settle(
    client,
    expected_names=None,
    timeout: float = 4.0,
    quiet_window: float = 0.20,
    poll: float = 0.08,
    baseline_attachment_count: int = 0,
    min_new_attachments: int = 0,
) -> bool:
    """
    Faster but still confirmed upload-settle guard.

    We proceed only after all of the following are true:
      1. no visible upload/progress indicator
      2. composer exists
      3. attachment evidence is present (by explicit filename chips or strict
         attachment/remove controls)
      4. the evidence is stable for a short quiet window

    This avoids long waits caused by overly broad page-wide attachment matches.
    """
    t_wait = _ts_now()
    if client.driver is None:
        log_timing("upload settle skipped", t_wait, "driver unavailable", level="WARN")
        return False

    expected_names = [str(x).strip().lower() for x in (expected_names or []) if str(x).strip()]

    busy_selectors = [
        ".upload-progress",
        "[aria-label*='Uploading']",
        "[aria-label*='uploading']",
        "[aria-label*='Processing upload']",
        "[aria-label*='processing upload']",
        "[class*='uploading']",
    ]

    good_since = None
    last_signature = None
    last_detail = ""

    while _ts_now() - t_wait < timeout:
        page_txt = _page_text_lower(client.driver)

        busy_count = _count_visible_matches(client.driver, busy_selectors)
        busy_text = any(tok in page_txt for tok in ["uploading", "processing", "preparing"])

        composer_ready = False
        try:
            ed = _fast_find_prompt_editable(client)
            composer_ready = ed is not None
        except Exception:
            composer_ready = False

        attachment_count, attachment_names = _attachment_probe(client.driver)
        new_attachments = max(0, attachment_count - baseline_attachment_count)

        names_seen = 0
        if expected_names:
            page_name_hits = sum(1 for name in expected_names if name in page_txt)
            chip_name_hits = sum(1 for name in expected_names if name in attachment_names)
            names_seen = max(page_name_hits, chip_name_hits)

        names_ready = bool(expected_names) and (names_seen >= len(expected_names))
        attachment_ready = (min_new_attachments > 0) and (new_attachments >= min_new_attachments)
        send_ready = get_safe_send_button(client) is not None

        # Current Gemini can collapse a multi-image batch into one visible
        # "Image uploaded" status instead of one chip per file. upload_files()
        # has already fail-closed unless Gemini visibly acknowledged the batch,
        # so a visible acknowledgement is sufficient here.
        upload_ack = "image uploaded" in page_txt and "file upload error" not in page_txt
        # The 2026 Gemini composer can hide filenames/remove controls after a
        # successful image batch and expose only the accessible status
        # "Image uploaded". Treat that acknowledgement as authoritative.
        files_ready = names_ready or attachment_ready or (attachment_count > baseline_attachment_count) or upload_ack

        signature = (busy_count, busy_text, attachment_count, names_seen, upload_ack, send_ready, composer_ready)
        # "Image uploaded" itself contains the substring "upload", but it is a
        # completed-state acknowledgement, not a busy indicator. Ignore generic
        # busy_text once this positive acknowledgement is present.
        stable_now = (busy_count == 0) and (not busy_text or upload_ack) and composer_ready and files_ready and send_ready
        last_detail = (
            f"names_seen={names_seen}/{len(expected_names) if expected_names else 0}, "
            f"attachment_count={attachment_count}, baseline_attachment_count={baseline_attachment_count}, "
            f"new_attachments={new_attachments}, composer_ready={composer_ready}, send_ready={send_ready}, "
            f"busy_count={busy_count}, busy_text={busy_text}"
        )

        if stable_now and signature == last_signature:
            if good_since is None:
                good_since = _ts_now()
            elif _ts_now() - good_since >= quiet_window:
                log_timing("upload settle confirmed", t_wait, last_detail)
                return True
        else:
            good_since = None

        last_signature = signature
        time.sleep(poll)

    log_timing("upload settle timeout", t_wait, last_detail, level="WARN")
    return False


def stop_generation_if_present(client) -> bool:
    if client.driver is None:
        return False

    selectors = [
        "//button[contains(@aria-label,'Stop')]",
        "//button[contains(@title,'Stop')]",
        "//button[.//span[contains(normalize-space(.),'Stop')]]",
    ]

    for sel in selectors:
        try:
            btns = client.driver.find_elements("xpath", sel)
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
                        client.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.08)
                    return True
            except Exception:
                pass

    return False


def get_composer_text(client) -> str:
    if client.driver is None:
        return ""

    try:
        ed = _fast_find_prompt_editable(client)
    except Exception:
        return ""

    try:
        txt = client.driver.execute_script(
            """
            const root = arguments[0];
            if (!root) return "";

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
                root.querySelectorAll('[contenteditable="true"], div[role="textbox"], textarea, p, span')
                    .forEach(harvest);
            } catch (e) {}

            vals.sort((a, b) => b.length - a.length);
            return vals.length ? vals[0] : "";
            """,
            ed,
        )
        return (txt or "").strip()
    except Exception:
        return ""


def inject_prompt_text(client, text: str, verify_timeout: float = 1.2, poll: float = 0.04) -> bool:
    """Paste into the actual visible contenteditable so Gemini records trusted editor input."""
    t_inject = _ts_now()
    if client.driver is None:
        log_timing("prompt inject skipped", t_inject, "driver unavailable", level="WARN")
        return False

    try:
        ed = _fast_find_prompt_editable(client)
        if ed is None:
            log_timing("prompt inject trusted", t_inject, "editable not found", level="WARN")
            return False

        ed.click()
        # WebDriver send_keys() is silently ignored by Gemini's Quill editor on
        # this Chrome build. CDP Input.insertText goes through Chrome's input
        # pipeline and has been live-verified to update the Quill document.
        client.driver.execute_cdp_cmd("Input.insertText", {"text": text})

        log_timing("prompt inject trusted", t_inject, "CDP Input.insertText dispatched")
        t0 = _ts_now()
        while _ts_now() - t0 < verify_timeout:
            if prompt_verified_in_composer(client, text):
                log_timing("prompt verify after inject", t0, "prompt confirmed in composer")
                return True
            time.sleep(poll)

        verified = prompt_verified_in_composer(client, text)
        log_timing("prompt verify after inject", t0, f"verified={verified}", level=("INFO" if verified else "WARN"))
        return verified

    except Exception as e:
        log_timing("prompt inject exception", t_inject, repr(e), level="WARN")
        return False


def prompt_verified_in_composer(client, prompt_text: str) -> bool:
    current = " ".join(get_composer_text(client).split())
    if not current:
        return False

    prompt_norm = " ".join(prompt_text.split())
    probe = prompt_norm[:60].strip()
    if probe and probe in current:
        return True

    lead = prompt_norm[:220]
    tokens = [
        tok for tok in re.findall(r"[A-Za-z0-9_.:/\\\\-]{4,}", lead)
        if tok.lower() not in {"your", "with", "that", "this", "have", "from", "only", "must"}
    ]
    hits = sum(1 for tok in tokens[:12] if tok in current)

    return len(current) >= 40 and hits >= 3


def get_safe_send_button(client):
    if client.driver is None:
        return None

    stop_selectors = [
        "//button[contains(@aria-label,'Stop')]",
        "//button[contains(@title,'Stop')]",
        "//button[.//span[contains(normalize-space(.),'Stop')]]",
    ]
    for sel in stop_selectors:
        try:
            btns = client.driver.find_elements("xpath", sel)
        except Exception:
            btns = []
        for b in btns[-3:]:
            try:
                if b.is_displayed() and b.is_enabled():
                    return None
            except Exception:
                pass

    send_selectors = [
        '//button[@aria-label="Send message"]',
        '//button[contains(@aria-label,"Send")]',
        '//button[contains(@aria-label,"Ask")]',
        '//button[.//span[contains(normalize-space(.),"Send")]]',
        '//button[.//span[contains(normalize-space(.),"Ask")]]',
    ]
    for sel in send_selectors:
        try:
            btns = client.driver.find_elements("xpath", sel)
        except Exception:
            btns = []
        for b in reversed(btns[-4:]):
            try:
                if b.is_displayed() and b.is_enabled():
                    return b
            except Exception:
                pass

    return None




def wait_until_send_actionable(
    client,
    prompt_text: str = "",
    timeout: float = 8.0,
    poll: float = 0.04,
    stable_rounds: int = 1,
) -> bool:
    """
    Fast pre-send gate:
      - prompt is still present in the composer
      - no obvious upload/progress indicator remains
      - Send button is visible and enabled

    We poll these exact conditions at high frequency and proceed immediately
    once they are stable. This targets the specific stall where the prompt is
    already visible in Gemini's composer but Send has not yet become safely
    actionable.
    """
    if client.driver is None:
        return False

    prompt_probe = " ".join((prompt_text or "").split())[:80].strip()
    t0 = _ts_now()
    stable = 0
    last_status = {}

    while _ts_now() - t0 < timeout:
        try:
            status = client.driver.execute_script(
                """
                const probe = arguments[0] || "";
                const norm = (s) => String(s || "").replace(/\s+/g, " ").trim();

                const isVisible = (el) => {
                    if (!el) return false;
                    const cs = getComputedStyle(el);
                    const r = el.getBoundingClientRect();
                    return cs.display !== "none" &&
                           cs.visibility !== "hidden" &&
                           r.width > 0 && r.height > 0;
                };

                const bodyText = norm((document.body && document.body.innerText) || "").toLowerCase();

                let busyCount = 0;
                const busySelectors = [
                    ".upload-progress",
                    "[aria-label*='Uploading']",
                    "[aria-label*='uploading']",
                    "[aria-label*='Processing upload']",
                    "[aria-label*='processing upload']",
                    "[class*='uploading']",
                ];
                for (const sel of busySelectors) {
                    try {
                        for (const el of document.querySelectorAll(sel)) {
                            if (isVisible(el)) busyCount += 1;
                        }
                    } catch (e) {}
                }

                let composerText = "";
                const composerSelectors = [
                    'div[aria-label="Enter a prompt here"] [contenteditable="true"]',
                    'div[aria-label="Enter a prompt here"]',
                    '[contenteditable="true"][role="textbox"]',
                    'div[role="textbox"][contenteditable="true"]',
                    'textarea',
                ];
                for (const sel of composerSelectors) {
                    try {
                        const nodes = Array.from(document.querySelectorAll(sel));
                        for (const el of nodes) {
                            if (!isVisible(el)) continue;
                            const vals = [
                                el.value,
                                el.innerText,
                                el.textContent,
                            ].map(norm).filter(Boolean);
                            if (vals.length) {
                                vals.sort((a,b) => b.length - a.length);
                                composerText = vals[0];
                                break;
                            }
                        }
                    } catch (e) {}
                    if (composerText) break;
                }

                let sendEnabled = false;
                const sendX = [
                    "//button[@aria-label='Send message']",
                    "//button[contains(@aria-label,'Send')]",
                    "//button[contains(@aria-label,'Ask')]",
                    "//button[.//span[contains(normalize-space(.),'Send')]]",
                    "//button[.//span[contains(normalize-space(.),'Ask')]]",
                ];
                const stopX = [
                    "//button[contains(@aria-label,'Stop')]",
                    "//button[contains(@title,'Stop')]",
                    "//button[.//span[contains(normalize-space(.),'Stop')]]",
                ];

                const hasVisibleEnabled = (xps) => {
                    for (const xp of xps) {
                        try {
                            const it = document.evaluate(xp, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                            for (let i = 0; i < it.snapshotLength; i++) {
                                const el = it.snapshotItem(i);
                                if (isVisible(el) && !el.disabled && el.getAttribute("aria-disabled") !== "true") {
                                    return true;
                                }
                            }
                        } catch (e) {}
                    }
                    return false;
                };

                const stopVisible = hasVisibleEnabled(stopX);
                if (!stopVisible) {
                    sendEnabled = hasVisibleEnabled(sendX);
                }

                const probeOk = !probe || composerText.includes(probe);
                const busyText = ["uploading", "processing", "preparing"].some(tok => bodyText.includes(tok));

                return {
                    prompt_ok: probeOk,
                    send_ready: sendEnabled,
                    busy_count: busyCount,
                    busy_text: busyText,
                    composer_text: composerText.slice(0, 120),
                };
                """,
                prompt_probe,
            ) or {}
        except Exception:
            status = {}

        last_status = status or {}
        prompt_ok = bool(status.get("prompt_ok"))
        send_ready = bool(status.get("send_ready"))
        busy_count = int(status.get("busy_count", 0) or 0)
        busy_text = bool(status.get("busy_text"))

        if prompt_ok and send_ready and busy_count == 0 and not busy_text:
            stable += 1
            if stable >= stable_rounds:
                log_timing("send actionable wait", t0, f"stable_rounds={stable_rounds}, composer={status.get('composer_text','')[:80]}")
                return True
        else:
            stable = 0

        time.sleep(poll)

    detail = (
        f"prompt_ok={bool(last_status.get('prompt_ok'))}, send_ready={bool(last_status.get('send_ready'))}, "
        f"busy_count={int(last_status.get('busy_count', 0) or 0)}, busy_text={bool(last_status.get('busy_text'))}, "
        f"composer={str(last_status.get('composer_text', ''))[:80]}"
    )
    log_timing("send actionable wait timeout", t0, detail, level="WARN")
    return False

def click_safe_send_button(client, before_model_count: int = 0, before_user_count: int = 0) -> bool:
    t_click = _ts_now()
    btn = get_safe_send_button(client)
    if btn is None:
        # Do not press Enter for image-bearing mapping requests. Gemini can
        # clear the composer and make that look submitted without actually
        # starting multimodal generation. Wait briefly for the real Send
        # control to materialize after attachment processing.
        deadline = time.time() + 5.0
        while time.time() < deadline and btn is None:
            time.sleep(0.10)
            btn = get_safe_send_button(client)
        if btn is None:
            # The readiness probe can see current Gemini's icon-only submit
            # control even when legacy XPath selectors cannot. Resolve that
            # exact enabled button with DOM semantics and return it to Selenium.
            try:
                btn = client.driver.execute_script(
                    """
                    const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
                    const buttons = [...document.querySelectorAll('button')].filter(visible);
                    const scored = buttons.filter(b => {
                      const s=((b.getAttribute('aria-label')||'')+' '+(b.getAttribute('data-tooltip')||'')+' '+(b.title||'')+' '+(b.textContent||'')).toLowerCase();
                      const disabled=b.disabled || b.getAttribute('aria-disabled')==='true';
                      return !disabled && (s.includes('send') || s.includes('submit'));
                    });
                    return scored.length ? scored[scored.length-1] : null;
                    """
                )
            except Exception:
                btn = None
        if btn is None:
            log_timing("send click skipped", t_click, "real Gemini Send control unavailable; Enter fallback disabled", level="WARN")
            return False

    try:
        client.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    except Exception:
        pass

    def _has_send_effect() -> bool:
        try:
            return bool(client.driver.execute_script(
                """
                const beforeModels=Number(arguments[0]||0);
                const beforeUsers=Number(arguments[1]||0);
                const vis=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const stop=[...document.querySelectorAll('button')].some(
                    b=>vis(b)&&((b.getAttribute('aria-label')||'').toLowerCase().includes('stop'))
                );
                const users=[...document.querySelectorAll('user-query')].filter(vis).length;
                const models=[...document.querySelectorAll('model-response')].filter(vis).length;
                return stop || users>beforeUsers || models>beforeModels;
                """,
                int(before_model_count),
                int(before_user_count),
            ))
        except Exception:
            return False

    try:
        btn.click()
        time.sleep(0.20)
        if _has_send_effect():
            log_timing("send click", t_click, "native click with confirmed UI effect")
            return True
        log_timing("send click semantic miss", t_click, "native click returned but Gemini state did not change", level="WARN")
    except Exception as e:
        log(f"[SEND-DIAG] native click raised {e!r}", "WARN")

    try:
        # With a Quill prompt entered through CDP, first try Chrome's keyboard
        # pipeline. Some Gemini builds still discard CDP key events, so a final
        # native-Windows fallback follows below.
        ed = _fast_find_prompt_editable(client)
        if ed is None:
            raise RuntimeError("Gemini prompt editor unavailable for Enter submit")
        ed.click()
        client.driver.execute_cdp_cmd("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13
        })
        client.driver.execute_cdp_cmd("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13
        })
        time.sleep(0.35)
        if _has_send_effect():
            log_timing("send click", t_click, "CDP Enter with confirmed UI effect")
            return True
        log_timing("send click semantic miss", t_click, "CDP Enter produced no Gemini state change", level="WARN")
    except Exception as e:
        log(f"[SEND-DIAG] CDP Enter raised {e!r}", "WARN")

    # Final trusted-input fallback: uniquely mark the Selenium-controlled tab,
    # focus that exact Chrome window via Windows UI Automation, and send one
    # native Enter keystroke. This avoids accidentally targeting another Gemini
    # window while still verifying the resulting DOM state.
    marker = f"MICROGEN_AUTOMATION_TARGET_{os.getpid()}"
    old_title = ""
    try:
        from pywinauto import Desktop
        from pywinauto.keyboard import send_keys as native_send_keys

        old_title = client.driver.title or "Google Gemini"
        client.driver.execute_script("document.title=arguments[0]", marker)
        time.sleep(0.25)

        wins = [w for w in Desktop(backend="uia").windows() if marker in w.window_text()]
        if len(wins) != 1:
            raise RuntimeError(f"Expected exactly one marked Gemini Chrome window; found {len(wins)}")

        wins[0].set_focus()
        client.driver.execute_script("arguments[0].focus()", ed)
        time.sleep(0.08)
        native_send_keys("{ENTER}", pause=0.05)
        time.sleep(0.55)

        if _has_send_effect():
            log_timing("send click", t_click, "native Windows Enter with confirmed UI effect")
            return True
        log_timing("send click failed", t_click, "native Windows Enter produced no Gemini state change", level="WARN")
        return False
    except Exception as e:
        log_timing("send click failed", t_click, f"native Windows Enter failed: {e!r}", level="WARN")
        return False
    finally:
        if old_title:
            try:
                client.driver.execute_script("document.title=arguments[0]", old_title)
            except Exception:
                pass


def _send_registered(client, before_text: str = "", before_model_count: int = 0, before_user_count: int = 0) -> bool:
    """Require positive Gemini DOM evidence that the request actually started."""
    if client.driver is None:
        return False

    try:
        # A visible Stop control is direct evidence that Gemini is generating.
        for sel in [
            "//button[contains(@aria-label,'Stop')]",
            "//button[contains(@title,'Stop')]",
            "//button[.//span[contains(normalize-space(.),'Stop')]]",
        ]:
            for b in client.driver.find_elements("xpath", sel)[-3:]:
                try:
                    if b.is_displayed() and b.is_enabled():
                        return True
                except Exception:
                    pass

        # A newly-created model response is also positive evidence.
        models = [e for e in client.driver.find_elements("css selector", "model-response") if e.is_displayed()]
        if len(models) > before_model_count:
            return True

        # A real Gemini user turn is represented by a top-level <user-query>.
        # Do not count nested classes containing "user-query": those transient
        # components caused false submission positives during development.
        users = client.driver.execute_script(
            """
            const vis=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            return [...document.querySelectorAll('user-query')].filter(vis).length;
            """
        ) or 0
        if int(users) > int(before_user_count):
            return True
    except Exception:
        pass

    # Composer disappearance alone is deliberately NOT proof of submission.
    return False


def wait_for_prompt_to_leave_composer(client, before_text: str = "", timeout: float = 1.2, poll: float = 0.04, before_model_count: int = 0, before_user_count: int = 0) -> bool:
    t0 = _ts_now()

    while _ts_now() - t0 < timeout:
        if _send_registered(client, before_text=before_text, before_model_count=before_model_count, before_user_count=before_user_count):
            log_timing("prompt left composer", t0, "positive submission evidence")
            return True
        time.sleep(poll)

    try:
        snap = client.driver.execute_script(
            """
            const vis=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const buttons=[...document.querySelectorAll('button')].filter(vis).map(b=>({
              aria:b.getAttribute('aria-label')||'',
              title:b.title||'',
              text:(b.textContent||'').trim()
            })).filter(x=>x.aria||x.title||x.text);
            const sels=['user-query','[data-message-author-role="user"]','[class*="user-query"]'];
            const users=new Set();
            for(const s of sels) for(const e of document.querySelectorAll(s)) if(vis(e)) users.add(e);
            const models=[...document.querySelectorAll('model-response')].filter(vis);
            const ed=[...document.querySelectorAll('[contenteditable="true"][role="textbox"],div[role="textbox"][contenteditable="true"],textarea')].find(vis);
            return {
              url:location.href,
              user_count:users.size,
              model_count:models.length,
              composer:ed?((ed.value||ed.innerText||ed.textContent||'').trim().slice(0,240)):'',
              buttons:buttons.slice(-12)
            };
            """
        ) or {}
        log(f"[SEND-DIAG] timeout snapshot={snap!r}", "WARN")
    except Exception as e:
        log(f"[SEND-DIAG] timeout snapshot failed: {e!r}", "WARN")
    log_timing("prompt left composer timeout", t0, "submission not confirmed", level="WARN")
    return False


def _mapping_response_is_substantial(text: str) -> bool:
    cleaned = clean_model_text(text or "")
    if len(cleaned) < 20:
        return False
    return True


def _send_prompt_and_capture_mapping_text(client, instruction_text: str, wait_cap: int) -> str:
    t_total = _ts_now()
    if client.driver is None:
        raise RuntimeError("Selenium client driver is not available.")

    baseline_response = clean_model_text(get_latest_response_text(client.driver))
    send_ok = False

    for attempt in range(3):
        t_attempt = _ts_now()
        log(f"[TIMING] prompt attempt {attempt+1}: started", "INFO")

        t_step = _ts_now()
        if stop_generation_if_present(client):
            log_timing(f"attempt {attempt+1} stop prior generation", t_step, "clicked stop", level="WARN")
            time.sleep(0.08)
        else:
            log_timing(f"attempt {attempt+1} stop prior generation", t_step, "no stop button")

        t_step = _ts_now()
        clear_composer(client)
        time.sleep(0.02)
        log_timing(f"attempt {attempt+1} clear composer", t_step)

        t_step = _ts_now()
        injected = inject_prompt_text(client, instruction_text, verify_timeout=0.30, poll=0.02)
        log_timing(f"attempt {attempt+1} inject+verify prompt", t_step, f"injected={injected}", level=("INFO" if injected else "WARN"))
        if not injected:
            time.sleep(0.10)
            log_timing(f"attempt {attempt+1} total", t_attempt, "failed at inject step", level="WARN")
            continue

        t_step = _ts_now()
        composer_before_send = get_composer_text(client)
        prompt_ok = prompt_verified_in_composer(client, instruction_text)
        log_timing(f"attempt {attempt+1} prompt snapshot", t_step, f"prompt_ok={prompt_ok}; snapshot={repr(composer_before_send[:120])}", level=("INFO" if prompt_ok else "WARN"))
        if not prompt_ok:
            time.sleep(0.10)
            log_timing(f"attempt {attempt+1} total", t_attempt, "failed at prompt verification", level="WARN")
            continue

        t_step = _ts_now()
        actionable = wait_until_send_actionable(
            client,
            prompt_text=instruction_text,
            timeout=min(6.0, max(2.0, float(wait_cap) * 0.08)),
            poll=0.04,
            stable_rounds=1,
        )
        log_timing(f"attempt {attempt+1} wait send actionable", t_step, f"actionable={actionable}", level=("INFO" if actionable else "WARN"))
        if not actionable:
            time.sleep(0.10)
            log_timing(f"attempt {attempt+1} total", t_attempt, "send never became actionable", level="WARN")
            continue

        # Snapshot conversation-node counts before clicking Send so a cleared
        # composer cannot masquerade as a successful submission.
        try:
            before_model_count = len([e for e in client.driver.find_elements("css selector", "model-response") if e.is_displayed()])
            before_user_count = int(client.driver.execute_script(
                """const vis=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                return [...document.querySelectorAll('user-query')].filter(vis).length;"""
            ) or 0)
        except Exception:
            before_model_count = 0
            before_user_count = 0

        t_step = _ts_now()
        clicked = click_safe_send_button(
            client,
            before_model_count=before_model_count,
            before_user_count=before_user_count,
        )
        log_timing(f"attempt {attempt+1} click send", t_step, f"clicked={clicked}", level=("INFO" if clicked else "WARN"))
        if not clicked:
            time.sleep(0.08)
            log_timing(f"attempt {attempt+1} total", t_attempt, "send click failed", level="WARN")
            continue

        t_step = _ts_now()
        registered = wait_for_prompt_to_leave_composer(client, before_text=composer_before_send, timeout=3.0, poll=0.05, before_model_count=before_model_count, before_user_count=before_user_count)
        log_timing(f"attempt {attempt+1} register send", t_step, f"registered={registered}", level=("INFO" if registered else "WARN"))
        if registered:
            send_ok = True
            log_timing(f"attempt {attempt+1} total", t_attempt, "submission registered")
            break

        log(f"Prompt did not register after Send on attempt {attempt+1}.", "WARN")
        time.sleep(0.12)
        log_timing(f"attempt {attempt+1} total", t_attempt, "registration failed", level="WARN")

    if not send_ok:
        log_timing("prompt send pipeline total", t_total, "all attempts failed", level="WARN")
        raise RuntimeError("Prompt could not be reliably submitted to Gemini.")

    t_step = _ts_now()
    # Mapping responses are tiny. Watch the live response DOM directly and do
    # not depend on Gemini's changing generation-finished/thinking indicators.
    direct_wait = min(float(wait_cap), 90.0)
    early = wait_for_mapping_response_ready(client, baseline_text=baseline_response, timeout=direct_wait, poll=0.20)
    log_timing("direct mapping DOM wait", t_step, f"hit={bool(early)}; timeout={direct_wait:.0f}s")
    if early:
        log_timing("prompt send pipeline total", t_total, "returned from direct DOM mapping confirmation")
        return early

    latest_diag = clean_model_text(get_latest_response_text(client.driver))
    log(f"[DIAG] Direct mapping watcher timed out; latest response={repr(latest_diag[-1200:])}", "WARN")
    if latest_diag and parse_mapping_lines(latest_diag):
        log_timing("prompt send pipeline total", t_total, "returned from timeout-edge DOM mapping")
        return latest_diag

    log(f"Waiting for Gemini response to finish (fallback capture, max_wait={wait_cap}) ...")

    t_step = _ts_now()
    gemsel._wait_until_generation_finishes(client.driver, timeout=float(wait_cap), poll=0.35)
    log_timing("wait until generation finishes", t_step)

    t_step = _ts_now()
    dom_ready = clean_model_text(get_latest_response_text(client.driver))
    dom_parseable = bool(dom_ready and parse_mapping_lines(dom_ready))
    log_timing("post-finish DOM check", t_step, f"parseable={dom_parseable}")
    if dom_parseable:
        log_timing("prompt send pipeline total", t_total, "returned from post-finish DOM check")
        return dom_ready

    t_step = _ts_now()
    copied = gemsel.capture_gemini_response_like_manual_copy(
        client.driver,
        wait_cap=wait_cap,
        prefer_latex_doc=False,
        retries=6,
        min_chars=20,
        accept_fn=_mapping_response_is_substantial,
    )
    cleaned = clean_model_text(copied or "")
    log_timing("manual-copy capture", t_step, f"chars={len(cleaned)}")
    if cleaned:
        log_timing("prompt send pipeline total", t_total, "returned from manual-copy capture")
        return cleaned

    log("Strict clipboard capture failed; trying bounded DOM extraction.", "WARN")
    t_step = _ts_now()
    dom = gemsel.adaptive_wait_and_copy_full(
        client.driver,
        preset="short",
        overrides={
            "max_wait": min(int(wait_cap), 60),
            "min_chars": 20,
            "stable_rounds": 2,
            "poll": 0.5,
        },
    )
    cleaned = clean_model_text(dom or "")
    log_timing("bounded DOM extraction", t_step, f"chars={len(cleaned)}")
    if cleaned:
        log_timing("prompt send pipeline total", t_total, "returned from bounded DOM extraction")
        return cleaned

    t_step = _ts_now()
    copied = gemsel.capture_gemini_response_like_manual_copy(
        client.driver,
        wait_cap=20,
        prefer_latex_doc=False,
        retries=3,
        min_chars=20,
        accept_fn=_mapping_response_is_substantial,
    )
    cleaned = clean_model_text(copied or "")
    log_timing("final manual-copy capture", t_step, f"chars={len(cleaned)}")
    if cleaned:
        log_timing("prompt send pipeline total", t_total, "returned from final manual-copy capture")
        return cleaned

    log_timing("prompt send pipeline total", t_total, "no usable mapping text", level="WARN")
    raise RuntimeError("Gemini did not return any usable mapping text.")


# -------- Per-page workflow --------
def map_and_rename_single_step(
    client: gemsel.GeminiSeleniumClient,
    page_png: Path,
    crops_dir: Path,
    wait_cap: int,
    upload_only_crops: bool = False
) -> tuple[Optional[Path], list[Path]]:
    """
    Returns: (mapping_txt_path_or_None, mapped_outputs_in_crops_dir)

    Robust strategy:
    - real crop filenames always come from local crops_dir/fig_*.png
    - Gemini's returned crop filename is ignored
    - mapping is assigned by response order to local fig_files order
    - Gemini UI interaction uses thick guarded control:
      upload settle -> prompt inject/verify -> safe send -> bounded response capture
    """
    t_page = _ts_now()
    fig_files = sorted(crops_dir.glob("fig_*.png"), key=lambda p: natural_sort_key(p.name))
    if not fig_files:
        log(f"No crops found in {crops_dir}; skipping mapping for {page_png.name}.", "WARN")
        return None, []

    t_step = _ts_now()
    client.open_clean_gemini_chat()
    log_timing(f"page {page_png.stem} open clean chat", t_step)

    to_upload = fig_files if upload_only_crops else [page_png] + fig_files

    baseline_attachment_count = 0
    if client.driver is not None:
        # Aborted/failed Gemini sends can leave attachment tiles in the composer
        # even after opening a clean chat. Remove them before establishing the
        # baseline for this page.
        for _ in range(12):
            stale = client.driver.find_elements("css selector", 'button[aria-label="close attachment"]')
            stale = [b for b in stale if b.is_displayed()]
            if not stale:
                break
            try:
                client.driver.execute_script("arguments[0].click();", stale[-1])
            except Exception:
                try:
                    stale[-1].click()
                except Exception:
                    break
            time.sleep(0.12)
        baseline_attachment_count = get_visible_attachment_count(client.driver)
        if baseline_attachment_count:
            raise RuntimeError(f"Could not clear {baseline_attachment_count} stale Gemini attachment(s).")

    t_step = _ts_now()
    client.upload_files(to_upload)
    log_timing(f"page {page_png.stem} upload_files call", t_step, f"files={len(to_upload)}")

    # upload_files() is the authoritative fail-closed upload check. Current
    # Gemini collapses image chips and can remove the accessible acknowledgement
    # before the legacy settle probe observes it, so a second independent gate
    # can contradict a confirmed upload. Keep only a short stabilization delay.
    t_step = _ts_now()
    time.sleep(0.6)
    page_txt_now = _page_text_lower(client.driver) if client.driver is not None else ""
    if "file upload error" in page_txt_now:
        raise RuntimeError(
            f"Gemini reported a file upload error for {page_png.name}; refusing to submit text."
        )
    log_timing(f"page {page_png.stem} post-upload stabilization", t_step, "upload_files confirmed")

    crop_manifest = "\n".join(f"{i+1}. {p.name}" for i, p in enumerate(fig_files))

    prompt = (
        "You are given one full textbook page image and several cropped figure images from that page.\n\n"
        "IMPORTANT:\n"
        "The actual crop files, in order, are:\n"
        f"{crop_manifest}\n\n"
        "For each crop, identify the correct figure caption label from the page and propose the target filename.\n"
        "Return exactly one line per crop, in the SAME ORDER as the crop list above.\n"
        "Do not add commentary.\n"
        "Use exactly this format:\n"
        'anything.png : "Figure 22.4" : Figure 22.4.png\n'
        "The left-hand filename may be any attachment name, and will be ignored by the script.\n"
    )

    t_step = _ts_now()
    raw = _send_prompt_and_capture_mapping_text(client, prompt, wait_cap=wait_cap)
    log_timing(f"page {page_png.stem} prompt-to-response pipeline", t_step)
    txt = clean_model_text(raw)
    log("[DEBUG] model_txt_first_400=" + repr((txt or "")[:400]))

    parsed = parse_mapping_lines(txt or "")
    log(f"[PARSE] {page_png.name}: parsed {len(parsed)} raw mapping line(s).")

    # Retry once if Gemini answered in prose instead of mapping lines
    if not parsed:
        retry_prompt = (
            "Your previous reply did not follow the required format.\n"
            "Reply again using ONLY mapping lines, one line per crop, in the SAME ORDER as the crop list.\n"
            "No explanation, no bullets, no summary.\n"
            'Required format example:\n'
            'crop_1.png : "Figure 22.4" : Figure 22.4.png\n'
        )
        raw_retry = _send_prompt_and_capture_mapping_text(client, retry_prompt, wait_cap=wait_cap)
        txt_retry = clean_model_text(raw_retry)
        log("[DEBUG] retry_model_txt_first_400=" + repr((txt_retry or "")[:400]))
        parsed = parse_mapping_lines(txt_retry or "")
        if parsed:
            txt = txt_retry
            log(f"[PARSE] {page_png.name}: parsed {len(parsed)} raw mapping line(s) after retry.")

    mapping_txt = page_png.with_name(page_png.stem + "_mapping.txt")

    if not parsed:
        mapping_txt.write_text((txt or "").strip() + "\n", encoding="utf-8")
        log(f"[WARN] No valid mapping lines parsed. Check {mapping_txt.name} formatting.", "WARN")
        return mapping_txt, []

    # Keep only as many mappings as local crops available
    usable_count = min(len(parsed), len(fig_files))
    if len(parsed) != len(fig_files):
        log(
            f"[WARN] Parsed {len(parsed)} mapping line(s) but found {len(fig_files)} local crop(s). "
            f"Using first {usable_count} by order.",
            "WARN",
        )

    # Ignore Gemini-returned source name completely; assign by local fig_files order
    resolved_triples: List[Tuple[str, str, str]] = []
    for i in range(usable_count):
        _returned_name, label, target = parsed[i]
        local_crop_name = fig_files[i].name
        resolved_triples.append((local_crop_name, label, target))

    # Save resolved mapping text, not raw Gemini text
    resolved_lines = [
        f'{crop_name} : "{label}" : {target}'
        for crop_name, label, target in resolved_triples
    ]
    mapping_txt.write_text("\n".join(resolved_lines) + "\n", encoding="utf-8")
    log(f"[WRITE] Resolved mapping saved to {mapping_txt.name}")

    # Copy under mapped names; group for merge
    mapped: Dict[Path, List[Path]] = {}
    rename_count = 0

    for crop_name, _label, target in resolved_triples:
        src = crops_dir / crop_name
        if not src.exists():
            log(f"[WARN] Missing crop referenced after order resolution: {src}", "WARN")
            continue

        rawname = str(target).translate(SMART_TO_ASCII)
        rawname = re.sub(r'[\\/*?:"<>|]', '-', rawname)
        rawname = re.sub(r'[\s\-]+', ' ', rawname)
        rawname = re.sub(r"\s+", " ", rawname).strip()
        rawname = re.sub(r"\.(png)\b.*$", ".png", rawname, flags=re.IGNORECASE)

        if not re.search(r"\.png$", rawname, flags=re.IGNORECASE):
            rawname += ".png"
        rawname = re.sub(r"\.png$", ".png", rawname, flags=re.IGNORECASE)

        base = re.sub(r"[^A-Za-z0-9 ._\-\(\)]", "", rawname).strip()
        if not base:
            base = "Figure_unnamed.png"
        elif not base.lower().endswith(".png"):
            base += ".png"

        dst = crops_dir / base
        try:
            if OVERWRITE_ALWAYS and dst.exists():
                dst.unlink()
            shutil.copy2(src, dst)
            mapped.setdefault(dst, []).append(src)
            rename_count += 1
            log(f"[COPY] {src.name} -> {dst.name}")
        except Exception as e:
            log(f"[WARN] Copy failed {src.name} -> {dst.name}: {e}", "WARN")

    if mapped and Image is not None:
        for dst, srcs in mapped.items():
            if len(srcs) > 1:
                try:
                    merge_images_horizontally(srcs, dst)
                except Exception as e:
                    log(f"[WARN] Merge failed for {dst.name}: {e}", "WARN")

    produced_targets = sorted(mapped.keys(), key=lambda p: p.name.lower())
    existing = sorted([p.name for p in crops_dir.glob("*.png")], key=natural_sort_key)
    log(f"[LIST] {crops_dir}: " + ", ".join(existing))
    log(f"[OK] Completed mapping; {rename_count} crop(s) written in {crops_dir}")
    log_timing(f"page {page_png.stem} total", t_page, f"renamed={rename_count}, produced={len(produced_targets)}")
    return mapping_txt, produced_targets

# -------- Orchestration --------
def run_mapping(
    pages_dir: str,
    crops_dir: str,
    start_idx: int,
    end_idx: int,
    wait_cap: int,
    upload_only_crops: bool,
    copy_to_root: bool
):
    pages_root = CFG.root / pages_dir
    crops_root = CFG.root / crops_dir
    if not pages_root.exists() or not crops_root.exists():
        raise RuntimeError("Missing pages/ or crops/ directory. Run crop_figs.py first.")

    # Build selenium client config (keeps v7 behaviour; controlled by SAFE_CHROME env var)
    scfg = gemsel.Config(
        root=CFG.root,
        pages_dir=CFG.pages_dir,
        crops_dir=CFG.crops_dir,
        gemini_url=CFG.gemini_url,
        debug_port=CFG.debug_port,
        wait_mapping_max=CFG.wait_mapping_max,
        chrome_exe=CFG.chrome_exe,
        user_data_dir=CFG.user_data_dir,
        profile_directory=CFG.profile_directory,
        fallback_user_data_dir=CFG.fallback_user_data_dir,
        fallback_profile_directory=CFG.fallback_profile_directory,
        use_persistent_chrome=CFG.use_persistent_chrome,
        force_kill_chrome_to_free_port=CFG.force_kill_chrome_to_free_port,
    )
    client = gemsel.GeminiSeleniumClient(scfg)

    # Start selenium once for the whole run (same as v7)
    client.start(ensure_gemini_on_launch=True)

    try:
        page_dirs = sorted(pages_root.glob("page_*"), key=lambda p: natural_sort_key(p.name))
        if not page_dirs:
            log("No page_* directories found under pages/.", "ERR")
            return

        selected = []
        for d in page_dirs:
            try:
                idx = int(d.name.split("_")[1])
            except Exception:
                continue
            if start_idx <= idx <= end_idx:
                selected.append((idx, d))

        if not selected:
            log("No pages in the requested index range.", "ERR")
            return

        total = len(selected)
        for k, (idx, page_dir) in enumerate(selected, 1):
            page_png    = page_dir / f"page_{idx}.png"
            crops_dir_i = crops_root / f"page_{idx}"
            log(f"[{k}/{total}] Processing {page_png}")
            if not page_png.exists():
                log(f"Missing {page_png} -- skipping.", "WARN"); continue
            if not crops_dir_i.exists():
                log(f"Missing crops dir {crops_dir_i} -- skipping.", "WARN"); continue

            try:
                _mapping_txt = None
                new_pngs = []
                page_attempts = max(1, int(os.getenv("GEMINI_PAGE_ATTEMPTS", "2")))
                for page_attempt in range(1, page_attempts + 1):
                    try:
                        if page_attempt > 1:
                            log(
                                f"[RETRY] Re-running page {idx} in a fresh Gemini chat "
                                f"(attempt {page_attempt}/{page_attempts}).",
                                "WARN",
                            )
                        _mapping_txt, new_pngs = map_and_rename_single_step(
                            client, page_png, crops_dir_i,
                            wait_cap=wait_cap,
                            upload_only_crops=upload_only_crops,
                        )
                        break
                    except GeminiGenerationStalled as e:
                        log(
                            f"[STALL] Page {idx} attempt {page_attempt}/{page_attempts}: {e}",
                            "WARN",
                        )
                        try:
                            stopped = stop_generation_if_present(client)
                            log(
                                f"[STALL] Stop response requested before reset: stopped={stopped}",
                                "WARN",
                            )
                        except Exception:
                            pass
                        setattr(client, "_map_prompt_cache", None)
                        time.sleep(0.6)
                        if page_attempt >= page_attempts:
                            raise

                if copy_to_root:
                    root = Path(".").resolve()
                    for p in new_pngs:
                        if p.exists():
                            dst = root / p.name
                            try:
                                if dst.exists():
                                    dst.unlink()
                                shutil.copy2(str(p), str(dst))
                                log(f"[STATUS] Generated: {p} | Copied to Root: {dst.name}")
                            except Exception as e:
                                log(f"[WARN] Failed to copy {p.name} to root: {e}", "WARN")

            except Exception as e:
                log(f"[ERROR] Failed to process page {idx}: {e}", "ERR")
                continue

        log("All mappings completed.")
    finally:
        # Close the automation Chrome session launched by this run (and only that one)
        client.shutdown()
        #pass


def parse_args():
    import argparse
    ap = argparse.ArgumentParser(description="Selenium->Gemini mapping with robust upload/parsing and horizontal merges (v7 refactor).")
    ap.add_argument("--pages_dir", default="pages", help="Pages folder (default: pages)")
    ap.add_argument("--crops_dir", default="crops", help="Crops folder (default: crops)")
    ap.add_argument("--start", type=int, default=1, help="First page index (default: 1)")
    ap.add_argument("--end", type=int, default=10**9, help="Last page index (default: huge)")
    ap.add_argument("--wait_cap", type=int, default=int(os.getenv("WAIT_MAPPING_MAX", "120")),
                    help="Max adaptive wait seconds for mapping (default: 120)")
    ap.add_argument("--upload_only_crops", type=int, default=0,
                    help="1 to upload only crops (skip page PNG), 0 to upload page+crop (default 0)")
    ap.add_argument("--copy_to_root", type=int, default=1,
                    help="Copy newly created PNGs to project root (default 1)")
    return ap.parse_args()


# ---- run main ----
args = parse_args()
CFG = Config(root=Path.cwd(), wait_mapping_max=args.wait_cap)

try:
    
    ##
    SCRIPT_1 = "launch_gemini_chrome.py"
    script_path = Path(__file__).resolve().with_name(SCRIPT_1)
    result = subprocess.run(
        [sys.executable, str(script_path)],
        check=True
    )
    ##
    
    run_mapping(
        pages_dir=args.pages_dir,
        crops_dir=args.crops_dir,
        start_idx=args.start,
        end_idx=args.end,
        wait_cap=args.wait_cap,
        upload_only_crops=bool(args.upload_only_crops),
        copy_to_root=bool(args.copy_to_root),
    )

    # ----- LAST TASK -----
    import merge_lettered_figs_v3
    # Do not let the merge helper reparse this mapper's --start/--end/etc.
    merge_lettered_figs_v3.main([])

finally:
    # Nothing to do here: run_mapping() already shuts down the automation Chrome.
    pass
