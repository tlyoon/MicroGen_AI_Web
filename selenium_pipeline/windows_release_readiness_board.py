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


def _autonomous_qa_matches_distinct_second_source(
    autonomous_qa: dict, second_candidate: dict,
) -> bool:
    """Never transfer AI evidence to a different source or publish a pilot."""
    return bool(
        type(autonomous_qa) is dict
        and type(second_candidate) is dict
        and autonomous_qa.get("status") ==
            "AI_SOURCE_SPEECH_AND_SYNC_MEDIA_TECHNICAL_QA_VERIFIED"
        and autonomous_qa.get("autonomous_scoped_technical_qa_accepted") is True
        and autonomous_qa.get("student_publication_authorized") is False
        and second_candidate.get(
            "technical_second_source_candidate_ready_for_academic_review") is True
        and second_candidate.get("distinct_original_source_sha256_verified") is True
        and autonomous_qa.get("source_sha256") ==
            second_candidate.get("candidate_source_sha256")
        and second_candidate.get("historical_source_sha256")
            != second_candidate.get("candidate_source_sha256")
    )


def inspect_release(*, repo: Path, jobs_dir: Path,
                    fresh_trial_dir: Path,
                    worker_python: Path | None = None,
                    reuse_scoped_pr362: bool = False,
                    reviewed_media_dir: Path | None = None,
                    include_stack_batches: bool = False,
                    verify_exact_head_ci_online: bool = False,
                    github_repository: str = "tlyoon/MicroGen_AI_Web",
                    audit_open_pr_stack_online: bool = False,
                    autonomous_qa_inputs: dict | None = None) -> dict:
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
    from .windows_second_source_candidate import compare_source_provenance
    second_candidate = compare_source_provenance(
        historic=prior_reference, candidate=media)
    # The owner's current contract uses autonomous AI source/audio/video QA.
    # This separate read-only path revalidates real source, AI review, ASR
    # receipts and pixel-verified MP4; never fabricates human approval.
    autonomous_qa = {
        "status": "AUTONOMOUS_AI_SOURCE_SPEECH_MEDIA_QA_NOT_REQUESTED",
        "autonomous_scoped_technical_qa_accepted": False,
        "student_publication_authorized": False,
    }
    if autonomous_qa_inputs is not None:
        from .windows_autonomous_lecture_qa import inspect as inspect_ai
        try:
            autonomous_qa = inspect_ai(**autonomous_qa_inputs)
        except (CampaignRecoveryBlocked, OSError, ValueError, TypeError,
                KeyError, json.JSONDecodeError) as error:
            autonomous_qa = {
                "status": "AUTONOMOUS_AI_SOURCE_SPEECH_MEDIA_QA_BLOCKED",
                "reason_type": type(error).__name__,
                "autonomous_scoped_technical_qa_accepted": False,
                "student_publication_authorized": False,
            }
    # Technical AI evidence applies only to the exact independently
    # media-verified SHA-distinct second original. It does not independently
    # prove voice identity, diagram semantics or student-release consent.
    ai_candidate_match = _autonomous_qa_matches_distinct_second_source(
        autonomous_qa, second_candidate,
    )
    stack_plan = {
        "status": "NO_BOUNDED_STACK_REVIEW_REQUESTED",
        "historical_stack_review_completed": False,
        "automatic_merge_or_release_authorized": False,
        "student_publication_authorized": False,
    }
    if include_stack_batches:
        from .windows_historical_stack_batch_plan import plan_stack
        stack_plan = plan_stack(repo=repo)
    github_ci = {
        "status": "EXACT_HEAD_ONLINE_CI_CHECK_NOT_REQUESTED",
        "exact_head_windows_ci_verified": False,
        "student_publication_authorized": False,
    }
    if verify_exact_head_ci_online:
        from .windows_exact_head_github_ci import inspect_ci
        github_ci = inspect_ci(
            repository=github_repository, head_sha=head,
            tracked_main_sha=tracked_origin_main)
    open_pr_catalog = {
        "status": "LIVE_OPEN_PR_STACK_METADATA_NOT_REQUESTED",
        "historical_stack_fully_reviewed_or_approved": False,
        "may_merge_automatically": False,
    }
    if audit_open_pr_stack_online:
        from .windows_github_pr_stack_readonly_audit import audit as pr_audit
        open_pr_catalog = pr_audit(
            repository=github_repository,
            expected_latest_head_sha=head)
    gates = {
        "native_windows_only": True,
        "current_worktree_clean": not dirty,
        "tracked_origin_main_ancestor_no_divergence": behind == 0,
        "windows_ci_workflows_only": ci["all_runner_declarations_windows"],
        "source_checkpoint_integrity": safe_checkpoint,
        "clean_isolated_windows_worker_install_verified": worker["passed"],
        "github_ci_exact_final_sha_independently_verified":
            github_ci["exact_head_windows_ci_verified"] is True,
        "github_live_origin_main_freshness_verified":
            github_ci.get("remote_tracked_main_matches_current_github") is True,
        "at_least_one_full_original_source_reference_verified":
            prior_reference is not None,
        "reviewed_sourcebound_mp4_technical_integrity_verified":
            media["technical_sourcebound_mp4_verified"] is True,
        "second_distinct_original_technical_candidate_verified":
            second_candidate["technical_second_source_candidate_ready_for_academic_review"],
        "bounded_historical_stack_review_plan_available":
            stack_plan["status"] ==
            "HISTORICAL_STACK_READ_ONLY_BATCH_PLAN_AVAILABLE",
        "source_distinct_autonomous_ai_science_speech_media_technical_qa_verified":
            ai_candidate_match,
        # A batch PLAN is not independent PR review, merge approval or release.
        # Technical distinctness never grants any academic or voice signoff.
        "second_distinct_new_original_full_lecture_accepted": False,
        "entire_historical_stack_dependency_and_review_completed": False,
        "production_installation_smoke_and_release_approval": False,
    }
    # Native engineering qualification can pass independently of human
    # academic acceptance. A successful build NEVER authorizes release.
    engineering_keys = (
        "native_windows_only", "current_worktree_clean",
        "tracked_origin_main_ancestor_no_divergence",
        "windows_ci_workflows_only", "source_checkpoint_integrity",
        "clean_isolated_windows_worker_install_verified",
        "github_ci_exact_final_sha_independently_verified",
        "github_live_origin_main_freshness_verified",
        "bounded_historical_stack_review_plan_available",
    )
    engineering_ready = all(gates[k] for k in engineering_keys)
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
        "second_independent_original_candidate": second_candidate,
        "autonomous_original_lecture_qa": autonomous_qa,
        "historical_stack_review_batch_plan": stack_plan,
        "github_open_pr_dependency_catalog_read_only": open_pr_catalog,
        "exact_head_github_windows_ci_evidence": github_ci,
        "engineering_technical_release_candidate_ready": engineering_ready,
        "engineering_candidate_not_student_release": True,
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
            "Review the bounded historical stack batches, then independently approve PR dependencies",
            "Independent exact-head GitHub Windows CI review",
            "Existing PR362 one-source accepted evidence is reusable only at matching SHA",
            "Recheck an exact SHA-bound reviewed MP4 using --reviewed-media-dir without encoding",
            "Compare a SHA-distinct second original-source technical candidate with the historical accepted reference",
            "Collect verified two-pass AI scientific and independent model audio QA, original figure-diagram semantics, and synchronized media evidence; do not require manual academic signoff",
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
    p.add_argument("--include-stack-batches", action="store_true",
                   help="Read-only bounded plan for historical commit review, never merge")
    p.add_argument("--verify-exact-head-ci-online", action="store_true",
                   help="Opt-in GitHub HTTPS read-only CI lookup, never publish")
    p.add_argument("--github-repository", default="tlyoon/MicroGen_AI_Web",
                   help="Only GitHub owner/repo exact CI source")
    p.add_argument("--audit-open-pr-stack-online", action="store_true",
                   help="Read-only GitHub open PR base/head dependency catalog; never merge")
    for key in ("autonomous-qa-folder", "autonomous-qa-queue-root",
                "autonomous-qa-plan", "autonomous-qa-audio",
                "autonomous-qa-asr-dir"):
        p.add_argument("--" + key, type=Path,
                       help="Existing independent AI/ASR/media evidence; all five required")
    a = p.parse_args(argv)
    values = (a.autonomous_qa_folder, a.autonomous_qa_queue_root,
              a.autonomous_qa_plan, a.autonomous_qa_audio,
              a.autonomous_qa_asr_dir)
    if any(v is not None for v in values) and not all(v is not None for v in values):
        p.error("Autonomous QA needs all five existing source-bound inputs")
    ai_inputs = (
        dict(zip(("folder", "queue_root", "plan", "audio", "asr_dir"), values))
        if all(v is not None for v in values) else None
    )
    try:
        result = inspect_release(repo=a.repo, jobs_dir=a.jobs_dir,
                                 fresh_trial_dir=a.fresh_trial_dir,
                                 worker_python=a.worker_python,
                                 reuse_scoped_pr362=a.reuse_scoped_pr362,
                                 reviewed_media_dir=a.reviewed_media_dir,
                                 include_stack_batches=a.include_stack_batches,
                                 verify_exact_head_ci_online=a.verify_exact_head_ci_online,
                                 github_repository=a.github_repository,
                                 audit_open_pr_stack_online=a.audit_open_pr_stack_online,
                                 autonomous_qa_inputs=ai_inputs)
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
