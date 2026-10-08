#!/usr/bin/env python3
"""
Fix Moodle MCQ XML files by replacing

<answernumbering>abcde</answernumbering>

with

<answernumbering>abc</answernumbering>

Can be run as a script or imported as a module.
"""

from pathlib import Path


OLD = "<answernumbering>abcde</answernumbering>"
NEW = "<answernumbering>abc</answernumbering>"


def fix_answernumbering(directory: Path | str = ".") -> tuple[int, int]:
    """
    Scan all XML files in a directory and replace invalid answernumbering.

    Returns
    -------
    (files_modified, total_replacements)
    """

    directory = Path(directory)

    xml_files = list(directory.glob("*.xml"))

    files_modified = 0
    total_replacements = 0

    for f in xml_files:
        text = f.read_text(encoding="utf-8")

        count = text.count(OLD)

        if count > 0:
            new_text = text.replace(OLD, NEW)
            f.write_text(new_text, encoding="utf-8")

            print(f"{f.name}: replaced {count} occurrence(s)")

            files_modified += 1
            total_replacements += count

    print("\nSummary")
    print("-------")
    print(f"Files modified: {files_modified}")
    print(f"Total replacements: {total_replacements}")

    return files_modified, total_replacements


def main():
    """Entry point when run as script."""
    fix_answernumbering(".")


if __name__ == "__main__":
    main()