"""Independent, read-only evidence for exact source-PDF figure panel labels.

Does not infer author-intended panel boundaries, the complete figure crop,
scientific meaning, or production permission. Missing/ambiguous labels block.
"""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from .figure_source_identity import require, _sha
from .figure_vector_region_discovery import discover_vector_figure_candidate

_PANEL = re.compile(r"^\(([a-f])\)$")
_FIGURE = r"^\s*FIGURE\s+{}\b"


def inspect_source_panel_label_evidence(*, source: Path, page_number: int,
                                        figure_id: str) -> dict:
    """Locate independently extractable source labels; never certify panels."""
    parent = discover_vector_figure_candidate(
        source=source, page_number=page_number, figure_id=figure_id
    )
    path = Path(source).absolute()
    original_sha = parent["source_sha256"]
    with pymupdf.open(path) as pdf:
        page = pdf[page_number - 1]
        anchor = pymupdf.Rect(parent["caption_block_bbox"])
        drawing = pymupdf.Rect(parent["candidate_vector_bbox"])
        expression = re.compile(_FIGURE.format(re.escape(figure_id)), re.I)
        heading_lines = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                box = pymupdf.Rect(line["bbox"])
                if expression.search(line_text) and anchor.intersects(box):
                    heading_lines.append((line_text.strip(), box))
        # A whole text block may mix caption and body. Never regard it
        # as an exact caption or allow nearby discussion as a panel label.
        heading_unique = len(heading_lines) == 1
        labels = []
        for word in page.get_text("words"):
            match = _PANEL.fullmatch(str(word[4]).strip())
            if not match:
                continue
            bbox = pymupdf.Rect(word[:4])
            center = pymupdf.Point((bbox.x0 + bbox.x1) / 2,
                                   (bbox.y0 + bbox.y1) / 2)
            if drawing.contains(center):
                labels.append({"id": match.group(1),
                               "bbox": [round(v, 3) for v in bbox]})
        labels.sort(key=lambda label: (label["id"], label["bbox"][1],
                                       label["bbox"][0]))
        ids = [label["id"] for label in labels]
        distinct = len(set(ids)) == len(ids)
        consecutive = (len(ids) >= 2 and distinct and
                       ids == list("abcdef"[:len(ids)]))
        if not heading_unique:
            status = "SOURCE_FIGURE_HEADING_LINE_AMBIGUOUS"
        elif not distinct:
            status = "SOURCE_PANEL_LABELS_DUPLICATED"
        elif not consecutive:
            status = "SOURCE_PANEL_LABELS_MISSING_OR_INCOMPLETE"
        else:
            status = "EXTRACTABLE_SOURCE_PANEL_LABEL_CANDIDATES_ONLY"
        result = {
            "schema_version": 1,
            "status": status,
            "source_sha256": original_sha,
            "source_page": page_number,
            "figure_id": figure_id,
            "parent_candidate_drawing_index": parent["candidate_drawing_index"],
            "parent_candidate_vector_bbox": parent["candidate_vector_bbox"],
            "caption_heading_line_count": len(heading_lines),
            "caption_heading_line_text": heading_lines[0][0] if heading_unique else None,
            "extractable_panel_label_candidates": labels,
            "panel_label_count": len(labels),
            "panel_labels_are_distinct_consecutive_candidates": consecutive,
            "complete_figure_crop_certified": False,
            "panel_boundaries_source_verified": False,
            "panel_ids_source_verified": False,
            "figure_semantics_certified": False,
            "source_to_slide_equivalence_certified": False,
            "tts_or_video_authorized": False,
            "human_review_claimed": False,
        }
    require(_sha(path) == original_sha, "Original PDF changed during audit")
    return result
