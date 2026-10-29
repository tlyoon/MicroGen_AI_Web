"""Non-destructive review of proposed selective TTS QA repairs.

Never replace an original slide WAV as a side effect of automated QA.
Repaired WAVs are stored in an isolated review-only snapshot. Real publication
requires a separate, audited and independently approved handoff.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
import uuid
from pathlib import Path

from .runner import blocks, load_microvid_env
from .tts import _chirp_say_with_watchdog, _gemini_say_with_watchdog, _tts_workspace_lock
from .tts_fidelity import build_report, write_report


def failing_slides(report: dict) -> list[int]:
    return [int(item["slide"]) for item in report["slides"] if item["status"] != "pass"]


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _validate_originals(
    folder: Path, narrations: dict[int, str], *,
    provider: str, tts_model: str, voice: str,
) -> tuple[bytes, bytes, dict[str, str]]:
    """Reject unproven model/voice/text before *any* replacement API request."""
    script_path = folder / "script.txt"
    manifest_path = folder / "tts_input_manifest.json"
    if (script_path.is_symlink() or manifest_path.is_symlink()
            or not manifest_path.is_file()):
        raise RuntimeError("Original TTS manifest is missing or unsafe; no repair request")
    script = script_path.read_bytes()
    manifest = manifest_path.read_bytes()
    try:
        doc = json.loads(manifest)
        primary = doc["primary"]
        rows = doc["slides"]
        bound = {int(row["slide"]): row for row in rows}
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise RuntimeError("Original TTS manifest is invalid; no repair request") from exc
    if (primary != {"provider": provider, "model": tts_model, "voice": voice}
            or len(bound) != len(rows) or set(bound) != set(narrations)):
        raise RuntimeError("Original TTS provider/model/voice/slide identity mismatch")
    fallback_used = doc.get("all_slides_one_effective_voice") is True
    if fallback_used:
        from .tts_attempt_evidence import AttemptEvidence
        AttemptEvidence.verify_saved(
            folder, list(narrations.items()), doc.get("attempt_evidence"))
        actual = {"provider": provider, "model": tts_model, "voice": voice}
        requested = doc.get("requested_primary")
        chain = doc.get("fallback_chain")
        if (not isinstance(requested, dict)
                or requested.get("provider") != "gemini"
                or requested.get("model") != "gemini-3.8-flash-lite-tts"
                or requested.get("voice") != "Kore"
                or actual not in (
                    {"provider": "gemini", "model": "gemini-3.8-flash-tts", "voice": "Kore"},
                    {"provider": "chirp3", "model": "chirp3-hd",
                     "voice": "en-US-Chirp3-HD-Corey"})):
            raise RuntimeError("Unrecognized fallback provider, voice or original identity")
        if chain != (["gemini-3.8-flash-lite-tts"] if provider == "gemini"
                     else ["gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"]):
            raise RuntimeError("Incomplete Gemini retry/fallback history")
    originals: dict[str, str] = {}
    for number, expected in narrations.items():
        entry = bound[number]
        if (entry.get("tts_text") != expected
                or entry.get("provider") != provider
                or entry.get("model") != tts_model
                or entry.get("voice") != voice
                or entry.get("fallback_used") is not fallback_used
                or (fallback_used and
                    (entry.get("primary_model") != "gemini-3.8-flash-lite-tts"
                     or entry.get("primary_voice") != "Kore"))):
            raise RuntimeError("Original TTS narration or model provenance mismatch")
        item = folder / f"slide{number}.wav"
        if not item.is_file() or item.is_symlink():
            raise RuntimeError(f"Missing/unsafe original audio for slide{number}")
        wav = item.read_bytes()
        if len(wav) <= 44 or wav[:4] not in (b"RIFF", b"RF64"):
            raise RuntimeError(f"Invalid original WAV for slide{number}")
        originals[item.name] = _sha(wav)
    return script, manifest, originals


def _new_review_snapshot(
    folder: Path, script: bytes, manifest: bytes, originals: dict[str, str],
) -> Path:
    """Create a new, isolated folder. Never write repaired audio to originals."""
    root = folder / ".tts_qa_review_candidates"
    if root.is_symlink():
        raise RuntimeError("Unsafe symlink for TTS QA review root")
    root.mkdir(exist_ok=True)
    review = root / uuid.uuid4().hex
    review.mkdir()
    with (review / "script.txt").open("xb") as out:
        out.write(script)
    with (review / "tts_input_manifest.json").open("xb") as out:
        out.write(manifest)
    for filename, digest in originals.items():
        source = folder / filename
        if source.is_symlink() or _sha(source.read_bytes()) != digest:
            raise RuntimeError("Original audio changed during QA snapshot; stop")
        with (review / filename).open("xb") as out:
            out.write(source.read_bytes())
    return review


def repair(folder: Path, *, model: str, threshold: float, provider: str,
           tts_model: str, voice: str, max_repairs: int = 2) -> dict:
    """Propose repairs for review; never auto-promote or overwrite original WAVs."""
    if max_repairs < 0:
        raise ValueError("max_repairs must be nonnegative")
    narrations = dict(blocks((folder / "script.txt").read_text(encoding="utf-8")))
    initial_report = build_report(folder, model=model, threshold=threshold)
    failed = failing_slides(initial_report)
    if not failed:
        # No replacement is needed; retain the existing QA-only behavior.
        write_report(folder, initial_report)
        print(f"[tts-qa-repair] original audio already passed QA; no replacement")
        return initial_report
    if max_repairs == 0:
        raise RuntimeError(
            f"TTS QA failed; slides still blocked: {failed}; no repair authorized"
        )
    # Before making any new paid request, verify immutable input identity
    # against the manifest created by the initial TTS stage.
    script, manifest, originals = _validate_originals(
        folder, narrations, provider=provider, tts_model=tts_model, voice=voice,
    )
    review = _new_review_snapshot(folder, script, manifest, originals)
    evidence = {
        "status": "REVIEW_ONLY_UNPUBLISHED",
        "source_script_sha256": _sha(script),
        "source_manifest_sha256": _sha(manifest),
        "original_wav_sha256": originals,
        "provider": provider, "tts_model": tts_model, "voice": voice,
        "fidelity_model": model, "threshold": threshold,
        "proposed_replacements": [],
        "academic_approved": False,
        "video_publication_approved": False,
        "original_audio_modified": False,
    }
    report = initial_report
    try:
        for round_number in range(1, max_repairs + 1):
            failed = failing_slides(report)
            if not failed:
                break
            print(
                f"[tts-qa-repair] review-only round {round_number}/{max_repairs}: "
                f"slides {failed}", flush=True,
            )
            # Serialize against other TTS writers in this local staging area,
            # but never update the original completed slideN.wav files.
            with _tts_workspace_lock(folder):
                for number in failed:
                    if number not in narrations:
                        raise RuntimeError(f"No narration for slide{number}")
                    try:
                        if provider == "gemini":
                            payload = _gemini_say_with_watchdog(
                                narrations[number], number, tts_model, voice)
                        elif provider == "chirp3":
                            payload = _chirp_say_with_watchdog(
                                narrations[number], number, voice)
                        else:
                            raise ValueError("Unapproved TTS provider")
                        if len(payload) <= 44 or payload[:4] not in (b"RIFF", b"RF64"):
                            raise RuntimeError("TTS returned invalid WAV")
                        # Keep each generated attempt separately; update only
                        # the copy in the review snapshot, not the source.
                        attempt = review / f"attempt{round_number}_slide{number}.wav"
                        with attempt.open("xb") as stream:
                            stream.write(payload)
                        target = review / f"slide{number}.wav"
                        if target.is_symlink():
                            raise RuntimeError("Unsafe review-only target symlink")
                        with target.open("wb") as stream:
                            stream.write(payload)
                        evidence["proposed_replacements"].append({
                            "slide": number, "round": round_number,
                            "wav_sha256": _sha(payload),
                        })
                    except Exception as exc:
                        print(
                            "[tts-qa-repair] review-only slide"
                            f"{number} failed: {type(exc).__name__}",
                            flush=True,
                        )
            report = build_report(review, model=model, threshold=threshold)
            write_report(review, report)
            if failing_slides(report) and round_number < max_repairs:
                time.sleep(max(0, float(os.environ.get(
                    "MICROGEN_TTS_QA_REPAIR_DELAY_SECONDS", "15"))))
    finally:
        evidence["proposed_remaining_failures"] = failing_slides(report)
        evidence["candidate_wav_sha256"] = {
            name: _sha((review / name).read_bytes()) for name in originals
        }
        evidence["original_audio_modified"] = any(
            not (folder / name).is_file()
            or (folder / name).is_symlink()
            or _sha((folder / name).read_bytes()) != digest
            for name, digest in originals.items()
        )
        with (review / "review_only_receipt.json").open("x", encoding="utf-8") as out:
            json.dump(evidence, out, indent=2, sort_keys=True)
            out.write("\n")
    if evidence["original_audio_modified"]:
        raise RuntimeError("Original TTS audio changed externally during review")
    remaining = failing_slides(report)
    if remaining:
        raise RuntimeError(
            f"TTS QA still blocked: {remaining}; candidate preserved for review at {review}"
        )
    # Deliberately fail the runner's TTS QA stage; a passing synthetic or
    # automated review does not authorize replacing published audio.
    raise RuntimeError(
        f"TTS QA repair candidate requires independent review before publication: {review}"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--provider", choices=("gemini", "chirp3"), required=True)
    parser.add_argument("--tts-model", required=True)
    parser.add_argument("--voice", required=True)
    parser.add_argument("--max-repairs", type=int, default=2)
    parser.add_argument("--confirm-gemini-api-cost", action="store_true")
    parser.add_argument("--confirm-google-cloud-tts-cost", action="store_true")
    parser.add_argument("--routine-production-gemini", action="store_true",
                        help="Existing standing approval for routine Gemini production")
    parser.add_argument("--conditional-cloud-fallback", action="store_true",
                        help="Only the verified Lite->Flash->Chirp production fallback")
    args = parser.parse_args(argv)
    from .tts_billing_guard import require_tts_cost_authorization
    # A repair can synthesize NEW audio; provenance checks cannot replace
    # an explicit provider-specific authorization for that expense.
    require_tts_cost_authorization(
        args.provider, gemini_approved=args.confirm_gemini_api_cost,
        cloud_approved=args.confirm_google_cloud_tts_cost,
        routine_gemini=(args.routine_production_gemini or args.provider == "gemini"),
        conditional_cloud_fallback=args.conditional_cloud_fallback)
    if args.conditional_cloud_fallback:
        if args.provider != "chirp3":
            raise RuntimeError("Conditional Cloud flag requires Cloud provider")
        manifest_path = args.folder / "tts_input_manifest.json"
        if not manifest_path.is_file() or manifest_path.is_symlink():
            raise RuntimeError("Conditional Cloud requires an original TTS manifest")
        history = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (history.get("all_slides_one_effective_voice") is not True
                or history.get("fallback_chain") != [
                    "gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"]
                or history.get("primary") != {
                    "provider": "chirp3", "model": "chirp3-hd",
                    "voice": "en-US-Chirp3-HD-Corey"}):
            raise RuntimeError("Cloud TTS conditional fallback history is not verified")
        from .tts_attempt_evidence import AttemptEvidence
        actual_script = (args.folder / "script.txt").read_text(encoding="utf-8")
        AttemptEvidence.verify_saved(
            args.folder, blocks(actual_script), history.get("attempt_evidence"))
    load_microvid_env()
    repair(args.folder, model=args.model, threshold=args.threshold,
           provider=args.provider, tts_model=args.tts_model, voice=args.voice,
           max_repairs=args.max_repairs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
