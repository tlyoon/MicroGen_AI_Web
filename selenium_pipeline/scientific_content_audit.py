"""Read-only Stage 7 source/slide quality screening for MicroGen_AI_Web.

This screen catches provable assembly failures, not scientific correctness.
Figures, derivations, pedagogical choices and readability still require a
qualified review of the rendered slide against its textbook source.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from .cleanup import _ensure_latex_graphics
from .reliability_audit import source_folders

WORD = re.compile(r"[A-Za-z]{4,}")
FIGURE = re.compile(r"\b(?:Figure|Fig\.)\s*\d+[.\-]\d+[A-Za-z]?\b", re.I)
STOPS = frozenset("""
about after again also although among another around because before being
between could different every first following from have into just lecture
more most other over same should shown slide slides some source than that
their there these this those through using were what when where which while
with would your they does will have each also next text
""".split())


def _terms(s: str) -> set[str]:
    return {t for m in WORD.finditer(s) if (t := m.group().lower()) not in STOPS}


def inspect(folder: Path) -> dict:
    import pymupdf

    folder = Path(folder).expanduser().resolve()
    issues: list[dict] = []
    def flag(level: str, code: str, detail: str, page: int | None = None):
        item = {"severity": level, "code": code, "detail": detail}
        if page is not None:
            item["slide"] = page
        issues.append(item)

    source = folder / "source.pdf"
    deck = folder / "slides.pdf"
    tex = folder / "slides.tex"
    result = {"subchapter": folder.name, "source_dir": str(folder),
              "source_present": source.is_file(), "slide_pdf_present": deck.is_file(),
              "issues": issues}
    def finalize() -> dict:
        result["blockers"] = sum(x["severity"] == "blocker" for x in issues)
        result["review_flags"] = sum(x["severity"] == "review" for x in issues)
        result["classification"] = ("blocked" if result["blockers"] else
                                    "review_required" if result["review_flags"] else
                                    "structurally_screened")
        result["scientific_correctness_certified"] = False
        return result

    if not source.is_file() or source.is_symlink():
        flag("blocker", "source_missing", "Required original source.pdf is missing")
        return finalize()

    source_text = ""
    source_images = 0
    try:
        with pymupdf.open(source) as src:
            source_text = "\n".join(p.get_text() for p in src)
            source_images = sum(len(p.get_images()) for p in src)
            result["source_pages"] = len(src)
    except (OSError, RuntimeError, ValueError) as exc:
        flag("blocker", "source_unreadable", f"Source PDF is unreadable: {type(exc).__name__}")
        return finalize()

    result["source_figure_mentions"] = len(set(m.group().lower() for m in FIGURE.finditer(source_text)))
    result["source_embedded_images"] = source_images
    if len(source_text.strip()) < 100:
        flag("review", "source_image_only", "Source has little extractable text; visual inspection is necessary")
    if tex.is_file():
        try:
            _ensure_latex_graphics(folder, None)
            result["latex_graphics"] = "present"
        except (OSError, ValueError) as exc:
            result["latex_graphics"] = "blocked"
            flag("blocker", "missing_latex_graphic", str(exc)[:450])
    else:
        result["latex_graphics"] = "not_published"
        flag("review", "latex_not_published", "Cannot verify figures because slides.tex is absent")

    if not deck.is_file() or deck.is_symlink():
        flag("blocker", "slides_missing", "Slide PDF has not been generated")
        return finalize()
    all_text = []
    image_count = 0
    vector_pages = 0
    try:
        with pymupdf.open(deck) as doc:
            result["slide_count"] = len(doc)
            if len(doc) < 1:
                flag("blocker", "zero_slides", "Slide PDF has no pages")
            for idx, page in enumerate(doc, 1):
                text = page.get_text().strip()
                all_text.append(text)
                images = len(page.get_images())
                drawings = len(page.get_drawings())
                image_count += images
                vector_pages += bool(drawings)
                words = len(text.split())
                # Text can be represented as paths or raster images. Only a
                # completely blank PDF page is an objective blocker.
                if len(text) < 8 and images == 0 and drawings == 0:
                    flag("blocker", "blank_pdf_page", "No text, raster or vector drawing in PDF page", idx)
                elif len(text) < 20 and images == 0:
                    flag("review", "sparse_pdf_page", "Little extractable text; verify rendered visual", idx)
                if words > 165:
                    flag("review", "dense_slide_text", f"Slide has {words} extracted words", idx)
                for block in page.get_text("blocks"):
                    if len(block) < 5 or not str(block[4]).strip():
                        continue
                    x0, y0, x1, y1 = block[:4]
                    # Beamer's legitimate corner frame counter may start
                    # fractionally above y=0 due to font ascender metrics.
                    # It is not a genuinely overflowing physics text block.
                    if (x0 > page.rect.width * .70 and y0 < page.rect.height * .12
                            and re.fullmatch(r"\s*\d+\s*/\s*\d+\s*", str(block[4]).strip())):
                        continue
                    if x0 < -5 or y0 < -5 or x1 > page.rect.width + 5 or y1 > page.rect.height + 5:
                        flag("review", "text_outside_page", "Text extends outside PDF page geometry", idx)
                        break
    except (OSError, RuntimeError, ValueError) as exc:
        flag("blocker", "slides_unreadable", f"Slide PDF is unreadable: {type(exc).__name__}")
        return finalize()

    from .latex_footer import incorrect_page_totals
    for bad in incorrect_page_totals(deck):
        flag("blocker", "incorrect_beamer_page_total",
             f"Slide displays {bad['display']}, but deck has {bad['actual_total']} pages",
             bad["slide"])
    result["pdf_embedded_images"] = image_count
    result["pages_with_vector_drawings"] = vector_pages
    combined = "\n".join(all_text)
    source_terms = _terms(source_text)
    slide_terms = _terms(combined)
    overlap = len(source_terms & slide_terms)
    result["source_term_overlap_ratio"] = round(overlap / max(1, len(slide_terms)), 3)
    # This is *only* a heuristic; paraphrasing, image-only sources and
    # legitimately new illustrative examples can give low overlap.
    if source_terms and slide_terms and overlap / len(slide_terms) < .08:
        flag("review", "low_textual_source_overlap",
             "Low source/slide vocabulary overlap; check facts and topic manually")
    if result["source_figure_mentions"] and not image_count and not vector_pages:
        flag("review", "no_slide_diagrams_detected",
             "Source refers to figures; no raster/vector diagrams detected in compiled deck")
    if result["source_figure_mentions"] and not image_count:
        flag("review", "figure_rendering_requires_review",
             "Source references numbered figures but no embedded raster slide figures were detected; "
             "vector diagrams are possible")

    result["blockers"] = sum(x["severity"] == "blocker" for x in issues)
    result["review_flags"] = sum(x["severity"] == "review" for x in issues)
    result["classification"] = ("blocked" if result["blockers"] else
                                "review_required" if result["review_flags"] else
                                "structurally_screened")
    result["scientific_correctness_certified"] = False
    return finalize()


def inspect_campaign(root: Path) -> dict:
    root = Path(root).expanduser().resolve()
    jobs = [inspect(p) for p in source_folders(root)]
    from collections import Counter
    return {"root": str(root), "checked_utc": datetime.now(timezone.utc).isoformat(),
            "total": len(jobs), "classes": dict(Counter(j["classification"] for j in jobs)),
            "scientific_correctness_certified": False, "jobs": jobs}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    scope = p.add_mutually_exclusive_group(required=True)
    scope.add_argument("--folder", type=Path)
    scope.add_argument("--source-root", type=Path)
    p.add_argument("--expected", type=int)
    p.add_argument("--report", type=Path, help="New report path OUTSIDE source tree; never overwritten")
    args = p.parse_args(argv)
    if args.folder:
        data = inspect(args.folder)
        checks = [data]
    else:
        data = inspect_campaign(args.source_root)
        checks = data["jobs"]
        if args.expected is not None and len(checks) != args.expected:
            raise ValueError(f"Expected {args.expected} subchapters, found {len(checks)}")
    if args.report:
        source = args.folder or args.source_root
        destination = args.report.expanduser().resolve()
        if source.expanduser().resolve() in destination.parents:
            raise ValueError("Quality report must remain outside the source tree")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8") as out:
            json.dump(data, out, indent=2)
    print(json.dumps(data if args.folder else
                     {k: v for k,v in data.items() if k != "jobs"}, indent=2))
    return 3 if any(j.get("blockers", 0) > 0 for j in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
