"""Split lecture slide PDF locally; atomically publish verified one-page files.

This maintained module replaces the old vendor slice_pdf.py stage on all PCs.
It reads source bytes from the configured root, but does all PDF manipulation
on local temporary storage before publishing individual slides.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified_copy(source: Path, destination: Path, expected: str) -> None:
    """Refuse corrupted or simultaneously-changing cloud-mount copies."""
    shutil.copy2(source, destination)
    if sha256(destination) != expected:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Slide PDF copy changed during publication: {source}")


def split_slides(folder: Path) -> int:
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        from pypdf import PdfReader, PdfWriter
    folder = folder.expanduser().resolve()
    source = folder / "slides.pdf"
    if not source.is_file() or source.stat().st_size < 100:
        raise FileNotFoundError(f"Missing/empty validated slides.pdf: {source}")
    signature = sha256(source)
    with tempfile.TemporaryDirectory(prefix="microgen_slide_split_") as scratch:
        tmp = Path(scratch)
        local_source = tmp / "slides.pdf"
        verified_copy(source, local_source, signature)
        with local_source.open("rb") as stream:
            pages = PdfReader(stream)
            count = len(pages.pages)
            if count <= 0:
                raise ValueError("slides.pdf contains no pages")
            print(f"[slide-split] {count} pages; local scratch={tmp}", flush=True)
            for index, page in enumerate(pages.pages, start=1):
                writer = PdfWriter()
                writer.add_page(page)
                local = tmp / f"slide{index}.pdf"
                with local.open("wb") as target:
                    writer.write(target)
                if len(PdfReader(str(local)).pages) != 1:
                    raise RuntimeError(f"Slide {index} failed one-page verification")
                digest = sha256(local)
                dest = folder / local.name
                if dest.is_file() and sha256(dest) == digest:
                    print(f"[slide-split] reused slide {index}/{count}", flush=True)
                    continue
                staging = folder / f".{local.name}.pending.{os.getpid()}"
                try:
                    verified_copy(local, staging, digest)
                    staging.replace(dest)
                finally:
                    staging.unlink(missing_ok=True)
                print(f"[slide-split] published slide {index}/{count}", flush=True)
    return count


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="MicroGen safe local slide splitter")
    parser.add_argument("--folder", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        count = split_slides(args.folder)
        print(f"[slide-split] SUCCESS: {count} validated one-page PDFs", flush=True)
    except Exception as exc:
        print(f"[slide-split] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
