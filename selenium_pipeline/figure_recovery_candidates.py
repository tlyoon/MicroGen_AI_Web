"""Source-PDF-grounded visual review candidates for unresolved slide figures.

This module deliberately NEVER auto-publishes a crop as a finished diagram.
A textbook caption identifies a *page*, not an exact image boundary. It
creates an inspectable manifest and thumbnails for human/semantic approval.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .figure_audit import audit_one

FIGURE_NUMBER = re.compile(r"(?i)fig(?:ure)?[ _-]*(\d+)[ ._-]+(\d+)")


def figure_number(name: str) -> tuple[int, int] | None:
    match = FIGURE_NUMBER.search(name)
    return (int(match[1]), int(match[2])) if match else None


def caption_pages(source_pdf: Path, number: tuple[int, int]) -> list[int]:
    import pymupdf
    major, minor = number
    caption = re.compile(rf"(?i)\bfig(?:ure)?\s*{major}\s*[.\-]\s*{minor}\b")
    pages = []
    with pymupdf.open(source_pdf) as pdf:
        for i, page in enumerate(pdf):
            content = " ".join(page.get_text().split())
            if caption.search(content):
                pages.append(i)
    return pages


def stage_review(folder: Path, output: Path, *, maximum_pages: int = 3) -> dict:
    """Write new review artifacts, without touching the source or lecture."""
    if maximum_pages < 1 or maximum_pages > 12:
        raise ValueError("maximum_pages must be 1..12")
    folder = Path(folder)
    output = Path(output)
    audit = audit_one(folder)
    unresolved = [entry for entry in audit["graphics"] if entry["status"] != "present"]
    source = folder / "source.pdf"
    import pymupdf
    # Refuse to overwrite a previous review or any output inside the textbook PDF.
    output.mkdir(parents=True, exist_ok=False)
    previews = []
    records = []
    with pymupdf.open(source) as pdf:
        for item in unresolved:
            number = figure_number(item["reference"])
            pages = caption_pages(source, number) if number is not None else []
            candidates = []
            for index in pages[:maximum_pages]:
                name = f"figure_{len(records)+1}_page_{index+1}.png"
                rendered = output / name
                pdf[index].get_pixmap(matrix=pymupdf.Matrix(1.25, 1.25),
                                       alpha=False).save(rendered)
                candidates.append({"source_page": index + 1, "preview": name})
                previews.append(name)
            records.append({"reference": item["reference"], "status": item["status"],
                            "figure_number": number, "matching_pdf_pages": [x+1 for x in pages],
                            "page_previews": candidates, "requires_semantic_crop_approval": True})
    manifest = {"source": str(source), "source_sha256": audit["source_sha256"],
                "published_images_modified": False, "records": records}
    with (output / "manifest.json").open("x", encoding="utf-8") as fp:
        json.dump(manifest, fp, indent=2)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review source-PDF pages for missing LaTeX figures")
    parser.add_argument("--subchapter-folder", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--maximum-pages", type=int, default=3)
    args = parser.parse_args(argv)
    result = stage_review(args.subchapter_folder, args.output_dir,
                          maximum_pages=args.maximum_pages)
    print(json.dumps({"unresolved": len(result["records"]),
                      "review_dir": str(args.output_dir),
                      "note": "No original lecture files were modified."}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
