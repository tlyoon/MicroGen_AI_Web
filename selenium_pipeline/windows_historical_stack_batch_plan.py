"""Read-only, bounded review batch plan for the historical Windows PR stack.

No git fetch/checkout/reset/rebase/merge/cherry-pick/tag/push; no source,
Gemini, TTS, FFmpeg or publisher assets. SHA-locked local origin/main must
be independently refreshed/verified before formal release decisions.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, require,
)


def _git(repo: Path, *argv: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *argv], capture_output=True,
        text=True, encoding="utf8", errors="replace", timeout=50,
    )
    require(proc.returncode == 0,
            "Local read-only Git history unavailable: " + " ".join(argv))
    return proc.stdout.strip()


def _risk_paths(paths: list[str]) -> list[str]:
    flags = set()
    for s in paths:
        p = s.replace("\\", "/").lower()
        if p.startswith("selenium_pipeline/"):
            flags.add("PIPELINE_RUNTIME")
        if p.startswith("tests/") or p.startswith("selenium_pipeline/tests/"):
            flags.add("REGRESSION_TESTS")
        if p.startswith(".github/workflows/"):
            flags.add("WINDOWS_CI")
        if p.startswith("docs/") or p == "readme.md":
            flags.add("DOCUMENTATION")
        if p.startswith(("requirements", "setup.", "pyproject", "microgen-windows")):
            flags.add("WINDOWS_PACKAGING_OR_LAUNCHER")
        if p.endswith((".pdf", ".wav", ".mp4", ".env")):
            flags.add("SOURCE_OR_AUDIO_MEDIA_ASSET")
    return sorted(flags or {"MISCELLANEOUS"})


def plan_stack(*, repo: Path, batch_size: int = 20,
               max_commits: int = 2500) -> dict:
    require(os.name == "nt", "Native Windows only stack review")
    repo = Path(repo).absolute()
    local = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    require(local.is_dir() and repo.is_dir()
            and not repo.is_symlink() and repo.is_relative_to(local)
            and (repo / ".git").exists()
            and not (repo / ".git").is_symlink(),
            "Use a real isolated checkout under LOCALAPPDATA, not dirty publisher G:")
    require(type(batch_size) is int and 1 <= batch_size <= 40
            and type(max_commits) is int and 1 <= max_commits <= 5000,
            "Review must be bounded to safe, finite commit batches")
    head = _git(repo, "rev-parse", "HEAD")
    base = _git(repo, "rev-parse", "refs/remotes/origin/main")
    require(re.fullmatch(r"[a-f0-9]{40}", head) is not None
            and re.fullmatch(r"[a-f0-9]{40}", base) is not None,
            "Untrusted exact Git commit SHA")
    dirty = bool(_git(repo, "status", "--porcelain"))
    behind = int(_git(repo, "rev-list", "--count", "HEAD..origin/main"))
    shallow = _git(repo, "rev-parse", "--is-shallow-repository") == "true"
    if behind or shallow:
        return {
            "schema_version": 1,
            "status": "RELEASE_STACK_TOPOLOGY_NOT_VERIFIABLE_FROM_LOCAL_REFS",
            "exact_head_sha": head,
            "local_origin_main_sha": base,
            "commits_behind_origin_main": behind,
            "shallow_repository": shallow,
            "batches": [],
            "manual_review_required": True,
            "historical_stack_review_completed": False,
            "automatic_merge_or_release_authorized": False,
            "student_publication_authorized": False,
        }
    commits = _git(repo, "rev-list", "--topo-order", "--reverse",
                   "origin/main..HEAD").splitlines()
    require(len(commits) <= max_commits,
            "Historical stack too large for declared finite review bound")
    require(all(re.fullmatch(r"[a-f0-9]{40}", commit)
                for commit in commits), "Invalid SHA from local Git history")
    # A review batch is a contiguous SHA window, NOT a merged/reviewed PR.
    # Each batch can be inspected without changing checkout refs.
    batches = []
    previous = base
    for start in range(0, len(commits), batch_size):
        chunk = commits[start:start + batch_size]
        last = chunk[-1]
        changed = _git(repo, "diff", "--name-only", previous, last)
        paths = [x for x in changed.splitlines() if x]
        batches.append({
            "batch_number": len(batches) + 1,
            "start_exclusive_sha": previous,
            "first_commit_sha": chunk[0],
            "end_inclusive_sha": last,
            "commit_count": len(chunk),
            "changed_path_count": len(paths),
            "review_risk_categories": _risk_paths(paths),
            "individual_pr_dependencies_independently_verified": False,
            "code_and_academic_review_complete": False,
            "merge_or_publication_authorized": False,
        })
        previous = last
    require(sum(x["commit_count"] for x in batches) == len(commits),
            "Missing history segment in staged review batch plan")
    return {
        "schema_version": 1,
        "status": ("HISTORICAL_STACK_READ_ONLY_BATCH_PLAN_AVAILABLE"
                   if batches else "NO_COMMITS_AHEAD_OF_TRACKED_MAIN"),
        "exact_head_sha": head,
        "local_origin_main_sha": base,
        "tracked_origin_main_requires_independent_freshness_check": True,
        "local_worktree_clean": not dirty,
        "shallow_repository": shallow,
        "commits_behind_origin_main": behind,
        "commits_ahead_of_origin_main": len(commits),
        "review_batch_size_limit": batch_size,
        "review_batch_count": len(batches),
        "batches": batches,
        "history_batches_only_no_pr_review_claim": True,
        "historical_stack_review_completed": False,
        "new_model_or_tts_calls": False,
        "git_changes_performed": False,
        "automatic_merge_or_release_authorized": False,
        "student_publication_authorized": False,
        "recommended_next_action": (
            "Independently refresh origin/main, map exact commit windows to "
            "draft PR dependencies, review WINDOWS CI/source/voice/academic "
            "changes in bounded batches, then seek formal approval. "
            "Never blindly merge the entire historical stack."),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path,
                    default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--batch-size", type=int, default=20)
    ap.add_argument("--max-commits", type=int, default=2500)
    a = ap.parse_args(argv)
    try:
        data = plan_stack(repo=a.repo, batch_size=a.batch_size,
                          max_commits=a.max_commits)
    except (CampaignRecoveryBlocked, OSError, ValueError,
            subprocess.TimeoutExpired) as exc:
        data = {"status": "HISTORICAL_STACK_BATCH_REVIEW_REJECTED",
                "reason": str(exc), "new_model_or_tts_calls": False,
                "automatic_merge_or_release_authorized": False,
                "student_publication_authorized": False}
        print(json.dumps(data, indent=2))
        return 2
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
