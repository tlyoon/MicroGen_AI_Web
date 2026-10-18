"""Audit repaired TTS candidates and export reviewed audio to a NEW isolated folder.

No Google SDK/network, billing, automatic approvals, original WAV replacement,
video rendering or student publication is performed by this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

from .runner import blocks
from .tts_pcm_contract import verify_pcm, TTSPCMContractError
from .tts_effective_identity import (
    verify_effective_identity, TTSEffectiveIdentityError,
)
from .tts_attempt_evidence import (
    AttemptEvidence, TTSAttemptEvidenceError, ROOT as ATTEMPT_ROOT,
)


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
    try:
        effective = verify_effective_identity(manifest, items)
    except TTSEffectiveIdentityError as exc:
        raise AudioPromotionBlocked(str(exc)) from exc
    observed_retry_digest = None
    if effective["fallback_used"]:
        try:
            AttemptEvidence.verify_saved(
                src, items, manifest.get("attempt_evidence"))
        except TTSAttemptEvidenceError as exc:
            raise AudioPromotionBlocked(
                f"Unverified observed Gemini fallback attempts: {exc}") from exc
        observed_retry_digest = manifest["attempt_evidence"]["sha256"]
    if (any((receipt.get("provider") != effective["provider"],
             receipt.get("tts_model") != effective["model"],
             receipt.get("voice") != effective["voice"]))
            or receipt.get("fidelity_model") != report.get("model")
            or threshold < 99.0 or threshold > 100.0
            or float(report.get("threshold_percent", -1)) != threshold):
        raise AudioPromotionBlocked("TTS provenance or QA threshold mismatch")
    changed = set()
    last_attempt_by_slide = {}
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
        try:
            verify_pcm(attempt_wav, label=f"attempt{attempt}_slide{number}.wav")
        except TTSPCMContractError as exc:
            raise AudioPromotionBlocked(str(exc)) from exc
        if _digest(attempt_wav) != digest:
            raise AudioPromotionBlocked("Attempt WAV digest does not match receipt")
        if number in last_attempt_by_slide and attempt <= last_attempt_by_slide[number][0]:
            raise AudioPromotionBlocked("Attempt history is repeated or out of order")
        last_attempt_by_slide[number] = (attempt, digest)
        changed.add(number)
    for number, narration in items:
        name = f"slide{number}.wav"
        source_wav = _read_file(src, name)
        review_wav = _read_file(rev, name)
        try:
            verify_pcm(source_wav, label=f"original {name}")
            verify_pcm(review_wav, label=f"reviewed {name}")
        except TTSPCMContractError as exc:
            raise AudioPromotionBlocked(str(exc)) from exc
        if (_digest(source_wav) != orig[name]
                or _digest(review_wav) != proposed[name]):
            raise AudioPromotionBlocked("Original or proposed WAV digest mismatch")
        row = manifest_by_number[number]
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
        if number in changed and _digest(review_wav) != last_attempt_by_slide[number][1]:
            raise AudioPromotionBlocked("Final repair WAV differs from latest recorded attempt")
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
        "provider": effective["provider"],
        "tts_model": effective["model"],
        "voice": effective["voice"],
        "requested_primary": effective["requested_primary"],
        "fallback_chain": effective["fallback_chain"],
        "fallback_used": effective["fallback_used"],
        "attempt_evidence_sha256": observed_retry_digest,
        "voice_listening_field": effective["voice_listening_field"],
        "human_review_approved": False,
        "video_publication_approved": False,
    }


def _export(source: Path, review: Path, destination: Path, *,
            attestation_path: Path | None,
            confirm_reviewed_audio: bool,
            confirm_isolated_export: bool) -> dict:
    """Copy fully technically verified audio with OPTIONAL human review.

    No human attestation is needed to advance to the next internal stage.
    The separate human-reviewed label remains reserved for actual signoff.
    Neither path authorizes student publication or replaces original WAVs.
    """
    if attestation_path is not None and (
            not confirm_reviewed_audio or not confirm_isolated_export):
        raise AudioPromotionBlocked("Both explicit reviewed-audio and isolated-export flags required")
    verification = audit(source, review)
    if attestation_path is not None:
        if attestation_path.is_symlink() or not attestation_path.is_file():
            raise AudioPromotionBlocked("Independent review attestation is missing or unsafe")
        attestation_location = attestation_path.resolve(strict=True)
        source_location = source.resolve(strict=True)
        review_location = review.resolve(strict=True)
        if (attestation_location == source_location
                or source_location in attestation_location.parents
                or attestation_location == review_location
                or review_location in attestation_location.parents):
            raise AudioPromotionBlocked(
                "Attestation must be independently supplied outside the original/review tree")
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
        if (verification["fallback_used"] and
                attestation.get("attempt_evidence_sha256")
                    != verification["attempt_evidence_sha256"]):
            raise AudioPromotionBlocked(
                "Human reviewer did not attest to the actual retry-attempt journal")
        if (not isinstance(attestation.get("reviewer"), str)
                or attestation.get("reviewer", "").strip() in ("", "automated", "ChatGPT")
                or attestation.get("review_scope") != "tts-audio-only"
                or attestation.get("audio_listened") is not True
                or attestation.get("mathematical_pronunciation_reviewed") is not True
                or attestation.get(verification["voice_listening_field"]) is not True
                or (verification["fallback_used"]
                    and attestation.get("fallback_provider_change_reviewed") is not True)
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
    # Build completely in a temporary sibling and rename only when all WAVs,
    # hashes, manifest, and handoff receipt are present. An interrupted write
    # cannot leave a misleadingly named finished reviewed-audio directory.
    staged = Path(tempfile.mkdtemp(prefix=".microgen_tts_export_", dir=dest_parent))
    try:
        source_script = _read_file(review, "script.txt")
        source_manifest = _read_file(review, "tts_input_manifest.json")
        for name, payload in (
            ("script.txt", source_script), ("tts_input_manifest.json", source_manifest)):
            with (staged / name).open("xb") as stream:
                stream.write(payload)
        for name, expected_hash in verification["candidate_wav_sha256"].items():
            payload = _read_file(review, name)
            if _digest(payload) != expected_hash:
                raise AudioPromotionBlocked("Candidate WAV changed during read")
            with (staged / name).open("xb") as stream:
                stream.write(payload)
        if verification["fallback_used"]:
            items = blocks(source_script.decode("utf-8"))
            observed = src / ATTEMPT_ROOT
            if observed.is_symlink() or not observed.is_dir():
                raise AudioPromotionBlocked("Unsafe fallback attempt journal")
            shutil.copytree(observed, staged / ATTEMPT_ROOT)
            try:
                AttemptEvidence.verify_saved(
                    staged, items, json.loads(source_manifest)["attempt_evidence"])
            except TTSAttemptEvidenceError as exc:
                raise AudioPromotionBlocked("Retry evidence changed during export") from exc
        if audit(source, review) != verification:
            raise AudioPromotionBlocked("Review evidence changed during export")
        # An isolated audio handoff NEVER carries downstream release authority.
        handoff = {
            **verification,
            "status": ("AUDIO_REVIEWED_ISOLATED_COPY"
                       if attestation_path is not None else
                       "AUDIO_TECHNICALLY_VERIFIED_ISOLATED_COPY"),
            "destination": str(destination.absolute()),
            "attestation_sha256": (_digest(attestation_path.read_bytes())
                                   if attestation_path is not None else None),
            "human_review_approved": attestation_path is not None,
            "human_review_required_for_next_stage": False,
            "technical_audio_qa_passed": True,
            "video_publication_approved": False,
        }
        with (staged / "tts_reviewed_handoff.json").open("x", encoding="utf-8") as stream:
            json.dump(handoff, stream, indent=2, sort_keys=True)
            stream.write("\n")
        if destination.exists() or destination.is_symlink():
            raise AudioPromotionBlocked("Destination appeared during export; no overwrite permitted")
        staged.rename(destination)
    finally:
        if staged.exists():
            shutil.rmtree(staged)
    return handoff


def export_verified(source: Path, review: Path, destination: Path) -> dict:
    """Standard unattended, source-hash-bound audio handoff, no human gate."""
    return _export(source,review,destination,attestation_path=None,
                   confirm_reviewed_audio=False,confirm_isolated_export=False)


def export_reviewed(source: Path, review: Path, destination: Path, *,
                    attestation_path: Path, confirm_reviewed_audio: bool,
                    confirm_isolated_export: bool) -> dict:
    """Optional independent human signoff; label must never be fabricated."""
    if attestation_path is None:
        raise AudioPromotionBlocked("Human-reviewed export requires real attestation")
    return _export(source,review,destination,attestation_path=attestation_path,
                   confirm_reviewed_audio=confirm_reviewed_audio,
                   confirm_isolated_export=confirm_isolated_export)


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
        if args.attestation is not None:
            result = export_reviewed(
                args.source, args.review, args.destination,
                attestation_path=args.attestation,
                confirm_reviewed_audio=args.confirm_reviewed_audio,
                confirm_isolated_export=args.confirm_isolated_export,
            )
        else:
            if args.confirm_reviewed_audio:
                parser.error("Cannot declare human-reviewed audio without an attestation")
            result = export_verified(args.source,args.review,args.destination)
    else:
        if args.attestation or args.confirm_reviewed_audio or args.confirm_isolated_export:
            parser.error("Review confirmation flags may only be supplied with --destination")
        result = audit(args.source, args.review)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
