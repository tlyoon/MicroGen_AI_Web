"""Pre-generation source-scanning and draft series-planning tools.

Only writes an explicit, non-existing output JSON file. No TTS or Gemini calls,
slide generation, source-PDF modifications or MP4 production are performed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..domains import ProfileError, load_profile
from .lesson_planner import LessonPlanError, plan_series
from .draft_outline import draft_page_outline
from .source_scan import SourceScanError, scan_pdf


def _strict_pairs(pairs):
    found = {}
    for k, v in pairs:
        if k in found:
            raise ValueError(f"Duplicate outline key: {k}")
        found[k] = v
    return found


def _write_new_json(path: Path, document: dict) -> None:
    """No-overwrite delivery, no intermediate file in the source directory."""
    target = path.expanduser().absolute()
    if not target.parent.is_dir():
        raise LessonPlanError(f"Output directory does not exist: {target.parent}")
    with target.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(document, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only PDF scan / reviewed top-down plan")
    parser.add_argument("action", choices=("scan", "draft", "plan"))
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-pdf", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True,
                        help="New JSON file; refuses existing paths")
    parser.add_argument("--outline", type=Path,
                        help="Reviewed concept outline; required for plan")
    parser.add_argument("--domain", default=None,
                        help="Built-in domain or declared ID of explicit --profile-file")
    parser.add_argument("--profile-file", type=Path)
    args = parser.parse_args(argv)
    try:
        scan = scan_pdf(args.source_pdf, source_root=args.source_root)
        if args.action == "scan":
            _write_new_json(args.out, scan)
            print(f"Unreviewed source scan: {args.out} ({scan['page_count']} pages)")
            return 0
        if not args.domain and not args.profile_file:
            parser.error("draft/plan requires --domain or --profile-file")
        if args.action == "draft":
            profile = load_profile(args.domain, profile_file=args.profile_file)
            document = draft_page_outline(args.source_pdf, scan, profile)
            _write_new_json(args.out, document)
            print(f"UNREVIEWED page-outline scaffold: {args.out}")
            return 0
        if not args.outline:
            parser.error("plan requires --outline (reviewed source concept map)")
        if not args.outline.is_file() or args.outline.stat().st_size > 2_000_000:
            raise LessonPlanError("Reviewed concept outline missing or exceeds 2 MiB")
        with args.outline.open(encoding="utf-8-sig") as stream:
            outline = json.load(stream, object_pairs_hook=_strict_pairs)
        profile = load_profile(args.domain, profile_file=args.profile_file)
        plan = plan_series(outline, scan, profile, source_pdf=args.source_pdf)
        _write_new_json(args.out, plan)
        print(f"Planned {len(plan['parts'])} review-bound video parts: {args.out}")
        return 0
    except (LessonPlanError, SourceScanError, ProfileError, OSError,
            ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Planning blocked: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
