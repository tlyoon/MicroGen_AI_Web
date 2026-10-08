# MicroGen_AI Educational Automation Package
# (c) 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.
# This file is part of the MicroGen_AI package.
# Licensed under the MIT License (see LICENSE file in the project root).
# You may not use this file except in compliance with the License.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
check_gen.py

Scan numbered chapter directories (e.g. 22/, 26/)
and their subdirectories (e.g. 22.1, 22.2, 26.3)
to verify whether generated files exist.

Files checked:
    slides.pdf
    slides.tex
    script.txt
    slides.mp4
"""

from pathlib import Path
import re

# Files that should exist in each subchapter directory
REQUIRED_FILES = [
    "slides.pdf",
    "slides.tex",
    "script.txt",
    "slides.mp4",
]

ROOT = Path.cwd()


def is_numbered_dir(name: str) -> bool:
    """Return True if directory name is purely numeric (e.g. '22')."""
    return re.fullmatch(r"\d+", name) is not None


def is_subchapter_dir(name: str, chapter: str) -> bool:
    """
    Return True if directory looks like a subchapter
    such as 22.1, 22.2, 22.10 etc.
    """
    return re.fullmatch(rf"{chapter}\.\d+", name) is not None


def check_subchapter(path: Path):
    """Check whether required files exist in a subchapter directory."""
    missing = []
    existing = []

    for f in REQUIRED_FILES:
        if (path / f).exists():
            existing.append(f)
        else:
            missing.append(f)

    if not missing:
        print(f"[OK]   {path.name} : {REQUIRED_FILES} generated.")
    else:
        print(f"[MISS] {path.name}")
        print(f"       Missing : {', '.join(missing)}")
        if existing:
            print(f"       Present : {', '.join(existing)}")
    print('')

def main():

    print("\nScanning generated outputs...\n")

    for chapter_dir in sorted(ROOT.iterdir()):

        if not chapter_dir.is_dir():
            continue

        if not is_numbered_dir(chapter_dir.name):
            continue

        chapter = chapter_dir.name

        for sub in sorted(chapter_dir.iterdir()):

            if not sub.is_dir():
                continue

            if is_subchapter_dir(sub.name, chapter):
                check_subchapter(sub)

    print("\nScan complete.\n")


if __name__ == "__main__":
    main()