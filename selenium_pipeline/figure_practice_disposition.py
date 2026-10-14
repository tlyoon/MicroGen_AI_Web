"""Explicit experimental handling of *unlabeled* exercise graphics.

Original crops remain in crops/page_N/ for practice; never rename them as
textbook Figure X.Y or silently discard them. This cannot approve lessons.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re

MANIFEST = "figure_practice_disposition.json"
VERSION = 1
MODE = "experimental_unreviewed_practice_only"
ENABLE_FLAG = "MICROGEN_ENABLE_EXPERIMENTAL_PRACTICE_SCOPE"
FIGURE_RE = re.compile(r"\bfig(?:ure)?\.?\s*\d+(?:[.\-]\d+)+", re.I)
CROP_RE = re.compile(r"fig_[1-9]\d*\.png", re.I)


class PracticeDispositionError(ValueError):
    """Cannot prove an explicit, source-grounded practice-only page."""


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _pdf_page_text(pdf: Path, page: int) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise PracticeDispositionError("pypdf is required for source text checking") from exc
    reader = PdfReader(str(pdf))
    if page < 1 or page > len(reader.pages):
        raise PracticeDispositionError("Exercise-page number exceeds source PDF")
    return reader.pages[page-1].extract_text() or ""


def _paths(root: Path, page: int) -> tuple[Path, Path, Path, Path]:
    if type(page) is not int or not 1 <= page <= 10000:
        raise PracticeDispositionError("Invalid exercise page number")
    root = Path(root).resolve()
    return (root / "source.pdf",
            root / "pages" / f"page_{page}" / f"page_{page}.png",
            root / "crops" / f"page_{page}",
            root / MANIFEST)


def _observed_page(root: Path, page: int, anchor: str) -> dict:
    source, png, crops, _ = _paths(root, page)
    if not source.is_file() or not png.is_file() or not crops.is_dir():
        raise PracticeDispositionError("Source PDF / page PNG / crops directory missing")
    if source.is_symlink() or png.is_symlink():
        raise PracticeDispositionError("Source/page links are not accepted")
    if not isinstance(anchor, str) or len(anchor.strip()) < 8:
        raise PracticeDispositionError("A specific printed exercise heading is required")
    page_text = _pdf_page_text(source, page)
    if re.sub(r"\s+", " ", anchor).casefold() not in re.sub(r"\s+", " ", page_text).casefold():
        raise PracticeDispositionError("Evidence heading not found on this PDF page")
    if FIGURE_RE.search(page_text):
        raise PracticeDispositionError(
            "A printed numbered Figure is present on this page; cannot exclude its crops"
        )
    originals = sorted(
        (p for p in crops.iterdir() if p.is_file() and CROP_RE.fullmatch(p.name)),
        key=lambda p: int(p.stem.split("_")[1]),
    )
    if not originals:
        raise PracticeDispositionError("Only pages with uncaptioned source crops can be excluded")
    if any(p.is_symlink() for p in originals):
        raise PracticeDispositionError("Linked source crops are not accepted")
    return {
        "page": page,
        "reason": "unlabeled_exercise_graphs_not_textbook_figures",
        "source_heading": anchor,
        "page_png_sha256": _hash(png),
        "original_crops": [{"filename": p.name, "sha256": _hash(p)} for p in originals],
        "preserve_original_crops": True,
        "scientific_review_status": "unreviewed",
        "student_publication_permitted": False,
    }


def create_experimental_disposition(root: Path, page: int, anchor: str) -> Path:
    """Create exactly one explicit immutable experiment manifest (no overwrite)."""
    root = Path(root).resolve()
    source, _, _, dest = _paths(root, page)
    entry = _observed_page(root, page, anchor)
    record = {
        "schema_version": VERSION,
        "mode": MODE,
        "source_pdf_sha256": _hash(source),
        "pages": [entry],
    }
    # Refuse silent overwrites even if another process has written this file.
    with dest.open("x", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return dest


def _read_verified(root: Path) -> dict | None:
    root = Path(root).resolve()
    dest = root / MANIFEST
    if not dest.exists():
        return None
    if dest.is_symlink() or not dest.is_file():
        raise PracticeDispositionError("Practice disposition path must be a regular file")
    if os.environ.get(ENABLE_FLAG) != "1":
        raise PracticeDispositionError(
            f"Unreviewed practice-graphic exclusions require explicit {ENABLE_FLAG}=1"
        )
    if dest.stat().st_size > 256_000:
        raise PracticeDispositionError("Practice disposition file too large")
    record = json.loads(dest.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or set(record) != {
        "schema_version", "mode", "source_pdf_sha256", "pages"
    } or record["schema_version"] != VERSION or record["mode"] != MODE:
        raise PracticeDispositionError("Unsupported or malformed practice disposition")
    source = root / "source.pdf"
    if not source.is_file() or record["source_pdf_sha256"] != _hash(source):
        raise PracticeDispositionError("Source PDF changed since practice classification")
    pages = record["pages"]
    if not isinstance(pages, list) or not pages or len(pages) > 100:
        raise PracticeDispositionError("Invalid excluded practice-page list")
    observed = []
    for entry in pages:
        if not isinstance(entry, dict) or type(entry.get("page")) is not int:
            raise PracticeDispositionError("Unrecognized practice-page record")
        observed.append(_observed_page(root, entry["page"], entry.get("source_heading")))
    if observed != pages or len({x["page"] for x in pages}) != len(pages):
        raise PracticeDispositionError("Practice page, image or crop hashes do not match")
    return record


def practice_page_excluded(root: Path, page: int) -> bool:
    """Skip an explicit source-verified practice page; otherwise map normally."""
    record = _read_verified(root)
    return record is not None and any(x["page"] == page for x in record["pages"])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Create an unapproved, source-bound experiment-only practice-graphic exclusion")
    p.add_argument("--work-root", type=Path, required=True)
    p.add_argument("--page", type=int, required=True)
    p.add_argument("--source-heading", required=True, help="An exact heading present in PDF text for this page")
    args = p.parse_args(argv)
    dest = create_experimental_disposition(args.work_root, args.page, args.source_heading)
    print(f"[experimental practice graphics; human review required] {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
