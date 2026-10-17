"""Read-only, repeatable technical audit of an EXISTING MicroGen review bundle.

It checks the actual encoded MP4 video/element pixels each invocation, not
just saved hashes or a stale signed-off receipt. It does not regenerate,
publish, rewrite, review speech acoustics, or approve scientific mappings.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .element_highlight_workflow import (
    HighlightReviewGateError, verify_rendered,
)


def audit_existing(*, source: Path, slides: Path, authored: Path,
                   audio: Path, review_root: Path) -> dict:
    root = Path(review_root)
    if root.is_symlink() or not root.is_dir():
        raise HighlightReviewGateError("Existing review root is absent or symlinked")
    root = root.resolve(strict=True)
    source, slides, authored, audio = map(
        Path, (source, slides, authored, audio))
    if (any(path.is_symlink() for path in (source, slides, authored, audio))
            or root == source.parent.resolve()
            or root.is_relative_to(source.parent.resolve())
            or root == audio.resolve()
            or root.is_relative_to(audio.resolve())):
        raise HighlightReviewGateError(
            "Review bundle must be outside the original source/audio directories")
    for subfolder in ("staged", "rendered"):
        location = root / subfolder
        if location.is_symlink() or not location.is_dir():
            raise HighlightReviewGateError(
                f"Existing {subfolder} review folder is absent or symlinked")
    checked = verify_rendered(
        source=source, slides=slides, authored=authored, audio=audio,
        staged=root / "staged", rendered=root / "rendered",
        output=None, recheck_pixels=True)
    return {
        **checked,
        "status": "EXISTING_VIDEO_REVIEW_TECHNICAL_RECHECK_ONLY",
        "audit_mode": "read_only_redecoded_mp4_pixels",
        "mp4_pixel_qa_fresh": True,
        "human_listening_approved": False,
        "scientific_semantic_mapping_approved": False,
        "production_approved": False,
        "student_published": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "slides", "authored", "audio", "review-root"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(argv)
    result = audit_existing(
        source=args.source, slides=args.slides, authored=args.authored,
        audio=args.audio, review_root=args.review_root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
