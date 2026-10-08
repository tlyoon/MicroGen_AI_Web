# -*- coding: utf-8 -*-

# MicroGen_AI Educational Automation Package
# © 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.
# This file is part of the MicroGen_AI package.
# Licensed under the MIT License (see LICENSE file in the project root).
# You may not use this file except in compliance with the License.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

"""
gen_slides_selenium_v11.py
- Uses source.pdf in the current directory.
- Uses gen_slides_prompt_v23.txt as the prompt template.
- Integrates the functionality of png_dimensions_to_json_v4.py directly.
- Generates png_dimensions.json before slide generation.
- Renders a prompt file with embedded PNG metadata for Gemini.
- Uploads source.pdf and the rendered prompt to Gemini.
- Writes Gemini output to slides.tex.
- Sanitizes copied Gemini UI response to remove labels like "Code snippet".
- Runs fix_latex_selenium_v4.fix_latex(slides.tex) only if needed.
"""

from __future__ import annotations

import json
import os
import sys
import time
import shutil
from pathlib import Path
import importlib.util
import subprocess
from typing import Any, Dict, Optional, List
import re

from PIL import Image

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

import fix_latex_selenium_v4

# ------------------------------------------------------------
# Early exit if slides already exist
# ------------------------------------------------------------
slides_tex = Path("slides.tex")
slides_pdf = Path("slides.pdf")

def log(msg: str, level: str = "INFO") -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)

if slides_tex.exists() and slides_pdf.exists():
    log("slides.tex and slides.pdf already exist. Skipping Gemini submission.", "INFO")
    sys.exit(0)
    
# ------------------------------------------------------------
# Pre-check compile
# ------------------------------------------------------------
def pdflatex_compiles(tex_path: Path) -> bool:
    """Return True if pdflatex compiles the file (single pass)."""
    try:
        cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name]
        proc = subprocess.run(
            cmd,
            cwd=str(tex_path.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
        )
        (tex_path.with_suffix(".compile0.log")).write_text(proc.stdout, encoding="utf-8", newline="\n")
        return proc.returncode == 0
    except Exception as e:
        (tex_path.with_suffix(".compile0.log")).write_text(f"[compile exception] {e}\n", encoding="utf-8")
        return False


# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
def log(msg: str, level: str = "INFO") -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


# ------------------------------------------------------------
# Text cleanup
# ------------------------------------------------------------
def strip_code_fences(text: str) -> str:
    """Remove leading/trailing Markdown code fences if present."""
    if not isinstance(text, str):
        return str(text)
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def strip_leading_nonlatex(text: str) -> str:
    """
    Remove Gemini/UI artefacts and any leading chatter before the real LaTeX starts.
    Common culprits include lines such as 'Code snippet', 'LaTeX', or short prose
    copied together with the code block from the Gemini UI.
    """
    if not isinstance(text, str):
        text = str(text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.lstrip("\ufeff \t\n")

    disposable_labels = {
        "code snippet", "latex", "tex", "output", "response", "code", "snippet"
    }

    lines = text.split("\n")
    while lines:
        first = lines[0].strip().strip(":").lower()
        if first in disposable_labels:
            lines.pop(0)
            continue
        if first.startswith("here is") or first.startswith("below is"):
            lines.pop(0)
            continue
        break
    text = "\n".join(lines).lstrip()

    markers = ["\\documentclass", "\\begin{document}", "\\title{"]
    positions = [text.find(m) for m in markers if text.find(m) != -1]
    if positions:
        text = text[min(positions):]

    return text.lstrip()


def strip_trailing_nonlatex(text: str) -> str:
    """Drop any copied UI artefacts or commentary after the LaTeX document ends."""
    if not isinstance(text, str):
        text = str(text)

    end_marker = "\\end{document}"
    pos = text.rfind(end_marker)
    if pos != -1:
        text = text[:pos + len(end_marker)]
    return text.rstrip()


def normalize_unicode_to_latex(text: str) -> str:
    """Replace common Unicode glyphs that can break pdflatex."""
    if not isinstance(text, str):
        text = str(text)

    replacements = {
        "−": "-",
        "±": "\\pm ",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "…": "...",
        "–": "-",
        "—": "-",
        "×": "\\times ",
        "·": "\\cdot ",
        "→": "\\to ",
        "⇒": "\\Rightarrow ",
        "°": "^\\circ",
        "µ": "\\mu ",
        "α": "\\alpha ",
        "β": "\\beta ",
        "γ": "\\gamma ",
        "θ": "\\theta ",
        "Δ": "\\Delta ",
        "Ω": "\\Omega ",
        "≤": "\\le ",
        "≥": "\\ge ",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    superscripts = {
        "²": "^2",
        "³": "^3",
        "⁴": "^4",
        "⁵": "^5",
        "⁶": "^6",
        "⁷": "^7",
        "⁸": "^8",
        "⁹": "^9",
        "⁰": "^0",
        "¹": "^1",
    }
    for bad, good in superscripts.items():
        text = text.replace(bad, good)

    return text


def sanitize_gemini_latex_response(text: str) -> str:
    """
    Robust response sanitizer for Gemini UI copy output.
    1. remove markdown fences
    2. remove leading non-LaTeX UI labels/chatter
    3. trim anything after \end{document}
    4. normalize common Unicode glyphs that break pdflatex
    """
    text = strip_code_fences(text)
    text = strip_leading_nonlatex(text)
    text = strip_trailing_nonlatex(text)
    text = normalize_unicode_to_latex(text)
    return text.strip()


# ------------------------------------------------------------
# Integrated png_dimensions_to_json_v4.py functionality
# ------------------------------------------------------------
def classify_orientation(width: int, height: int) -> str:
    ratio = width / height
    if ratio > 1.2:
        return "landscape"
    if ratio < 0.8:
        return "portrait"
    return "square"


def classify_figure_category(filename: str, width: int, height: int) -> str:
    name = filename.lower()
    ratio = width / height

    if any(k in name for k in ["charles", "coulomb", "newton", "einstein", "portrait", "photo"]):
        return "portrait_photo"
    if any(k in name for k in ["diagram", "schematic", "circuit", "setup", "apparatus"]):
        return "diagram"
    if any(k in name for k in ["graph", "plot", "chart"]):
        return "graph"
    if "figure" in name:
        if ratio > 1.6:
            return "wide_figure"
        if ratio < 0.75:
            return "tall_figure"
        return "standard_figure"
    return "unknown"


def read_pdf_page_size(pdf_path: Path) -> Optional[Dict[str, Any]]:
    if not pdf_path.exists():
        return None

    if PdfReader is None:
        return {"error": "PyPDF2 not installed. Install with: pip install PyPDF2"}

    try:
        reader = PdfReader(str(pdf_path))
        if not reader.pages:
            return {"error": f"{pdf_path.name} exists but has no pages"}

        page0 = reader.pages[0]
        mediabox = page0.mediabox
        width_pt = float(mediabox.width)
        height_pt = float(mediabox.height)
        width_in = width_pt / 72.0
        height_in = height_pt / 72.0
        aspect_ratio = width_pt / height_pt if height_pt else None

        return {
            "file": pdf_path.name,
            "page_width_pt": round(width_pt, 3),
            "page_height_pt": round(height_pt, 3),
            "page_width_in": round(width_in, 3),
            "page_height_in": round(height_in, 3),
            "page_aspect_ratio": round(aspect_ratio, 3) if aspect_ratio else None,
        }
    except Exception as e:
        return {"error": str(e)}


def compute_slide_fit(
    img_width_px: int,
    img_height_px: int,
    slide_width_pt: Optional[float],
    slide_height_pt: Optional[float],
) -> Dict[str, Any]:
    img_ratio = img_width_px / img_height_px

    if not slide_width_pt or not slide_height_pt:
        return {"fit_guidance_available": False}

    slide_ratio = slide_width_pt / slide_height_pt
    height_fraction_if_fit_width = slide_ratio / img_ratio
    width_fraction_if_fit_height = img_ratio / slide_ratio

    fit_by_width_safe = height_fraction_if_fit_width <= 0.82
    fit_by_height_safe = width_fraction_if_fit_height <= 0.9

    if fit_by_width_safe:
        recommended_fit_mode = "width"
    elif fit_by_height_safe:
        recommended_fit_mode = "height"
    else:
        recommended_fit_mode = "bounded_box"

    return {
        "fit_guidance_available": True,
        "image_aspect_ratio": round(img_ratio, 3),
        "slide_aspect_ratio": round(slide_ratio, 3),
        "height_fraction_if_fit_width": round(height_fraction_if_fit_width, 3),
        "width_fraction_if_fit_height": round(width_fraction_if_fit_height, 3),
        "fit_by_width_safe": fit_by_width_safe,
        "fit_by_height_safe": fit_by_height_safe,
        "recommended_fit_mode": recommended_fit_mode,
    }


def choose_bounded_box_latex_option(width: int, height: int) -> str:
    """
    Robust bounded-box heuristic:
    - aspect_ratio > 1.6              -> width=0.90\\textwidth,height=0.62\\textheight
    - 1.1 <= aspect_ratio <= 1.6      -> width=0.82\\textwidth,height=0.50\\textheight
    - 0.8 <= aspect_ratio < 1.1       -> width=0.68\\textwidth,height=0.38\\textheight
    - aspect_ratio < 0.8              -> width=\\linewidth,height=0.60\\textheight

    Use both width and height together with keepaspectratio so the figure
    stays within a safe bounding box on the Beamer frame.
    """
    aspect_ratio = width / height
    if aspect_ratio > 1.6:
        return r"width=0.90\textwidth,height=0.62\textheight"
    if 1.1 <= aspect_ratio <= 1.6:
        return r"width=0.82\textwidth,height=0.50\textheight"
    if 0.8 <= aspect_ratio < 1.1:
        return r"width=0.68\textwidth,height=0.38\textheight"
    return r"width=\linewidth,height=0.60\textheight"


def determine_latex_settings(
    width: int,
    height: int,
    category: str,
    slide_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ratio = width / height
    orientation = classify_orientation(width, height)

    slide_width_pt = None
    slide_height_pt = None
    if slide_info and "page_width_pt" in slide_info and "page_height_pt" in slide_info:
        slide_width_pt = slide_info["page_width_pt"]
        slide_height_pt = slide_info["page_height_pt"]

    fit_info = compute_slide_fit(width, height, slide_width_pt, slide_height_pt)
    suggested_option = choose_bounded_box_latex_option(width, height)

    suggested_width = None
    suggested_height = None
    for part in suggested_option.split(","):
        part = part.strip()
        if part.startswith("width="):
            suggested_width = part.split("=", 1)[1]
        elif part.startswith("height="):
            suggested_height = part.split("=", 1)[1]

    if ratio > 1.6:
        recommended_columns_layout = "single_column"
        beamer_scale = 0.90
    elif 1.1 <= ratio <= 1.6:
        recommended_columns_layout = "single_column"
        beamer_scale = 0.82
    elif 0.8 <= ratio < 1.1:
        recommended_columns_layout = "single_column"
        beamer_scale = 0.68
    else:
        recommended_columns_layout = "two_columns"
        beamer_scale = 0.60

    return {
        "aspect_ratio": round(ratio, 3),
        "orientation": orientation,
        "suggested_latex_width": suggested_width,
        "suggested_latex_height": suggested_height,
        "suggested_latex_option": suggested_option,
        "suggested_beamer_scale": beamer_scale,
        "recommended_columns_layout": recommended_columns_layout,
        "slide_fit": fit_info,
        "mandatory_heuristic_case": (
            "figure_dominant_single_column" if ratio > 1.6 else
            "balanced_single_column" if 1.1 <= ratio <= 1.6 else
            "text_heavy_single_column" if 0.8 <= ratio < 1.1 else
            "two_column_or_tall"
        ),
    }


def build_record(png_file: Path, slide_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    with Image.open(png_file) as img:
        width, height = img.size

    category = classify_figure_category(png_file.name, width, height)
    latex_info = determine_latex_settings(width, height, category, slide_info)

    return {
        "width_px": width,
        "height_px": height,
        "figure_category": category,
        **latex_info,
        "latex_example": (
            f"\\includegraphics[{latex_info['suggested_latex_option']},keepaspectratio]"
            f"{{{png_file.name}}}"
        ),
    }


def generate_png_dimension_data(folder: Path) -> Dict[str, Any]:
    png_files = sorted(folder.glob("*.png"))
    slide_info = read_pdf_page_size(folder / "slides.pdf")

    data: Dict[str, Any] = {
        "directory": str(folder.resolve()),
        "unit": "pixels",
        "generator": "integrated_png_dimensions_to_json_v4",
        "purpose": (
            "Image metadata for Gemini / LaTeX / Beamer slide generation. "
            "Use as layout hints, not academic content."
        ),
        "slide_reference": slide_info,
        "files": {},
    }

    for png_file in png_files:
        try:
            data["files"][png_file.name] = build_record(png_file, slide_info)
        except Exception as e:
            data["files"][png_file.name] = {"error": str(e)}

    return data


def write_png_dimensions_json(folder: Path, out_json: Path) -> Path:
    data = generate_png_dimension_data(folder)
    out_json.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log(f"Generated {out_json.name} with metadata for {len(data.get('files', {}))} PNG file(s).", "OK")
    return out_json


# ------------------------------------------------------------
# Prompt rendering
# ------------------------------------------------------------
def render_prompt_template(template_path: Path, png_json_path: Path, rendered_prompt_path: Path) -> Path:
    template = template_path.read_text(encoding="utf-8")
    png_json_text = png_json_path.read_text(encoding="utf-8")

    replacements = {
        "{png_dimension_json}": png_json_text,
        "{pdf_content}": (
            "Use the attached file source.pdf as the sole sub-chapter content source. "
            "Do not expect inline PDF text in this prompt."
        ),
    }

    rendered = template
    for old, new in replacements.items():
        rendered = rendered.replace(old, new)

    rendered_prompt_path.write_text(rendered, encoding="utf-8", newline="\n")
    log(f"Rendered Gemini prompt with embedded PNG metadata: {rendered_prompt_path.name}", "OK")
    return rendered_prompt_path


# ------------------------------------------------------------
# Gemini UI automation layer (reusable)
# ------------------------------------------------------------
_SEL_PATH = Path(__file__).with_name("selenium.py")
spec = importlib.util.spec_from_file_location("gemini_selenium", str(_SEL_PATH))
gemsel = importlib.util.module_from_spec(spec)
assert spec and spec.loader, f"Failed to load local selenium.py from {_SEL_PATH}"
sys.modules[spec.name] = gemsel
spec.loader.exec_module(gemsel)

_wait_until_generation_finishes = gemsel._wait_until_generation_finishes
_copy_via_toolbar_copy_button = gemsel._copy_via_toolbar_copy_button
_copy_via_more_menu = gemsel._copy_via_more_menu


def latest_response_container(driver):
    selectors = [
        "message-content",
        "div[role='article']",
        "div[class*='response']",
        "div[class*='model']",
    ]
    found = []
    seen = set()

    for sel in selectors:
        try:
            els = driver.find_elements(gemsel.By.CSS_SELECTOR, sel)
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
            found.append(el)

    return found[-1] if found else None


def extract_longest_codeblock_from_latest_response(driver) -> str:
    root = latest_response_container(driver)
    if root is None:
        return ""

    try:
        txt = driver.execute_script(
            """
            const root = arguments[0];
            if (!root) return "";

            const blocks = [];
            root.querySelectorAll('pre code, pre').forEach(el => {
                const t = (el.innerText || el.textContent || "").trim();
                if (t) blocks.push(t);
            });

            blocks.sort((a, b) => b.length - a.length);
            return blocks.length ? blocks[0] : "";
            """,
            root,
        )
        return (txt or "").strip()
    except Exception:
        return ""


def extract_latest_response_text_from_dom(driver) -> str:
    root = latest_response_container(driver)
    if root is None:
        return ""

    try:
        txt = driver.execute_script(
            """
            const root = arguments[0];
            if (!root) return "";
            return (root.innerText || root.textContent || "").trim();
            """,
            root,
        )
        return (txt or "").strip()
    except Exception:
        return ""

FENCED_LATEX_RE = re.compile(
    r"```(?:latex)?\s*(.*?)```",
    flags=re.IGNORECASE | re.DOTALL,
)

def extract_fenced_latex_block(text: str) -> str:
    """
    Extract the longest fenced code block from copied Gemini text.
    Prefer a block containing \\documentclass.
    """
    if not text:
        return ""

    blocks = [m.group(1).strip() for m in FENCED_LATEX_RE.finditer(text)]
    if not blocks:
        return ""

    with_doc = [b for b in blocks if "\\documentclass" in b]
    if with_doc:
        return max(with_doc, key=len).strip()

    return max(blocks, key=len).strip()


def capture_transport_block_via_copy_icon(
    client: "gemsel.GeminiSeleniumClient",
    wait_cap: int,
    retries: int = 8,
) -> str:
    """
    Copy-first transport capture:
    1. wait for Gemini to finish
    2. click Copy icon / Copy menu
    3. extract fenced LaTeX block from copied text
    4. fall back to raw copied text only if it already looks like a full LaTeX doc
    """
    if client.driver is None:
        raise RuntimeError("Selenium client driver is not available.")

    _wait_until_generation_finishes(client.driver, timeout=float(wait_cap), poll=0.5)

    best_raw = ""
    deadline = time.time() + min(max(wait_cap, 20), 90)

    while time.time() < deadline:
        copied = _copy_via_toolbar_copy_button(client.driver) or ""
        if not copied:
            copied = _copy_via_more_menu(client.driver) or ""

        copied = (copied or "").strip()
        if copied:
            best_raw = copied

            fenced = extract_fenced_latex_block(copied)
            if fenced and "\\documentclass" in fenced and "\\end{document}" in fenced:
                return fenced.strip()

            if "\\documentclass" in copied and "\\end{document}" in copied:
                return copied.strip()

        time.sleep(1.0)

    if best_raw:
        fenced = extract_fenced_latex_block(best_raw)
        if fenced:
            return fenced.strip()
        return best_raw.strip()

    return ""

def candidate_tex_compiles(tex_text: str, target_dir: Path) -> bool:
    probe = target_dir / "_slides_transport_probe.tex"
    try:
        probe.write_text(tex_text + "\n", encoding="utf-8", newline="\n")
        ok = pdflatex_compiles(probe)
        return ok
    finally:
        for ext in [
            ".tex",
            ".pdf",
            ".aux",
            ".log",
            ".nav",
            ".out",
            ".snm",
            ".toc",
            ".synctex.gz",
            ".compile0.log",
        ]:
            try:
                (target_dir / f"_slides_transport_probe{ext}").unlink()
            except Exception:
                pass


def _strip_latex_comments(tex: str) -> str:
    """Remove LaTeX comments, but keep escaped percent signs."""
    lines = []
    for line in tex.splitlines():
        lines.append(re.sub(r"(?<!\\)%.*$", "", line))
    return "\n".join(lines)


def compile_candidate_and_count_pages(tex_text: str, target_dir: Path) -> tuple[bool, Optional[int], str]:
    """
    Compile a temporary probe file and return:
      (compile_ok, pdf_page_count, compile_log)
    """
    stem = "_slides_sanity_probe"
    probe = target_dir / f"{stem}.tex"
    pdf = target_dir / f"{stem}.pdf"

    try:
        probe.write_text(tex_text + "\n", encoding="utf-8", newline="\n")

        cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", probe.name]
        proc = subprocess.run(
            cmd,
            cwd=str(target_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
        )

        compile_log = proc.stdout or ""
        ok = proc.returncode == 0

        page_count = None
        if ok and pdf.exists() and PdfReader is not None:
            try:
                reader = PdfReader(str(pdf))
                page_count = len(reader.pages)
            except Exception:
                page_count = None

        return ok, page_count, compile_log

    except Exception as e:
        return False, None, f"[compile exception] {e}"

    finally:
        for ext in [
            ".tex", ".pdf", ".aux", ".log", ".nav", ".out", ".snm", ".toc",
            ".synctex.gz", ".vrb", ".fls", ".fdb_latexmk"
        ]:
            try:
                (target_dir / f"{stem}{ext}").unlink()
            except Exception:
                pass


def beamer_stack_sanity_check(
    tex_text: str,
    target_dir: Path,
    min_slides: int = 6,
    max_slides: int = 25,
) -> tuple[bool, List[str]]:
    """
    Strict sanity gate for MicroGen Beamer slide stacks.

    A candidate passes only if it:
      1. is a Beamer document, not article/report/book;
      2. has a complete document environment;
      3. contains a reasonable Beamer frame stack;
      4. contains title/outline structure;
      5. compiles with pdflatex;
      6. produces a PDF with a slide count in the expected range.
    """
    reasons: List[str] = []

    if not tex_text or not tex_text.strip():
        return False, ["empty LaTeX payload"]

    raw = tex_text.strip()
    tex = _strip_latex_comments(raw)
    compact = re.sub(r"\s+", " ", tex)

    # ------------------------------------------------------------
    # Reject obvious transport / UI failures
    # ------------------------------------------------------------
    lower_head = raw[:2000].lower()
    bad_transport_markers = [
        "normally i can help",
        "i don't seem to have access",
        "i do not have access",
        "try again or ask me",
        "i cannot access the file",
        "i can't access the file",
    ]

    for marker in bad_transport_markers:
        if marker in lower_head:
            reasons.append(f"Gemini transport/refusal marker detected: {marker!r}")

    if raw.startswith("```") or raw.endswith("```"):
        reasons.append("markdown code fence still present after sanitization")

    # ------------------------------------------------------------
    # Document-class gate
    # ------------------------------------------------------------
    docclass = re.search(
        r"\\documentclass(?:\s*\[[^\]]*\])?\s*\{([^}]+)\}",
        tex,
        flags=re.IGNORECASE,
    )

    if not docclass:
        reasons.append("missing \\documentclass")
    else:
        docclass_name = docclass.group(1).strip().lower()
        if docclass_name != "beamer":
            reasons.append(f"wrong document class: expected beamer, found {docclass_name!r}")

    if re.search(r"\\documentclass(?:\s*\[[^\]]*\])?\s*\{(?:article|report|book|standalone)\}", tex):
        reasons.append("non-Beamer document class detected")

    # ------------------------------------------------------------
    # Required LaTeX document structure
    # ------------------------------------------------------------
    begin_doc_pos = tex.find(r"\begin{document}")
    end_doc_pos = tex.rfind(r"\end{document}")

    if begin_doc_pos == -1:
        reasons.append("missing \\begin{document}")

    if end_doc_pos == -1:
        reasons.append("missing \\end{document}")

    if begin_doc_pos != -1 and end_doc_pos != -1 and begin_doc_pos > end_doc_pos:
        reasons.append("\\begin{document} occurs after \\end{document}")

    # ------------------------------------------------------------
    # Beamer frame-stack structure
    # ------------------------------------------------------------
    begin_frame_count = len(re.findall(r"\\begin\s*\{frame\}", tex))
    end_frame_count = len(re.findall(r"\\end\s*\{frame\}", tex))

    # Count also compact \frame{...} title-page style frames.
    frame_macro_count = len(re.findall(r"\\frame\s*(?:<[^>]*>)?\s*\{", tex))

    total_frame_count = begin_frame_count + frame_macro_count

    if begin_frame_count != end_frame_count:
        reasons.append(
            f"unbalanced frame environments: begin={begin_frame_count}, end={end_frame_count}"
        )

    if total_frame_count < min_slides:
        reasons.append(
            f"too few Beamer frames: found {total_frame_count}, expected at least {min_slides}"
        )

    if total_frame_count > max_slides + 3:
        reasons.append(
            f"too many Beamer frames: found {total_frame_count}, expected about {min_slides}-{max_slides}"
        )

    # ------------------------------------------------------------
    # Required presentation components
    # ------------------------------------------------------------
    #if r"\title" not in compact:
    #    reasons.append("missing \\title{...}")

    if not re.search(r"\\title\s*\{[^}]*\}", tex):
        reasons.append("missing \\title{...}")

    if (r"\titlepage" not in compact) and (r"\maketitle" not in compact):
        reasons.append("missing title slide command: \\titlepage or \\maketitle")
    
    '''
    if r"\tableofcontents" not in compact:
        reasons.append("missing outline slide: \\tableofcontents")

    if r"\section" not in compact:
        reasons.append("missing at least one \\section{...}")
    '''
    
    has_toc = r"\tableofcontents" in compact

    has_section = bool(
        re.search(r"\\section\s*(?:\[[^\]]*\])?\s*\{[^}]+\}", tex)
    )
    
    has_manual_outline_frame = bool(
        re.search(
            r"\\begin\s*\{frame\}(?:\s*\[[^\]]*\])?\s*\{"
            r"\s*(outline|overview|contents|key topics|key topics covered|learning objectives)"
            r"\s*\}",
            tex,
            flags=re.IGNORECASE,
        )
    ) or bool(
        re.search(
            r"\\frametitle\s*\{"
            r"\s*(outline|overview|contents|key topics|key topics covered|learning objectives)"
            r"\s*\}",
            tex,
            flags=re.IGNORECASE,
        )
    )
    
    if not (has_toc or has_manual_outline_frame):
        reasons.append(
            "missing outline slide: expected either \\tableofcontents or a frame titled Outline/Overview/Contents"
        )
    
    # Only require sections if the document uses \tableofcontents.
    # A manual Outline frame does not need \section commands.
    if has_toc and not has_section:
        reasons.append("uses \\tableofcontents but has no \\section{...} entries")
    
    
    # A 6-25 slide lecture should not be a tiny one-line document.
    if len(raw) < 2500:
        reasons.append(f"payload too short for a Beamer lecture stack: {len(raw)} characters")

    # ------------------------------------------------------------
    # Compile and inspect produced PDF page count
    # ------------------------------------------------------------
    compile_ok, page_count, compile_log = compile_candidate_and_count_pages(raw, target_dir)

    if not compile_ok:
        reasons.append("pdflatex failed during sanity probe")

    if compile_ok and page_count is not None:
        if page_count < min_slides:
            reasons.append(
                f"compiled PDF has too few pages: {page_count}, expected at least {min_slides}"
            )
        if page_count > max_slides + 3:
            reasons.append(
                f"compiled PDF has too many pages: {page_count}, expected about {min_slides}-{max_slides}"
            )

    return len(reasons) == 0, reasons


def send_prompt_and_capture_transport_block(
    client: "gemsel.GeminiSeleniumClient",
    instruction_text: str,
    wait_cap: int,
) -> str:
    if client.driver is None:
        raise RuntimeError("Selenium client driver is not available.")

    if not client.type_prompt_text(instruction_text, retries=3):
        raise RuntimeError("Could not type into Gemini prompt field after retries.")

    if not client.click_send_with_fallbacks(retries=3):
        raise RuntimeError("Could not send the prompt after retries.")

    # -----------------------------
    # First choice: use Gemini's own Copy action
    # -----------------------------
    copied = capture_transport_block_via_copy_icon(client, wait_cap=wait_cap, retries=8)
    if copied:
        return copied.strip()

    # -----------------------------
    # Last-resort fallback: DOM scrape
    # -----------------------------
    _wait_until_generation_finishes(client.driver, timeout=float(wait_cap), poll=0.5)

    deadline = time.time() + 20.0
    best = ""
    stable = 0

    while time.time() < deadline:
        block = extract_longest_codeblock_from_latest_response(client.driver)

        if block:
            if block == best:
                stable += 1
            else:
                best = block
                stable = 0

            if "\\documentclass" in block and "\\end{document}" in block and stable >= 1:
                return block.strip()

        time.sleep(0.8)

    fallback = extract_latest_response_text_from_dom(client.driver).strip()
    if fallback:
        fenced = extract_fenced_latex_block(fallback)
        if fenced:
            return fenced.strip()
        return fallback

    return ""


def generate_slides_tex(
    client: "gemsel.GeminiSeleniumClient",
    pdf_path: Path,
    prompt_path: Path,
    png_json_path: Path,
    out_tex: Path,
    wait_cap: int,
) -> Path:
    """
    Robust generation:
      - open chat
      - upload files
      - ask Gemini to return the whole LaTeX document inside ONE fenced code block
      - extract that code block directly from the latest response DOM
      - sanitize and compile-gate before accepting
    """
    last_latex = ""
    last_preview = ""

    #for attempt in range(1, 4):
    #    log(f"Slides generation attempt {attempt}/3", "INFO")

    max_attempts = int(os.getenv("SLIDES_MAX_ATTEMPTS", "6"))
    
    for attempt in range(1, max_attempts + 1):
        log(f"Slides generation attempt {attempt}/{max_attempts}", "INFO")        
              
        client.open_clean_gemini_chat()
        client.upload_files([pdf_path, prompt_path, png_json_path])

        instruction = (
            f"Please read the attached file '{prompt_path.name}' and execute the instructions EXACTLY as written. "
            f"Use the attached file '{pdf_path.name}' as the sole academic content source. "
            f"The PNG dimension metadata has already been embedded into '{prompt_path.name}' and is also attached as '{png_json_path.name}'. "
            "Use that metadata only for figure sizing and slide layout decisions. "
            "Use the metadata field recommended_columns_layout to decide when a two-column Beamer layout is preferable. "
            "If a figure is tall, portrait-oriented, or side-by-side explanation improves readability, strongly prefer a two-column layout. "
            "Preserve figure aspect ratio at all times. "
            "Do not distort figures. "
            "Use robust bounded-box sizing in \\includegraphics: normally specify both width=... and height=... together with keepaspectratio so figures cannot exceed safe slide limits in either direction. "
            "If a slide contains substantial text, reduce the allowed figure height. "
            "Prefer two-column layout when a nontrivial figure must coexist with several bullets. "
            "If readability is still poor, split the content into a dedicated figure-focused slide rather than oversizing the figure. "
            "Your output must be a single LaTeX Beamer .tex document that compiles with pdflatex. "
            "TRANSPORT OVERRIDE FOR THIS RUN: Ignore any earlier instruction that forbids code fences. "
            "Return the ENTIRE LaTeX document inside EXACTLY ONE fenced code block that begins with ```latex and ends with ```. "
            "Do not place any text before or after that fenced block. "
            "Inside the fenced block, preserve literal raw LaTeX source exactly. "
            "Do NOT visually render mathematics, fractions, arrows, or Greek letters as pretty Unicode symbols. "
            "Keep literal commands such as \\alpha, \\beta, \\theta, \\Delta, \\Omega, \\mu, \\frac{...}{...}, \\vec{E}, and \\times inside the fenced source. "
            "The fenced block must contain the full document from \\documentclass through \\end{document}."
        )
        
        ###
        response_text = send_prompt_and_capture_transport_block(
            client=client,
            instruction_text=instruction,
            wait_cap=wait_cap,
        )
        
        raw_attempt_path = out_tex.with_name(f"slides_attempt_{attempt}_raw.txt")
        raw_attempt_path.write_text(response_text or "", encoding="utf-8", newline="\n")
        
        if not response_text.strip():
            log(f"Attempt {attempt}: no response text recovered from Gemini transport.", "WARN")
            continue
        
        latex = sanitize_gemini_latex_response(response_text)
        latex = normalize_unicode_to_latex(latex)
        
        last_latex = latex
        last_preview = latex[:500].replace("\n", "\\n")
        
        ###

        sanity_ok, sanity_reasons = beamer_stack_sanity_check(
            latex,
            out_tex.parent,
            min_slides=int(os.getenv("SLIDES_MIN_COUNT", "4")),
            max_slides=int(os.getenv("SLIDES_MAX_COUNT", "25")),
        )
        
        if not sanity_ok:
            failed_candidate = out_tex.with_name(f"slides_attempt_{attempt}_failed_sanity.tex")
            failed_report = out_tex.with_name(f"slides_attempt_{attempt}_failed_sanity_report.txt")
        
            failed_candidate.write_text(latex + "\n", encoding="utf-8", newline="\n")
            failed_report.write_text(
                "\n".join(f"- {r}" for r in sanity_reasons) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        
            log(
                f"Attempt {attempt}: rejected by Beamer sanity gate: "
                + "; ".join(sanity_reasons[:4]),
                "WARN",
            )
            continue
        
        out_tex.write_text(latex + "\n", encoding="utf-8", newline="\n")
        log(f"Wrote accepted Beamer slide stack to {out_tex.name}", "OK")
        return out_tex


        
        
        '''
        if "\\documentclass" not in latex[:400]:
            failed_candidate = out_tex.with_name(f"slides_attempt_{attempt}_missing_docclass.txt")
            failed_candidate.write_text(response_text + "\n", encoding="utf-8", newline="\n")
            log(f"Attempt {attempt}: missing \\documentclass near the top.", "WARN")
            continue        
        ###
        
        if "\\end{document}" not in latex:
            log(f"Attempt {attempt}: missing \\end{{document}}.", "WARN")
            continue

        if not candidate_tex_compiles(latex, out_tex.parent):
            failed_candidate = out_tex.with_name(f"slides_attempt_{attempt}_failed_compile.tex")
            failed_candidate.write_text(latex + "\n", encoding="utf-8", newline="\n")
            log(f"Attempt {attempt}: candidate LaTeX failed compile gate.", "WARN")
            continue

        out_tex.write_text(latex + "\n", encoding="utf-8", newline="\n")
        log(f"Wrote {out_tex.name}", "OK")
        return out_tex
        '''
        ###

    ###
    '''
    if last_latex:
        out_tex.write_text(last_latex + "\n", encoding="utf-8", newline="\n")
        log(
            "All guarded transport attempts failed compile gate. Wrote the last recovered candidate to slides.tex for inspection.",
            "WARN",
        )
        return out_tex

    raise RuntimeError(
        "Failed to recover any LaTeX payload from the Gemini UI response. "
        f"Last preview: {last_preview}"
    )
    '''
    ###

    if last_latex:
        rejected_path = out_tex.with_name("slides_last_rejected_candidate.tex")
        rejected_path.write_text(last_latex + "\n", encoding="utf-8", newline="\n")
        log(
            f"All attempts failed the Beamer sanity gate. "
            f"Last rejected candidate was saved as {rejected_path.name}, not released as slides.tex.",
            "ERROR",
        )
    
    raise RuntimeError(
        "Failed to produce a valid Beamer slide stack after all attempts. "
        f"Last preview: {last_preview}"
    )
    


# ------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------
def cleanup_latex_artifacts(stem: str = "slides") -> None:
    list2rem = [
        "cleaned_slides.tex",
        "defective_slides.tex",
        f"{stem}.aux",
        f"{stem}.log",
        f"{stem}.nav",
        f"{stem}.out",
        f"{stem}.snm",
        f"{stem}.toc",
        f"{stem}.synctex.gz",
    ]
    for f in list2rem:
        try:
            os.remove(f)
            log(f"Removed {f}", "INFO")
        except Exception:
            pass


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main() -> int:
    print(
        "\n# ================================================================\n"
        "# This code is designed to work on Windows with Chrome + Gemini UI\n"
        "# ================================================================\n"
    )

    current_dir = Path.cwd()
    pdf_path = current_dir / "source.pdf"
    out_tex = current_dir / "slides.tex"
    prompt_template_path = current_dir / "gen_slides_prompt_v23.txt"
    rendered_prompt_path = current_dir / "gen_slides_prompt_v23_rendered.txt"
    png_json_path = current_dir / "png_dimensions.json"

    if not pdf_path.is_file():
        print("source.pdf not found. Please provide input source.pdf and retry")
        return 2

    if not prompt_template_path.is_file():
        print("gen_slides_prompt_v23.txt not found in current directory.")
        return 2

    if not shutil.which("pdflatex"):
        print("pdflatex not found in PATH")
        print("Fix this issue to retry.")
        return 2

    # Step 1: integrated equivalent of png_dimensions_to_json_v4.py
    write_png_dimensions_json(current_dir, png_json_path)

    # Step 2: render prompt with embedded metadata
    render_prompt_template(prompt_template_path, png_json_path, rendered_prompt_path)

    debug_port = int(os.getenv("DEBUG_PORT", "9222"))
    gemini_url = os.getenv("GEMINI_URL", "https://gemini.google.com/app")
    wait_cap = int(os.getenv("WAIT_SLIDES_MAX", os.getenv("WAIT_MAPPING_MAX", "240")))

    cfg = gemsel.Config(
        root=current_dir,
        gemini_url=gemini_url,
        debug_port=debug_port,
        wait_mapping_max=wait_cap,
        chrome_exe=os.getenv("CHROME_EXE", gemsel.Config.chrome_exe),
        user_data_dir=os.getenv("GEMINI_USER_DATA_DIR", gemsel.Config.user_data_dir),
        profile_directory=os.getenv("GEMINI_PROFILE_DIRECTORY", gemsel.Config.profile_directory),
        fallback_user_data_dir=os.getenv("GEMINI_FALLBACK_USER_DATA_DIR", gemsel.Config.fallback_user_data_dir),
        fallback_profile_directory=os.getenv("GEMINI_FALLBACK_PROFILE_DIRECTORY", gemsel.Config.fallback_profile_directory),
        use_persistent_chrome=(os.getenv("USE_PERSISTENT_CHROME", "1") != "0"),
        force_kill_chrome_to_free_port=(os.getenv("SAFE_CHROME", "0") != "1"),
    )

    client = gemsel.GeminiSeleniumClient(cfg)

    try:
        log("Starting Gemini Selenium client...", "INFO")
        client.start(ensure_gemini_on_launch=True)
        generate_slides_tex(
            client=client,
            pdf_path=pdf_path,
            prompt_path=rendered_prompt_path,
            png_json_path=png_json_path,
            out_tex=out_tex,
            wait_cap=wait_cap,
        )
    finally:
        try:
            client.shutdown()
            #pass
        except Exception:
            pass
        log("Selenium session is done.", "INFO")

    time.sleep(1.0)
    log("Compiling latex (pre-check) ...", "INFO")
    if pdflatex_compiles(out_tex):
        log("slides.tex compiles. Skipping fix_latex_selenium_v4.", "OK")
    else:
        log("slides.tex failed to compile. Running fix_latex_selenium_v4.", "WARN")
        fix_latex_selenium_v4.fix_latex(str(out_tex))

        cleanup_latex_artifacts(stem="slides")
    return 0


if __name__ == "__main__":
    
    ##
    SCRIPT_1 = "launch_gemini_chrome.py"
    script_path = Path(__file__).resolve().with_name(SCRIPT_1)
    result = subprocess.run(
        [sys.executable, str(script_path)],
        check=True
    )
    ##
    raise SystemExit(main())
