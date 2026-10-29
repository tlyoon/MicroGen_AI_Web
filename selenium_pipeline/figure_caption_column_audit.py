"""Read-only evidence of PDF figure-caption/text-column collisions.

Source caption headings do not imply that their enclosing PDF text block
contains only caption text. This module only identifies ambiguity; it does
not auto-crop, split figure panels, or grant media authorization.
"""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from .figure_source_identity import require, _sha


def audit_caption_column_collision(*, source: Path, page_number: int,
                                   figure_id: str) -> dict:
    path = Path(source).absolute()
    for part in (path, *path.parents):
        require(not part.is_symlink()
                and not getattr(part, "is_junction", lambda: False)(),
                "Symlink or junction PDF path is prohibited")
    require(path.is_file() and path.suffix.lower() == ".pdf",
            "Regular PDF required")
    require(type(page_number) is int and page_number > 0,
            "One-based source page required")
    require(isinstance(figure_id, str)
            and re.fullmatch(r"[1-9][0-9]*\.[0-9]+", figure_id),
            "Chapter.figure identifier required")
    sha = _sha(path)
    with pymupdf.open(path) as doc:
        require(0 < page_number <= len(doc) <= 250, "Invalid source page")
        page = doc[page_number - 1]
        re_heading = re.compile(
            r"^\s*FIGURE\s+" + re.escape(figure_id) + r"\b", re.I
        )
        blocks = page.get_text("dict")["blocks"]
        headings = []
        lines = []
        for index, block in enumerate(blocks):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                words = "".join(str(span.get("text", "")) for span in line.get("spans", []))
                box = pymupdf.Rect(line["bbox"])
                if words.strip():
                    lines.append((index, words.strip(), box))
                if re_heading.search(words):
                    headings.append((index, words.strip(), box))
        require(len(headings) == 1, "Exactly one independent source figure heading required")
        caption_block, heading_text, heading_rect = headings[0]
        # A wide caption-column threshold is a conservative rejection
        # heuristic only, NOT a recovered author caption boundary.
        split_x = max(page.rect.width * .32, heading_rect.x1 + 55)
        adjacent = []
        same_block = []
        for index, text, box in lines:
            if index == caption_block and not re_heading.search(text):
                same_block.append((text, box))
            if (box.x0 >= split_x
                and box.y1 >= heading_rect.y0 - 2
                and box.y0 <= heading_rect.y0 + 180
                and len(re.findall(r"[A-Za-z]{3,}", text)) >= 4):
                adjacent.append((index, text, box))
        # Require multiple independent lines: a long single caption
        # statement must not be accepted as proof of a separate column.
        intrusive = [line for line in adjacent
                     if line[2].y0 < heading_rect.y0 + 155]
        overlapping = sum(1 for idx, _, _ in intrusive if idx == caption_block)
        status = ("CAPTION_PARALLEL_PROSE_COLLISION_REVIEW_REQUIRED"
                  if len(intrusive) >= 2 else
                  "CAPTION_LAYOUT_CANDIDATE_REVIEW_REQUIRED")
        result = {
            "schema_version": 1,
            "status": status,
            "source_sha256": sha,
            "source_page": page_number,
            "figure_id": figure_id,
            "heading_text": heading_text,
            "heading_bbox": [round(v, 3) for v in heading_rect],
            "heading_text_block_index": caption_block,
            "parallel_prose_line_count": len(intrusive),
            "parallel_prose_same_block_count": overlapping,
            "parallel_prose_bboxes": [
                [round(v, 3) for v in rect] for _, _, rect in intrusive
            ],
            "caption_region_author_verified": False,
            "author_intended_complete_crop_certified": False,
            "panel_boundaries_source_verified": False,
            "source_to_slide_equivalence_certified": False,
            "tts_or_video_authorized": False,
        }
    require(_sha(path) == sha, "Source changed during read-only audit")
    return result
