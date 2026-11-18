"""Execute bounded *offline* patch-integrity checks for planned Git batches.

This extends the authoritative historical stack planner, not a separate
review/merge pipeline. No generated content, provider calls or source writes.
A successful patch check is never a semantic code, scientific, QA or merge
approval. Findings quarantine their batch and execution advances to the next
independent batch within finite bounds; receipts survive process restarts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .original_multisource_recovery_campaign import CampaignRecoveryBlocked, require
from .windows_historical_stack_batch_plan import plan_stack, _git

MECHANISM = "VERIFY_EACH_HISTORICAL_COMMIT_PATCH_AND_ADVANCE_SAFE_BATCHES"
SIGNATURE = "HISTORICAL_STACK_PLAN_HAS_NO_RESTARTABLE_BATCH_EXECUTION"
SCHEMA = 1
MAX_DIFF_BYTES = 350_000
CHECK_VERSION = 1


def _hash_lines(items: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(items, separators=(",", ":"), ensure_ascii=False).encode("utf8")
    ).hexdigest()


def _check_commit(repo: Path, sha: str, *, run=None) -> dict:
    require(re.fullmatch(r"[a-f0-9]{40}", sha) is not None,
            "Invalid commit SHA in offline patch check")
    fn = subprocess.run if run is None else run
    try:
        result = fn(
            ["git", "-C", str(repo), "show", "--no-ext-diff",
             "--no-renames", "--format=", "--check", sha],
            capture_output=True, text=True, encoding="utf8",
            errors="replace", timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CampaignRecoveryBlocked(
            "Read-only historical commit checker unavailable") from exc
    require(type(result.returncode) is int
            and isinstance(result.stdout, str)
            and isinstance(result.stderr, str)
            and len(result.stdout.encode("utf8")) <= MAX_DIFF_BYTES
            and len(result.stderr.encode("utf8")) <= MAX_DIFF_BYTES,
            "Unbounded or malformed historical Git checker output")
    # A non-zero result is a quarantined finding, not an invitation to
    # rewrite historical commits or bypass source / reviewer acceptance.
    return {
        "sha": sha,
        "patch_check_passed": result.returncode == 0
                                and not result.stdout.strip()
                                and not result.stderr.strip(),
        "check_exit_code": result.returncode,
        "tool_output_sha256": hashlib.sha256(
            (result.stdout + "\x00" + result.stderr).encode("utf8")
        ).hexdigest(),
    }


def _receipt_path(*, repo: Path, plan: dict, batch: dict,
                  local: Path) -> Path:
    own_version = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    receipt_dir = local / "MicroGen_AI_Web_Checkpoints" / "historical_code_batch_execution_v1"
    require(not receipt_dir.is_symlink()
            and not receipt_dir.parent.is_symlink(),
            "Unsafe historical batch receipt directory")
    receipt_dir.mkdir(parents=True, exist_ok=True)
    return receipt_dir / (
        plan["exact_head_sha"][:16] + "_b" +
        f'{batch["batch_number"]:03d}' + "_" + own_version[:12] + ".json"
    )


def _persist_or_verify(path: Path, record: dict) -> tuple[dict, bool]:
    raw = (json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False)
           + "\n").encode("utf8")
    require(not path.is_symlink(), "Linked batch receipt is forbidden")
    if path.exists():
        require(path.is_file() and path.read_bytes() == raw,
                "Saved batch evidence conflicts with current exact commit audit")
        return record, True
    try:
        with path.open("xb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
    except FileExistsError:
        require(not path.is_symlink() and path.read_bytes() == raw,
                "Concurrent batch audit changed checkpoint")
        return record, True
    return record, False


def execute_batches(*, repo: Path, batch_size: int = 20,
                    first_batch: int = 1, last_batch: int | None = None,
                    max_commits: int = 2500, run=None) -> dict:
    """Perform finite SHA-locked patch checks and resume unchanged receipts.

    Each batch is independently evaluated and any findings remain quarantined
    without stopping valid later batch checks. A plan is not approval.
    """
    repo = Path(repo).absolute()
    plan = plan_stack(repo=repo, batch_size=batch_size,
                      max_commits=max_commits)
    require(plan["status"] == "HISTORICAL_STACK_READ_ONLY_BATCH_PLAN_AVAILABLE"
            and plan["local_worktree_clean"] is True
            and plan["commits_behind_origin_main"] == 0,
            "Exact isolated clean historical stack required")
    from .recovery_registry import lookup_mechanism
    require(lookup_mechanism("historical_batch_execution", SIGNATURE) == MECHANISM,
            "Historical batch execution mechanism missing or retired")
    count = plan["review_batch_count"]
    stop = count if last_batch is None else last_batch
    require(type(first_batch) is int and type(stop) is int
            and 1 <= first_batch <= stop <= count,
            "Invalid finite historical review batch range")
    commits = _git(repo, "rev-list", "--topo-order", "--reverse",
                   "origin/main..HEAD").splitlines()
    require(len(commits) == plan["commits_ahead_of_origin_main"]
            and all(re.fullmatch(r"[a-f0-9]{40}", sha) for sha in commits),
            "Changed or invalid Git commit history after planning")
    local = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    require(local.is_dir() and repo.is_relative_to(local),
            "Historical code evidence may only be recorded on local Windows checkout")
    batches = []
    position = 0
    for batch in plan["batches"]:
        unit = commits[position:position + batch["commit_count"]]
        position += batch["commit_count"]
        require(len(unit) == batch["commit_count"]
                and unit[0] == batch["first_commit_sha"]
                and unit[-1] == batch["end_inclusive_sha"],
                "Historical batch membership or SHA boundary changed")
        index = batch["batch_number"]
        if not first_batch <= index <= stop:
            continue
        receipt = _receipt_path(repo=repo, plan=plan, batch=batch, local=local)
        # A completed exact-content receipt can be reused; its SHA and the
        # checker implementation are in the filename. This survives restarts.
        if receipt.exists():
            require(not receipt.is_symlink() and receipt.is_file(),
                    "Untrusted historical batch checkpoint")
            existing = json.loads(receipt.read_text(encoding="utf8"))
            require(type(existing) is dict
                    and existing.get("schema_version") == SCHEMA
                    and existing.get("exact_head_sha") == plan["exact_head_sha"]
                    and existing.get("batch_number") == index
                    and existing.get("batch_end_sha") == unit[-1]
                    and existing.get("member_commit_sha256") == _hash_lines(unit)
                    and existing.get("touched_paths_sha256") ==
                        batch["all_touched_paths_sha256"]
                    and existing.get("semantic_code_review_completed") is False
                    and existing.get("student_publication_authorized") is False
                    and existing.get("automatic_merge_authorized") is False,
                    "Saved historical batch receipt does not match source history")
            result = {**existing, "receipt_reused_after_restart": True,
                      "receipt_path": str(receipt)}
            batches.append(result)
            continue
        check_results = [_check_commit(repo, sha, run=run) for sha in unit]
        failures = [entry["sha"] for entry in check_results
                    if not entry["patch_check_passed"]]
        record = {
            "schema_version": SCHEMA,
            "status": ("OFFLINE_HISTORICAL_PATCH_INTEGRITY_PASS_REVIEW_PENDING"
                       if not failures else
                       "OFFLINE_HISTORICAL_PATCH_FINDINGS_QUARANTINED"),
            "exact_head_sha": plan["exact_head_sha"],
            "batch_number": index,
            "batch_start_exclusive_sha": batch["start_exclusive_sha"],
            "batch_end_sha": unit[-1],
            "member_commit_sha256": _hash_lines(unit),
            "touched_paths_sha256": batch["all_touched_paths_sha256"],
            "checked_commit_count": len(check_results),
            "patch_check_failure_count": len(failures),
            "failure_commit_shas": failures,
            "check_results_sha256": _hash_lines([
                r["sha"] + ":" + str(r["check_exit_code"])
                + ":" + r["tool_output_sha256"] for r in check_results]),
            "historical_transient_path_count": batch["transient_or_reverted_path_count"],
            "semantic_code_review_completed": False,
            "independent_academic_qa_accepted": False,
            "automatic_merge_authorized": False,
            "student_publication_authorized": False,
            "model_or_tts_calls": 0,
        }
        _persist_or_verify(receipt, record)
        batches.append({**record, "receipt_reused_after_restart": False,
                        "receipt_path": str(receipt)})
    require(len(batches) == stop - first_batch + 1,
            "Historical batch execution incomplete")
    require(_git(repo, "rev-parse", "HEAD") == plan["exact_head_sha"]
            and not _git(repo, "status", "--porcelain"),
            "Repository changed during the batch execution")
    blocked = [b["batch_number"] for b in batches if b["patch_check_failure_count"]]
    return {
        "schema_version": SCHEMA,
        "status": ("OFFLINE_BATCH_PATCH_FINDINGS_REVIEW_REQUIRED"
                   if blocked else
                   "OFFLINE_BATCH_PATCH_CHECKS_COMPLETE_CODE_REVIEW_PENDING"),
        "exact_head_sha": plan["exact_head_sha"],
        "first_batch": first_batch,
        "last_batch": stop,
        "batch_count_completed": len(batches),
        "commits_checked_or_reused": sum(b["checked_commit_count"] for b in batches),
        "quarantined_batch_numbers": blocked,
        "saved_receipts_reused": sum(b["receipt_reused_after_restart"]
                                     for b in batches),
        "batch_receipts": batches,
        "semantic_code_review_completed": False,
        "full_historical_stack_reviewer_acceptance": False,
        "automatic_merge_authorized": False,
        "student_publication_authorized": False,
        "model_or_tts_calls": 0,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path,
                   default=Path(__file__).resolve().parent.parent)
    p.add_argument("--first-batch", type=int, default=1)
    p.add_argument("--last-batch", type=int, default=None)
    p.add_argument("--batch-size", type=int, default=20)
    p.add_argument("--max-commits", type=int, default=2500)
    args = p.parse_args(argv)
    try:
        result = execute_batches(repo=args.repo, first_batch=args.first_batch,
                                 last_batch=args.last_batch,
                                 batch_size=args.batch_size,
                                 max_commits=args.max_commits)
    except (CampaignRecoveryBlocked, ValueError, OSError,
            subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "HISTORICAL_BATCH_EXECUTION_BLOCKED",
                          "reason_type": type(exc).__name__,
                          "automatic_merge_authorized": False,
                          "student_publication_authorized": False}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if not result["quarantined_batch_numbers"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
