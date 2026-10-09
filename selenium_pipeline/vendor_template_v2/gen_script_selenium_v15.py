# -*- coding: utf-8 -*-

# MicroGen_AI Educational Automation Package
# (C) 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.
# This file is part of the MicroGen_AI package.
# Licensed under the MIT License (see LICENSE file in the project root).
# You may not use this file except in compliance with the License.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

"""
gen_script_selenium_v14.py

Air-tight Gemini narration pipeline via the project's local selenium.py module.

Fixes versus the earlier v12:
- Ignores Beamer/PDF viewer page-counter artefacts such as "1 / 1", "2 over 1".
- Extracts real slide titles from slides.pdf instead of footer/header counters.
- Refuses extracted title lists that are mostly page counters.
- Rebuilds each script block while stripping leading page-counter junk from Gemini output.
- Drops duplicate title lines accidentally copied by Gemini into the narration body.
- Rejects scripts that still contain page-counter artefacts in title or narration lines.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# =========================
# Logging / utils
# =========================
def log(msg: str, level: str = "INFO") -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def strip_code_fences(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[\w\-]*\s*", "", s, flags=re.S)
        s = re.sub(r"\s*```$", "", s, flags=re.S)
    return s.strip()


def strip_leading_ui_artifacts(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = strip_code_fences(text)
    text = strip_inline_citation_artifacts(text)

    m = re.search(r"(?im)^\*{0,2}\s*Slide\s+1\s*\[[^\]]+\]:", text)
    if m:
        text = text[m.start():]

    lines = text.splitlines()
    ui_labels = {
        "code snippet",
        "plain text",
        "response",
        "output",
        "text",
        "script",
    }
    while lines and lines[0].strip().lower() in ui_labels:
        lines.pop(0)

    text = "\n".join(lines).strip()
    text = strip_inline_citation_artifacts(text)
    return text


def backup_existing(path: Path) -> None:
    if path.exists():
        i = 1
        while True:
            cand = path.with_name(f"{path.stem}_{i}{path.suffix}")
            if not cand.exists():
                path.rename(cand)
                log(f"Existing {path.name} renamed to {cand.name}", "WARN")
                return
            i += 1


def _load_local_gemini_selenium_module():
    here = Path(__file__).resolve().parent
    mod_path = here / "selenium.py"
    if not mod_path.exists():
        raise FileNotFoundError(f"selenium.py not found: {mod_path}")

    spec = importlib.util.spec_from_file_location("gemini_selenium_local", str(mod_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not create import spec for: {mod_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


# =========================
# Config (env-overridable)
# =========================
SLIDES_PDF = Path(os.environ.get("SLIDES_PDF", "slides.pdf"))
SOURCE_PDF = Path(os.environ.get("SOURCE_PDF", "source.pdf"))
PROMPT_FILE = Path(os.environ.get("PROMPT_FILE", "gen_script_prompt_v10.txt"))
RENDERED_PROMPT_FILE = Path(os.environ.get("RENDERED_PROMPT_FILE", "gen_script_prompt_v10_rendered.txt"))
EXACT_TITLES_JSON = Path(os.environ.get("EXACT_TITLES_JSON", "slide_titles_exact.json"))
OUT_SCRIPT = Path(os.environ.get("OUT_SCRIPT", "script.txt"))
WAIT_CAP = int(os.environ.get("WAIT_CAP", "420"))
MIN_RESPONSE_CHARS = int(os.environ.get("MIN_RESPONSE_CHARS", "1200"))
RETRY_COUNT = int(os.environ.get("RETRY_COUNT", "1"))
DEFAULT_DURATION = os.environ.get("DEFAULT_DURATION", "30 sec")
CUSTOM_FORBIDDEN_PHRASES = os.environ.get(
    "FORBIDDEN_PHRASES",
    "Welcome to this lecture module|Welcome to this course|ZCE 111|ZCE111|ZCA 110|ZCA110",
)

PAGE_COUNTER_RE = re.compile(
    r"^\s*(?:page\s*)?\d+\s*(?:/|\\|\||over)\s*\d+\s*$",
    flags=re.I,
)

# also catches ugly variants such as "2 over 11 / 1"
PAGE_COUNTER_FRAGMENT_RE = re.compile(
    r"\b\d+\s*(?:/|over)\s*\d+(?:\s*(?:/|over)\s*\d+)*\b",
    flags=re.I,
)

LATEX_INLINE_RE = re.compile(r"\$[^$]+\$")
LATEX_COMMAND_RE = re.compile(r"\\(?:[A-Za-z]+|[,;!])")
CARET_UNDERSCORE_RE = re.compile(r"(?<!\*)\b[A-Za-z0-9]+(?:_[A-Za-z0-9()+\-]+|\^[A-Za-z0-9()+\-]+)+\b")
UNICODE_SUBSUP_RE = re.compile(r"[₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾]")
SYMBOLIC_EQUATION_RE = re.compile(
    r"\b(?:[A-Za-z][A-Za-z0-9]*|Δ[A-Za-z]+|[α-ωΑ-Ω])\s*=\s*[^\n]{0,80}",
    flags=re.I,
)

OUT_SCRIPT = Path(os.environ.get("OUT_SCRIPT", "script.txt"))
# ------------------------------------------------------------
# Early exit if script already exists
# ------------------------------------------------------------
if OUT_SCRIPT.exists():
    log(f"{OUT_SCRIPT.name} already exists. Skipping Gemini submission.", "INFO")
    sys.exit(0)
    
def looks_like_symbolic_math(line: str) -> bool:
    s = _normalize_line(line)
    if not s:
        return False
    if LATEX_INLINE_RE.search(s):
        return True
    if LATEX_COMMAND_RE.search(s):
        return True
    if CARET_UNDERSCORE_RE.search(s):
        return True
    if UNICODE_SUBSUP_RE.search(s):
        return True
    if SYMBOLIC_EQUATION_RE.search(s):
        return True
    return False


# =========================
# PDF helpers
# =========================
def _load_pdf_reader(pdf_path: Path):
    last_error: Optional[Exception] = None

    try:
        from pypdf import PdfReader  # type: ignore
        return PdfReader(str(pdf_path))
    except Exception as e:
        last_error = e

    try:
        from PyPDF2 import PdfReader  # type: ignore
        return PdfReader(str(pdf_path))
    except Exception as e:
        last_error = e

    raise RuntimeError(f"Could not open PDF {pdf_path}: {last_error}")


def count_pdf_pages(pdf_path: Path) -> int:
    return len(_load_pdf_reader(pdf_path).pages)


def extract_page_texts(pdf_path: Path) -> list[str]:
    reader = _load_pdf_reader(pdf_path)
    page_texts: list[str] = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        txt = txt.replace("\r\n", "\n").replace("\r", "\n")
        page_texts.append(txt)
    return page_texts


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def is_page_counter_line(line: str) -> bool:
    s = _normalize_line(line)
    if not s:
        return False
    return bool(PAGE_COUNTER_RE.fullmatch(s))


def _is_meaningful_title_candidate(line: str) -> bool:
    s = _normalize_line(line)
    if not s:
        return False
    if is_page_counter_line(s):
        return False
    if re.fullmatch(r"\d+", s):
        return False
    if re.fullmatch(r"Page\s+\d+", s, flags=re.I):
        return False
    if len(s) == 1 and not s.isalpha():
        return False
    return True


def extract_exact_slide_titles(slides_pdf: Path) -> list[str]:
    titles: list[str] = []
    texts = extract_page_texts(slides_pdf)

    for idx, txt in enumerate(texts, start=1):
        lines = [_normalize_line(x) for x in txt.splitlines()]
        candidates = [x for x in lines if _is_meaningful_title_candidate(x)]
        title = candidates[0] if candidates else f"Slide {idx}"
        titles.append(title)

    counter_like = sum(1 for t in titles if is_page_counter_line(t))
    if counter_like:
        raise RuntimeError(
            f"Title extraction failed: {counter_like} extracted title(s) still look like page counters."
        )
    return titles


# =========================
# Prompt rendering
# =========================
def format_exact_titles_block(titles: list[str]) -> str:
    return "\n".join(f"{i}. {title}" for i, title in enumerate(titles, start=1))


def format_forbidden_phrases_block() -> str:
    parts = [x.strip() for x in CUSTOM_FORBIDDEN_PHRASES.split("|") if x.strip()]
    return "\n".join(f"- {x}" for x in parts)


def render_prompt_template(prompt_path: Path, slide_count: int, exact_titles: list[str]) -> str:
    template = prompt_path.read_text(encoding="utf-8")
    replacements = {
        "{slide_count}": str(slide_count),
        "{first_slide_title}": exact_titles[0] if exact_titles else "Slide 1",
        "{forbidden_phrases}": format_forbidden_phrases_block(),
    }
    rendered = template
    for k, v in replacements.items():
        rendered = rendered.replace(k, v)
    return rendered


def save_rendered_prompt(rendered: str) -> None:
    backup_existing(RENDERED_PROMPT_FILE)
    RENDERED_PROMPT_FILE.write_text(rendered, encoding="utf-8", newline="\n")
    log(f"Wrote {RENDERED_PROMPT_FILE.name}", "OK")


def save_exact_titles_json(slides_pdf: Path, titles: list[str]) -> None:
    backup_existing(EXACT_TITLES_JSON)
    data = {
        "slides_pdf": str(slides_pdf.resolve()),
        "slide_count": len(titles),
        "titles": [{"slide": i, "title": t} for i, t in enumerate(titles, start=1)],
    }
    EXACT_TITLES_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Wrote {EXACT_TITLES_JSON.name}", "OK")


# =========================
# Script parsing / rebuilding
# =========================
HEADER_RE = re.compile(r"(?im)^\*{0,2}\s*Slide\s+(\d+)\s+\[([^\]]+)\]:")


def _clean_block_body(text: str) -> str:
    t = text.strip()
    t = re.sub(r"\*{2}\s*$", "", t).strip()
    return t


def parse_slide_blocks(text: str) -> list[dict[str, str]]:
    s = strip_leading_ui_artifacts(text)
    matches = list(HEADER_RE.finditer(s))
    blocks: list[dict[str, str]] = []
    if not matches:
        return blocks

    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(s)
        chunk = s[start:end].strip()
        m2 = re.match(r"(?is)^\*{0,2}\s*Slide\s+(\d+)\s+\[([^\]]+)\]:\s*(.*)$", chunk, flags=re.S)
        if not m2:
            continue
        slide_no = int(m2.group(1))
        duration = re.sub(r"\s+", " ", m2.group(2)).strip()
        content = _clean_block_body(m2.group(3))
        blocks.append({"slide": str(slide_no), "duration": duration or DEFAULT_DURATION, "content": content, "raw": chunk})
    return blocks


def _normalize_for_compare(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def _extract_content_lines(block: dict[str, str]) -> list[str]:
    raw = block.get("raw", "")
    after_header = re.sub(r"(?is)^\*{0,2}\s*Slide\s+\d+\s+\[[^\]]+\]:\s*", "", raw).strip()
    after_header = re.sub(r"\*{2}\s*$", "", after_header).strip()
    lines = [_normalize_line(ln) for ln in after_header.splitlines() if _normalize_line(ln)]
    while lines and is_page_counter_line(lines[0]):
        lines.pop(0)
    return lines


def _remove_leading_title_like_lines(lines: list[str], slide_no: int, exact_titles: list[str]) -> list[str]:
    out = list(lines)
    norm_titles = {_normalize_for_compare(t) for t in exact_titles}
    target_title = _normalize_for_compare(exact_titles[slide_no - 1]) if 1 <= slide_no <= len(exact_titles) else ""
    while out:
        first = _normalize_for_compare(out[0])
        raw_first = out[0]
        if is_page_counter_line(raw_first):
            out.pop(0)
            continue
        if first in norm_titles or first == target_title:
            out.pop(0)
            continue
        if raw_first.lower().startswith("title:") or raw_first.lower().startswith("slide "):
            out.pop(0)
            continue
        break
    return out


def rebuild_script_with_first_title_only(raw_text: str, exact_titles: list[str]) -> str:
    blocks = parse_slide_blocks(raw_text)
    indexed = {int(b["slide"]): b for b in blocks}
    out_blocks: list[str] = []
    for slide_no in range(1, len(exact_titles) + 1):
        block = indexed.get(slide_no, {})
        duration = str(block.get("duration", DEFAULT_DURATION)).strip() or DEFAULT_DURATION
        lines = _extract_content_lines(block) if block else []
        if slide_no == 1:
            out_blocks.append(f"**Slide 1 [{duration}]:\n{exact_titles[0]}**")
            continue
        lines = _remove_leading_title_like_lines(lines, slide_no, exact_titles)
        body = "\n".join(lines).strip()
        if not body:
            body = "[Narration missing. Regeneration required.]"
        out_blocks.append(f"**Slide {slide_no} [{duration}]:\n{body}**")
    return "\n\n".join(out_blocks).strip() + "\n"


# =========================
# Validation
# =========================
def extract_script_slide_numbers(path: Path) -> list[int]:
    if not path.is_file():
        return []
    content = path.read_text(encoding="utf-8")
    nums = re.findall(r"\*\*Slide\s+(\d+)\s+\[[^\]]+\]:", content)
    return [int(x) for x in nums]


def extract_script_block_lines(path: Path) -> list[list[str]]:
    if not path.is_file():
        return []
    content = path.read_text(encoding="utf-8")
    blocks = parse_slide_blocks(content)
    out: list[list[str]] = []
    for b in blocks:
        body = b.get("content", "")
        lines = [_normalize_line(ln) for ln in body.splitlines() if _normalize_line(ln)]
        out.append(lines)
    return out


def find_format_warnings(path: Path) -> list[str]:
    if not path.is_file():
        return [f"File not found: {path.name}"]

    content = path.read_text(encoding="utf-8").strip()
    warnings = []

    if not content.startswith("**Slide 1"):
        warnings.append("Script does not start with '**Slide 1'.")
    if "Would you like me to" in content:
        warnings.append("Script contains unwanted trailing assistant commentary.")
    if "\n---\n" in content or content.endswith("---"):
        warnings.append("Script contains an unwanted horizontal rule.")
    if not re.findall(r"\*\*Slide\s+\d+\s+\[[^\]]+\]:", content):
        warnings.append("No correctly formatted slide headers found.")
    return warnings


def find_empty_slide_warnings(path: Path) -> list[str]:
    if not path.is_file():
        return [f"File not found: {path.name}"]
    blocks = extract_script_block_lines(path)
    if not blocks:
        return ["No slide blocks found in script.txt"]
    warnings: list[str] = []
    for idx, lines in enumerate(blocks, start=1):
        if idx == 1:
            if not lines:
                warnings.append("Slide 1 is missing the title line.")
            elif len(lines) != 1:
                warnings.append("Slide 1 must contain only the title line and no narration.")
        else:
            if not lines:
                warnings.append(f"Slide {idx} has missing narration content.")
            elif "[Narration missing. Regeneration required.]" in "\n".join(lines):
                warnings.append(f"Slide {idx} contains a missing narration placeholder.")
    return warnings


def find_slide_count_warnings(script_path: Path, slides_pdf_path: Path) -> list[str]:
    if not script_path.is_file():
        return [f"File not found: {script_path.name}"]
    if not slides_pdf_path.is_file():
        return [f"File not found: {slides_pdf_path.name}"]

    try:
        expected = count_pdf_pages(slides_pdf_path)
    except Exception as e:
        return [f"Could not determine slide count from {slides_pdf_path.name}: {e}"]

    nums = extract_script_slide_numbers(script_path)
    if not nums:
        return ["No slide blocks found in script.txt"]

    warnings: list[str] = []
    actual = len(nums)

    if actual != expected:
        warnings.append(
            f"Slide block count mismatch: script.txt has {actual} block(s) but slides.pdf has {expected} page(s)."
        )

    expected_sequence = list(range(1, expected + 1))
    if nums != expected_sequence:
        warnings.append(f"Slide numbering mismatch: found {nums}, expected {expected_sequence}.")
    return warnings


def find_exact_title_warnings(script_path: Path, exact_titles: list[str]) -> list[str]:
    if not script_path.is_file():
        return [f"File not found: {script_path.name}"]
    blocks = extract_script_block_lines(script_path)
    warnings: list[str] = []
    if len(blocks) != len(exact_titles):
        warnings.append(f"Block count mismatch for title validation: script has {len(blocks)} blocks but expected {len(exact_titles)}.")
        return warnings
    slide1 = blocks[0] if blocks else []
    if not slide1:
        warnings.append("Slide 1 is missing its title line.")
    else:
        if slide1[0].strip() != exact_titles[0].strip():
            warnings.append(f"Slide 1 title mismatch: got '{slide1[0]}' but expected '{exact_titles[0]}'.")
        if len(slide1) != 1:
            warnings.append("Slide 1 must contain only the title and no narration.")
    norm_titles = {_normalize_for_compare(t) for t in exact_titles}
    for idx in range(2, len(blocks) + 1):
        lines = blocks[idx - 1]
        if not lines:
            continue
        first = _normalize_for_compare(lines[0])
        if first in norm_titles:
            warnings.append(f"Slide {idx} begins with a slide title, but slides 2 onward must not include titles.")
        if is_page_counter_line(lines[0]):
            warnings.append(f"Slide {idx} begins with a page-counter artefact: {lines[0]}")
    return warnings


def _normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def find_course_code_contamination(script_path: Path, slides_page_texts: Iterable[str]) -> list[str]:
    if not script_path.is_file():
        return [f"File not found: {script_path.name}"]

    script_text = script_path.read_text(encoding="utf-8")
    script_norm = _normalize_space(script_text)
    slides_norm = "\n".join(_normalize_space(t) for t in slides_page_texts)
    warnings: list[str] = []

    code_pat = re.compile(r"\b[A-Z]{2,4}\s*\d{3}\b")
    found_codes = sorted(set(code_pat.findall(script_norm)))
    for code in found_codes:
        if _normalize_space(code) not in slides_norm:
            warnings.append(f"Ungrounded course-code-like reference found in script: {code}")

    for phrase in [x.strip() for x in CUSTOM_FORBIDDEN_PHRASES.split("|") if x.strip()]:
        if re.search(re.escape(phrase), script_text, flags=re.I):
            warnings.append(f"Forbidden contamination phrase found in script: {phrase}")
    return warnings


def find_page_counter_artifact_warnings(script_path: Path) -> list[str]:
    if not script_path.is_file():
        return [f"File not found: {script_path.name}"]

    warnings: list[str] = []
    text = script_path.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), start=1):
        s = _normalize_line(line)
        if is_page_counter_line(s):
            warnings.append(f"Page-counter artefact found on line {i}: {s}")
        elif PAGE_COUNTER_FRAGMENT_RE.search(s) and "Slide " not in s:
            warnings.append(f"Page-counter-like fragment found on line {i}: {s}")
    return warnings


def find_symbolic_math_warnings(script_path: Path) -> list[str]:
    if not script_path.is_file():
        return [f"File not found: {script_path.name}"]

    warnings: list[str] = []
    text = script_path.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), start=1):
        s = _normalize_line(line)
        if not s or s.startswith("**Slide "):
            continue
        if looks_like_symbolic_math(s):
            warnings.append(f"Symbolic or LaTeX-style math found on line {i}: {s}")
    return warnings


def collect_all_warnings(script_path: Path, slides_pdf_path: Path, exact_titles: list[str]) -> list[str]:
    page_texts = extract_page_texts(slides_pdf_path)
    return (
        find_empty_slide_warnings(script_path)
        + find_format_warnings(script_path)
        + find_slide_count_warnings(script_path, slides_pdf_path)
        + find_exact_title_warnings(script_path, exact_titles)
        + find_course_code_contamination(script_path, page_texts)
        + find_page_counter_artifact_warnings(script_path)
        + find_symbolic_math_warnings(script_path)
        + find_citation_artifact_warnings(script_path)
    )



# =========================
# Script generation helpers
# =========================

RAW_RESPONSE_FILE = Path(os.environ.get("RAW_RESPONSE_FILE", "gemini_raw_response.txt"))

def save_raw_gemini_response(text: str) -> None:
    RAW_RESPONSE_FILE.write_text(text or "", encoding="utf-8", newline="\n")
    log(f"Wrote raw Gemini capture to {RAW_RESPONSE_FILE.name}", "INFO")

def raw_response_has_real_narration(text: str, expected_slide_count: int) -> bool:
    blocks = parse_slide_blocks(text)
    if len(blocks) != expected_slide_count:
        return False

    nonempty_narration_blocks = 0
    for b in blocks:
        slide_no = int(b["slide"])
        if slide_no == 1:
            continue
        body = _clean_block_body(b.get("content", ""))
        if body and "[Narration missing. Regeneration required.]" not in body and len(_normalize_line(body)) >= 40:
            nonempty_narration_blocks += 1

    return nonempty_narration_blocks >= max(2, expected_slide_count // 3)


def gemini_connection_interrupted(driver) -> bool:
    """Return True when Gemini shows its transient interrupted-connection banner."""
    try:
        body = (driver.find_element("tag name", "body").text or "").lower()
    except Exception:
        return False
    return (
        "connection interrupted" in body
        or "waiting for the complete answer" in body
    )


def latest_model_response_text(driver) -> str:
    """Return the latest visible Gemini model-response text, if any."""
    try:
        nodes = [e for e in driver.find_elements("css selector", "model-response") if e.is_displayed()]
    except Exception:
        return ""
    if not nodes:
        return ""
    try:
        return (nodes[-1].get_attribute("innerText") or nodes[-1].text or "").strip()
    except Exception:
        return ""


def wait_for_fresh_complete_narration_dom(
    driver,
    baseline_text: str,
    expected_slide_count: int,
    baseline_url: str = "",
    timeout: float = 45.0,
    poll: float = 0.35,
) -> str:
    """Prefer a fresh completed DOM response before slower Copy-icon capture."""
    baseline = (baseline_text or "").strip()
    started = time.time()
    last = ""
    stable_rounds = 0

    while time.time() - started < timeout:
        current = latest_model_response_text(driver)
        try:
            state = driver.execute_script(
                """
                const vis=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const generating=[...document.querySelectorAll('button')].some(
                  b=>vis(b)&&((b.getAttribute('aria-label')||'').toLowerCase().includes('stop'))
                );
                const body=(document.body && document.body.innerText || '').toLowerCase();
                const interrupted=body.includes('connection interrupted') ||
                                  body.includes('waiting for the complete answer');
                return [generating, interrupted];
                """
            ) or [False, False]
            generating = bool(state[0])
            interrupted = bool(state[1])
        except Exception:
            generating = False
            interrupted = False

        try:
            current_url = driver.current_url or ""
        except Exception:
            current_url = ""
        routed_fresh = (
            bool(baseline_url)
            and current_url != baseline_url
            and re.match(r"^https://gemini\.google\.com/app/[A-Za-z0-9_-]+", current_url) is not None
        )
        fresh = (current != baseline) or routed_fresh

        copy_visible = False
        try:
            copy_visible = bool(driver.execute_script(
                """
                const vis=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                return [...document.querySelectorAll('button')].some(
                  b=>vis(b)&&((b.getAttribute('aria-label')||'').toLowerCase()==='copy')
                );
                """
            ))
        except Exception:
            pass

        if current and fresh and raw_response_has_real_narration(current, expected_slide_count):
            if current == last:
                stable_rounds += 1
            else:
                last = current
                stable_rounds = 0

            # Completion is defined by the response content itself, not by
            # Gemini's transient Stop/Copy controls. In the current UI those
            # controls can lag or remain inconsistent after slide 11 is already
            # fully rendered. A fresh, structurally valid narration that is
            # byte-for-byte stable across consecutive polls is authoritative.
            if stable_rounds >= 2:
                log(
                    f"Accepted fresh complete narration from stable model-response DOM "
                    f"after {time.time() - started:.1f}s ({len(current)} chars; "
                    f"stable_rounds={stable_rounds}).",
                    "OK",
                )
                return current
        else:
            last = current
            stable_rounds = 0

        time.sleep(poll)

    return ""


CITATION_ARTIFACT_RE = re.compile(
    r"""
    \[
        \s*
        (?:
            cite\s+start
            |
            cite
            (?:\s*:\s*[^\]]*)?
            |
            source
            (?:s)?
            (?:\s*:\s*[^\]]*)?
        )
        \s*
    \]
    """,
    flags=re.I | re.X,
)

GENERIC_BRACKET_METADATA_RE = re.compile(
    r"""
    \[
        \s*
        (?:
            \d+\s*,\s*\d+
            |
            ref(?:erence)?s?
            |
            grounded
        )
        \s*
    \]
    """,
    flags=re.I | re.X,
)

def strip_inline_citation_artifacts(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)

    protected_headers = {}

    def _protect_header(match):
        key = f"__SLIDE_HEADER_{len(protected_headers)}__"
        protected_headers[key] = match.group(0)
        return key

    # protect valid slide headers first
    text = re.sub(
        r"(?im)^\*{0,2}\s*Slide\s+\d+\s+\[[^\]]+\]:",
        _protect_header,
        text,
    )

    text = CITATION_ARTIFACT_RE.sub("", text)
    text = GENERIC_BRACKET_METADATA_RE.sub("", text)

    # restore protected slide headers
    for key, value in protected_headers.items():
        text = text.replace(key, value)

    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" *\n", "\n", text)
    return text.strip()


def build_instruction(rendered_prompt_name: str, slide_count: int) -> str:
    return (
        f"Read the attached file '{rendered_prompt_name}' and follow it exactly.\n"
        "Use 'slides.pdf' for slide order and visible slide content.\n"
        "Use 'source.pdf' only as background reference for the same topic.\n"
        f"There are exactly {slide_count} slide pages, so return exactly {slide_count} slide blocks.\n"
        "Return only the plain-text script. No code fences, no commentary before Slide 1, and no commentary after the last block.\n"
        "Math must be verbalized in plain English only. Do not use LaTeX, TeX, Markdown math, backslash commands, dollar-delimited math, subscripts, superscripts, or symbolic equation strings anywhere in the narration."
    )


def sanitize_and_rebuild_script(script_text: str, exact_titles: list[str]) -> str:
    cleaned = strip_leading_ui_artifacts(script_text)
    cleaned = strip_inline_citation_artifacts(cleaned)
    return rebuild_script_with_first_title_only(cleaned, exact_titles)

def save_script_text(script_text: str) -> None:
    backup_existing(OUT_SCRIPT)
    OUT_SCRIPT.write_text(script_text, encoding="utf-8", newline="\n")
    log(f"Wrote {OUT_SCRIPT.name}", "OK")

def find_citation_artifact_warnings(script_path: Path) -> list[str]:
    if not script_path.is_file():
        return [f"File not found: {script_path.name}"]

    warnings = []
    text = script_path.read_text(encoding="utf-8")

    bad_patterns = [
        r"\[\s*cite\s+start\s*\]",
        r"\[\s*cite\s*:\s*[^\]]+\]",
        r"\[\s*cite\s*\]",
        r"\[\s*source(?:s)?(?:\s*:\s*[^\]]+)?\s*\]",
    ]

    for pat in bad_patterns:
        for m in re.finditer(pat, text, flags=re.I):
            warnings.append(f"Citation artefact found: {m.group(0)}")

    return warnings

'''
def run_post_processors() -> None:
    for cmd, label in [
        ([sys.executable, "sanitize_script.py"], "sanitize_script.py"),
        ([sys.executable, "fix_script.py"], "fix_script.py"),
    ]:
        try:
            subprocess.run(cmd, check=False)
            log(f"Ran {label}", "INFO")
        except Exception as e:
            log(f"Could not run {label}: {e}", "WARN")
'''

def run_post_processors() -> None:
    cmd = [sys.executable, "postprocess_script.py"]
    try:
        subprocess.run(cmd, check=False)
        log("Ran postprocess_script.py", "INFO")
    except Exception as e:
        log(f"Could not run postprocess_script.py: {e}", "WARN")




def force_exact_titles_after_postprocessing(exact_titles: list[str]) -> None:
    if not OUT_SCRIPT.exists():
        return
    current = OUT_SCRIPT.read_text(encoding="utf-8")
    rebuilt = rebuild_script_with_first_title_only(current, exact_titles)
    OUT_SCRIPT.write_text(rebuilt, encoding="utf-8", newline="\n")
    log("Re-applied the exact first-slide title after post-processing.", "INFO")


def request_script_once(client, gemsel_module, instruction: str, expected_slide_count: int) -> Optional[str]:
    client.open_clean_gemini_chat()
    client.upload_files([SLIDES_PDF, SOURCE_PDF, RENDERED_PROMPT_FILE])

    baseline_response = latest_model_response_text(client.driver)
    try:
        baseline_url = client.driver.current_url or ""
    except Exception:
        baseline_url = ""

    if not client.type_prompt_text(instruction, retries=3):
        raise RuntimeError("Could not type into Gemini prompt field after retries.")
    log("[SEND-VERIFY] narration prompt typed; invoking durable Gemini submit.", "INFO")
    sent = bool(client.click_send_with_fallbacks(retries=3))
    log(f"[SEND-VERIFY] click_send_with_fallbacks returned {sent}.", "INFO")
    if not sent:
        raise RuntimeError("Could not durably submit the Gemini narration prompt after retries.")

    response = wait_for_fresh_complete_narration_dom(
        client.driver,
        baseline_text=baseline_response,
        expected_slide_count=expected_slide_count,
        baseline_url=baseline_url,
        timeout=float(WAIT_CAP),
    )

    if not response and gemini_connection_interrupted(client.driver):
        log(
            "Gemini reported 'Connection interrupted' before a complete narration was available; "
            "aborting this attempt so the outer regeneration loop can retry immediately.",
            "WARN",
        )
        return None

    if not response:
        log(
            f"Direct DOM narration capture exhausted the wait window; falling back to COPY-icon capture "
            f"(max_wait={WAIT_CAP}) ...",
            "INFO",
        )
        response = gemsel_module.capture_gemini_response_like_manual_copy(
            client.driver,
            wait_cap=WAIT_CAP,
            prefer_latex_doc=False,
            retries=10,
            min_chars=MIN_RESPONSE_CHARS,
            accept_fn=lambda txt: raw_response_has_real_narration(txt, expected_slide_count),
        )

    if response and response.strip():
        save_raw_gemini_response(response)

    if response and len(response.strip()) >= MIN_RESPONSE_CHARS and raw_response_has_real_narration(response, expected_slide_count):
        log(f"Gemini response received ({len(response)} chars)", "OK")
        return response

    if response and response.strip():
        log(
            f"Gemini response was captured but appears incomplete ({len(response)} chars or missing narration bodies). Rejecting it.",
            "WARN",
        )
        return None

    log("No response received from Gemini or response is empty", "ERR")
    return None


# =========================
# Main
# =========================
def main() -> int:
    print(
        """
# =====================================================================
# gen_script_selenium_v15.py  Selenium web-UI pipeline via selenium.py
# - Uploads: slides.pdf + source.pdf + gen_script_prompt_v10_rendered.txt
# - Extracts exact slide titles locally from slides.pdf
# - Forces only the exact first-slide title into final script.txt
# - Captures response through Gemini's Copy icon
# - Saves response to script.txt
# - Runs postprocess_script.py
# - Enforces block count, numbering, exact title match, contamination rules,
#   and page-counter-artifact rejection
# =====================================================================
"""
    )

    ##
    SCRIPT_1 = "launch_gemini_chrome.py"
    script_path = Path(__file__).resolve().with_name(SCRIPT_1)
    result = subprocess.run(
        [sys.executable, str(script_path)],
        check=True
    )
    ##

    missing = [p for p in [SLIDES_PDF, SOURCE_PDF, PROMPT_FILE] if not p.exists()]
    if missing:
        for m in missing:
            log(f"Missing required file: {m}", "ERR")
        return 1

    try:
        slide_count = count_pdf_pages(SLIDES_PDF)
        exact_titles = extract_exact_slide_titles(SLIDES_PDF)
        if len(exact_titles) != slide_count:
            raise RuntimeError(
                f"Title extraction mismatch: got {len(exact_titles)} titles for {slide_count} slide pages."
            )
        log(f"Detected {slide_count} slide page(s) in {SLIDES_PDF.name}", "INFO")
        log(f"Extracted {len(exact_titles)} exact slide title(s) from {SLIDES_PDF.name}", "INFO")
    except Exception as e:
        log(f"Could not prepare slide metadata from {SLIDES_PDF.name}: {e}", "ERR")
        return 1

    try:
        rendered_prompt = render_prompt_template(PROMPT_FILE, slide_count, exact_titles)
        save_rendered_prompt(rendered_prompt)
        save_exact_titles_json(SLIDES_PDF, exact_titles)
    except Exception as e:
        log(f"Could not render prompt or title metadata: {e}", "ERR")
        return 1

    gemsel = _load_local_gemini_selenium_module()
    cfg = gemsel.Config(root=Path.cwd())
    client = gemsel.GeminiSeleniumClient(cfg)
    instruction = build_instruction(RENDERED_PROMPT_FILE.name, slide_count)

    try:
        client.start(ensure_gemini_on_launch=True)

        attempts = RETRY_COUNT + 1
        last_warnings: list[str] = []

        for attempt in range(1, attempts + 1):
            if attempt > 1:
                log(f"Regeneration attempt {attempt} of {attempts}", "WARN")

            #response = request_script_once(client, gemsel, instruction)
            response = request_script_once(client, gemsel, instruction, slide_count)
            
            if not response:
                continue

            rebuilt = sanitize_and_rebuild_script(response, exact_titles)
            save_script_text(rebuilt)
            run_post_processors()
            force_exact_titles_after_postprocessing(exact_titles)            
            warnings = collect_all_warnings(OUT_SCRIPT, SLIDES_PDF, exact_titles)
            if not warnings:
                run_post_processors()  #### additional post_process to filter out title's possible error after exiting for loop
                log("Script validation passed.", "OK")
                return 0

            last_warnings = warnings
            for w in warnings:
                log(w, "WARN")

            try:
                OUT_SCRIPT.unlink(missing_ok=True)
                log(f"Removed {OUT_SCRIPT.name} to regenerate it.", "WARN")
            except Exception as e:
                log(f"Could not remove {OUT_SCRIPT.name}: {e}", "WARN")
        
        
        
        for w in last_warnings:
            log(f"Final failure: {w}", "ERR")
        return 1

    finally:
        try:
            client.shutdown()
            #pass
        except Exception:
            pass
        log("Selenium session finished.", "OK")


if __name__ == "__main__":
    raise SystemExit(main())
