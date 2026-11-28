"""Catch a persistent Dell-115 controller up to newer CI-certified GitHub main.

This solves the original G2/G3 source admission deadlock when a separately
authorized project PR advances protected main while the running long-horizon
daemon and Selenium writer still own their previous clean checkout.

The controller may request ONLY the already-certified guarded cutover, never
merge a PR, mutate arbitrary tasks, issue a model Send, or publish to students.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

from .development_ci_gated_merge_v1 import api
from .development_pending_merge_restart_bridge_v1 import _verified_merged_ci
from .development_certified_candidate_deploy_v1 import deploy, attested_task
from .development_persistent_selenium_author_v1 import TERMINAL
from .recovery_registry import lookup_mechanism

KIND = "ci_merged_main_autocutover"
SIGNATURE = "FOREIGN_CI_CERTIFIED_MAIN_MERGE_LEAVES_DELL_CODE_DAEMON_ON_STALE_CHECKOUT"
MECHANISM = "VERIFY_MERGED_PR_ANCESTRY_WINDOWS_CI_AND_GUARDED_SOURCE_CUTOVER"
SHA = re.compile(r"[0-9a-f]{40}\Z")
REPO = "tlyoon/MicroGen_AI_Web"
PREFIX = "repos/" + REPO + "/"
MAX_FORWARD_COMMITS = 50
SAFE_WAIT_STATES = TERMINAL


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def original_git(repo: Path, *args, runner=subprocess.run):
    value = runner(["git", "-C", str(repo), *args],
                   capture_output=True, text=True, timeout=45)
    require(value.returncode == 0 and len(value.stdout) <= 10000,
            "Original source Git readback unavailable")
    return value.stdout.strip()


def get_merge_pulls(sha: str):
    require(type(sha) is str and SHA.fullmatch(sha),
            "Untrusted merged commit identity")
    path = PREFIX + "commits/" + sha + "/pulls?per_page=100"
    value = subprocess.run(["gh", "api", path], capture_output=True,
                           text=True, timeout=45)
    require(value.returncode == 0 and len(value.stdout) <= 120000,
            "Cannot independently attribute protected GitHub main to a PR")
    result = json.loads(value.stdout)
    require(type(result) is list and len(result) <= 100,
            "Ambiguous latest-merge PR inventory")
    return result


def verify(*, old_repo: Path, controller_root: Path,
           fetch=api, pull_list=get_merge_pulls, git=original_git,
           ci=_verified_merged_ci):
    old_repo, controller_root = Path(old_repo), Path(controller_root)
    require(old_repo.is_dir() and not old_repo.is_symlink()
            and old_repo.parent.name == "RECONCILE_20261125"
            and re.fullmatch(r"post_pr[0-9]{3,5}_main", old_repo.name)
            and controller_root.is_dir() and not controller_root.is_symlink()
            and controller_root.name == "AUTONOMOUS_CODE_PROMOTION_V1_20261127"
            and controller_root.parent == old_repo.parent.parent,
            "Source catch-up paths are not owned by original Dell checkpoint")
    require(lookup_mechanism(KIND, SIGNATURE) == MECHANISM,
            "Source catch-up not registered in executable recovery policy")
    old = git(old_repo, "rev-parse", "HEAD")
    require(type(old) is str and SHA.fullmatch(old)
            and git(old_repo, "status", "--porcelain") == "",
            "Old protected-source checkout is not clean and exact")
    main = fetch(PREFIX + "commits/main")
    latest = main.get("sha")
    require(type(latest) is str and SHA.fullmatch(latest),
            "Current protected GitHub main lacks a complete source SHA")
    if old == latest:
        return {"status": "EXACT_PROTECTED_MAIN_CURRENT",
                "old_sha": old, "merged_sha": latest,
                "provider_sends": 0, "paid_api_requests": 0,
                "student_publication_authorized": False}
    diff = fetch(PREFIX + "compare/" + old + "..." + latest)
    commits = diff.get("commits")
    require(diff.get("status") == "ahead"
            and diff.get("behind_by") == 0
            and type(diff.get("ahead_by")) is int
            and 1 <= diff["ahead_by"] <= MAX_FORWARD_COMMITS
            and type(commits) is list
            and len(commits) == diff["ahead_by"]
            and all(type(x) is dict
                    and type(x.get("sha")) is str
                    and SHA.fullmatch(x["sha"]) for x in commits)
            and commits[-1]["sha"] == latest,
            "Remote protected source is not a finite forward GitHub ancestry")
    matches = [p for p in pull_list(latest)
               if type(p) is dict and p.get("state") == "closed"
               and p.get("merged_at") and p.get("merge_commit_sha") == latest
               and p.get("base", {}).get("ref") == "main"
               and p.get("head", {}).get("repo", {}).get("full_name") == REPO]
    require(len(matches) == 1,
            "Protected source not attributable to one exact merged PR")
    pr = matches[0]
    number = pr.get("number")
    head = pr.get("head", {}).get("sha")
    branch = pr.get("head", {}).get("ref")
    require(type(number) is int and 1 <= number <= 1_000_000
            and type(head) is str and SHA.fullmatch(head)
            and type(branch) is str and len(branch) > 3,
            "Latest merged PR original head identity is invalid")
    git_merge = fetch(PREFIX + "git/commits/" + latest)
    parents = git_merge.get("parents")
    require(type(parents) is list and len(parents) == 1
            and type(parents[0]) is dict
            and type(parents[0].get("sha")) is str
            and SHA.fullmatch(parents[0]["sha"]),
            "Only source-attested squash merges may update code owners")
    ci_run = ci(pr_number=number, head_sha=head,
                base_sha=parents[0]["sha"], merged_sha=latest,
                branch=branch, fetch=fetch)
    require(type(ci_run) is int and ci_run > 0,
            "Latest protected main has no verified Windows CI run")
    # Recheck the remote source at the end of all network verification.
    require(fetch(PREFIX + "commits/main").get("sha") == latest,
            "Protected main moved during automatic source certification")
    return {"status": "LATEST_MAIN_CI_CERTIFIED_GUARDED_CUTOVER_ELIGIBLE",
            "old_sha": old, "merged_sha": latest, "pr_number": number,
            "head_sha": head, "latest_windows_ci_run_id": ci_run,
            "forward_commits": diff["ahead_by"],
            "provider_sends": 0, "paid_api_requests": 0,
            "student_publication_authorized": False}


def catch_up(*, old_repo: Path, controller_root: Path,
             cutover_root: Path, template_root: Path,
             verifier=verify, deployed=deploy, owner=attested_task) -> dict:
    old_repo = Path(old_repo).absolute()
    controller_root = Path(controller_root).absolute()
    cutover_root = Path(cutover_root).absolute()
    template_root = Path(template_root).absolute()
    proof = verifier(old_repo=old_repo, controller_root=controller_root)
    if proof["status"] == "EXACT_PROTECTED_MAIN_CURRENT":
        return proof
    require(proof["status"] == "LATEST_MAIN_CI_CERTIFIED_GUARDED_CUTOVER_ELIGIBLE"
            and proof.get("student_publication_authorized") is False
            and proof.get("provider_sends") == 0
            and proof.get("paid_api_requests") == 0
            and template_root == old_repo / "scripts"
            and cutover_root == old_repo.parent,
            "Remote source advancement not covered by a reviewed guarded cutover")
    # Do not interrupt an outstanding original code model claim.
    hb = controller_root.parent / "LONG_HORIZON_CODE_AUTHOR_V1_20261126" / "worker_heartbeat.json"
    require(hb.is_file() and not hb.is_symlink() and
            1 <= hb.stat().st_size <= 50000, "Unknown Selenium author heartbeat")
    state = json.loads(hb.read_text(encoding="utf8"))
    jobs = state.get("jobs")
    require(type(jobs) is list and 0 < len(jobs) <= 16
            and all(type(j) is dict
                    and j.get("status") in SAFE_WAIT_STATES
                    and j.get("paid_api_requests") == 0 for j in jobs)
            and state.get("student_publication_authorized") is False
            and state.get("new_paid_api_requests") == 0,
            "Original model author is not safely quiescent for source cutover")
    require(owner("MicroGen_AI_Web_v71_OfflineDevelopment", old_repo)
            and owner("MicroGen_AI_Web_v1_PersistentCodeAuthor", old_repo),
            "Original two running development owners not independently attested")
    result = deployed(number=proof["pr_number"], head_sha=proof["head_sha"],
                      cutover_root=cutover_root, current_repo=old_repo,
                      template_root=template_root, record_root=controller_root)
    require(result.get("status") == "GUARDED_DEPLOYED"
            and result.get("deployed_main_sha") == proof["merged_sha"]
            and result.get("student_publication_authorized") is False,
            "Original protected main source cutover not independently completed")
    return {**proof, "status": "CERTIFIED_MAIN_SOURCE_AUTO_CUTOVER_DEPLOYED"}
