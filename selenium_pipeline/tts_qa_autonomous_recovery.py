"""Reuse prior selective TTS regeneration + QA to advance ordinary runner.

A source-locked PCM failure is routed through the existing TTS provider
watchdogs with a finite per-slide budget; no unrelated slides are regenerated.
Model-based phonetic/soundalike QA must ALSO pass before installing changed
WAVs in the internal *workspace*. Source PDFs and published lecture folders
are never modified here. Actual public release remains unauthorized.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import time

from .pcm_signal_integrity import inspect_pcm_signal, PCMIntegrityBlocked
from .runner import blocks
from .tts_auto_recovery_install import (
    install_verified, resume_pending, TTSRecoveryInstallBlocked,
)
from .tts_fidelity import build_report, write_report
from .tts_qa_repair import (
    _validate_originals, _new_review_snapshot, _tts_workspace_lock,
    _gemini_say_with_watchdog, _chirp_say_with_watchdog,
    failing_slides,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _damaged(audio: Path, numbers: list[int]) -> dict[int, str]:
    damaged = {}
    for n in numbers:
        path = audio / f"slide{n}.wav"
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"Untrusted original TTS audio: slide{n}")
        try:
            inspect_pcm_signal(path.read_bytes(), label=path.name)
        except (PCMIntegrityBlocked, ValueError) as exc:
            damaged[n] = str(exc)
    return damaged


def _save_receipt(review: Path, evidence: dict, originals: dict,
                  folder: Path, remaining: list[int]):
    evidence["proposed_remaining_failures"] = remaining
    evidence["candidate_wav_sha256"] = {
        name: _sha((review / name).read_bytes()) for name in originals
    }
    evidence["original_audio_modified"] = any(
        not (folder / name).is_file()
        or (folder / name).is_symlink()
        or _sha((folder / name).read_bytes()) != digest
        for name, digest in originals.items()
    )
    with (review / "review_only_receipt.json").open("x", encoding="utf8") as output:
        json.dump(evidence, output, indent=2, sort_keys=True)
        output.write("\n")
    if evidence["original_audio_modified"]:
        raise RuntimeError("Source TTS WAV changed during isolated repair")


def _reuse_recorded_repair(folder: Path, narrations: dict[int, str], *,
                           provider: str, model: str, tts_model: str,
                           voice: str, threshold: float,
                           max_repairs: int) -> dict | None:
    """Do not re-Send a completed or exhausted unchanged selective TTS job."""
    root = folder / ".tts_qa_review_candidates"
    if not root.exists():
        return None
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("Untrusted historical selective repair root")
    script_hash = _sha((folder / "script.txt").read_bytes())
    manifest_hash = _sha((folder / "tts_input_manifest.json").read_bytes())
    original_hashes = {
        f"slide{n}.wav": _sha((folder / f"slide{n}.wav").read_bytes())
        for n in narrations
    }
    for review in sorted(root.iterdir()):
        if review.is_symlink() or not review.is_dir():
            raise RuntimeError("Unsafe historical selective repair snapshot")
        intent = review / "automatic_internal_repair_intent.json"
        if not intent.is_file():
            # Historical review-only snapshots never requested automatic
            # internal reuse and must not be reinterpreted as such.
            continue
        if intent.is_symlink():
            raise RuntimeError("Unsafe selective repair intent symlink")
        marker = json.loads(intent.read_text(encoding="utf8"))
        if (marker.get("source_script_sha256") != script_hash
                or marker.get("source_manifest_sha256") != manifest_hash
                or marker.get("original_wav_sha256") != original_hashes
                or marker.get("provider") != provider
                or marker.get("tts_model") != tts_model
                or marker.get("voice") != voice
                or marker.get("fidelity_model") != model
                or marker.get("threshold") != threshold):
            continue
        script = review / "script.txt"
        manifest = review / "tts_input_manifest.json"
        if (not script.is_file() or script.is_symlink()
                or not manifest.is_file() or manifest.is_symlink()
                or _sha(script.read_bytes()) != script_hash
                or _sha(manifest.read_bytes()) != manifest_hash):
            continue
        evidence_path = review / "review_only_receipt.json"
        if not evidence_path.is_file() or evidence_path.is_symlink():
            # Identical source and original WAVs but unknown provider Send
            # outcome. Never replay an uncertain paid request.
            raise RuntimeError("Unresolved previous selective TTS attempt "
                               f"without completed receipt at {review}; "
                               "no duplicate provider Send")
        record = json.loads(evidence_path.read_text(encoding="utf8"))
        if (record.get("automatic_internal_repair_requested") is not True
                or record.get("original_audio_modified") is not False
                or record.get("source_script_sha256") != script_hash
                or record.get("source_manifest_sha256") != manifest_hash
                or record.get("original_wav_sha256") != original_hashes
                or record.get("provider") != provider
                or record.get("tts_model") != tts_model
                or record.get("voice") != voice
                or record.get("fidelity_model") != model
                or record.get("threshold") != threshold):
            continue
        remaining = record.get("proposed_remaining_failures")
        if remaining == []:
            # The standard historical audit rechecks provider/voice, exact
            # WAV+script hashes, every attempt and real post-TTS QA verdict.
            # No new Gemini call is authorized for the same approved source.
            install_verified(folder, review)
            print("[tts-auto-recovery] reused previously accepted candidate "
                  "without another TTS or listener request", flush=True)
            return json.loads((folder / "tts_fidelity_report.json").read_text("utf8"))
        attempts = record.get("rejected_attempts", []) + record.get(
            "proposed_replacements", [])
        for number in remaining or []:
            rounds = {row.get("round") for row in attempts
                      if isinstance(row, dict) and row.get("slide") == number
                      and type(row.get("round")) is int}
            if len(rounds) >= max_repairs:
                raise RuntimeError("Previous identical selective TTS repair "
                                   f"exhausted {max_repairs} rounds for slide {number}; "
                                   "no repeated provider requests on unchanged evidence")
    return None


def recover(*, folder: Path, model: str, threshold: float, provider: str,
            tts_model: str, voice: str, max_repairs: int = 2) -> dict:
    """Finite, source/voice-verified selective repair and normal-stage return."""
    folder = Path(folder).absolute()
    if type(max_repairs) is not int or not 0 <= max_repairs <= 3:
        raise ValueError("Automated per-slide TTS repair budget must be 0..3")
    # If the previous worker died during safe candidate installation, finish
    # exactly that checkpoint with ZERO more model or provider calls.
    resumed = resume_pending(folder)
    if resumed is not None:
        report = json.loads((folder / "tts_fidelity_report.json").read_text("utf8"))
        if (report.get("model") != model or
                report.get("threshold_percent") != threshold):
            raise RuntimeError(
                "Recovered previous repair under different QA model/threshold; "
                "do not accept stale phonetic QA")
        print("[tts-auto-recovery] recovered an interrupted accepted install; "
              "continuing ordinary pipeline without TTS regeneration", flush=True)
        return report
    narrations = dict(blocks((folder / "script.txt").read_text(encoding="utf8")))
    if not narrations:
        raise RuntimeError("Source narration has no slide segments")
    recorded = _reuse_recorded_repair(
        folder, narrations, provider=provider, model=model,
        tts_model=tts_model, voice=voice, threshold=threshold,
        max_repairs=max_repairs)
    if recorded is not None:
        return recorded
    damaged = _damaged(folder, list(narrations))
    if damaged:
        print(f"[tts-auto-recovery] detected objectively defective slides "
              f"{sorted(damaged)}; skip costly acoustic review of broken PCM",
              flush=True)
        report = None
        failed = sorted(damaged)
    else:
        report = build_report(folder, model=model, threshold=threshold)
        failed = failing_slides(report)
        if not failed:
            write_report(folder, report)
            return report
    if max_repairs == 0:
        raise RuntimeError(f"TTS failures without allowed repair budget: {failed}")
    # Historic mechanism performs strong source-script/effective-voice and
    # all-slides fallback journal verification, BEFORE any paid regeneration.
    script, manifest, originals = _validate_originals(
        folder, narrations, provider=provider, tts_model=tts_model, voice=voice)
    review = _new_review_snapshot(folder, script, manifest, originals)
    # Save the immutable retry identity BEFORE the first provider call.
    # If the worker dies after an uncertain Send, a restart cannot silently
    # duplicate it. Existing legacy review-only snapshots are unaffected.
    intent = {"schema_version": 1, "source_script_sha256": _sha(script),
              "source_manifest_sha256": _sha(manifest),
              "original_wav_sha256": originals,
              "provider": provider, "tts_model": tts_model, "voice": voice,
              "fidelity_model": model, "threshold": threshold}
    with (review / "automatic_internal_repair_intent.json").open("x",encoding="utf8") as output:
        json.dump(intent, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    # The historical phonetic QA cache keys already include WAV bytes, script,
    # model, QA prompt/policy and threshold. Copy only whitelisted, regular
    # per-slide receipts; the listener will revalidate every key before reuse.
    # Without this, a one-slide repair caused 13 unnecessary Gemini reviews.
    old_cache = folder / ".tts_qa_cache"
    if old_cache.is_dir() and not old_cache.is_symlink():
        new_cache = review / ".tts_qa_cache"
        new_cache.mkdir()
        for number in narrations:
            prior = old_cache / f"slide{number}.json"
            if prior.is_file() and not prior.is_symlink():
                shutil.copyfile(prior, new_cache / prior.name)
    evidence = {
        "status": "REVIEW_ONLY_UNPUBLISHED",
        "source_script_sha256": _sha(script),
        "source_manifest_sha256": _sha(manifest),
        "original_wav_sha256": originals,
        "provider": provider, "tts_model": tts_model, "voice": voice,
        "fidelity_model": model, "threshold": threshold,
        "proposed_replacements": [],
        "rejected_attempts": [],
        "academic_approved": False,
        "video_publication_approved": False,
        "original_audio_modified": False,
        "automatic_internal_repair_requested": True,
    }
    remaining = failed
    try:
        for round_number in range(1, max_repairs+1):
            current = sorted(set(remaining))
            print(f"[tts-auto-recovery] round {round_number}/{max_repairs}, "
                  f"only slides {current}", flush=True)
            # Existing per-workspace lock prevents competing paid requests.
            with _tts_workspace_lock(folder):
                for number in current:
                    try:
                        if provider == "gemini":
                            payload = _gemini_say_with_watchdog(
                                narrations[number], number, tts_model, voice,
                                attempts_override=1)
                        elif provider == "chirp3":
                            payload = _chirp_say_with_watchdog(
                                narrations[number], number, voice)
                        else:
                            raise ValueError("Unapproved TTS provider")
                        # Preserve every byte returned, even rejected audio,
                        # but a failed signal never becomes the chosen WAV.
                        attempted = review / f"attempt{round_number}_slide{number}.wav"
                        with attempted.open("xb") as stream:
                            stream.write(payload)
                        try:
                            inspect_pcm_signal(payload, label=attempted.name)
                        except (PCMIntegrityBlocked, ValueError) as exc:
                            evidence["rejected_attempts"].append({
                                "slide": number, "round": round_number,
                                "reason": str(exc),
                                "wav_sha256": _sha(payload)})
                            print(f"[tts-auto-recovery] reject damaged replacement "
                                  f"for slide {number}", flush=True)
                            continue
                        target = review / f"slide{number}.wav"
                        if target.is_symlink():
                            raise RuntimeError("Unsafe candidate audio symlink")
                        target.write_bytes(payload)
                        evidence["proposed_replacements"].append({
                            "slide": number, "round": round_number,
                            "wav_sha256": _sha(payload)})
                    except Exception as exc:
                        evidence["rejected_attempts"].append({
                            "slide": number, "round": round_number,
                            "reason": type(exc).__name__})
                        print(f"[tts-auto-recovery] bounded provider exception "
                              f"on slide {number}: {type(exc).__name__}",
                              flush=True)
            # First repair obvious PCM damage across the entire snapshot.
            still_damaged = _damaged(review, list(narrations))
            if still_damaged:
                remaining = sorted(still_damaged)
            else:
                # Reuse cached original Gemini QA receipts for unchanged WAVs.
                # Changed WAV hashes force fresh source-aware phonetic QA.
                report = build_report(review, model=model, threshold=threshold)
                write_report(review, report)
                remaining = failing_slides(report)
            if not remaining:
                break
            if round_number < max_repairs:
                time.sleep(max(0, min(30, float(os.environ.get(
                    "MICROGEN_TTS_QA_REPAIR_DELAY_SECONDS", "15")))))
    finally:
        _save_receipt(review, evidence, originals, folder, remaining)
    if remaining:
        raise RuntimeError("TTS automatic selective repair exhausted its finite "
                           f"budget for slides {remaining}; originals retained; "
                           f"diagnostic review at {review}")
    if not evidence["proposed_replacements"]:
        raise RuntimeError("No verified new selective audio candidate")
    # Strict historic QA receipt validates all talk-to-text judgments and
    # provider/voice/attempt history. New installer rechecks actual PCM signal,
    # locks original hashes and retains full rollback originals and receipts.
    installed = install_verified(folder, review)
    print("[tts-auto-recovery] source-bound technical repair and phonetic QA "
          f"passed for {sorted(installed['changed_wavs'])}; "
          "resuming next normal runner stage", flush=True)
    return report
