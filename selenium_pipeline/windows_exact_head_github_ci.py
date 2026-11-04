"""Online READ-ONLY exact-HEAD GitHub Windows CI attestation.

An optional release inspector. Offline mode remains the default elsewhere.
Only GitHub's HTTPS API supplies run/job status; local JSON, test printouts,
a different SHA or a previous green PR cannot authorize formal release.
Does not set academic, publishing or merge acceptance.
"""
from __future__ import annotations

import argparse
import json
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

_SHA = re.compile(r"[a-f0-9]{40}\Z")
_REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_EXPECTED = (
    "offline-regressions",
    "Full offline suite (Windows, Python 3.12)",
)
_WORKFLOW = ".github/workflows/microgen-reliability-tests.yml"


def _fetch(url: str) -> dict:
    require = "https://api.github.com/repos/"
    if not url.startswith(require) or any(c in url for c in ("#", "\n", "\r")):
        raise ValueError("Only fixed GitHub public REST endpoints permitted")
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "MicroGen-Windows-ReadOnly-CI-Attestation",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urlopen(request, timeout=20) as resp:
        data = resp.read(1_000_001)
    if len(data) > 1_000_000:
        raise ValueError("Unbounded GitHub CI response rejected")
    value = json.loads(data.decode("utf8"))
    if type(value) is not dict:
        raise ValueError("GitHub response must be an object")
    return value


def inspect_ci(*, repository: str, head_sha: str,
               tracked_main_sha: str | None = None, fetch=None) -> dict:
    """One exact SHA / latest PR run; never claim green from previous SHA."""
    if (_REPO.fullmatch(repository) is None
            or _SHA.fullmatch(head_sha) is None
            or (tracked_main_sha is not None
                and _SHA.fullmatch(tracked_main_sha) is None)
            or ".." in repository or repository.startswith("-")):
        raise ValueError("Expected trusted GitHub owner/repo and exact lowercase HEAD SHA")
    base = f"https://api.github.com/repos/{repository}"
    result = {
        "schema_version": 1,
        "status": "EXACT_HEAD_WINDOWS_CI_UNVERIFIED",
        "repository": repository,
        "head_sha": head_sha,
        "exact_head_windows_ci_verified": False,
        "remote_tracked_main_matches_current_github": False,
        "remote_main_sha_freshness_check_requested":
            tracked_main_sha is not None,
        "ci_read_only": True,
        "model_or_tts_called": False,
        "git_worktree_mutated": False,
        "historical_stack_merge_authorized": False,
        "student_publication_authorized": False,
    }
    fn = _fetch if fetch is None else fetch
    try:
        listings = fn(
            f"{base}/actions/runs?head_sha={head_sha}&event=pull_request&per_page=100")
        raw = listings.get("workflow_runs")
        if type(raw) is not list or len(raw) > 100:
            raise ValueError("GitHub CI workflow list absent or unbounded")
        matching = [r for r in raw if (
            type(r) is dict
            and r.get("head_sha") == head_sha
            and r.get("name") == "MicroGen reliability regressions"
            and str(r.get("path", "")).split("@")[0] == _WORKFLOW
            and r.get("event") == "pull_request"
            and type(r.get("id")) is int
            and r["id"] > 0
            and type(r.get("run_attempt")) is int
            and r["run_attempt"] >= 1)]
        if not matching:
            result["status"] = "NO_EXACT_HEAD_PULL_REQUEST_WINDOWS_CI_RUN"
            return result
        matching.sort(key=lambda r: (r.get("created_at", ""),
                                     r["id"], r["run_attempt"]), reverse=True)
        run = matching[0]
        result["github_run_id"] = run["id"]
        result["github_run_attempt"] = run["run_attempt"]
        result["workflow_run_conclusion"] = run.get("conclusion")
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            result["status"] = "EXACT_HEAD_WINDOWS_CI_PENDING_OR_FAILED"
            return result
        listing = fn(
            f"{base}/actions/runs/{run['id']}/jobs?filter=latest&per_page=100")
        jobs = listing.get("jobs")
        if type(jobs) is not list or len(jobs) > 100:
            raise ValueError("Unbounded GitHub CI job list")
        actual = {}
        for job in jobs:
            if type(job) is not dict or type(job.get("name")) is not str:
                raise ValueError("GitHub job invalid")
            if job["name"] in actual:
                raise ValueError("Duplicate GitHub workflow job names")
            actual[job["name"]] = job
        statuses = {name: {
            "status": actual.get(name, {}).get("status"),
            "conclusion": actual.get(name, {}).get("conclusion"),
        } for name in _EXPECTED}
        result["expected_windows_jobs"] = statuses
        if not all(statuses[x]["status"] == "completed"
                   and statuses[x]["conclusion"] == "success"
                   for x in _EXPECTED):
            result["status"] = "EXACT_HEAD_WINDOWS_CI_JOBS_NOT_ALL_GREEN"
            return result
        result["status"] = "EXACT_HEAD_GITHUB_WINDOWS_CI_INDEPENDENTLY_VERIFIED"
        result["exact_head_windows_ci_verified"] = True
        if tracked_main_sha is not None:
            ref = fn(f"{base}/git/ref/heads/main")
            current = ref.get("object")
            if type(current) is not dict or (
                    type(current.get("sha")) is not str
                    or _SHA.fullmatch(current["sha"]) is None):
                raise ValueError("GitHub current main reference invalid")
            result["live_github_main_sha"] = current["sha"]
            result["remote_tracked_main_matches_current_github"] = (
                current["sha"] == tracked_main_sha)
            if current["sha"] != tracked_main_sha:
                result["status"] = "LOCAL_TRACKED_ORIGIN_MAIN_STALE_VS_GITHUB"
        return result
    except (OSError, TimeoutError, UnicodeError, ValueError, TypeError,
            KeyError, json.JSONDecodeError) as exc:
        result["status"] = "EXACT_HEAD_CI_REMOTE_EVIDENCE_UNAVAILABLE"
        result["safe_diagnostic"] = type(exc).__name__
        return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repository", required=True)
    ap.add_argument("--head-sha", required=True)
    ap.add_argument("--tracked-main-sha", help="Optional strict live GitHub origin/main freshness check")
    args = ap.parse_args(argv)
    try:
        report = inspect_ci(repository=args.repository, head_sha=args.head_sha,
                            tracked_main_sha=args.tracked_main_sha)
    except ValueError as exc:
        report = {"status": "EXACT_HEAD_CI_INPUT_REJECTED", "reason": str(exc),
                  "student_publication_authorized": False}
    print(json.dumps(report, indent=2))
    return 0 if report.get("exact_head_windows_ci_verified") else 2


if __name__ == "__main__":
    raise SystemExit(main())
