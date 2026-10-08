# MicroGen_AI Educational Automation Package
# Â© 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.
#
# This file is part of the MicroGen_AI package.
#
# Licensed under the MIT License (see LICENSE file in the project root).
# You may not use this file except in compliance with the License.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_problem_sets_selenium_v10.py

Workflow:
  1. Upload problems.pdf to Gemini UI via the LOCAL selenium.py used by MicroGen_AI.
  2. Ask Gemini to generate one LaTeX file per detected problem sub-section.
  3. Capture Gemini's response exclusively via Gemini's Copy icon / Copy menu path.
  4. Parse the returned LaTeX blocks and save them as *_problemset.tex files.
  5. Fix/compile each LaTeX file using fix_latex_selenium_v4.py.
  6. Run the existing cleanup helper afterwards.

Important:
- Gemini UI communication is outsourced exclusively to the LOCAL selenium.py.
- All redundant in-script LaTeX-fixing logic has been removed.
- LaTeX fixing is delegated to fix_latex_selenium_v4.py.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple



# Force-load the local customized selenium.py that sits beside this script.
_LOCAL_SELENIUM_PATH = Path(__file__).with_name("selenium.py")

if not _LOCAL_SELENIUM_PATH.exists():
    raise FileNotFoundError(f"Custom selenium.py not found: {_LOCAL_SELENIUM_PATH}")

_spec = importlib.util.spec_from_file_location("local_selenium_wrapper", _LOCAL_SELENIUM_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Could not create import spec for {_LOCAL_SELENIUM_PATH}")

local_selenium = importlib.util.module_from_spec(_spec)
sys.modules["local_selenium_wrapper"] = local_selenium
_spec.loader.exec_module(local_selenium)

# Pull symbols from the customized wrapper, not from the pip selenium package.
By = local_selenium.By
Keys = local_selenium.Keys
StaleElementReferenceException = local_selenium.StaleElementReferenceException

GeminiSeleniumClient = local_selenium.GeminiSeleniumClient
log = local_selenium.log


# ---------------- Console encoding ----------------
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ---------------- Logging ----------------
def log(msg: str, level: str = "INFO") -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


# ---------------- Local module import helpers ----------------
def import_local_module(module_filename: str, module_name: str):
    """
    Import a LOCAL project module by filename, avoiding collisions with
    installed pip packages. The module is registered in sys.modules before
    exec_module() so that decorators such as @dataclass work correctly.
    """
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


# ---- load LOCAL selenium.py ----
_local_selenium = import_local_module("selenium.py", "microgen_local_selenium")
SeleniumConfig = _local_selenium.Config
GeminiSeleniumClient = _local_selenium.GeminiSeleniumClient
_wait_until_generation_finishes = _local_selenium._wait_until_generation_finishes
_copy_via_toolbar_copy_button = _local_selenium._copy_via_toolbar_copy_button
_copy_via_more_menu = _local_selenium._copy_via_more_menu
capture_gemini_response_like_manual_copy = getattr(
    _local_selenium,
    "capture_gemini_response_like_manual_copy",
    None,
)
adaptive_wait_and_copy_full = getattr(
    _local_selenium,
    "adaptive_wait_and_copy_full",
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
        txt = ""
        for _ in range(max(1, retries)):
            txt = (_copy_via_toolbar_copy_button(driver) or "").strip()
            if not txt:
                txt = (_copy_via_more_menu(driver) or "").strip()
            if not txt:
                time.sleep(0.8)
                continue
            if prefer_latex_doc and not (r"\documentclass" in txt and r"\end{document}" in txt):
                time.sleep(0.8)
                continue
            if len(txt) < int(min_chars):
                time.sleep(0.8)
                continue
            if accept_fn is not None:
                try:
                    if not accept_fn(txt):
                        time.sleep(0.8)
                        continue
                except Exception:
                    time.sleep(0.8)
                    continue
            return txt
        return ""

if adaptive_wait_and_copy_full is None:
    adaptive_wait_and_copy_full = _local_selenium.adaptive_wait_and_copy

# ---- load LOCAL fix_latex_selenium_v4.py ----
_local_fixlatex = import_local_module("fix_latex_selenium_v4.py", "microgen_local_fixlatex")
fix_latex = _local_fixlatex.fix_latex


# Optional clipboard (used indirectly by selenium.py copy helpers)
try:
    import pyperclip  # noqa: F401
except Exception:
    pyperclip = None


# ---------------- Config ----------------
@dataclass
class Config:
    root: Path
    wait_response_max: int = int(os.environ.get("WAIT_RESPONSE_MAX", "240"))
    debug_port: int = int(os.environ.get("GEMINI_DEVTOOLS_PORT", "9222"))


CLIENT: Optional[GeminiSeleniumClient] = None


# ---------------- Prompt + parsing ----------------
GEMINI_PROMPT = r"""
You are an expert LaTeX editor and physics tutor.

I have uploaded a PDF file named `problems.pdf`. It contains physics problems
organized by sub-sections of the form "Section 39.1 ...", "Section 39.2 ...", etc.
(Section numbers and titles may differ; always use exactly what appears in the PDF
for the section identifiers and titles.)

CRITICAL OUTPUT RULE FOR AUTOMATION:
Your response will be copied automatically from the web UI. Therefore you MUST
output each LaTeX file as LITERAL SOURCE CODE, not visually rendered mathematics.
Backslashes, braces, carets, underscores, dollar signs, and double backslashes must
appear literally in the copied text. Do NOT rely on rendered math formatting.

To force literal copying, EVERY LaTeX file MUST be placed inside a fenced code block
with language identifier latex, exactly like this:

===FILE_START: SECTION 39.1.tex===
```latex
\documentclass{article}
...
\end{document}
```
===FILE_END===

Do not put any prose inside the code fence. Do not omit the code fences.

IMPORTANT CONTENT TRANSFORMATION RULE:
You MUST NOT copy textbook problem statements verbatim or near-verbatim.
You MUST rewrite all problem statements in fresh wording while preserving the
physics meaning, numerical data, symbols, and required tasks.
Your output must be a transformed, paraphrased study version of the problems,
written in clear original wording.

Your tasks:

1. Identify sub-sections
   - Analyze the document content to determine the distinct problem sub-sections.
   - Use the exact section identifiers and titles that appear in the PDF whenever possible.
   - If the PDF has a heading such as "Section 39.1 Blackbody Radiation and Planck's Hypothesis",
     preserve that identifier and title.
   - At the very beginning of your response, output one summary line of the form:
       SECTIONS_FOUND: SECTION 39.1, SECTION 39.2, ...
     followed by a line:
       NUM_SECTIONS: N
     where N is the number of sub-sections identified.
   - After these two summary lines, output the LaTeX files as described below.

2. Generate one LaTeX file per sub-section
   For EACH sub-section:

   (a) Create a standalone LaTeX document that begins with:
       \documentclass{article}
       \usepackage{graphicx}
       \usepackage{amsmath}
       \usepackage{geometry}
       \usepackage{amsfonts}
       \usepackage{amssymb}
       \usepackage{textcomp}
       \usepackage{ifpdf}
       \usepackage{caption}
       \usepackage[utf8]{inputenc}
       \usepackage[T1]{fontenc}
       \usepackage{bm}
       \usepackage{enumitem}
       \geometry{margin=1in}
       \captionsetup[figure]{labelformat=empty}

   (b) The document must contain ONLY the problems belonging to that sub-section.

   (c) For each problem in that sub-section, produce a rewritten version that:
       - preserves the original problem number
       - preserves all numerical values, symbols, and physical quantities
       - preserves the required task or question
       - uses original paraphrased wording
       - does NOT quote the textbook wording verbatim
       - remains concise, accurate, and suitable for study use

   (d) Use a clean structure such as:
       \section*{Section 39.1: ...}
       \begin{enumerate}[leftmargin=*]
       \item ...
       \item ...
       \end{enumerate}

   (e) If a problem contains multiple parts such as (a), (b), (c), preserve those parts,
       but rewrite them in fresh wording.

   (f) If a problem refers to a figure such as "Figure P39.4", "Figure P39.19", etc.:
       - do NOT reproduce the figure itself
       - insert a conditional placeholder using the exact figure label
       - use exactly this template, changing only the figure label:

           \IfFileExists{Figure P39.19.png}{%
           \begin{figure}[h]
             \centering
             \includegraphics[height=0.16\textheight,keepaspectratio]{Figure P39.19.png}%
             \caption{Figure P39.19}
           \end{figure}
           }{}

       - The \caption text MUST be exactly the figure label from the PDF.
       - Do NOT add extra caption text.
       - If multiple problems in the same section reference the same figure, include the
         figure placeholder only once at the first appropriate place.

   (g) End each file with:
       \end{document}

3. File naming
   - Each logical LaTeX document must correspond to exactly ONE sub-section.
   - Use the section identifier in the filename, for example:
       SECTION 39.1.tex
       SECTION 39.2.tex
   - Preserve the exact section numbering from the PDF.

4. Response format for automation
   After the initial two summary lines:

       SECTIONS_FOUND: SECTION ...
       NUM_SECTIONS: N

   return each LaTeX file wrapped exactly like this:

       ===FILE_START: SECTION 39.1.tex===
       ```latex
       \documentclass{article}
       ...
       \end{document}
       ```
       ===FILE_END===

   Continue for all sections in order.

   Requirements:
   - The filename after FILE_START must be exactly the LaTeX filename.
   - There must be no extra prose outside these blocks other than the two summary lines.
   - The latex code fence is REQUIRED for every file block.
   - Do NOT include explanations before, between, or after the file blocks.

5. LaTeX validation requirement
   Before sending your response, you MUST validate that each LaTeX document is syntactically correct:
   - \documentclass, \begin{document}, and \end{document} are present and balanced
   - all \begin{...} have matching \end{...}
   - all braces are balanced
   - all enumerate/item structures are valid
   - all math is valid LaTeX math
   - all figure placeholders compile safely even if the PNG file is missing

   If any file has a LaTeX syntax problem, fix it before returning the response.

6. STRICT SOURCE-CODE RULES
   - Output ONLY ASCII source code inside the code fences.
   - Convert Unicode symbols to LaTeX commands or ASCII equivalents.
     Examples:
       θ -> \theta
       μ -> \mu
       Ω -> \Omega
       × -> \times
       ≤ -> \leq
       ≥ -> \geq
       ± -> \pm
   - Do not output zero-width spaces or hidden Unicode characters.
   - All math must remain in LaTeX math mode.
   - Escape special characters properly, including:
       %  _  #  &
   - If you use tables, every row break must be written literally as \\
   - Do not output visually formatted superscripts or subscripts outside LaTeX math.

7. Scope
   - Ignore copyright notices, running headers/footers, chapter summaries, and page numbers.
   - Focus ONLY on the problems and their figure references within each sub-section.
   - Ignore adjacent textbook material outside the actual problem sets.
   - Do NOT include chapter summary text unless it is necessary to understand a specific problem reference.

8. Content policy for this task
   - Rewrite and transform the problems into original study-use wording.
   - Preserve the physics content and intent.
   - Do NOT reproduce textbook wording verbatim or near-verbatim.
   - Do NOT output long copied passages from the PDF.
   - Your output must be a structured LaTeX transformation, not a transcription.

Remember:
- The code fence is mandatory for every file block.
- Output literal LaTeX source code, not rendered mathematics.
- Preserve meaning, numbers, equations, symbols, and task structure.
- Rewrite the wording in original language.
- Do not include extra commentary.
"""

FILE_BLOCK_RE = re.compile(
    r"===FILE_START:\s*(.+?)===\s*(.*?)\s*===FILE_END===",
    re.DOTALL,
)

CODE_FENCE_RE = re.compile(
    r"^```(?:latex|tex)?\s*\n?(.*?)\n?```$",
    re.DOTALL | re.IGNORECASE,
)

UI_CODE_LABEL_LINE_RE = re.compile(
    r"(?im)^\s*(?:code\s+snippet|code\s+block|snippet)\s*$"
)

ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\u2060\uFEFF]")
SUSPICIOUS_UNICODE_RE = re.compile(r"[Î¸Î¼Î©Î±Î²Î³ÎÏÏÎ»â¤â¥Â±ââââ]")
SUPERSCRIPT_CHAR_RE = re.compile(r"[â°Â¹Â²Â³â´âµâ¶â·â¸â¹]")


def strip_ui_code_labels(content: str) -> str:
    s = (content or "")
    s = ZERO_WIDTH_RE.sub("", s)
    lines = s.splitlines()

    while lines and UI_CODE_LABEL_LINE_RE.match(lines[0] or ""):
        lines.pop(0)

    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines).strip()


def unwrap_latex_code_fence(content: str) -> str:
    s = strip_ui_code_labels(content)
    m = CODE_FENCE_RE.match(s)
    if m:
        s = m.group(1).strip()
    return strip_ui_code_labels(s)


def parse_latex_files_from_response(response_text: str) -> List[Tuple[str, str]]:
    files: List[Tuple[str, str]] = []
    for m in FILE_BLOCK_RE.finditer(response_text):
        name = m.group(1).strip()
        content = unwrap_latex_code_fence(m.group(2))
        files.append((name, content))
    return files


def latex_content_has_copy_artifacts(content: str) -> bool:
    s = content or ""
    if ZERO_WIDTH_RE.search(s):
        return True
    if SUSPICIOUS_UNICODE_RE.search(s):
        return True
    if SUPERSCRIPT_CHAR_RE.search(s):
        return True
    if "\x00" in s:
        return True
    if r"\begin{tabular}" in s and ("\\" + "\n" + r"\hline") in s:
        return True
    return False


def to_problemset_name(fname: str) -> str:
    """
    Convert e.g.
      'SECTION 14.3.tex'        -> 'SECTION_14-3_problemset.tex'
      'ADDITIONAL PROBLEMS.tex' -> 'ADDITIONAL_PROBLEMS_problemset.tex'
    """
    m = re.match(r"^(.+?)\s+(\d+)\.(\d+)\.tex$", fname)
    if m:
        prefix, major, minor = m.groups()
        return f"{prefix}_{major}-{minor}_problemset.tex"
    stem, ext = os.path.splitext(fname)
    stem_compact = stem.replace(" ", "_")
    return f"{stem_compact}_problemset{ext}"


##
# -------- Fast local UI helpers (script-local; does not modify selenium.py) --------
def _fast_find_prompt_editable(client: GeminiSeleniumClient):
    if client.driver is None:
        return None

    cache = getattr(client, "_gps_prompt_cache", None)
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
                    setattr(client, "_gps_prompt_cache", el)
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
              for (const el of document.querySelectorAll(sel)) {
                if (isVisible(el)) return el;
              }
            }
            return null;
            """
        )
        if el is not None:
            setattr(client, "_gps_prompt_cache", el)
            return el
    except Exception:
        pass
    return None


def _attachment_probe(driver) -> tuple[int, list[str]]:
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
                    if (/\.(png|jpg|jpeg|pdf|docx?|tex|txt)$/i.test(name)) out.push(name);
                    else out.push('');
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
    return count, names


def wait_until_send_actionable(
    client: GeminiSeleniumClient,
    prompt_text: str = "",
    timeout: float = 6.0,
    poll: float = 0.04,
    stable_rounds: int = 1,
) -> bool:
    if client.driver is None:
        return False

    prompt_probe = " ".join((prompt_text or "").split())[:80].strip()
    t0 = time.perf_counter()
    stable = 0

    while time.perf_counter() - t0 < timeout:
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
                    "[role='progressbar']",
                    "mat-progress-bar",
                    ".upload-progress",
                    "[aria-label*='Uploading']",
                    "[aria-label*='uploading']",
                    "[aria-label*='Processing']",
                    "[aria-label*='processing']",
                    "[class*='progress']",
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
                    '[contenteditable="true"][role="textbox"]',
                    'div[role="textbox"][contenteditable="true"]',
                    'textarea',
                    'div[aria-label="Enter a prompt here"]'
                ];
                for (const sel of composerSelectors) {
                    try {
                        for (const el of document.querySelectorAll(sel)) {
                            if (!isVisible(el)) continue;
                            const vals = [el.value, el.innerText, el.textContent].map(norm).filter(Boolean);
                            if (vals.length) {
                                vals.sort((a,b) => b.length - a.length);
                                composerText = vals[0];
                                break;
                            }
                        }
                    } catch (e) {}
                    if (composerText) break;
                }

                const hasVisibleEnabled = (xps) => {
                    for (const xp of xps) {
                        try {
                            const it = document.evaluate(xp, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                            for (let i = 0; i < it.snapshotLength; i++) {
                                const el = it.snapshotItem(i);
                                if (isVisible(el) && !el.disabled && el.getAttribute("aria-disabled") !== "true") return true;
                            }
                        } catch (e) {}
                    }
                    return false;
                };

                const stopVisible = hasVisibleEnabled([
                    "//button[contains(@aria-label,'Stop')]",
                    "//button[contains(@title,'Stop')]",
                    "//button[.//span[contains(normalize-space(.),'Stop')]]",
                ]);

                const sendEnabled = !stopVisible && hasVisibleEnabled([
                    "//button[@aria-label='Send message']",
                    "//button[contains(@aria-label,'Send')]",
                    "//button[contains(@aria-label,'Ask')]",
                    "//button[.//span[contains(normalize-space(.),'Send')]]",
                    "//button[.//span[contains(normalize-space(.),'Ask')]]",
                ]);

                const probeOk = !probe || composerText.includes(probe);
                const busyText = ["uploading", "processing", "preparing"].some(tok => bodyText.includes(tok));

                return {
                    prompt_ok: probeOk,
                    send_ready: sendEnabled,
                    busy_count: busyCount,
                    busy_text: busyText
                };
                """,
                prompt_probe,
            ) or {}
        except Exception:
            status = {}

        if bool(status.get("prompt_ok")) and bool(status.get("send_ready")) and int(status.get("busy_count", 0) or 0) == 0 and not bool(status.get("busy_text")):
            stable += 1
            if stable >= stable_rounds:
                return True
        else:
            stable = 0
        time.sleep(poll)
    return False

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

    time.sleep(0.03)

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


def wait_for_upload_to_settle(
    client: GeminiSeleniumClient,
    expected_names=None,
    timeout: float = 10.0,
    quiet_window: float = 0.35,
    poll: float = 0.12,
    baseline_attachment_count: int = 0,
    min_new_attachments: int = 0,
) -> bool:
    if client.driver is None:
        return False

    expected_names = [str(x).strip().lower() for x in (expected_names or []) if str(x).strip()]
    busy_selectors = [
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

    t0 = time.time()
    good_since = None
    last_signature = None
    last_report = 0.0

    while time.time() - t0 < timeout:
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
        files_ready = names_ready or attachment_ready or (attachment_count > baseline_attachment_count)

        signature = (busy_count, busy_text, attachment_count, names_seen, send_ready, composer_ready)
        stable_now = (busy_count == 0) and (not busy_text) and composer_ready and files_ready and send_ready

        if stable_now and signature == last_signature:
            if good_since is None:
                good_since = time.time()
            elif time.time() - good_since >= quiet_window:
                log(
                    f"Upload settled after {time.time() - t0:.1f}s "
                    f"(names_seen={names_seen}/{len(expected_names) if expected_names else 0}, "
                    f"attachment_count={attachment_count}, baseline_attachment_count={baseline_attachment_count}, "
                    f"new_attachments={new_attachments}).",
                    "INFO",
                )
                return True
        else:
            good_since = None

        if time.time() - last_report >= 2.0:
            log(
                f"[upload-settle] busy_count={busy_count}, busy_text={busy_text}, composer_ready={composer_ready}, "
                f"names_seen={names_seen}/{len(expected_names) if expected_names else 0}, "
                f"attachment_count={attachment_count}, baseline_attachment_count={baseline_attachment_count}, "
                f"new_attachments={new_attachments}, min_new_attachments={min_new_attachments}",
                "DEBUG",
            )
            last_report = time.time()

        last_signature = signature
        time.sleep(poll)

    log(
        f"Upload settle timed out after {timeout:.1f}s "
        f"(names_seen={names_seen}/{len(expected_names) if expected_names else 0}, "
        f"attachment_count={attachment_count}, baseline_attachment_count={baseline_attachment_count}, "
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
        return ""

    try:
        ed = _fast_find_prompt_editable(client)
    except Exception:
        return ""

    try:
        txt = client.driver.execute_script("""
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
        """, ed)

        return (txt or "").strip()
    except Exception:
        return ""


def inject_prompt_text(
    client: GeminiSeleniumClient,
    text: str,
    verify_timeout: float = 0.35,
    poll: float = 0.02,
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


def get_safe_send_button(client: GeminiSeleniumClient):
    """
    Return a real Send/Ask button only if no Stop button is currently active.
    """
    if client.driver is None:
        return None

    # If Stop is present, do not attempt Send.
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
            time.sleep(0.15)
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
    timeout: float = 1.6,
    poll: float = 0.04,
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

    m = re.search(r"NUM_SECTIONS:\s*(\d+)", response_text)
    if not m:
        return False

    expected = int(m.group(1))
    starts = re.findall(r"===FILE_START:\s*.+?===", response_text)
    ends = re.findall(r"===FILE_END===", response_text)

    if len(starts) != expected:
        return False
    if len(ends) != expected:
        return False

    files = parse_latex_files_from_response(response_text)
    if len(files) != expected:
        return False

    for _, content in files:
        if r"\documentclass" not in content:
            return False
        if r"\begin{document}" not in content:
            return False
        if r"\end{document}" not in content:
            return False
        if latex_content_has_copy_artifacts(content):
            return False

    return True

#
def response_looks_partial_but_promising(response_text: str) -> bool:
    """
    A looser gate than response_looks_complete().
    Used to keep the best snapshot even before Gemini has finished.
    """
    s = (response_text or "").strip()
    if not s:
        return False

    if "Problem with Gemini" in s:
        return False
    if "don't seem to have access to that content" in s:
        return False

    if "===FILE_START:" not in s:
        return False

    # A promising partial capture should already look like literal LaTeX blocks
    # rather than rendered prose/math.
    if r"\documentclass" not in s:
        return False

    return True


def page_shows_gemini_failure(client: GeminiSeleniumClient) -> bool:
    if client.driver is None:
        return False

    try:
        txt = client.driver.execute_script(
            "return (document.body && document.body.innerText) || '';"
        ) or ""
    except Exception:
        txt = ""

    txt_norm = " ".join(str(txt).split()).lower()

    failure_markers = [
        "problem with gemini",
        "normally i can help with things like this",
        "i don't seem to have access to that content",
        "you can try again or ask me for something else",
    ]
    return any(marker in txt_norm for marker in failure_markers)


def generation_still_running(client: GeminiSeleniumClient) -> bool:
    """
    True while Gemini still appears to be generating.
    """
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

        for btn in btns[-4:]:
            try:
                if btn.is_displayed() and btn.is_enabled():
                    return True
            except Exception:
                pass

    return False


def try_copy_latest_response_once(client: GeminiSeleniumClient) -> str:
    """
    One opportunistic copy attempt using the same response-scoped helpers
    already provided by local selenium.py.
    """
    if client.driver is None:
        return ""

    txt = ""
    try:
        txt = (_copy_via_toolbar_copy_button(client.driver) or "").strip()
    except Exception:
        txt = ""

    if not txt:
        try:
            txt = (_copy_via_more_menu(client.driver) or "").strip()
        except Exception:
            txt = ""

    return (txt or "").strip()

def get_latest_response_dom_text(client: GeminiSeleniumClient) -> str:
    """
    Read the visible text of the latest Gemini response container directly from the DOM.
    This is used as a fallback when the Copy button does not yield clipboard content
    during streaming.
    """
    if client.driver is None:
        return ""

    selectors = [
        "message-content",
        "div[role='article']",
        "div[class*='response']",
        "div[class*='model']",
    ]

    for sel in selectors:
        try:
            els = client.driver.find_elements("css selector", sel)
        except Exception:
            els = []

        if not els:
            continue

        for el in reversed(els[-4:]):
            try:
                txt = el.get_attribute("innerText") or el.text or ""
            except Exception:
                txt = ""

            txt = (txt or "").strip()
            if len(txt) >= 40:
                return txt

    return ""


def looks_like_dom_machine_parseable_candidate(txt: str) -> bool:
    """
    Looser than full validation, but enough to preserve a promising visible on-screen
    response before Gemini replaces it with an error.
    """
    s = (txt or "").strip()
    if not s:
        return False

    if "Problem with Gemini" in s:
        return False
    if "don't seem to have access to that content" in s:
        return False

    # Look for visible signs that the response is following the automation format.
    has_markers = ("===FILE_START:" in s) or ("NUM_SECTIONS:" in s)
    has_latex = (r"\documentclass" in s) or (r"\begin{document}" in s)

    return has_markers or has_latex

def write_capture_diagnostics(client: GeminiSeleniumClient, outdir: Path, prefix: str) -> None:
    """
    Best-effort diagnostics so failed runs leave useful evidence behind.
    """
    try:
        diag_dir = outdir / "_gemini_diag"
        diag_dir.mkdir(parents=True, exist_ok=True)

        page_txt = ""
        if client.driver is not None:
            try:
                page_txt = client.driver.execute_script(
                    "return (document.body && document.body.innerText) || '';"
                ) or ""
            except Exception:
                page_txt = ""

        (diag_dir / f"{prefix}_page_text.txt").write_text(page_txt, encoding="utf-8")

        copied_toolbar = ""
        try:
            copied_toolbar = (_copy_via_toolbar_copy_button(client.driver) or "").strip()
        except Exception:
            copied_toolbar = ""
        (diag_dir / f"{prefix}_toolbar_copy.txt").write_text(copied_toolbar, encoding="utf-8")

        copied_more = ""
        try:
            copied_more = (_copy_via_more_menu(client.driver) or "").strip()
        except Exception:
            copied_more = ""
        (diag_dir / f"{prefix}_moremenu_copy.txt").write_text(copied_more, encoding="utf-8")
    except Exception:
        pass


def capture_last_good_response_during_generation(
    client: GeminiSeleniumClient,
    wait_cap: int,
    outdir: Optional[Path] = None,
    poll: float = 2.0,
    baseline_text: str = "",
) -> str:
    """
    Watch Gemini while it is generating.

    Strategy:
      - try response-scoped Copy opportunistically
      - if Copy yields nothing, also read the latest visible response DOM text
      - preserve the last COMPLETE valid response if one appears
      - otherwise preserve the best promising partial/DOM snapshot
      - if Gemini later collapses to 'Problem with Gemini', return the best preserved snapshot
    """
    if client.driver is None:
        return ""

    t0 = time.time()
    best_complete = ""
    best_partial = ""
    best_partial_len = 0
    last_logged = 0.0

    # Gemini can briefly expose no Stop button immediately after Send, and the
    # Stop control can also disappear before the final response DOM settles.
    # Do not interpret a single "not running" observation as completion.
    baseline_text = (baseline_text or "").strip()
    seen_generation = False
    last_candidate_len = 0
    last_growth_at = t0
    startup_grace = min(8.0, max(3.0, float(wait_cap) * 0.08))
    idle_confirm = 3.0

    diag_dir = None
    if outdir is not None:
        try:
            diag_dir = outdir / "_gemini_diag"
            diag_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            diag_dir = None

    while time.time() - t0 < wait_cap:
        copied = try_copy_latest_response_once(client)
        copied = (copied or "").strip()

        dom_txt = get_latest_response_dom_text(client)
        dom_txt = (dom_txt or "").strip()

        # Prefer actual Copy text if present; otherwise use visible DOM text.
        candidate = copied if copied else dom_txt

        candidate_is_new = bool(candidate) and (
            (not baseline_text) or candidate != baseline_text
        )

        if candidate_is_new:
            seen_generation = True
            if len(candidate) != last_candidate_len:
                last_candidate_len = len(candidate)
                last_growth_at = time.time()

            if response_looks_complete(candidate):
                best_complete = candidate
                if diag_dir is not None:
                    try:
                        (diag_dir / "best_complete_snapshot.txt").write_text(
                            candidate, encoding="utf-8"
                        )
                    except Exception:
                        pass

            else:
                promising = False
                if response_looks_partial_but_promising(candidate):
                    promising = True
                elif looks_like_dom_machine_parseable_candidate(candidate):
                    promising = True

                if promising and len(candidate) > best_partial_len:
                    best_partial = candidate
                    best_partial_len = len(candidate)
                    if diag_dir is not None:
                        try:
                            (diag_dir / "best_partial_snapshot.txt").write_text(
                                candidate, encoding="utf-8"
                            )
                        except Exception:
                            pass

        if diag_dir is not None:
            try:
                if copied:
                    (diag_dir / "last_stream_copy.txt").write_text(copied, encoding="utf-8")
                if dom_txt:
                    (diag_dir / "last_stream_dom.txt").write_text(dom_txt, encoding="utf-8")
            except Exception:
                pass

        if page_shows_gemini_failure(client):
            log(
                "Gemini UI shows failure banner during generation; returning the last preserved snapshot.",
                "WARN",
            )
            break

        still_running = generation_still_running(client)
        now = time.time()

        if still_running:
            seen_generation = True
            # A visible Stop control is positive evidence that generation is active,
            # so reset the idle-completion timer even if the captured text did not grow.
            last_growth_at = now

        elapsed = now - t0
        idle_for = now - last_growth_at

        if (
            (not still_running)
            and seen_generation
            and elapsed >= startup_grace
            and idle_for >= idle_confirm
        ):
            # Re-sample twice before accepting idle as completion. If the response
            # grows during this settle window, resume watching instead of exiting.
            settled = True
            for _ in range(2):
                time.sleep(0.8)

                copied2 = try_copy_latest_response_once(client)
                dom2 = get_latest_response_dom_text(client)

                copied2 = (copied2 or "").strip()
                dom2 = (dom2 or "").strip()
                candidate2 = copied2 if copied2 else dom2
                candidate2_is_new = bool(candidate2) and (
                    (not baseline_text) or candidate2 != baseline_text
                )

                if not candidate2_is_new:
                    continue

                if len(candidate2) != last_candidate_len:
                    last_candidate_len = len(candidate2)
                    last_growth_at = time.time()
                    settled = False

                if response_looks_complete(candidate2):
                    best_complete = candidate2
                    continue

                promising2 = False
                if response_looks_partial_but_promising(candidate2):
                    promising2 = True
                elif looks_like_dom_machine_parseable_candidate(candidate2):
                    promising2 = True

                if promising2 and len(candidate2) > best_partial_len:
                    best_partial = candidate2
                    best_partial_len = len(candidate2)

            if settled and not generation_still_running(client):
                break

        if time.time() - last_logged >= 8.0:
            log(
                f"[watch-copy] elapsed={time.time()-t0:.1f}s, "
                f"have_complete={bool(best_complete)}, best_partial_len={best_partial_len}, "
                f"copied_now={bool(copied)}, dom_now_len={len(dom_txt)}, "
                f"still_running={still_running}",
                "DEBUG",
            )
            last_logged = time.time()

        time.sleep(poll)

    if best_complete:
        return best_complete.strip()

    return (best_partial or "").strip()
#

def send_prompt_and_copy_response_via_copy_icon(
    client: GeminiSeleniumClient,
    instruction_text: str,
    wait_cap: int,
    retries: int = 8,
    outdir: Optional[Path] = None,
) -> str:
    if client.driver is None:
        raise RuntimeError("Selenium client driver is not available.")

    # Snapshot the pre-send response so the completion watcher cannot mistake
    # the previous turn for the newly generated answer.
    baseline_text = (get_latest_response_dom_text(client) or "").strip()

    send_ok = False

    for attempt in range(3):
        if stop_generation_if_present(client):
            log(f"Stopped premature Gemini generation before prompt attempt {attempt+1}.", "WARN")
            time.sleep(0.15)

        clear_composer(client)
        time.sleep(0.03)

        injected = inject_prompt_text(client, instruction_text, verify_timeout=0.30, poll=0.02)
        if not injected:
            log(f"JS prompt injection failed on attempt {attempt+1}.", "WARN")
            time.sleep(0.10)
            continue

        composer_before_send = get_composer_text(client)
        if not prompt_verified_in_composer(client, instruction_text):
            log(
                f"Prompt not confirmed inside composer on attempt {attempt+1}. "
                f"Snapshot: {repr(composer_before_send[:160])}",
                "WARN",
            )
            time.sleep(0.10)
            continue

        if not wait_until_send_actionable(
            client,
            prompt_text=instruction_text,
            timeout=min(6.0, max(2.5, float(wait_cap) * 0.05)),
            poll=0.04,
            stable_rounds=1,
        ):
            log(f"Send button never became safely actionable on attempt {attempt+1}.", "WARN")
            time.sleep(0.10)
            continue

        if not click_safe_send_button(client):
            log(f"Safe Send button not available on attempt {attempt+1}.", "WARN")
            time.sleep(0.10)
            continue

        if wait_for_prompt_to_leave_composer(
            client,
            before_text=composer_before_send,
            timeout=1.6,
            poll=0.04,
        ):
            send_ok = True
            break

        log(f"Prompt did not register after Send on attempt {attempt+1}.", "WARN")
        time.sleep(0.12)

    if not send_ok:
        raise RuntimeError("Prompt could not be reliably submitted to Gemini.")

    log(
        f"Watching Gemini response during generation and preserving the last good snapshot "
        f"(max_wait={wait_cap}) ..."
    )

    watched_text = capture_last_good_response_during_generation(
        client=client,
        wait_cap=wait_cap,
        outdir=outdir,
        poll=1.0,
        baseline_text=baseline_text,
    )
    watched_text = (watched_text or "").strip()

    if watched_text and response_looks_complete(watched_text):
        return watched_text

    if watched_text:
        log(
            "A promising partial snapshot was preserved during generation, "
            "but it was not yet fully complete. Trying strict end-of-run capture.",
            "WARN",
        )

    strict_text = capture_gemini_response_like_manual_copy(
        client.driver,
        wait_cap=min(wait_cap, 20),
        prefer_latex_doc=True,
        retries=retries,
        min_chars=300,
        accept_fn=response_looks_complete,
    )
    if strict_text:
        return strict_text.strip()

    log(
        "Strict COPY-first capture did not yield a complete machine-parseable response; "
        "trying stabilized DOM fallback.",
        "WARN",
    )

    dom_text = adaptive_wait_and_copy_full(
        client.driver,
        preset="short",
        overrides={
            "max_wait": min(int(wait_cap), 45),
            "min_chars": 300,
            "stable_rounds": 3,
            "poll": 0.8,
        },
    )
    dom_text = (dom_text or "").strip()

    if response_looks_complete(dom_text):
        return dom_text

    if outdir is not None:
        write_capture_diagnostics(client, outdir, "failed_capture")

    if watched_text:
        log(
            "Returning the best preserved partial snapshot because Gemini collapsed before a final complete response was obtainable.",
            "WARN",
        )
        return watched_text

    raise RuntimeError(
        "Captured Gemini response did not pass strict LaTeX-source validation. "
        "No complete valid snapshot could be preserved before Gemini failed."
    )

def ascii_sanitize_text(txt: str) -> str:
    txt = strip_ui_code_labels(txt)
    replacements = {
        "â": "-",
        "â": "-",
        "â": "-",
        "â": "'",
        "â": "'",
        "â": '"',
        "â": '"',
        "Â ": " ",
        "â": "",
        "â": "",
        "â": "",
        "ï»¿": "",
    }
    for bad, good in replacements.items():
        txt = txt.replace(bad, good)
    return strip_ui_code_labels(txt)


def save_latex_files(files: List[Tuple[str, str]], outdir: Path) -> List[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    for fname, content in files:
        safe_name = fname.replace("/", "_").strip()
        final_name = to_problemset_name(safe_name)
        tex_path = outdir / final_name

        try:
            cleaned = ascii_sanitize_text(content)
            if latex_content_has_copy_artifacts(cleaned):
                raise ValueError(
                    "Captured content still appears to contain rendered-math copy artifacts; refusing to save defective LaTeX."
                )
            tex_path.write_text(cleaned, encoding="utf-8", newline="\n")
            written.append(tex_path)
            log(f"Saved LaTeX: {tex_path}")
        except Exception as e:
            log(f"Failed to write TeX file {tex_path}: {e}", "ERR")

    return written


def fix_saved_latex_files(tex_paths: List[Path]) -> None:
    """
    Delegate all LaTeX repair/compile logic to fix_latex_selenium_v4.py.
    """
    for tex_path in tex_paths:
        try:
            log(f"Delegating LaTeX fix/compile to fix_latex_selenium_v4.py for {tex_path.name}")
            fix_latex(str(tex_path))
        except Exception as e:
            log(f"fix_latex_selenium_v4.py failed for {tex_path.name}: {e}", "ERR")


# ---------------- CLI / orchestration ----------------
def parse_args():
    import argparse

    ap = argparse.ArgumentParser(
        description=(
            "Upload problems.pdf to Gemini and retrieve LaTeX problem sets per "
            "sub-section, with Gemini UI communication outsourced to local selenium.py."
        )
    )
    ap.add_argument(
        "--pdf",
        default="problems.pdf",
        help="Path to problems.pdf (default: problems.pdf in current dir)",
    )
    ap.add_argument(
        "--outdir",
        default=".",
        help="Output directory for .tex files (default: .)",
    )
    ap.add_argument(
        "--wait_cap",
        type=int,
        default=int(os.getenv("WAIT_RESPONSE_MAX", "420")),
        help="Max wait seconds for Gemini response (default: 420 or WAIT_RESPONSE_MAX env)",
    )
    return ap.parse_args()

import subprocess
def main() -> None:
    global CLIENT

    ##
    SCRIPT_1 = "launch_gemini_chrome.py"
    script_path = Path(__file__).resolve().with_name(SCRIPT_1)
    result = subprocess.run(
        [sys.executable, str(script_path)],
        check=True
    )
    ##

    args = parse_args()
    cfg = Config(root=Path.cwd(), wait_response_max=args.wait_cap)

    pdf_path = cfg.root / args.pdf
    outdir = cfg.root / args.outdir

    if not pdf_path.exists():
        raise FileNotFoundError(f"problems.pdf not found: {pdf_path}")

    selenium_cfg = SeleniumConfig(
        root=cfg.root,
        debug_port=cfg.debug_port,
        wait_mapping_max=cfg.wait_response_max,
    )
    CLIENT = GeminiSeleniumClient(selenium_cfg)

    import functions

    try:
        CLIENT.start(ensure_gemini_on_launch=True)

        log("Opening Gemini chat...")
        CLIENT.open_clean_gemini_chat()
        
        ###
        log(f"Uploading PDF: {pdf_path}")
        baseline_attachment_count = 0
        if CLIENT is not None and CLIENT.driver is not None:
            try:
                baseline_attachment_count = get_visible_attachment_count(CLIENT.driver)
            except Exception:
                baseline_attachment_count = 0
        CLIENT.upload_files([pdf_path])
        
        log("Waiting for upload to settle...")
#        if not wait_for_upload_to_settle(CLIENT, timeout=30):
            #log("Upload settle wait timed out; continuing with guarded prompt send.", "WARN")

        if not wait_for_upload_to_settle(
            CLIENT,
            expected_names=[pdf_path.name],
            timeout=10.0,
            quiet_window=0.35,
            poll=0.12,
            baseline_attachment_count=baseline_attachment_count,
            min_new_attachments=1,
        ):
            log("Upload settle wait timed out; continuing with guarded prompt send.", "WARN")
            
        ###
        '''
        log(f"Uploading PDF: {pdf_path}")
        CLIENT.upload_files([pdf_path])

        log("Waiting briefly for upload to register...")
        time.sleep(8)
        '''
        
        log("Sending LaTeX generation prompt to Gemini...")
        
        ##
        response_text = send_prompt_and_copy_response_via_copy_icon(
        client=CLIENT,
        instruction_text=GEMINI_PROMPT,
        wait_cap=args.wait_cap,
        outdir=outdir,
        )
        ##
        

        raw_response_path = outdir / "gemini_raw_response.txt"
        raw_response_path.parent.mkdir(parents=True, exist_ok=True)
        raw_response_path.write_text(response_text, encoding="utf-8")
        log(f"Raw Gemini response saved to: {raw_response_path}")

        log("Parsing LaTeX files from response...")
        files = parse_latex_files_from_response(response_text)

        m = re.search(r"NUM_SECTIONS:\s*(\d+)", response_text)
        if m:
            expected = int(m.group(1))
            if len(files) < expected:
                log(
                    f"Expected {expected} LaTeX files from NUM_SECTIONS, "
                    f"but only parsed {len(files)} FILE_START blocks.",
                    "WARN",
                )

        if not files:
            log("No LaTeX files detected in Gemini response.", "WARN")
        else:
            log(f"Detected {len(files)} LaTeX file(s). Saving TeX files...")
            tex_paths = save_latex_files(files, outdir)

            log("Fixing/compiling saved LaTeX files via fix_latex_selenium_v4.py ...")
            fix_saved_latex_files(tex_paths)

            # Keep existing cleanup helper behavior.
            functions.prefices(["run_clean_leftover"])

    finally:
        try:
            if CLIENT is not None:
                CLIENT.shutdown()
            #pass
        except Exception:
            pass


if __name__ == "__main__":
    main()
