"""Read-only GitHub open draft PR stack dependency audit (native Windows).

Checks live PR head/base branch links, exact SHAs, draft flags and pagination.
A chained draft stack is NOT an independently reviewed / merge-approved stack.
No git edits, PR mutation, Gemini, TTS, academic approval or publication.
"""
from __future__ import annotations

import argparse
import json
import re
from urllib.request import Request, urlopen

_SHA = re.compile(r"[a-f0-9]{40}\Z")
_REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


def _api_get(url: str) -> list[dict]:
    if not url.startswith("https://api.github.com/repos/") or "#" in url:
        raise ValueError("Unexpected GitHub PR metadata endpoint")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "MicroGen-Windows-PR-Stack-ReadOnly",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    with urlopen(Request(url, headers=headers), timeout=20) as response:
        raw = response.read(6_000_001)
    if len(raw) > 6_000_000:
        raise ValueError("GitHub PR metadata response exceeds bound")
    parsed = json.loads(raw.decode("utf8"))
    if not isinstance(parsed, list) or len(parsed) > 100:
        raise ValueError("Expected bounded GitHub pull request array")
    return parsed


def audit(*, repository: str,
          expected_latest_head_sha: str | None = None,
          max_pages: int = 7, fetch=None) -> dict:
    if (not isinstance(repository, str)
            or not _REPO.fullmatch(repository)
            or ".." in repository):
        raise ValueError("Expected exact GitHub owner/repository")
    if (expected_latest_head_sha is not None
            and (not isinstance(expected_latest_head_sha, str)
                 or not _SHA.fullmatch(expected_latest_head_sha))):
        raise ValueError("Exact 40-digit lowercase expected head SHA required")
    if type(max_pages) is not int or not 1 <= max_pages <= 10:
        raise ValueError("Bounded 1-10 page historic PR audit required")
    fn = _api_get if fetch is None else fetch
    base_url = f"https://api.github.com/repos/{repository}/pulls"
    incoming: list[dict] = []
    complete = False
    for page in range(1, max_pages + 1):
        url = f"{base_url}?state=open&per_page=100&page={page}"
        group = fn(url)
        if not isinstance(group, list) or len(group) > 100:
            raise ValueError("Malformed GitHub PR list")
        incoming.extend(group)
        if len(group) < 100:
            complete = True
            break
    if len(incoming) > max_pages * 100:
        raise ValueError("PR pagination exceed bound")
    selected = []
    by_num: set[int] = set()
    for pr in incoming:
        if not isinstance(pr, dict) or type(pr.get("number")) is not int:
            raise ValueError("Missing immutable pull request number")
        no = pr["number"]
        if no < 1 or no in by_num:
            raise ValueError("Duplicate/invalid GitHub PR number")
        by_num.add(no)
        head = pr.get("head")
        base = pr.get("base")
        if not isinstance(head, dict) or not isinstance(base, dict):
            raise ValueError("PR has no head/base branch")
        if (not isinstance(head.get("ref"), str)
                or not isinstance(base.get("ref"), str)
                or not head["ref"] or not base["ref"]
                or not isinstance(head.get("sha"), str)
                or not _SHA.fullmatch(head["sha"])
                or pr.get("state") != "open"
                or type(pr.get("draft")) is not bool):
            raise ValueError("Untrusted GitHub PR branch or SHA metadata")
        selected.append({
            "number": no,
            "head_branch": head["ref"],
            "head_sha": head["sha"],
            "base_branch": base["ref"],
            "draft": pr["draft"],
        })
    selected.sort(key=lambda x: x["number"], reverse=True)
    disagreements = []
    for current, older in zip(selected, selected[1:]):
        if current["base_branch"] != older["head_branch"]:
            disagreements.append({
                "newer_pr": current["number"],
                "newer_base_branch": current["base_branch"],
                "next_older_pr": older["number"],
                "next_older_head_branch": older["head_branch"],
            })
    # Number-ordered open PRs may include unrelated roots and historic main
    # branches. Identify the recent contiguous draft *review tranche* without
    # pretending the entire repository is one linear stack.
    recent_tranche: list[dict] = []
    for entry in selected:
        if not entry["draft"]:
            break
        if (recent_tranche and
                recent_tranche[-1]["base_branch"] != entry["head_branch"]):
            break
        recent_tranche.append(entry)
    head_matches = (bool(selected) and
                    (expected_latest_head_sha is None
                     or selected[0]["head_sha"] == expected_latest_head_sha))
    all_draft = bool(selected) and all(x["draft"] for x in selected)
    safe_topology = (complete and all_draft and not disagreements
                     and head_matches)
    return {
        "schema_version": 1,
        "status": (
            "OPEN_DRAFT_PR_LINKS_RECONCILED_NOT_MERGE_APPROVED"
            if safe_topology else
            "OPEN_PR_STACK_INCOMPLETE_OR_REVIEW_REQUIRED"),
        "repository": repository,
        "open_pr_count_in_audited_pages": len(selected),
        "pages_checked": min(max_pages, (len(incoming) // 100) + 1)
                         if complete else max_pages,
        "open_pr_catalog_pagination_complete": complete,
        "newest_open_pr": selected[0]["number"] if selected else None,
        "newest_open_head_sha": selected[0]["head_sha"] if selected else None,
        "oldest_open_pr": selected[-1]["number"] if selected else None,
        "oldest_open_base_branch": (
            selected[-1]["base_branch"] if selected else None),
        "all_open_prs_are_drafts": all_draft,
        "open_prs_not_draft_count": sum(not x["draft"] for x in selected),
        "newest_contiguous_draft_review_tranche_count": len(recent_tranche),
        "newest_contiguous_draft_review_tranche_oldest_pr":
            recent_tranche[-1]["number"] if recent_tranche else None,
        "newest_contiguous_tranche_still_requires_review": True,
        "expected_latest_head_sha_matches": head_matches,
        "adjacent_open_pr_branch_disagreements": disagreements[:30],
        "total_adjacent_disagreement_count": len(disagreements),
        "chain_consistent_only_for_audited_open_prs": safe_topology,
        "latest_open_pr_chain_preview": [
            {"number": x["number"], "base_branch": x["base_branch"],
             "head_branch": x["head_branch"], "draft": x["draft"]}
            for x in selected[:15]
        ],
        "closed_merged_or_unlisted_pr_dependencies_verified": False,
        "independent_per_pr_code_science_and_audio_reviews_completed": False,
        "historical_stack_fully_reviewed_or_approved": False,
        "may_merge_automatically": False,
        "new_model_or_tts_calls": False,
        "student_publication_authorized": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="tlyoon/MicroGen_AI_Web")
    parser.add_argument("--expected-latest-head-sha")
    parser.add_argument("--max-pages", type=int, default=7)
    opts = parser.parse_args(argv)
    try:
        report = audit(repository=opts.repository, max_pages=opts.max_pages,
                       expected_latest_head_sha=opts.expected_latest_head_sha)
    except (ValueError, TypeError, OSError, TimeoutError, UnicodeError) as exc:
        report = {
            "status": "GITHUB_PR_STACK_READ_ONLY_AUDIT_REJECTED",
            "diagnostic": type(exc).__name__,
            "historical_stack_fully_reviewed_or_approved": False,
            "may_merge_automatically": False,
            "student_publication_authorized": False,
        }
        print(json.dumps(report, indent=2))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["chain_consistent_only_for_audited_open_prs"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
