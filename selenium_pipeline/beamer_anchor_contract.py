"""Source-level anchor ID manifest checks for future Beamer/PDF geometry extraction.

This is not a geometry extractor: it only verifies semantic anchor *references*.
Rendered bounding boxes and scientific readability must be tested separately.
"""
from __future__ import annotations

import re
from .storyboard_gate import StoryboardError

_ANCHOR = re.compile(r"\\MGElement\s*\{\s*([A-Za-z][A-Za-z0-9_.-]{0,95})\s*\}")


def collect_tex_anchor_ids(latex: str) -> list[str]:
    r"""Collect non-commented \MGElement{stable-id}{displayed content} tags.

    TeX escaped-percent/comment grammar is tricky: retain only lines with no
    effective unescaped comment and scan their non-comment prefix.
    """
    actual = []
    for line in latex.splitlines():
        end = len(line)
        for i, ch in enumerate(line):
            if ch != "%":
                continue
            backslashes = 0
            j = i - 1
            while j >= 0 and line[j] == "\\":
                backslashes += 1
                j -= 1
            if backslashes % 2 == 0:
                end = i
                break
        actual.extend(m.group(1) for m in _ANCHOR.finditer(line[:end]))
    return actual


def verify_tex_anchor_coverage(latex: str, storyboard: dict) -> dict:
    """Fail on absent/duplicate/unknown tokens; cannot prove visible coordinates."""
    expected = [e["element_id"] for slide in storyboard["slides"]
                for e in slide["elements"]]
    found = collect_tex_anchor_ids(latex)
    if not found:
        raise StoryboardError("No semantic \\MGElement{...} anchors in LaTeX")
    if len(found) != len(set(found)):
        raise StoryboardError("Duplicate semantic LaTeX anchor IDs")
    missing = set(expected) - set(found)
    extra = set(found) - set(expected)
    if missing or extra:
        raise StoryboardError(
            f"Semantic LaTeX anchors do not match storyboard: "
            f"missing={sorted(missing)}, unexpected={sorted(extra)}"
        )
    return {
        "status": "source_tags_present_geometry_unverified",
        "tag_count": len(found),
        "needs": ["rendered_bounding_box_measurement", "slide_page_mapping",
                  "graphic_panel_visual_validation"],
    }
