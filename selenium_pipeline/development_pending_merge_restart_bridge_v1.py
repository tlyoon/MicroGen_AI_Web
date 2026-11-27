"""Verify a safely restartable OLD daemon when CI-certified main is ahead.

The old 5-minute watchdog requires the original daemon's checkout to equal
current GitHub main. If that daemon crashes AFTER a guarded code promotion has
merged but BEFORE deployment, it can never restart and the deploy controller
cannot finish its guarded cutover. Only one exact, independently CI-certified,
original SOURCE-CODE promoter claim grants a short-lived OLD owner reentry.

No new GitHub mutations, model Sends, paid calls, or academic publication.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

from .development_ci_gated_merge_v1 import (
    api, WORKFLOW_NAME, WORKFLOW_PATH, REQUIRED_WINDOWS_JOBS,
)
from .recovery_registry import lookup_mechanism

KIND = "ci_merged_old_daemon_cutover_reentry"
SIGNATURE = "GITHUB_MAIN_ADVANCED_WHILE_ORIGINAL_CI_DEPLOY_DAEMON_STOPPED"
MECHANISM = "VERIFY_ONE_MERGED_TESTED_PROMOTION_AND_RESTART_ONLY_OLD_OWNER"
SHA = re.compile(r"[a-f0-9]{40}\Z")
JOB = re.compile(r"[a-z][a-z0-9_]{6,50}\Z")
MAX_ORIGINAL_PROMOTIONS = 20
STATUS = "VERIFIED_PENDING_CI_MERGE_OLD_DAEMON_REENTRY_NO_SEND"


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def _git(args, runner):
    result = runner(args, capture_output=True, text=True, timeout=45)
    require(result.returncode == 0 and len(result.stdout) < 40000,
            "Original Git identity or protected main is unavailable")
    return result.stdout.strip()


def _json(path):
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= 30000,
            "Untrusted previous code-promotion receipt")
    value = json.loads(path.read_text(encoding="utf8"))
    require(type(value) is dict, "Code-promotion receipt must be a JSON object")
    return value


def _verified_merged_ci(*, pr_number: int, head_sha: str, base_sha: str,
                        merged_sha: str, branch: str, fetch=api):
    """Reestablish historical Windows CI from real GitHub, not local labels."""
    prefix = "repos/tlyoon/MicroGen_AI_Web/"
    pr = fetch(prefix + "pulls/" + str(pr_number))
    require(pr.get("number") == pr_number
            and pr.get("state") == "closed" and pr.get("merged_at")
            and pr.get("merge_commit_sha") == merged_sha
            and pr.get("head", {}).get("sha") == head_sha
            and pr.get("head", {}).get("ref") == branch
            and pr.get("head", {}).get("repo", {}).get("full_name")
                == "tlyoon/MicroGen_AI_Web"
            and pr.get("base", {}).get("ref") == "main",
            "Pending code promotion is not the original merged GitHub PR")
    main = fetch(prefix + "commits/main")
    git_main = fetch(prefix + "git/commits/" + merged_sha)
    git_head = fetch(prefix + "git/commits/" + head_sha)
    require(main.get("sha") == merged_sha
            and git_main.get("tree", {}).get("sha")
                == git_head.get("tree", {}).get("sha")
            and [p.get("sha") for p in git_main.get("parents", [])]
                == [base_sha],
            "GitHub merged source tree or parent differs from original work")
    listing = fetch(prefix + "actions/runs?head_sha=" + head_sha
                    + "&event=pull_request&per_page=100")
    runs = listing.get("workflow_runs")
    require(type(runs) is list
            and type(listing.get("total_count")) is int
            and 0 < listing["total_count"] <= 100
            and len(runs) == listing["total_count"],
            "Incomplete GitHub CI evidence for source-merged old daemon")
    candidates = [r for r in runs
                  if r.get("head_sha") == head_sha
                  and r.get("head_branch") == branch
                  and r.get("event") == "pull_request"
                  and r.get("path") == WORKFLOW_PATH
                  and r.get("name") == WORKFLOW_NAME]
    require(bool(candidates), "No original Windows regression workflow found")
    latest = max(candidates, key=lambda r: (
        r.get("created_at", ""), r.get("id", 0), r.get("run_attempt", 0)))
    require(latest.get("status") == "completed"
            and latest.get("conclusion") == "success"
            and type(latest.get("id")) is int and latest["id"] > 0
            and type(latest.get("run_attempt")) is int
            and latest["run_attempt"] >= 1
            and latest.get("created_at", "") >= pr.get("created_at", ""),
            "Latest exact-head Windows CI did not fully pass")
    # A second workflow on the SAME exact-head source may also fail. Match
    # the original main-gate rule: never ignore its latest terminal result.
    workflows = {}
    for row in runs:
        if row.get("head_sha") != head_sha or row.get("event") != "pull_request":
            continue
        wid = row.get("workflow_id")
        require(type(wid) is int and wid > 0,
                "Unidentified competing CI workflow for same source")
        key = (row.get("created_at", ""), row.get("id", 0),
               row.get("run_attempt", 0))
        if wid not in workflows or key > workflows[wid][0]:
            workflows[wid] = (key, row)
    require(all(r.get("status") == "completed"
                and r.get("conclusion") == "success"
                for _, r in workflows.values()),
            "Pending or failed other exact-source GitHub workflow")
    run_id = latest["id"]
    attempt = latest["run_attempt"]
    items = fetch(prefix + f"actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100")
    jobs = items.get("jobs")
    require(type(jobs) is list
            and type(items.get("total_count")) is int
            and 2 <= len(jobs) == items["total_count"] <= 100,
            "Incomplete original Windows regression job inventory")
    by_name = {}
    for row in jobs:
        name = row.get("name")
        require(type(name) is str and name not in by_name
                and row.get("status") == "completed"
                and row.get("conclusion") == "success"
                and row.get("run_id") == run_id
                and row.get("head_sha") == head_sha
                and row.get("workflow_name") == WORKFLOW_NAME,
                "Nonoriginal or failed Windows CI job")
        by_name[name] = row
    require(REQUIRED_WINDOWS_JOBS <= set(by_name),
            "Missing original two independent Windows regression jobs")
    return run_id


def verify(*, old_repo: Path, controller_root: Path,
           runner=subprocess.run, fetch=api) -> dict:
    """Admit one immutable merged source, never an arbitrary behind-main repo."""
    require(lookup_mechanism(KIND, SIGNATURE) == MECHANISM,
            "Cross-revision guarded recovery missing from executable registry")
    old_repo, controller_root = Path(old_repo), Path(controller_root)
    require(old_repo.is_dir() and not old_repo.is_symlink()
            and old_repo.parent.name == "RECONCILE_20261125"
            and re.fullmatch(r"post_pr[0-9]{3,5}_main", old_repo.name)
            and controller_root.is_dir() and not controller_root.is_symlink()
            and controller_root.name == "AUTONOMOUS_CODE_PROMOTION_V1_20261127"
            and controller_root.parent == old_repo.parent.parent,
            "Original guarded Windows production paths are not independent")
    original = _git(["git", "-C", str(old_repo), "rev-parse", "HEAD"], runner)
    current = _git(["gh", "api", "repos/tlyoon/MicroGen_AI_Web/commits/main",
                    "--jq", ".sha"], runner)
    clean = _git(["git", "-C", str(old_repo), "status", "--porcelain"], runner)
    require(SHA.fullmatch(original) and SHA.fullmatch(current)
            and original != current and clean == "",
            "Old checkout not clean, or not genuinely behind protected main")
    state_dir = controller_root / "promotions"
    require(state_dir.is_dir() and not state_dir.is_symlink(),
            "Original immutable promotion-receipt directory unavailable")
    paths = sorted(state_dir.glob("*.json"))
    require(1 <= len(paths) <= MAX_ORIGINAL_PROMOTIONS
            and all(f.is_file() and not f.is_symlink() for f in paths),
            "Ambiguous original source code promotion inventory")
    candidates = []
    for path in paths:
        data = _json(path)
        if data.get("status") != "MERGED_AWAITING_GUARDED_CUTOVER":
            continue
        require(path.stem == data.get("job_id")
                and JOB.fullmatch(path.stem)
                and data.get("schema_version") == 1
                and data.get("student_publication_authorized") is False
                and data.get("paid_api_requests") == 0
                and data.get("model_sends") == 0
                and data.get("merge_claimed") is True
                and type(data.get("pr_number")) is int
                and 1 <= data["pr_number"] <= 1_000_000
                and type(data.get("promotion_commit_sha")) is str
                and SHA.fullmatch(data["promotion_commit_sha"])
                and data.get("promotion_base_sha") == original
                and data.get("merge_commit_sha") == current
                and data.get("deployment_original_repo", str(old_repo))
                    == str(old_repo),
                "Untrusted/ambiguous original merged code-promotion claim")
        candidates.append(data)
    require(len(candidates) == 1,
            "Need exactly one original CI-approved pending code cutover")
    row = candidates[0]
    run_id = _verified_merged_ci(
        pr_number=row["pr_number"], head_sha=row["promotion_commit_sha"],
        base_sha=original, merged_sha=current, branch=row["branch"],
        fetch=fetch)
    return {"status": STATUS, "old_sha": original, "merged_sha": current,
            "original_pr_number": row["pr_number"],
            "original_job_id": row["job_id"],
            "exact_head_windows_ci_run_id": run_id,
            "provider_sends": 0, "paid_api_requests": 0,
            "student_publication_authorized": False}
