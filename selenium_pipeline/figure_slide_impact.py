"""Identify restored-figure slide numbers using LaTeX frame boundaries.

For decks with one output page per frame, this gives precise affected slides
without relying on recompilation-sensitive PDF text. Unsupported overlays
are flagged for full semantic review.
"""
from __future__ import annotations
import re
from pathlib import Path
from .figure_audit import GRAPHIC

FRAME_START = re.compile(r"\\begin\s*\{frame\}")
FRAME_END = re.compile(r"\\end\s*\{frame\}")

def figure_slide_map(tex: Path) -> dict:
    source=Path(tex).read_text(encoding="utf-8",errors="replace")
    frames=[]
    position=0
    while True:
        start=FRAME_START.search(source,position)
        if start is None:
            break
        end=FRAME_END.search(source,start.end())
        if end is None:
            raise ValueError("Unclosed LaTeX frame")
        frames.append(source[start.start():end.end()])
        position=end.end()
    if not frames:
        raise ValueError("No LaTeX frames")
    return {reference:[i for i,frame in enumerate(frames,1)
                       if reference in GRAPHIC.findall(frame)]
            for reference in GRAPHIC.findall(source)}

def restored_figure_impact(tex: Path, references: list[str], pdf_pages: int) -> dict:
    mapping=figure_slide_map(tex)
    frame_count=max((i for values in mapping.values() for i in values),default=0)
    text=Path(tex).read_text(encoding="utf-8",errors="replace")
    actual_frames=len(FRAME_START.findall(text))
    unsafe=actual_frames!=pdf_pages or bool(re.search(r"\\(?:pause|only|onslide|uncover|visible)\b",text))
    missing=[name for name in references if name not in mapping]
    if missing:
        raise ValueError(f"Unmapped figures: {missing}")
    affected=sorted({i for name in references for i in mapping[name]})
    if unsafe:
        affected=list(range(1,pdf_pages+1))
    return {"affected":affected,"page_count_changed":actual_frames!=pdf_pages,
            "requires_semantic_review":bool(affected),
            "conservative_full_review":unsafe,
            "figure_to_slides":{name:mapping[name] for name in references}}
