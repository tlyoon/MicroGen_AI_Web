"""Fail-closed validation of Gemini figure/caption mappings before file publication.

A source figure comprising panels (a), (b), (c) cannot be reconstructed by
arbitrarily concatenating Docling crops. Without authoritative source-space
bounding boxes, colliding/misidentified targets require review, not merging.
This module performs no Gemini calls and writes no teaching assets.
"""
from __future__ import annotations

import re
from collections import defaultdict

_FIGURE_ID = re.compile(r"(?i)\bfig(?:ure)?[\s._-]*(\d+)[\s._-]+(\d+)\b")
_PANEL_ID = re.compile(r"(?i)(?:\s|_|-|(?<=\d))\(([a-z])\)(?=[.\s_-]|$)")
_TRANSLATE = str.maketrans({"\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-"})

class FigureCompositeReviewRequired(ValueError):
    """A mapping would silently lose/mislabel figure or subpanel content."""

    def __init__(self, issues: list[dict]):
        self.issues = issues
        detail = "; ".join(x["reason"] for x in issues)
        super().__init__(f"Figure composite review required: {detail}")


def normalized_target_filename(target: str) -> str:
    """Mirror the vendor mapper's filename cleaning, without path traversal."""
    raw = str(target).strip()
    if not raw or "/" in raw or "\\" in raw or ".." in raw:
        raise FigureCompositeReviewRequired([
            {"reason": "unsafe_or_empty_target", "target": raw}
        ])
    raw = raw.translate(_TRANSLATE)
    raw = re.sub(r'[\\/*?:"<>|]', "-", raw)
    raw = re.sub(r"[\s\-]+", " ", raw).strip()
    raw = re.sub(r"\.(png)\b.*$", ".png", raw, flags=re.IGNORECASE)
    if not raw.lower().endswith(".png"):
        raw += ".png"
    raw = re.sub(r"\.png$", ".png", raw, flags=re.IGNORECASE)
    base = re.sub(r"[^A-Za-z0-9 ._\-()]", "", raw).strip()
    if not base or base.lower() == ".png":
        raise FigureCompositeReviewRequired([
            {"reason": "empty_after_sanitization", "target": str(target)}
        ])
    return base


def _figure_id(text: str) -> str | None:
    hit = _FIGURE_ID.search(text)
    return f"{int(hit[1])}.{int(hit[2])}" if hit else None


def _panel_id(text: str) -> str | None:
    hit = _PANEL_ID.search(text)
    return hit[1].lower() if hit else None


def validate_and_prepare_mappings(
    triples: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """Return safe canonical targets, or reject before any mapped PNG is copied.

    This is *not* proof that an apparently complete crop contains every panel.
    Such source-grounded visual completeness is a separate acceptance gate.
    """
    prepared = []
    issues = []
    by_target = defaultdict(list)
    by_figure = defaultdict(list)

    for crop, label, original_target in triples:
        target = normalized_target_filename(original_target)
        prepared.append((crop, label, target))
        by_target[target.casefold()].append(crop)
        source_figure = _figure_id(label)
        target_figure = _figure_id(target)
        source_panel = _panel_id(label)
        target_panel = _panel_id(target)
        if source_figure and target_figure and source_figure != target_figure:
            issues.append({"reason": "figure_number_mismatch", "crop": crop,
                           "label": label, "target": target})
        if source_panel != target_panel and (source_panel or target_panel):
            issues.append({"reason": "panel_identifier_mismatch", "crop": crop,
                           "label": label, "target": target})
        if source_figure:
            by_figure[source_figure].append((crop, source_panel, target_panel))

    for target, crops in by_target.items():
        if len(crops) > 1:
            issues.append({"reason": "ambiguous_duplicate_target_no_layout_provenance",
                           "target": target, "crops": crops})

    for figure, entries in by_figure.items():
        # A parent crop and separate lettered crops may both be legitimate,
        # but their spatial relationship is unknown here. Do not publish
        # them as independently authoritative versions of the same figure.
        if len(entries) > 1 and any(panel is None for _, panel, _ in entries) \
                and any(panel is not None for _, panel, _ in entries):
            issues.append({"reason": "mixed_parent_and_subpanel_crops",
                           "figure": figure, "crops": [e[0] for e in entries]})

    if issues:
        raise FigureCompositeReviewRequired(issues)
    return prepared



def require_non_destructive_destination(src, dst) -> bool:
    """Return True if identical destination already exists; reject data loss.

    This guard is run for every proposed destination *before* any image copy.
    A changed published figure needs explicit review, not an automatic rewrite.
    """
    from pathlib import Path
    import hashlib
    src, dst = Path(src), Path(dst)
    if not src.is_file():
        raise FileNotFoundError(f"Missing original figure crop: {src.name}")
    if src.resolve() == dst.resolve():
        raise FigureCompositeReviewRequired([
            {"reason": "source_equals_destination", "target": dst.name}
        ])
    if not dst.exists():
        return False
    if not dst.is_file():
        raise FigureCompositeReviewRequired([
            {"reason": "figure_target_not_regular_file", "target": dst.name}
        ])
    digest = lambda p: hashlib.sha256(p.read_bytes()).digest()
    if digest(src) != digest(dst):
        raise FigureCompositeReviewRequired([
            {"reason": "existing_figure_conflicts_with_new_crop", "target": dst.name,
             "crop": src.name}
        ])
    return True
