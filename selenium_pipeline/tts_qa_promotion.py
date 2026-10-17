"""Audit repaired TTS candidates and export reviewed audio to a NEW isolated folder.

No Google SDK/network, billing, automatic approvals, original WAV replacement,
video rendering or student publication is performed by this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from .runner import blocks


class AudioPromotionBlocked(RuntimeError):
    pass


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_file(folder: Path, name: str) -> bytes:
    path = folder / name
    if path.is_symlink() or not path.is_file():
        raise AudioPromotionBlocked(f"Missing or symlinked evidence: {name}")
    return path.read_bytes()


def _read_json(folder: Path, name: str) -> tuple[dict, bytes]:
    raw = _read_file(folder, name)
    try:
        result = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise AudioPromotionBlocked(f"Invalid JSON evidence: {name}") from exc
    if not isinstance(result, dict):
        raise AudioPromotionBlocked(f"Evidence is not a JSON object: {name}")
    return result, raw


def audit(source: Path, review: Path) -> dict:
    """Verify original and reviewed audio plus full QA report; NO filesystem writes."""
    if source.is_symlink() or review.is_symlink():
        raise AudioPromotionBlocked("Source and review directories cannot be symlinks")
    try:
        src = source.resolve(strict=True)
        rev = review.resolve(strict=True)
    except OSError as exc:
        raise AudioPromotionBlocked("Missing source or review directory") from exc
    if not src.is_dir() or not rev.is_dir():
        raise AudioPromotionBlocked("Source and review must be directories")
    if rev.parent != src / ".tts_qa_review_candidates":
        raise AudioPromotionBlocked("Review folder is not attached to the given source")
    receipt, receipt_bytes = _read_json(rev, "review_only_receipt.json")
    report, report_bytes = _read_json(rev, "tts_fidelity_report.json")
    source_script = _read_file(src, "script.txt")
    source_manifest = _read_file(src, "tts_input_manifest.json")
    if (_digest(source_script) != receipt.get("source_script_sha256")
            or _digest(source_manifest) != receipt.get("source_manifest_sha256")
            or source_script != _read_file(rev, "script.txt")
            or source_manifest != _read_file(rev, "tts_input_manifest.json")):
        raise AudioPromotionBlocked("Source/review script or manifest has changed")
    if (receipt.get("status") != "REVIEW_ONLY_UNPUBLISHED"
            or receipt.get("original_audio_modified") is not False
            or receipt.get("academic_approved") is not False
            or receipt.get("video_publication_approved") is not False):
        raise AudioPromotionBlocked("Receipt status is not review-only or trustworthy")
    if receipt.get("proposed_remaining_failures") != []:
        raise AudioPromotionBlocked("Audio repair has unresolved QA failures")
    if (receipt.get("provider") != "gemini"
            or receipt.get("tts_model") != "gemini-3.8-flash-lite-tts"
            or receipt.get("voice") != "Kore"):
        raise AudioPromotionBlocked("Unexpected provider, model or voice")
    try:
        manifest = json.loads(source_manifest)
        orig = receipt["original_wav_sha256"]
        proposed = receipt["candidate_wav_sha256"]
        changes = receipt["proposed_replacements"]
        items = blocks(source_script.decode("utf-8"))
        n_to_text = dict(items)
        slide_names = {f"slide{i}.wav" for i, _ in items}
        manifest_rows = manifest["slides"]
        report_rows = report["slides"]
        row_by_number = {int(row["slide"]): row for row in report_rows}
        manifest_by_number = {int(row["slide"]): row for row in manifest_rows}
        threshold = float(receipt["threshold"])
    except (UnicodeDecodeError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise AudioPromotionBlocked("Malformed source, receipt or QA report") from exc
    if (not items or len(items) != len(n_to_text)
            or not isinstance(orig, dict) or not isinstance(proposed, dict)
            or set(orig) != slide_names or set(proposed) != slide_names
            or len(manifest_rows) != len(items) or len(manifest_by_number) != len(items)
            or len(report_rows) != len(items) or len(row_by_number) != len(items)):
        raise AudioPromotionBlocked("Missing, extra or repeated slide identities")
    if (manifest.get("primary") != {
            "provider": "gemini", "model": "gemini-3.8-flash-lite-tts", "voice": "Kore"}
            or receipt.get("fidelity_model") != report.get("model")
            or threshold < 99.0 or threshold > 100.0
            or float(report.get("threshold_percent", -1)) != threshold):
        raise AudioPromotionBlocked("TTS provenance or QA threshold mismatch")
    changed = set()
    if not isinstance(changes, list) or not changes:
        raise AudioPromotionBlocked("No repair was proposed")
    for entry in changes:
        try:
            number = int(entry["slide"])
            attempt = int(entry["round"])
            digest = entry["wav_sha256"]
        except (ValueError, KeyError, TypeError) as exc:
            raise AudioPromotionBlocked("Malformed TTS replacement attempt") from exc
        if number not in n_to_text or attempt <= 0:
            raise AudioPromotionBlocked("Unrecognized slide or attempt number")
        attempt_wav = _read_file(rev, f"attempt{attempt}_slide{number}.wav")
        if _digest(attempt_wav) != digest:
            raise AudioPromotionBlocked("Attempt WAV digest does not match receipt")
        changed.add(number)
    for number, narration in items:
        name = f"slide{number}.wav"
        source_wav = _read_file(src, name)
        review_wav = _read_file(rev, name)
        if (_digest(source_wav) != orig[name]
                or _digest(review_wav) != proposed[name]):
            raise AudioPromotionBlocked("Original or proposed WAV digest mismatch")
        row = manifest_by_number[number]
        if (row.get("tts_text") != narration
                or row.get("provider") != "gemini"
                or row.get("model") != "gemini-3.8-flash-lite-tts"
                or row.get("voice") != "Kore"
                or row.get("fallback_used") is not False):
            raise AudioPromotionBlocked("Manifest text, model or voice mismatch")
        qa = row_by_number[number]
        if (qa.get("status") != "pass"
                or qa.get("audio_file") != name
                or qa.get("ground_truth") != narration
                or float(qa.get("fidelity_percent", -1)) < threshold
                or qa.get("critical_token_issues")
                or qa.get("audio_defects")
                or any(str(p.get("severity", "")).lower() == "major"
                       for p in qa.get("pronunciation_issues", []))):
            raise AudioPromotionBlocked(f"Slide {number} lacks strict QA acceptance")
        if number not in changed and source_wav != review_wav:
            raise AudioPromotionBlocked("Unrepaired slide was changed in candidate")
        if number in changed and source_wav == review_wav:
            raise AudioPromotionBlocked("Review claims repair but WAV was unchanged")
    if (report.get("summary", {}).get("review") != 0
            or report.get("summary", {}).get("blocking_failures") != 0
            or report.get("summary", {}).get("passed") != len(items)):
        raise AudioPromotionBlocked("QA summary does not confirm complete pass")
    return {
        "status": "VERIFIED_REVIEW_ONLY",
        "source": str(src),
        "review": str(rev),
        "slide_count": len(items),
        "changed_slide_numbers": sorted(changed),
        "receipt_sha256": _digest(receipt_bytes),
        "fidelity_report_sha256": _digest(report_bytes),
        "source_script_sha256": _digest(source_script),
        "source_manifest_sha256": _digest(source_manifest),
        "candidate_wav_sha256": proposed,
        "original_wav_sha256": orig,
        "provider": "gemini",
        "tts_model": "gemini-3.8-flash-lite-tts",
        "voice": "Kore",
        "human_review_approved": False,
        "video_publication_approved": False,
    }


def export_reviewed(source: Path, review: Path, destination: Path, *,
                    attestation_path: Path, confirm_reviewed_audio: bool,
                    confirm_isolated_export: bool) -> dict:
    """Copy approved audio to a fresh isolated directory; NEVER replace source."""
    if not confirm_reviewed_audio or not confirm_isolated_export:
        raise AudioPromotionBlocked("Both explicit reviewed-audio and isolated-export flags required")
    verification = audit(source, review)
    if attestation_path.is_symlink() or not attestation_path.is_file():
        raise AudioPromotionBlocked("Independent review attestation is missing or unsafe")
    try:
        attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise AudioPromotionBlocked("Invalid external attestation") from exc
    if not isinstance(attestation, dict):
        raise AudioPromotionBlocked("Independent attestation must be a JSON object")
    for key in ("receipt_sha256", "fidelity_report_sha256",
                "source_script_sha256", "source_manifest_sha256",
                "candidate_wav_sha256"):
        if attestation.get(key) != verification[key]:
            raise AudioPromotionBlocked(f"External reviewer attestation does not match {key}")
    if (attestation.get("reviewer", "").strip() in ("", "automated", "ChatGPT")
            or attestation.get("review_scope") != "tts-audio-only"
            or attestation.get("audio_listened") is not True
            or attestation.get("mathematical_pronunciation_reviewed") is not True
            or attestation.get("voice_kore_listening_verified") is not True
            or not isinstance(attestation.get("reviewed_at_utc"), str)
            or not attestation["reviewed_at_utc"].endswith("Z")):
        raise AudioPromotionBlocked("Independent human listening and voice/maths signoff missing")
    if destination.exists() or destination.is_symlink():
        raise AudioPromotionBlocked("Destination already exists; no replacement permitted")
    dest_parent = destination.parent.resolve(strict=True)
    src = source.resolve(strict=True)
    if dest_parent == src or src in dest_parent.parents:
        raise AudioPromotionBlocked("Export must be outside the original lecture tree")
    rev = review.resolve(strict=True)
    if dest_parent == rev or rev in dest_parent.parents:
        raise AudioPromotionBlocked("Export must be outside review tree")
    # Re-audit immediately before copying and enforce stable immutable hashes.
    if audit(source, review) != verification:
        raise AudioPromotionBlocked("Evidence changed during export preflight")
    destination.mkdir()
    source_script = _read_file(review, "script.txt")
    source_manifest = _read_file(review, "tts_input_manifest.json")
    for name, payload in (
        ("script.txt", source_script), ("tts_input_manifest.json", source_manifest)):
        with (destination / name).open("xb") as stream:
            stream.write(payload)
    for name, expected_hash in verification["candidate_wav_sha256"].items():
        payload = _read_file(review, name)
        if _digest(payload) != expected_hash:
            raise AudioPromotionBlocked("Candidate WAV changed during read")
        with (destination / name).open("xb") as stream:
            stream.write(payload)
    # The copied files are an isolated review-approved AUDIO HANDOFF, never
    # original assets, a rendered lecture, or permission for student publication.
    handoff = {
        **verification, "status": "AUDIO_REVIEWED_ISOLATED_COPY",
        "destination": str(destination.resolve()),
        "attestation_sha256": _digest(attestation_path.read_bytes()),
        "human_review_approved": True,
        "video_publication_approved": False,
    }
    with (destination / "tts_reviewed_handoff.json").open("x", encoding="utf-8") as stream:
        json.dump(handoff, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return handoff


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit TTS repairs, optionally export separately reviewed audio")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--attestation", type=Path)
    parser.add_argument("--confirm-reviewed-audio", action="store_true")
    parser.add_argument("--confirm-isolated-export", action="store_true")
    args = parser.parse_args(argv)
    if args.destination is not None:
        if args.attestation is None:
            parser.error("Reviewed export requires --attestation")
        result = export_reviewed(
            args.source, args.review, args.destination,
            attestation_path=args.attestation,
            confirm_reviewed_audio=args.confirm_reviewed_audio,
            confirm_isolated_export=args.confirm_isolated_export,
        )
    else:
        if args.attestation or args.confirm_reviewed_audio or args.confirm_isolated_export:
            parser.error("Review confirmation flags may only be supplied with --destination")
        result = audit(args.source, args.review)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
