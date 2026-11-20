"""Source-byte-locked horizontal math-row geometry from fragmented PDF glyph blocks.

The usual adjacent-2/3-text-block helper cannot represent PDF equations
whose numerator, denominator and radical occupy 4-8 separate, overlapping
visual blocks. This module discovers bounded physical *candidate regions*.
Neither a source equation nor a spoken mathematical claim is certified.
"""
from __future__ import annotations

import hashlib
import math
import re

import pymupdf


class MathRowBlocked(ValueError):
    pass


def need(ok: bool, why: str) -> None:
    if not ok:
        raise MathRowBlocked(why)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf8")).hexdigest()


def _math_signal(text: str) -> bool:
    return bool(re.search(r"[=+−√∫×ρτπ²³^]|\b(?:sqrt|sin|cos|tan|ln)\b",
                          text, re.I))


def _compact(block: tuple, page) -> bool:
    value = block[4] if len(block) > 4 else None
    if (not isinstance(value, str) or not (1 <= len(value.strip()) <= 150)
            or (len(block) > 6 and block[6] != 0)):
        return False
    rect = pymupdf.Rect(block[:4])
    return (not rect.is_empty and not rect.is_infinite
            and rect.width > 4 and rect.height > 4
            and rect.y0 >= 32 and rect.y1 < page.rect.height - 18
            and rect.width < page.rect.width * .82)


def _row_progression(a: pymupdf.Rect, b: pymupdf.Rect) -> bool:
    return (b.x0 >= a.x0 + 2.0 and b.x0 <= a.x1 + 25
            and max(a.y0, b.y0) <= min(a.y1, b.y1) + 8
            and abs((a.y0 + a.y1) / 2 - (b.y0 + b.y1) / 2) <= 24)


def math_row_rect(page, anchor: dict) -> pymupdf.Rect:
    need(type(anchor) is dict and anchor.get("type") == "math_row_group",
         "Expected an original authored math row group")
    indices, digests = anchor.get("indices"), anchor.get("text_sha256")
    need(type(indices) is list and type(digests) is list
         and 2 <= len(indices) <= 8 and len(indices) == len(digests)
         and all(type(i) is int and i >= 0 for i in indices)
         and all(type(h) is str and len(h) == 64 for h in digests)
         and indices == sorted(set(indices))
         and all(b - a == 1 for a, b in zip(indices, indices[1:])),
         "Only 2-8 distinct consecutive source PDF blocks may form a math row")
    original = page.get_text("blocks")
    need(indices[-1] < len(original), "Authored PDF math row is no longer present")
    items = []
    for i, h in zip(indices, digests):
        block = original[i]
        need(_compact(block, page) and digest(block[4]) == h,
             "Original source PDF math fragment hash or geometry changed")
        items.append((block[4], pymupdf.Rect(block[:4])))
    rects = [x[1] for x in items]
    need(all(_row_progression(a, b) for a, b in zip(rects, rects[1:])),
         "Math fragments cannot be assumed from spatially unrelated blocks")
    union = pymupdf.Rect(rects[0])
    for r in rects[1:]:
        union |= r
    full = " ".join(x[0] for x in items)
    need(any("=" in x[0] for x in items)
         and sum(_math_signal(x[0]) for x in items) >= 2
         and len(full) <= 540
         and union.height <= 55
         and union.width <= page.rect.width * .85
         and union.get_area() < page.rect.get_area() * .30
         and page.rect.contains(union),
         "Composite math row has no bounded physically witnessed equation")
    return union


def discover_math_rows(page, slide: int, targets: list[dict]) -> list[dict]:
    """Maximal horizontal equation runs, without filling gaps or inventing pixels."""
    need(type(slide) is int and slide >= 1, "Invalid source slide")
    raw = page.get_text("blocks")
    # Crucial: ordinary text candidates exclude short glyph fragments such
    # as 'R = 1', '2', or a denominator. Math grouping must inspect ALL
    # authentic authored PDF text blocks, including these excluded fragments.
    # Their physical bytes and geometry are independently rechecked below.
    valid = {i for i, block in enumerate(raw) if _compact(block, page)}
    rows = []
    covered_before = -1
    for start in sorted(valid):
        # Only the longest physically coherent row is offered. Numerous
        # overlapping suffix groups increase model ambiguity needlessly.
        if start <= covered_before or not (0 <= start < len(raw) and _compact(raw[start], page)):
            continue
        indices = [start]
        while len(indices) < 8:
            next_index = indices[-1] + 1
            if next_index not in valid or next_index >= len(raw) or not _compact(raw[next_index], page):
                break
            prev, cur = (pymupdf.Rect(raw[j][:4]) for j in (indices[-1], next_index))
            if not _row_progression(prev, cur):
                break
            indices.append(next_index)
        if len(indices) < 2:
            continue
        # Keep the longest geometrically supported prefix. It is okay if a
        # shorter subrun is later discovered; never merge across a bad block.
        for length in range(len(indices), 1, -1):
            chosen = indices[:length]
            key = tuple(chosen)
            if chosen[-1] <= covered_before:
                continue
            anchor = {"type": "math_row_group", "indices": chosen,
                      "text_sha256": [digest(raw[j][4]) for j in chosen]}
            try:
                rect = math_row_rect(page, anchor)
            except MathRowBlocked:
                continue
            covered_before = chosen[-1]
            text = " ".join(" ".join(raw[j][4].split()) for j in chosen)
            rows.append({
                "draft_element_id": f"s{slide:03d}.math_row." + "-".join(f"{j:03d}" for j in chosen),
                "type": "math_row_group",
                "anchor": anchor,
                "rect_pt": [round(float(v), 2) for v in rect],
                "visible_text": text[:540],
                "proposed_spoken_text": None,
                "original_math_block_hashes_verified": True,
                "mathematical_equivalence_proof_required": True,
                "narration_timing_verified": False,
                "review_required": True,
            })
            break
        if len(rows) >= 16:
            break
    return rows
