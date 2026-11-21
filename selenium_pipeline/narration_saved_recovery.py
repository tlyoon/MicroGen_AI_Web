"""Reuse a previously rejected but now fully validated, source-bound narration.

The rejected candidate is itself post-processed text, never a new model
request.  It may be recovered ONLY when the same original source and same
compiled slide PDF precede its creation, and the *current full* narration QA
accepts it. Never rewrite the original source or downgrade QA.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recover_saved_narration(
    folder: Path, *, source_pdf: Path, slides_pdf: Path,
    check_warnings: Callable[[Path], list[str]],
) -> dict | None:
    root = Path(folder)
    state = root / ".selenium_pipeline_state.json"
    target = root / "script.txt"
    if (not state.is_file() or state.is_symlink()
            or not source_pdf.is_file() or not slides_pdf.is_file()):
        return None
    try:
        receipt = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (receipt.get("failed_stage") != "narration"
            or receipt.get("source_sha256") != _sha(source_pdf)
            or not isinstance(receipt.get("completed", {}).get("slides"), dict)):
        return None
    # A source-checked stage cannot silently recover narration from slides
    # rebuilt AFTER the candidate was produced, even with identical titles.
    lower_bound = max(source_pdf.stat().st_mtime_ns, slides_pdf.stat().st_mtime_ns)
    matches = sorted(root.glob("script.rejected_api_attempt_*.txt"),
                     key=lambda p: p.stat().st_mtime_ns, reverse=True)
    for candidate in matches:
        if (not candidate.is_file() or candidate.is_symlink()
                or not 100 < candidate.stat().st_size < 2_000_000
                or candidate.stat().st_mtime_ns < lower_bound):
            continue
        try:
            warnings = check_warnings(candidate)
        except (OSError, ValueError, RuntimeError, ImportError):
            continue
        if warnings:
            continue
        # Stage output may be absent after a prior failed pass. Never destroy
        # a different preexisting script; archive it for reconciliation.
        if target.is_file():
            if _sha(target) != _sha(candidate):
                return None
            return {"status": "validated_existing", "candidate": candidate.name,
                    "source_sha256": _sha(source_pdf),
                    "slides_sha256": _sha(slides_pdf)}
        if target.exists():
            return None
        data = candidate.read_bytes()
        pending = root / "script.txt.recovering"
        if pending.exists():
            return None
        with pending.open("xb") as stream:
            stream.write(data)
        try:
            # Re-run the caller's *same* full QA on the adopted bytes before
            # treating them as a finished generation stage.
            if check_warnings(pending):
                return None
            pending.replace(target)
        finally:
            pending.unlink(missing_ok=True)
        return {"status": "accepted_saved_narration", "candidate": candidate.name,
                "source_sha256": _sha(source_pdf),
                "slides_sha256": _sha(slides_pdf)}
    return None
