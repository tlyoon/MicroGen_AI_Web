"""Read-only original source panel-marker lexical inventory.

Candidate printed '(a)' markers are NOT evidence of complete graph panels:
vector-drawn glyphs and multiple independent figures may share a page.
"""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from .figure_pre_caption_vector_inventory import inventory_pre_caption_vectors
from .figure_source_identity import _sha, require

MARKER = re.compile(r"^\s*\(([a-fA-F])\)\s*$")


def inventory_source_panel_text(*, source: Path, page_number: int,
                                figure_id: str) -> dict:
    base = inventory_pre_caption_vectors(
        source=source, page_number=page_number, figure_id=figure_id)
    path = Path(source).absolute()
    corridor = pymupdf.Rect(base["candidate_scan_corridor"])
    require(corridor.is_valid and not corridor.is_empty,
            "Invalid original source pre-caption corridor")
    candidates, outside, text_in_corridor = [], [], 0
    with pymupdf.open(path) as doc:
        page = doc[page_number - 1]
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                content = "".join(str(span.get("text", ""))
                                  for span in line.get("spans", []))
                rect = pymupdf.Rect(line["bbox"])
                if not content.strip() or not rect.is_valid:
                    continue
                center = pymupdf.Point((rect.x0 + rect.x1) / 2,
                                       (rect.y0 + rect.y1) / 2)
                in_corridor = corridor.contains(center)
                if in_corridor:
                    text_in_corridor += 1
                match = MARKER.fullmatch(content)
                if match:
                    record = {
                        "label": f"({match[1].lower()})",
                        "line_bbox": [round(float(v), 3) for v in rect],
                        "source_text_center_within_scan_corridor": in_corridor,
                    }
                    (candidates if in_corridor else outside).append(record)
    ids = [p["label"] for p in candidates]
    count_by_label = {v: ids.count(v) for v in sorted(set(ids))}
    repeated = [label for label, count in count_by_label.items() if count > 1]
    require(_sha(path) == base["source_sha256"],
            "Source changed while inspecting printed panel markers")
    return {
        "schema_version": 1,
        "status": ("PRECAPTION_PRINTED_PANEL_MARKERS_UNASSIGNED_REVIEW_REQUIRED"
                   if candidates else "NO_PRECAPTION_PRINTED_PANEL_MARKERS_REVIEW_REQUIRED"),
        "source_sha256": base["source_sha256"],
        "source_page": page_number,
        "figure_id": figure_id,
        "candidate_scan_corridor": base["candidate_scan_corridor"],
        "pre_caption_vector_object_count": base["pre_caption_object_count"],
        "pre_caption_text_line_count": text_in_corridor,
        "printed_panel_marker_candidates": candidates,
        "printed_panel_markers_outside_corridor": outside,
        "candidate_marker_repetitions": repeated,
        "original_panel_count_certified": False,
        "original_panel_ownership_certified": False,
        "vector_drawn_or_nonextractable_markers_ruled_out": False,
        "original_complete_figure_certified": False,
        "source_to_slide_content_certified": False,
        "narrated_highlight_authorized": False,
        "student_publication_authorized": False,
    }


def main(argv=None) -> int:
    import argparse
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--page", type=int, required=True)
    p.add_argument("--figure-id", required=True)
    a = p.parse_args(argv)
    result = inventory_source_panel_text(
        source=a.source, page_number=a.page, figure_id=a.figure_id)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
