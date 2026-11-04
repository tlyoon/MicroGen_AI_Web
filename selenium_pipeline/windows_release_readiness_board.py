"""Read-only native Windows cumulative stack/release-readiness gate.

This checks code ancestry and source-bound recovery evidence. It NEVER
merges/rebases the large historical draft-PR stack, creates tags, publishes
to students, or treats CI-green/dry-run as genuine source-to-video acceptance.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from .original_multisource_recovery_campaign import CampaignRecoveryBlocked, require
from .windows_recovery_integrity import audit


def _git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=30)
    require(p.returncode == 0,
            "Git read-only inspection failed: " + " ".join(args))
    return p.stdout.strip()


def _windows_ci_only(repo: Path) -> dict:
    folder = repo / ".github" / "workflows"
    require(folder.is_dir(), "GitHub Windows reliability workflow folder missing")
    workflows = sorted([*folder.glob("*.yml"), *folder.glob("*.yaml")])
    require(workflows, "No GitHub Windows workflow discovered")
    non_windows = []
    for workflow in workflows:
        require(workflow.is_file() and not workflow.is_symlink(),
                "Unsafe workflow definition")
        for line in workflow.read_text(encoding="utf8").splitlines():
            text = line.strip()
            if re.search(r"^runs-on\s*:", text):
                if "windows-" not in text.lower():
                    non_windows.append({"workflow": workflow.name,
                                        "declaration": text})
    return {"examined_workflows": len(workflows),
            "all_runner_declarations_windows": not non_windows,
            "non_windows_runner_declarations": non_windows}


def inspect_worker_install(*, repo: Path,
                           python: Path | None) -> dict:
    """Read-only, exact interpreter worker import/venv/pip qualification."""
    if python is None:
        return {"status": "NO_ISOLATED_WINDOWS_WORKER_SELECTED",
                "passed": False}
    path = Path(python).absolute()
    root = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    require(path.name.lower() == "python.exe"
            and path.parent.name.lower() == "scripts"
            and root.is_dir() and path.is_relative_to(root)
            and path.is_file() and not path.is_symlink(),
            "Unsafe or missing isolated Windows worker interpreter")
    try:
        result = subprocess.run(
            [str(path), "-m", "selenium_pipeline.windows_install_smoke"],
            cwd=repo, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120)
        data = json.loads(result.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {"status": "WINDOWS_ISOLATED_WORKER_SMOKE_FAILED",
                "passed": False}
    passed = (result.returncode == 0
              and data.get("status") == "WINDOWS_ISOLATED_WORKER_INSTALL_PASS"
              and data.get("isolated_virtual_environment") is True
              and data.get("pip_dependency_check_pass") is True
              and data.get("model_or_paid_tts_called") is False
              and data.get("student_publication_authorized") is False
              and data.get("sourcebound_full_lecture_production_certified")
              is False)
    return {"status": data.get("status", "UNKNOWN_WORKER_SMOKE"),
            "passed": passed,
            "tooling_only_not_video_acceptance": True}


def inspect_release(*, repo: Path, jobs_dir: Path,
                    fresh_trial_dir: Path,
                    worker_python: Path | None = None,
                    reuse_scoped_pr362: bool = False,
                    reviewed_media_dir: Path | None = None) -> dict:
    require(os.name == "nt", "Native Windows-only release readiness")
    repo = Path(repo).absolute()
    require(repo.is_dir() and (repo / ".git").exists(),
            "Existing isolated Windows Git checkout required")
    branch = _git(repo, "branch", "--show-current")
    head = _git(repo, "rev-parse", "HEAD")
    local_main = _git(repo, "rev-parse", "main")
    tracked_origin_main = _git(repo, "rev-parse", "origin/main")
    ahead = int(_git(repo, "rev-list", "--count", "origin/main..HEAD"))
    behind = int(_git(repo, "rev-list", "--count", "HEAD..origin/main"))
    dirty = bool(_git(repo, "status", "--porcelain"))
    ci = _windows_ci_only(repo)
    recovery = audit(jobs_dir=jobs_dir, fresh_trial_dir=fresh_trial_dir)
    worker = inspect_worker_install(repo=repo, python=worker_python)
    prior_reference = None
    if reuse_scoped_pr362:
        from .windows_scoped_prior_full_media_acceptance import (
            verify_scoped, sources_at_checkpoint,
        )
        historical_root = Path(os.environ["LOCALAPPDATA"]) / "MicroGen_AI_Web_Checkpoints"
        prior_reference = verify_scoped(**sources_at_checkpoint(historical_root))
    safe_checkpoint = (recovery["source_job_receipts_security_or_version_rejected"] == 0
                       and recovery["fresh_original_publisher_and_stage_sha_verified"]
                       and not recovery["automatic_provider_retry_authorized"])
    media = {
        "status": "NO_SOURCEBOUND_REVIEWED_MP4_EVIDENCE_SELECTED",
        "technical_sourcebound_mp4_verified": False,
        "new_model_or_tts_calls": False,
        "student_publication_authorized": False,
    }
    if reviewed_media_dir is not None:
        from .windows_lecture_media_handoff import (
            inspect_reviewed_media_for_release,
        )
        try:
            media = inspect_reviewed_media_for_release(
                trial_dir=fresh_trial_dir, media_dir=reviewed_media_dir)
        except (CampaignRecoveryBlocked, ValueError, OSError) as exc:
            media = {
                "status": "SOURCEBOUND_REVIEWED_MP4_EVIDENCE_REJECTED",
                "reason": str(exc),
                "technical_sourcebound_mp4_verified": False,
                "new_model_or_tts_calls": False,
                "student_publication_authorized": False,
            }
    gates = {
        "native_windows_only": True,
        "current_worktree_clean": not dirty,
        "tracked_origin_main_ancestor_no_divergence": behind == 0,
        "windows_ci_workflows_only": ci["all_runner_declarations_windows"],
        "source_checkpoint_integrity": safe_checkpoint,
        "clean_isolated_windows_worker_install_verified": worker["passed"],
        "github_ci_exact_final_sha_independently_verified": False,
        "at_least_one_full_original_source_reference_verified":
            prior_reference is not None,
        "reviewed_sourcebound_mp4_technical_integrity_verified":
            media["technical_sourcebound_mp4_verified"] is True,
        "second_distinct_new_original_full_lecture_accepted": False,
        "entire_historical_stack_dependency_and_review_completed": False,
        "production_installation_smoke_and_release_approval": False,
    }
    # Never promote historical PR362 scope to a new generated source or infer
    # video acceptance from a successful Windows test run or dry-run.
    ready = all(gates.values())
    return {
        "schema_version": 1,
        "status": ("WINDOWS_RELEASE_CANDIDATE_ELIGIBLE_FOR_FORMAL_APPROVAL"
                   if ready else "WINDOWS_RELEASE_CANDIDATE_BLOCKED"),
        "repository_head_sha": head,
        "local_main_sha": local_main,
        "tracked_origin_main_sha": tracked_origin_main,
        "local_main_is_stale_informational_only":
            local_main != tracked_origin_main,
        "worker_installation": worker,
        "prior_scoped_original_acceptance": prior_reference,
        "reviewed_sourcebound_mp4_evidence": media,
        "branch": branch,
        "commit_comparison_ref": "origin/main (last fetched)",
        "commits_ahead_of_tracked_origin_main": ahead,
        "commits_behind_tracked_origin_main": behind,
        "git_worktree_has_changes": dirty,
        "workflows": ci,
        "recovery": {
            "source_jobs_verified":
                recovery["source_job_receipts_current_and_sha_verified"],
            "source_jobs_rejected":
                recovery["source_job_receipts_security_or_version_rejected"],
            "fresh_original_figure_attempt_state":
                recovery["fresh_original_figure_attempt_state"],
            "automatic_provider_retry_authorized": False,
        },
        "required_release_gates": gates,
        "release_candidate_ready": ready,
        "may_merge_historical_stack_automatically": False,
        "new_model_or_tts_calls": False,
        "new_video_rendered": False,
        "student_publication_authorized": False,
        "next_actions": [
            "Fetch and verify current origin/main before interpreting commit distance",
            "Independent exact-head GitHub Windows CI review",
            "Existing PR362 one-source accepted evidence is reusable only at matching SHA",
            "Recheck an exact SHA-bound reviewed MP4 using --reviewed-media-dir without encoding",
            "Qualify a DISTINCT new original-source full synchronized multimedia lecture",
            f"Review stacked draft dependencies in safe batches; never merge {ahead} commits blindly",
            "Clean Windows installation smoke and separate explicit student release authorization",
        ],
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    p.add_argument("--jobs-dir", type=Path, required=True)
    p.add_argument("--fresh-trial-dir", type=Path, required=True)
    p.add_argument("--worker-python", type=Path,
                   help="Optional exact isolated Windows venv Python executable")
    p.add_argument("--reuse-scoped-pr362", action="store_true",
                   help="SHA-import already accepted PR362 review-only source/media as ONE historic example")
    p.add_argument("--reviewed-media-dir", type=Path,
                   help="Read-only revalidate PR506 original-source reviewed MP4 receipt and bytes")
    a = p.parse_args(argv)
    try:
        result = inspect_release(repo=a.repo, jobs_dir=a.jobs_dir,
                                 fresh_trial_dir=a.fresh_trial_dir,
                                 worker_python=a.worker_python,
                                 reuse_scoped_pr362=a.reuse_scoped_pr362,
                                 reviewed_media_dir=a.reviewed_media_dir)
    except (CampaignRecoveryBlocked, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "WINDOWS_RELEASE_BOARD_REJECTED",
                          "reason": str(exc),
                          "student_publication_authorized": False}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    # A blocked release is a correctly reported state; exit 0 for read-only
    # inspection, never return a code that could mean authorization to publish.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
