"""Inspect Beamer PDF page counters without changing the rendered lecture.

A single pdflatex pass can leave the total frame number at 1 although the
deck contains many pages. A successful compiler exit does NOT certify the
displayed denominator. This routine detects only unambiguous page-count bugs.
"""
from __future__ import annotations

from pathlib import Path
import re

COUNTER = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")


def incorrect_page_totals(pdf: Path) -> list[dict]:
    import pymupdf
    pdf = Path(pdf)
    with pymupdf.open(pdf) as doc:
        pages = len(doc)
        if pages < 2:
            return []
        found: list[dict] = []
        for i in sorted({0, pages - 1}):
            page = doc[i]
            # Beamer's frame count appears at the page's upper-right corner.
            # Requiring a geometric counter placement avoids mistaking an
            # actual physics fraction (e.g. 1 / 2) for a page footer.
            blocks = page.get_text("blocks")
            for block in blocks:
                x0, y0, _x1, _y1, text = block[:5]
                if x0 < page.rect.width * .70 or y0 > page.rect.height * .12:
                    continue
                match = COUNTER.fullmatch(str(text).strip())
                if match is None:
                    continue
                number, total = map(int, match.groups())
                if number == i + 1 and total != pages:
                    found.append({"slide": i + 1, "display": f"{number} / {total}",
                                  "actual_total": pages})
                    break
        return found


def enforce_correct_page_totals(pdf: Path) -> None:
    wrong = incorrect_page_totals(pdf)
    if wrong:
        raise ValueError(
            f"Beamer displayed slide total is wrong (actual pages="
            f"{wrong[0]['actual_total']}; examples={wrong[:2]}). "
            "Recompile slides.tex with pdflatex at least twice and recheck."
        )
