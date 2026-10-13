"""Offline inspection, draft scaffolding and authored storyboard contract checks.

This CLI never runs Gemini, Beamer, audio processing, FFmpeg or publication.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .domains import load_profile
from .planning import scan_pdf, validate_outline
from .storyboard_authoring import build_authoring_brief, draft_storyboard
from .storyboard_gate import StoryboardError, inspect_storyboard
from .beamer_anchor_contract import verify_tex_anchor_coverage


def _no_duplicate_json_keys(pairs):
    d = {}
    for key, val in pairs:
        if key in d:
            raise StoryboardError(f"Duplicate JSON object key: {key}")
        d[key] = val
    return d


def _load_json(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > 2_000_000:
        raise StoryboardError(f"Missing or excessive JSON file: {path}")
    obj = json.loads(path.read_text(encoding="utf-8-sig"),
                     object_pairs_hook=_no_duplicate_json_keys)
    if not isinstance(obj, dict):
        raise StoryboardError("Expected a JSON object")
    return obj


def _write_new(path: Path, data: str) -> None:
    if not path.parent.is_dir():
        raise StoryboardError(f"Output directory does not exist: {path.parent}")
    # A failed gate does not create any output file.
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline joint slide/narration storyboard contract")
    parser.add_argument("action", choices=("draft", "brief", "inspect"))
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-pdf", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--outline", type=Path, required=True)
    parser.add_argument("--domain", help="Built-in or declared custom domain ID")
    parser.add_argument("--profile-file", type=Path)
    parser.add_argument("--part", required=True, help="Part ID, e.g. part_01")
    parser.add_argument("--storyboard", type=Path,
                        help="Fully authored storyboard.json required to inspect")
    parser.add_argument("--latex", type=Path,
                        help="Optional Beamer LaTeX containing semantic MGElement tokens")
    parser.add_argument("--out", type=Path, required=True,
                        help="New file only. Existing output is never overwritten")
    args = parser.parse_args(argv)
    if not args.domain and not args.profile_file:
        parser.error("Specify --domain or explicit --profile-file")
    try:
        profile = load_profile(args.domain, profile_file=args.profile_file)
        scan = scan_pdf(args.source_pdf, source_root=args.source_root)
        outline = _load_json(args.outline)
        validate_outline(outline, scan, profile, source_pdf=args.source_pdf)
        plan = _load_json(args.plan)
        if plan.get("source_sha256") != scan["source_sha256"]:
            raise StoryboardError("Plan source hash does not match actual PDF")
        if args.action == "draft":
            scaffold = draft_storyboard(plan, outline, args.part, profile)
            data = json.dumps(scaffold, ensure_ascii=False, indent=2) + "\n"
        elif args.action == "brief":
            data = build_authoring_brief(plan, outline, args.part, profile) + "\n"
        else:
            if args.storyboard is None:
                parser.error("inspect requires --storyboard")
            authored = _load_json(args.storyboard)
            if authored.get("part_id") != args.part:
                raise StoryboardError("Inspect part ID mismatch")
            result = inspect_storyboard(
                authored, plan, outline, profile,
                scan=scan, source_pdf=args.source_pdf,
            )
            if args.latex:
                if not args.latex.is_file() or args.latex.stat().st_size > 3_000_000:
                    raise StoryboardError("Missing or excessive LaTeX source")
                result["latex_anchor_audit"] = verify_tex_anchor_coverage(
                    args.latex.read_text(encoding="utf-8"), authored
                )
            data = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        _write_new(args.out, data)
        print(f"Saved {args.action} (NOT a scientifically certified video): {args.out}")
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(2, f"Storyboard blocked: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
