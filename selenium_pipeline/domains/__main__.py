"""Inspect teaching profiles without running Gemini, TTS or lecture generation."""
from __future__ import annotations

import argparse
import json
from .registry import (
    BUILTIN_PROFILES, PROFILE_STAGES, ProfileError,
    load_profile, render_stage_guidance,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect MicroGen teaching profiles (no generation)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="Show supported built-in domain profiles")
    for name in ("inspect", "guidance"):
        cmd = sub.add_parser(name, help=f"{name.title()} a domain profile without generating media")
        cmd.add_argument("--domain", help="Built-in domain ID or declared custom domain ID")
        cmd.add_argument("--profile-file", help="Explicit path to custom JSON profile")
        if name == "guidance":
            cmd.add_argument("--stage", choices=PROFILE_STAGES, required=True)
    args = parser.parse_args(argv)
    if args.command == "list":
        for name in BUILTIN_PROFILES:
            profile = load_profile(name)
            print(f"{profile.id}: {profile.display_name} [{profile.maturity}]")
        return 0
    try:
        if not args.domain and not args.profile_file:
            parser.error("Specify --domain or --profile-file")
        profile = load_profile(args.domain, profile_file=args.profile_file)
        if args.command == "inspect":
            print(json.dumps({
                "id": profile.id, "version": profile.profile_version,
                "display_name": profile.display_name, "maturity": profile.maturity,
                "content_types": profile.content_types,
                "review_checks": profile.review_checks,
                "warning": "This CLI validates configuration only; no domain quality is certified.",
            }, indent=2))
        else:
            print(render_stage_guidance(profile, args.stage))
        return 0
    except ProfileError as exc:
        parser.exit(2, f"Profile error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
