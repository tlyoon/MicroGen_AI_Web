"""Read-only, caption-anchored candidate discovery for vector textbook figures.

Candidates are not complete-author-figure, panel-label, semantic or
production certificates. Ambiguous source geometry raises review required.
"""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from .figure_source_identity import require, _sha


def _embedded_prose_evidence(page, rectangle: pymupdf.Rect) -> tuple[int, int]:
    """Count substantial words/lines INSIDE a candidate vector rectangle.

    This is a conservative *rejection* signal, not proof of diagram identity.
    PDF writers frequently combine adjacent captions and unrelated boxed
    teaching instructions into one text block. A vector border surrounding
    paragraph-sized prose must never be called the textbook figure.
    """
    long_words_by_line: dict[tuple[int, int], int] = {}
    for word in page.get_text("words"):
        if len(word) < 7 or not re.search(r"[A-Za-z]{3,}", str(word[4])):
            continue
        x0, y0, x1, y1 = (float(v) for v in word[:4])
        centre = pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2)
        if rectangle.contains(centre):
            line_key = (int(word[5]), int(word[6]))
            long_words_by_line[line_key] = long_words_by_line.get(line_key, 0) + 1
    return (sum(long_words_by_line.values()),
            sum(count >= 4 for count in long_words_by_line.values()))


def discover_vector_figure_candidate(*, source: Path, page_number: int,
                                     figure_id: str) -> dict:
    """Return a bounded unique vector candidate, never a production approval."""
    path = Path(source).absolute()
    for part in (path, *path.parents):
        require(not part.is_symlink()
                and not getattr(part, "is_junction", lambda: False)(),
                "Symlink or junction path is prohibited")
    require(path.is_file() and path.suffix.lower() == ".pdf",
            "Regular PDF required")
    require(type(page_number) is int and page_number > 0,
            "Source page must be one-based integer")
    require(isinstance(figure_id, str)
            and re.fullmatch(r"[1-9][0-9]*\.[0-9]+", figure_id),
            "Figure identifier must have chapter.number form")
    original_hash = _sha(path)
    with pymupdf.open(path) as document:
        require(page_number <= len(document) and len(document) <= 250,
                "Source page outside bounded PDF")
        page = document[page_number - 1]
        pattern = re.compile(r"(?im)^\s*FIGURE\s+"
                             + re.escape(figure_id) + r"\b")
        anchors = [block for block in page.get_text("blocks")
                   if len(block) > 4 and isinstance(block[4], str)
                   and pattern.search(block[4])]
        require(len(anchors) == 1,
                "Exactly one extractable original figure heading required")
        anchor = pymupdf.Rect(anchors[0][:4])
        paths = page.get_drawings()
        candidates = []
        excluded = []
        for index, drawing in enumerate(paths):
            rect = pymupdf.Rect(drawing["rect"])
            if (rect.is_empty or rect.is_infinite
                or not page.rect.contains(rect)
                or rect.width < 40 or rect.height < 40
                or rect.y0 < anchor.y0 - 10
                or rect.y0 > anchor.y0 + 100
                or rect.y1 > anchor.y0 + 220):
                excluded.append(index)
                continue
            candidates.append((index, rect))
        require(len(candidates) == 1,
                "Source vector figure region absent or ambiguous")
        index, rect = candidates[0]
        long_word_count, dense_line_count = _embedded_prose_evidence(page, rect)
        # A nearby boxed set of prose instructions is not necessarily
        # artwork. Reject long multiline prose; absence is NOT scientific
        # proof that a region is the complete author-intended figure.
        require(not (long_word_count >= 25 or
                     (long_word_count >= 14 and dense_line_count >= 2)),
                "Candidate vector region encloses substantial prose or "
                "instructions; independent figure-source review required")
        record = {
            "schema_version": 1,
            "status": "VECTOR_REGION_CANDIDATE_REVIEW_REQUIRED",
            "source_sha256": original_hash,
            "source_page": page_number,
            "figure_id": figure_id,
            "caption_block_bbox": [round(v, 3) for v in anchor],
            "candidate_vector_bbox": [round(v, 3) for v in rect],
            "candidate_drawing_index": index,
            "all_page_drawing_count": len(paths),
            "rejected_drawing_count": len(excluded),
            "candidate_embedded_long_word_count": long_word_count,
            "candidate_dense_prose_line_count": dense_line_count,
            "unique_anchored_vector_candidate": True,
            "author_intended_complete_crop_certified": False,
            "panel_ids_source_verified": False,
            "panel_boundaries_source_verified": False,
            "figure_semantics_certified": False,
            "tts_or_video_authorized": False,
            "human_review_claimed": False,
        }
    require(_sha(path) == original_hash, "Original PDF changed during audit")
    return record
