"""Repair only WAVs that fail strict narration fidelity QA.

The QA cache is keyed to WAV bytes, so unchanged passing slides are reused.
Never permit video assembly while a slide remains unverified.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

from .runner import blocks, load_microvid_env
from .tts import _chirp_say_with_watchdog, _gemini_say_with_watchdog, _tts_workspace_lock
from .tts_fidelity import build_report, write_report


def failing_slides(report: dict) -> list[int]:
    return [int(item["slide"]) for item in report["slides"] if item["status"] != "pass"]


def repair(folder: Path, *, model: str, threshold: float, provider: str,
           tts_model: str, voice: str, max_repairs: int = 2) -> dict:
    if max_repairs < 0:
        raise ValueError("max_repairs must be nonnegative")
    narrations = dict(blocks((folder / "script.txt").read_text(encoding="utf-8")))
    report = build_report(folder, model=model, threshold=threshold)
    write_report(folder, report)
    for round_number in range(1, max_repairs + 1):
        failed = failing_slides(report)
        if not failed:
            break
        print(f"[tts-qa-repair] round {round_number}/{max_repairs}: "
              f"regenerating only slides {failed}", flush=True)
        with _tts_workspace_lock(folder):
            for number in failed:
                if number not in narrations:
                    raise RuntimeError(f"No narration found for slide{number}")
                text = narrations[number]
                try:
                    if provider == "gemini":
                        payload = _gemini_say_with_watchdog(text, number, tts_model, voice)
                    elif provider == "chirp3":
                        payload = _chirp_say_with_watchdog(text, number, voice)
                    else:
                        raise ValueError(f"Unsupported TTS provider: {provider}")
                    if payload[:4] not in (b"RIFF", b"RF64") or len(payload) <= 44:
                        raise RuntimeError("TTS returned invalid WAV")
                    with tempfile.NamedTemporaryFile(
                        prefix=f".slide{number}.repair_", suffix=".wav",
                        dir=folder, delete=False
                    ) as stream:
                        staged = Path(stream.name)
                        stream.write(payload)
                    try:
                        staged.replace(folder / f"slide{number}.wav")
                    finally:
                        staged.unlink(missing_ok=True)
                    print(f"[tts-qa-repair] replaced slide{number}.wav", flush=True)
                except Exception as exc:
                    print(f"[tts-qa-repair] slide{number} regeneration failed: {exc}",
                          flush=True)
        # QA cache includes audio bytes: passing slides remain cached,
        # replaced slides must be independently listened to again.
        report = build_report(folder, model=model, threshold=threshold)
        write_report(folder, report)
        if failing_slides(report) and round_number < max_repairs:
            time.sleep(max(0, float(os.environ.get("MICROGEN_TTS_QA_REPAIR_DELAY_SECONDS", "15"))))
    remaining = failing_slides(report)
    if remaining:
        raise RuntimeError(f"TTS QA failed after {max_repairs} selective repair round(s); "
                           f"slides still blocked: {remaining}")
    print(f"[tts-qa-repair] all {len(report['slides'])} slides passed", flush=True)
    return report


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
    args = parser.parse_args(argv)
    from .tts_billing_guard import require_tts_cost_authorization
    # A repair can synthesize NEW audio; provenance checks cannot replace
    # an explicit provider-specific authorization for that expense.
    require_tts_cost_authorization(
        args.provider, gemini_approved=args.confirm_gemini_api_cost,
        cloud_approved=args.confirm_google_cloud_tts_cost)
    load_microvid_env()
    repair(args.folder, model=args.model, threshold=args.threshold,
           provider=args.provider, tts_model=args.tts_model, voice=args.voice,
           max_repairs=args.max_repairs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
