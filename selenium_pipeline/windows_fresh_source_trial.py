"""Bounded, independent Windows original-source trial, never a PDF-fix loop.

Use a fresh Serway/source-only PDF and an external, SHA-pinned trial directory.
The normal seven-stage runner is reused. Dry-run cannot send a model request;
one optional real *figures-only* browser attempt requires an explicit flag,
writes an attempt ledger before calling the provider, and cannot be resent.
TTS, video, publication and scholarly acceptance are outside this stage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, _new_atomic, _verified_json, require,
)

def _digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode("utf8")).hexdigest()


def _source_paths(source_root: Path, section: str) -> tuple[Path, Path]:
    require(re.fullmatch(r"[0-9]+\.[0-9]+", section) is not None,
            "Expected one numeric textbook section, e.g. 22.1")
    source = source_root / section.split(".")[0] / section / "source.pdf"
    require(source.is_file() and not source.is_symlink()
            and source.stat().st_size > 100,
            "A genuine, non-empty original source.pdf must exist")
    return source, source.parent


def run_trial(*, source_root: Path, section: str, trial_dir: Path,
              attempt_figures: bool = False,
              subprocess_run=None, timeout_seconds: int = 180) -> dict:
    require(os.name == "nt", "Only native Windows Dell-115 original trials")
    require(30 <= timeout_seconds <= 600,
            "One bounded attempt must have a finite 30-600 second deadline")
    source_root = Path(source_root).absolute()
    trial_dir = Path(trial_dir).absolute()
    require(source_root.is_dir() and not source_root.is_symlink()
            and trial_dir.is_dir() and not trial_dir.is_symlink()
            and not trial_dir.is_relative_to(source_root)
            and not source_root.is_relative_to(trial_dir),
            "External versioned Windows trial folder required")
    source, original_folder = _source_paths(source_root, section)
    original_sha = file_sha256(source)
    staged_root = trial_dir / "source_tree"
    staged = staged_root / section.split(".")[0] / section
    staged_source = staged / "source.pdf"
    require(not staged.is_symlink()
            and not staged_source.is_symlink(),
            "Unsafe staged source symlink")
    staged.mkdir(parents=True, exist_ok=True)
    if not staged_source.exists():
        with source.open("rb") as src, staged_source.open("xb") as dest:
            shutil.copyfileobj(src, dest)
    require(file_sha256(staged_source) == original_sha,
            "Trial source changed: refuse to overwrite/re-run")
    source_contract = {
        "schema_version": 1,
        "status": "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL",
        "source_path": str(source),
        "source_sha256": original_sha,
        "staged_source_path": str(staged_source),
        "stage_goal": "figures",
        "paid_tts_authorized": False,
        "student_publication_authorized": False,
    }
    locked = trial_dir / "fresh_trial_contract.json"
    if locked.exists() or locked.is_symlink():
        require(_verified_json(locked) == source_contract,
                "Different source version: start NEW fresh-source trial")
    else:
        _new_atomic(locked, source_contract)
    run = subprocess_run or subprocess.run
    command = [sys.executable, "-m", "selenium_pipeline",
               "--source-root", str(staged_root),
               "--subchapter", section, "--through-stage", "figures",
               "--communication-mode", "selenium"]
    result = {
        "schema_version": 1,
        "source_section": section,
        "original_source_sha256": original_sha,
        "staged_original_sha256": file_sha256(staged_source),
        "new_model_or_tts_calls": False,
        "student_publication_authorized": False,
        "new_video_rendered": False,
        "genuine_full_original_e2e_accepted": False,
    }
    if not attempt_figures:
        try:
            completed = run(command + ["--dry-run"], cwd=Path(__file__).resolve().parent.parent,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=min(timeout_seconds, 60))
            result["status"] = ("FRESH_SOURCE_SEVEN_STAGE_DRY_RUN_READY"
                                if completed.returncode == 0
                                else "FRESH_SOURCE_DRY_RUN_FAILED")
            result["dry_run_exit_code"] = completed.returncode
        except subprocess.TimeoutExpired:
            result["status"] = "FRESH_SOURCE_DRY_RUN_TIMEOUT"
        require(file_sha256(source) == original_sha
                and file_sha256(staged_source) == original_sha,
                "Original publisher source changed during dry run")
        return result
    attempt = trial_dir / "figures_attempt_started.json"
    if attempt.exists() or attempt.is_symlink():
        prior = _verified_json(attempt)
        require(prior == {"schema_version": 1,
                           "source_sha256": original_sha,
                           "stage": "figures",
                           "single_provider_attempt_only": True},
                "Untrusted previous figure-model attempt ledger")
        result["status"] = "PREVIOUS_PROVIDER_ATTEMPT_NOT_RESENT"
        return result
    # Persist the send-intent *before* invoking an unpredictable browser.
    # A crash, ambiguous send or timeout must NEVER be silently retried.
    _new_atomic(attempt, {
        "schema_version": 1, "source_sha256": original_sha,
        "stage": "figures", "single_provider_attempt_only": True,
    })
    try:
        completed = run(command, cwd=Path(__file__).resolve().parent.parent,
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=timeout_seconds)
        result["figure_stage_exit_code"] = completed.returncode
        result["status"] = ("FIGURES_STAGE_RETURNED_SUCCESS_NOT_FULL_LECTURE"
                            if completed.returncode == 0
                            else "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY")
    except subprocess.TimeoutExpired:
        result["status"] = "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY"
    except OSError:
        result["status"] = "FIGURES_EXECUTION_ERROR_NO_AUTO_RETRY"
    result["provider_figure_attempt_may_have_occurred"] = True
    # A Selenium browser may have sent a request even if the process failed.
    # Never claim zero model calls or a safely retryable failure.
    result["new_model_or_tts_calls"] = None
    result["new_tts_calls"] = False
    result["model_browser_submission_outcome"] = "UNVERIFIED"
    require(file_sha256(source) == original_sha
            and file_sha256(staged_source) == original_sha,
            "Original publisher source changed during figure stage")
    _new_atomic(trial_dir / "figures_attempt_result.json", result)
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--subchapter", required=True)
    ap.add_argument("--trial-dir", type=Path, required=True)
    ap.add_argument("--attempt-figures-once", action="store_true")
    ap.add_argument("--timeout-seconds", type=int, default=180)
    a = ap.parse_args(argv)
    try:
        result = run_trial(source_root=a.source_root, section=a.subchapter,
                           trial_dir=a.trial_dir,
                           attempt_figures=a.attempt_figures_once,
                           timeout_seconds=a.timeout_seconds)
    except CampaignRecoveryBlocked as exc:
        result = {"status": "FRESH_SOURCE_TRIAL_REJECTED", "reason": str(exc),
                  "student_publication_authorized": False}
        print(json.dumps(result, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in {
        "FRESH_SOURCE_SEVEN_STAGE_DRY_RUN_READY",
        "PREVIOUS_PROVIDER_ATTEMPT_NOT_RESENT",
        "FIGURES_STAGE_RETURNED_SUCCESS_NOT_FULL_LECTURE",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
