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
            lines = doc[i].get_text().splitlines()
            matches = [m for line in lines[:8] if (m := COUNTER.fullmatch(line.strip()))]
            # The page index must match: ignore examples or fractions elsewhere
            # in slide body. Beamer often uses the top-right footer.
            for match in matches:
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
