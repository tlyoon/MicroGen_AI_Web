"""Safely reconcile an older MicroGen_AI_Web completion with lost sync metadata.

Stage 5 used to generate slide_narration_sync.json only in .microgen_work.
A completed legacy lecture may retain all validated final files and QA reports
after its workspace was removed. This explicit, OFF-BY-DEFAULT repair binds
current exact PDF/script/WAV bytes only after verifying QA and the final MP4.
No source, slide, script, WAV, MP4 or preexisting sync proof is rewritten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from .cleanup import (
    RECEIPT as COMPLETION_NAME,
    _final_hashes,
    _sha256,
    _write_receipt,
    completed_lecture,
)
from .slide_narration_sync import (
    RECEIPT as ALIGNMENT_NAME,
    inspect,
    verify,
)
from .video_ffmpeg import ffmpeg_executable, validate_video


def _json(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Required trustworthy report missing: {path.name}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"Invalid report: {path.name}")
    return obj


def reconcile(folder: Path, *, apply: bool = False) -> dict:
    folder = Path(folder).expanduser().resolve()
    source = folder / "source.pdf"
    completion_path = folder / COMPLETION_NAME
    proof = folder / ALIGNMENT_NAME

    # Source/MP4 hash gates are mandatory even for a dry run.
    if not completed_lecture(source):
        raise ValueError("Legacy lecture lacks an intact matching completion receipt")
    prior = _json(completion_path)
    if prior.get("structural_sync_sha256"):
        verify(folder)
        if _sha256(proof) != prior["structural_sync_sha256"]:
            raise ValueError("Existing synchronization receipt hash differs")
        return {"status": "already_certified", "source_folder": str(folder)}

    report = inspect(folder)
    if proof.exists():
        # Existing proof must not be overwritten, even if unexpectedly stale.
        verify(folder)

    fidelity = _json(folder / "tts_fidelity_report.json")
    summary = fidelity.get("summary", {})
    threshold = float(fidelity.get("threshold_percent", 99.0))
    entries = fidelity.get("slides")
    if (not isinstance(summary, dict)
            or summary.get("slides") != report["pages"]
            or summary.get("passed") != report["pages"]
            or summary.get("review") != 0
            or summary.get("blocking_failures") != 0
            or float(summary.get("minimum_fidelity_percent", -1)) < threshold
            or not isinstance(entries, list)
            or len(entries) != report["pages"]
            or {x.get("slide") for x in entries} != set(range(1, report["pages"] + 1))
            or any(x.get("status") != "pass" or
                   float(x.get("fidelity_percent", -1)) < threshold for x in entries)):
        raise ValueError("TTS fidelity report does not independently certify every slide")

    risk = _json(folder / "script_risk_report.json")
    if risk.get("summary", {}).get("blocking") != 0:
        raise ValueError("Narration script has blocking QA findings")

    # Validate the exact published MP4, not a cached or former candidate.
    expected_seconds = sum(track["duration_s"] for track in report["wav"])
    validate_video(ffmpeg_executable(), folder / "slides.mp4", expected_seconds)
    snapshot = {"source_sha256": _sha256(source),
                "final_sha256": _final_hashes(folder),
                "wav": {x["file"]: x["sha256"] for x in report["wav"]}}
    if (prior.get("source_sha256") != snapshot["source_sha256"]
            or prior.get("final_sha256") != snapshot["final_sha256"]):
        raise ValueError("Lecture changed while validating reconciliation")

    result = {"status": "eligible" if not apply else "reconciled",
              "source_folder": str(folder), "pages": report["pages"],
              "expected_audio_seconds": round(expected_seconds, 2),
              "original_media_unchanged": True}
    if not apply:
        return result

    if (snapshot["source_sha256"] != _sha256(source)
            or snapshot["final_sha256"] != _final_hashes(folder)
            or any(_sha256(folder / name) != digest
                   for name, digest in snapshot["wav"].items())):
        raise ValueError("Lecture changed before reconciliation; refusing write")

    # Preserve the old receipt first; never silently rewrite one without history.
    history = folder / ".history" / (
        "sync_reconcile_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    )
    history.mkdir(parents=True, exist_ok=False)
    shutil.copy2(completion_path, history / "previous_completion.json")

    if not proof.exists():
        temporary = folder / (ALIGNMENT_NAME + ".reconcile.tmp")
        try:
            temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
            temporary.replace(proof)
        finally:
            temporary.unlink(missing_ok=True)
    verify(folder)

    updated = dict(prior)
    updated["structural_sync_sha256"] = _sha256(proof)
    updated["structural_sync_reconciled_at_utc"] = datetime.now(timezone.utc).isoformat()
    _write_receipt(source, updated)
    if not completed_lecture(source):
        raise RuntimeError("Published receipt failed verification after reconciliation")
    if _final_hashes(folder) != snapshot["final_sha256"]:
        raise RuntimeError("A finalized deliverable changed unexpectedly")
    result["backup_receipt"] = str(history / "previous_completion.json")
    result["structural_sync_sha256"] = updated["structural_sync_sha256"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-folder", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="Explicitly enable receipt repair")
    args = parser.parse_args()
    print(json.dumps(reconcile(args.source_folder, apply=args.apply), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
