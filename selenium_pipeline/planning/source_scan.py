"""Read-only, hash-linked PDF evidence used by the future lesson planner.

Never infers complete textbook concept coverage from extracted text alone.
The returned scan is NOT an approved instructional outline.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path


class SourceScanError(ValueError):
    """Source PDF is missing, unreadable or outside the selected source tree."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_excerpt(s: str) -> str:
    """Normalize PDF line wraps for exact source-grounding tests."""
    return " ".join(re.sub(r"\s+", " ", s).strip().split()).casefold()


def scan_pdf(source_pdf: Path, *, source_root: Path) -> dict:
    """Collect page-wise text hashes, image counts and tiny preview fragments.

    A scan is evidence, not an automatically-approved source_inventory.json:
    PDF text may omit diagrams, math glyphs or meaningful captions.
    """
    try:
        import pymupdf
    except ImportError as exc:
        raise SourceScanError("PyMuPDF is required for read-only source scanning") from exc

    root = Path(source_root).expanduser().resolve()
    file = Path(source_pdf).expanduser().resolve()
    if not root.is_dir() or not file.is_file() or file.name.lower() != "source.pdf":
        raise SourceScanError("Expected an existing source.pdf under an existing source root")
    if not file.is_relative_to(root):
        raise SourceScanError("Source PDF must be inside the selected source root")
    before = sha256_file(file)
    pages = []
    try:
        with pymupdf.open(file) as pdf:
            if not len(pdf):
                raise SourceScanError("PDF has zero pages")
            if pdf.is_encrypted:
                raise SourceScanError("Encrypted PDF is not supported")
            for i, page in enumerate(pdf, 1):
                text = page.get_text("text", sort=True)
                normalized = normalize_excerpt(text)
                pages.append({
                    "page": i,
                    "text_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
                    "char_count": len(normalized),
                    "image_count": len(page.get_images(full=True)),
                    "text_preview": normalized[:160],
                    "text_extraction_warning": len(normalized) < 40,
                })
    except SourceScanError:
        raise
    except Exception as exc:
        raise SourceScanError("PDF cannot be parsed") from exc
    after = sha256_file(file)
    if before != after:
        raise SourceScanError("PDF changed during source inspection")
    return {
        "schema_version": 1, "source_pdf": "source.pdf",
        "source_sha256": before, "page_count": len(pages), "pages": pages,
        "coverage_status": "unreviewed",
    }


def verify_source_evidence(source_pdf: Path, scan: dict, references: list[dict]) -> None:
    """Verify each text excerpt; visual evidence must be explicitly reviewed.

    Visual evidence checks a page only; it cannot prove an image/figure's meaning.
    """
    import pymupdf
    pdf_path = Path(source_pdf)
    if sha256_file(pdf_path) != scan["source_sha256"]:
        raise SourceScanError("Source hash mismatch since scan")
    if scan["page_count"] != len(scan["pages"]):
        raise SourceScanError("Scan page count is inconsistent")
    with pymupdf.open(pdf_path) as pdf:
        if len(pdf) != scan["page_count"]:
            raise SourceScanError("Scan page count no longer matches source")
        texts = [normalize_excerpt(p.get_text("text", sort=True)) for p in pdf]
    for ref in references:
        page = ref.get("page")
        if type(page) is not int or not 1 <= page <= len(texts):
            raise SourceScanError("Concept refers to an invalid source page")
        method = ref.get("kind")
        if method == "text":
            excerpt = ref.get("excerpt", "")
            if not isinstance(excerpt, str) or len(normalize_excerpt(excerpt)) < 12:
                raise SourceScanError("Text evidence excerpt must have at least 12 characters")
            if normalize_excerpt(excerpt) not in texts[page - 1]:
                raise SourceScanError(f"Text excerpt not present on source page {page}")
        elif method == "visual_reviewed":
            if not isinstance(ref.get("description"), str) or len(ref["description"].strip()) < 12:
                raise SourceScanError("Visual evidence requires a meaningful reviewed description")
        else:
            raise SourceScanError("Evidence kind must be text or visual_reviewed")
