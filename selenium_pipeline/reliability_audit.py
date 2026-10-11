"""Read-only, source-adjacent verification of a MicroGen lecture campaign.

The shared worker checkpoint is useful for scheduling, but it is NOT evidence
that an MP4 is valid. Count only hash-verified receipts as completed lectures.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .cleanup import RECEIPT, _ensure_latex_graphics, completed_lecture
from .slide_narration_sync import verify as verify_sync

SUBCHAPTER = re.compile(r"^\d+\.\d+$")
ASSETS = ("slides.tex", "slides.pdf", "script.txt", "slides.mp4")


def source_folders(root: Path):
    """Yield genuine direct chapter/subchapter source folders only."""
    for chapter in sorted(root.iterdir()):
        if not chapter.is_dir() or not chapter.name.isdecimal():
            continue
        for folder in sorted(chapter.iterdir()):
            if (folder.is_dir() and SUBCHAPTER.fullmatch(folder.name)
                    and folder.name.split(".")[0] == chapter.name
                    and (folder / "source.pdf").is_file()):
                yield folder


def inspect_job(folder: Path) -> dict:
    source = folder / "source.pdf"
    files = {name: (folder / name).is_file() and
             (folder / name).stat().st_size > 0 for name in ASSETS}
    complete = completed_lecture(source)
    published = files["slides.mp4"]
    category = ("verified_complete" if complete else
                "published_requires_reconciliation" if published else
                "partial_slides" if files["slides.pdf"] else "no_published_slides")
    result = {
        "subchapter": folder.name,
        "category": category,
        "receipt_present": (folder / RECEIPT).is_file(),
        "receipt_valid": complete,
        "outputs": files,
        "wav_count": len(list(folder.glob("slide*.wav"))),
    }
    if files["slides.tex"]:
        try:
            _ensure_latex_graphics(folder, None)
            result["latex_graphics"] = "present"
        except (OSError, ValueError) as exc:
            result["latex_graphics"] = "blocked"
            result["latex_graphics_problem"] = str(exc)
    sync = folder / "slide_narration_sync.json"
    if sync.is_file():
        try:
            summary = verify_sync(folder)
            result["structural_sync"] = "verified"
            result["sync_slide_count"] = summary["pages"]
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            result["structural_sync"] = "invalid"
            result["sync_problem"] = str(exc)
    else:
        result["structural_sync"] = "absent"
    return result


def inspect_campaign(root: Path, *, expected_count: int | None = None) -> dict:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Missing campaign source root: {root}")
    jobs = [inspect_job(folder) for folder in source_folders(root)]
    if expected_count is not None and expected_count != len(jobs):
        raise ValueError(f"Expected {expected_count} source PDFs, found {len(jobs)}")
    categories = {name: sum(j["category"] == name for j in jobs)
                  for name in ("verified_complete",
                               "published_requires_reconciliation",
                               "partial_slides", "no_published_slides")}
    return {"source_root": str(root), "checked_utc": datetime.now(timezone.utc).isoformat(),
            "total_source_pdfs": len(jobs), "categories": categories,
            "all_verified_complete": bool(jobs) and categories["verified_complete"] == len(jobs),
            "jobs": jobs}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only verification of source-adjacent lecture outputs")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--expected", type=int, help="Fail if the source-PDF count differs")
    parser.add_argument("--report", type=Path, help="Write a NEW audit JSON file outside source folders")
    args = parser.parse_args(argv)
    data = inspect_campaign(args.source_root, expected_count=args.expected)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        # No clobbering old audit records and no source-file mutations.
        with args.report.open("x", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
    print(json.dumps({k: v for k, v in data.items() if k != "jobs"}, indent=2))
    return 0 if data["all_verified_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
