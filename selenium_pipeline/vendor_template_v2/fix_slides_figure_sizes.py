#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required. Install with: pip install pillow")
    raise


# ------------------------------------------------------------
# Image helpers
# ------------------------------------------------------------
def get_image_size(folder: Path, filename: str) -> Optional[Tuple[int, int]]:
    path = folder / filename
    if not path.exists():
        return None
    try:
        with Image.open(path) as img:
            return img.size
    except Exception:
        return None


def aspect_ratio_from_file(folder: Path, filename: str) -> Optional[float]:
    size = get_image_size(folder, filename)
    if not size:
        return None
    w, h = size
    if h == 0:
        return None
    return w / h


def classify_orientation(ratio: Optional[float]) -> str:
    if ratio is None:
        return "unknown"
    if ratio > 1.2:
        return "landscape"
    if ratio < 0.8:
        return "portrait"
    return "square"


# ------------------------------------------------------------
# Frame-level context
# ------------------------------------------------------------
FRAME_RE = re.compile(
    r"(\\begin\{frame\}(?:\[[^\]]*\])?\{.*?\}.*?\\end\{frame\})",
    flags=re.DOTALL
)

INCLUDEGRAPHICS_RE = re.compile(
    r"\\includegraphics\s*\[(.*?)\]\s*\{([^{}]+)\}",
    flags=re.DOTALL
)

COLUMN_RE = re.compile(
    r"\\column\{([^{}]+)\}",
    flags=re.DOTALL
)


def bullet_count(frame_text: str) -> int:
    count = len(re.findall(r"\\item\b", frame_text))
    count += len(re.findall(r"\\begin\{enumerate\}", frame_text))
    return count


def has_columns(frame_text: str) -> bool:
    return r"\begin{columns}" in frame_text and r"\end{columns}" in frame_text


def nearest_column_width_before(frame_text: str, pos: int) -> Optional[str]:
    widths = []
    for m in COLUMN_RE.finditer(frame_text):
        if m.start() < pos:
            widths.append(m.group(1).strip())
    return widths[-1] if widths else None


def looks_like_tall_figure(filename: str, ratio: Optional[float]) -> bool:
    name = filename.lower()
    if any(k in name for k in ["portrait", "photo", "charles", "coulomb", "newton", "einstein"]):
        return True
    return ratio is not None and ratio < 0.8


# ------------------------------------------------------------
# Heuristic sizing strategy
# ------------------------------------------------------------
def choose_single_column_option(ratio: Optional[float], bullets: int) -> str:
    """
    Based on the strategy in gen_slides_prompt_v23.txt:
    - figure-dominant: width=0.88\textwidth,height=0.56\textheight
    - balanced:        width=0.76\textwidth,height=0.42\textheight
    - text-heavy:      width=0.62\textwidth,height=0.32\textheight

    Also informed by the aspect-ratio logic in gen_slides_selenium_v11.py.
    """
    if ratio is None:
        if bullets >= 4:
            return r"width=0.62\textwidth,height=0.32\textheight,keepaspectratio"
        if bullets >= 2:
            return r"width=0.76\textwidth,height=0.42\textheight,keepaspectratio"
        return r"width=0.88\textwidth,height=0.56\textheight,keepaspectratio"

    if bullets >= 4:
        return r"width=0.62\textwidth,height=0.32\textheight,keepaspectratio"

    if bullets >= 2:
        if ratio > 1.6:
            return r"width=0.76\textwidth,height=0.42\textheight,keepaspectratio"
        if ratio >= 0.8:
            return r"width=0.76\textwidth,height=0.42\textheight,keepaspectratio"
        return r"width=0.62\textwidth,height=0.32\textheight,keepaspectratio"

    if ratio > 1.6:
        return r"width=0.88\textwidth,height=0.56\textheight,keepaspectratio"
    if ratio >= 1.1:
        return r"width=0.76\textwidth,height=0.42\textheight,keepaspectratio"
    if ratio >= 0.8:
        return r"width=0.76\textwidth,height=0.42\textheight,keepaspectratio"
    return r"width=0.62\textwidth,height=0.32\textheight,keepaspectratio"


def choose_two_column_option(ratio: Optional[float], filename: str) -> str:
    """
    Based on the strategy in gen_slides_prompt_v23.txt:
    - regular two-column image: width=\linewidth,height=0.52\textheight
    - tall portrait in two-column: width=\linewidth,height=0.56\textheight
    """
    if looks_like_tall_figure(filename, ratio):
        return r"width=\linewidth,height=0.56\textheight,keepaspectratio"
    return r"width=\linewidth,height=0.52\textheight,keepaspectratio"


def choose_bounded_box_option(
    frame_text: str,
    image_filename: str,
    match_start_in_frame: int,
    image_folder: Path,
) -> str:
    ratio = aspect_ratio_from_file(image_folder, image_filename)
    bullets = bullet_count(frame_text)

    if has_columns(frame_text):
        return choose_two_column_option(ratio, image_filename)

    return choose_single_column_option(ratio, bullets)


# ------------------------------------------------------------
# Sanitizers
# ------------------------------------------------------------
def remove_markdown_fences(text: str) -> str:
    lines = text.splitlines()
    cleaned = [ln for ln in lines if ln.strip() != "```"]
    return "\n".join(cleaned) + ("\n" if text.endswith("\n") else "")


def normalize_includegraphics_options(option_str: str) -> str:
    """
    Ensure keepaspectratio is present exactly once.
    """
    parts = [p.strip() for p in option_str.split(",") if p.strip()]
    parts_wo_keep = [p for p in parts if p != "keepaspectratio"]
    parts_wo_keep.append("keepaspectratio")
    return ",".join(parts_wo_keep)


# ------------------------------------------------------------
# Core rewrite
# ------------------------------------------------------------
def rewrite_frame(frame_text: str, image_folder: Path) -> Tuple[str, int]:
    replacements = 0

    matches = list(INCLUDEGRAPHICS_RE.finditer(frame_text))
    if not matches:
        return frame_text, replacements

    out = []
    last = 0

    for m in matches:
        original_options = m.group(1).strip()
        filename = m.group(2).strip()

        chosen = choose_bounded_box_option(
            frame_text=frame_text,
            image_filename=filename,
            match_start_in_frame=m.start(),
            image_folder=image_folder,
        )
        chosen = normalize_includegraphics_options(chosen)

        out.append(frame_text[last:m.start()])
        out.append(f"\\includegraphics[{chosen}]{{{filename}}}")
        last = m.end()
        replacements += 1

    out.append(frame_text[last:])
    return "".join(out), replacements


def rewrite_tex(tex_text: str, image_folder: Path) -> Tuple[str, int]:
    total = 0
    pieces = []
    last = 0

    for m in FRAME_RE.finditer(tex_text):
        pieces.append(tex_text[last:m.start()])
        new_frame, n = rewrite_frame(m.group(1), image_folder)
        pieces.append(new_frame)
        total += n
        last = m.end()

    pieces.append(tex_text[last:])
    new_text = "".join(pieces)
    new_text = remove_markdown_fences(new_text)
    return new_text, total


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main() -> int:
    tex_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("slides.tex")
    if not tex_path.is_file():
        print(f"ERROR: TeX file not found: {tex_path}")
        return 2

    folder = tex_path.parent.resolve()
    original = tex_path.read_text(encoding="utf-8")

    fixed, n = rewrite_tex(original, folder)

    backup = tex_path.with_suffix(tex_path.suffix + ".bak")
    backup.write_text(original, encoding="utf-8")
    tex_path.write_text(fixed, encoding="utf-8", newline="\n")

    print(f"[OK] Updated: {tex_path}")
    print(f"[OK] Backup : {backup}")
    print(f"[OK] Rewritten includegraphics entries: {n}")
    print("[OK] Removed stray Markdown fences if present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())