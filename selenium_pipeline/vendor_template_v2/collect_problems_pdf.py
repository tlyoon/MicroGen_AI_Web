#!/usr/bin/env python3
"""
Collect all problems.pdf files from numbered chapter folders into ./problems_pdf/

Expected source pattern:
    ./22/problems/problems.pdf
    ./23/problems/problems.pdf
    ./24/problems/problems.pdf
    ...

Output:
    ./problems_pdf/problems_22.pdf
    ./problems_pdf/problems_23.pdf
    ./problems_pdf/problems_24.pdf
    ...
"""

from pathlib import Path
import shutil


def is_numbered_dir(path: Path) -> bool:
    """Return True if the directory name is purely numeric."""
    return path.is_dir() and path.name.isdigit()


def main() -> None:
    base_dir = Path.cwd()
    output_dir = base_dir / "problems_pdf"
    output_dir.mkdir(exist_ok=True)

    copied_count = 0
    skipped_count = 0

    # Scan immediate subdirectories like 22, 23, 24, ...
    for item in sorted(base_dir.iterdir(), key=lambda p: (not p.name.isdigit(), p.name)):
        if not is_numbered_dir(item):
            continue

        chapter = item.name
        src_pdf = item / "problems" / "problems.pdf"

        if not src_pdf.is_file():
            print(f"[SKIP] Missing: {src_pdf}")
            skipped_count += 1
            continue

        dst_pdf = output_dir / f"problems_{chapter}.pdf"
        shutil.copy2(src_pdf, dst_pdf)
        print(f"[OK]   {src_pdf} -> {dst_pdf}")
        copied_count += 1

    print("\nDone.")
    print(f"Copied : {copied_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Output : {output_dir}")


if __name__ == "__main__":
    main()