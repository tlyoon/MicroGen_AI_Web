"""Persistent source-bound, offline-only code-development forward controller.

Runs a small *curated* sequence of historical regression milestones. Uses
immutable exact-HEAD and code-policy-locked journal receipts to move from a
passing (or quarantined) task to the next independent eligible task without a
new operator invocation. It does not send model messages, trigger TTS or media
publication, certify original science, merge PRs, or schedule itself after exit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys

from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, require,
)
from .windows_historical_stack_batch_plan import plan_stack
from .windows_historical_stack_batch_executor import execute_batches

SCHEMA = 1
SIGNATURE = "OFFLINE_HISTORICAL_CODE_REVIEW_NEEDS_RESTARTABLE_AUTOFORWARD"
MECHANISM = "SOURCE_LOCKED_CURATED_OFFLINE_TASK_QUEUE_AND_RESTART"
# These are source-only, no-network regression suites independently exercised
# on the same historical batch windows on 19 November 2026. They are NOT
# academic/media acceptance tests or billable provider integration tests.
TASKS = (
    {
        "id": "historical_source_regressions_batch_19",
        "batch": 19,
        "first_commit_prefix": "6d1af85",
        "last_commit_prefix": "6cd6266",
        "modules": (
            "tests.test_gemini_placeholder_grace",
            "tests.test_original_review_ambiguous_response_receipts",
            "tests.test_quote_spatial_continuity",
            "tests.test_original_trig_substitution_numeric_preflight",
        ),
    },
    {
        "id": "historical_source_regressions_batch_20",
        "batch": 20,
        "first_commit_prefix": "144f973",
        "last_commit_prefix": "6b45ee3",
        "modules": (
            "tests.test_original_slide4_exact_source_evidence",
            "tests.test_source_locked_academic_review",
            "tests.test_original_principal_root_interval_qa",
        ),
    },
    {
        "id": "historical_source_regressions_batch_21",
        "batch": 21,
        "first_commit_prefix": "48ca661",
        "last_commit_prefix": "549f858",
        "modules": (
            "tests.test_original_slide4_math_correction_pilot",
            "tests.test_original_slide4_pcm_provenance_pilot",
        ),
    },
)
MAX_STEPS = len(TASKS)
MAX_ATTEMPTS = 2
MAX_RECEIPT_BYTES = 256_000
MAX_LOG_BYTES = 500_000


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(obj: dict) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2)
            + "\n").encode("utf-8")


def _integrity(obj: dict) -> str:
    return _sha(json.dumps(
        {k: v for k, v in obj.items() if k != "integrity_sha256"},
        sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8"))


def _enveloped(record: dict) -> dict:
    result = dict(record)
    result["integrity_sha256"] = _integrity(result)
    return result


def _check_envelope(path: Path, expected: dict | None = None) -> dict:
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= MAX_RECEIPT_BYTES,
            "Missing, linked, empty or oversized developer checkpoint")
    obj = json.loads(path.read_text(encoding="utf-8"))
    require(type(obj) is dict
            and obj.get("integrity_sha256") == _integrity(obj)
            and obj.get("schema_version") == SCHEMA,
            "Corrupt or forged developer checkpoint")
    if expected is not None:
        require(all(obj.get(k) == v for k, v in expected.items()),
                "Developer checkpoint disagrees with original Git/task identity")
    return obj


def _atomic_create(path: Path, data: dict) -> None:
    """Write-once receipt, atomic even if a process dies during fsync."""
    require(not path.exists() and not path.is_symlink(),
            "Refuse to overwrite developer evidence")
    raw = _json_bytes(_enveloped(data))
    require(len(raw) <= MAX_RECEIPT_BYTES,
            "Developer checkpoint exceeds finite size")
    tmp = path.with_suffix(path.suffix + ".staging")
    require(not tmp.is_symlink() and not tmp.is_dir(),
            "Unsafe developer evidence stage")
    if tmp.exists():
        require(tmp.is_file() and tmp.stat().st_size <= MAX_RECEIPT_BYTES,
                "Unexpected staged developer evidence")
        tmp.unlink()  # stage is outside source, lock guards ownership
    with tmp.open("xb") as fd:
        fd.write(raw)
        fd.flush()
        os.fsync(fd.fileno())
    require(tmp.read_bytes() == raw and not path.exists(),
            "Staged developer checkpoint was altered")
    os.replace(tmp, path)


def _verify_repo(repo: Path) -> None:
    repo = Path(repo).absolute()
    local = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    require(os.name == "nt" and local.is_dir()
            and repo.is_dir() and not repo.is_symlink()
            and repo.is_relative_to(local)
            and (repo / ".git").exists(),
            "Only a local clean Dell Windows Git worktree is eligible")
    p = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain",
         "--untracked-files=all"],
        capture_output=True, text=True, timeout=30,
        check=False,
    )
    require(p.returncode == 0 and not p.stderr.strip()
            and not p.stdout.strip(),
            "Any unrecognized local/staged source edit blocks autonomous review")


def _source_modules(repo: Path, task: dict) -> list[dict]:
    result = []
    for name in task["modules"]:
        require(re.fullmatch(r"tests\.test_[A-Za-z0-9_]+", name) is not None,
                "Arbitrary dynamic Python module refused")
        path = repo / (name.replace(".", "/") + ".py")
        require(path.is_file() and not path.is_symlink()
                and path.resolve().is_relative_to(repo.resolve())
                and path.stat().st_size <= 3_000_000,
                "Missing, linked or unbounded curated test source")
        result.append({"name": name, "source_sha256": _sha(path.read_bytes())})
    require(1 <= len(result) <= 10,
            "No authorized bounded test modules for development stage")
    return result


def _subprocess_offline_tests(repo: Path, modules: tuple[str, ...]) -> dict:
    """Run source-regression tests with Python socket egress denied.

    Uses the actual local tests package and does NOT patch producer code.
    An explicitly selected offline unit test cannot silently use requests,
    urllib or the usual socket-based Gemini/Cloud transports.
    """
    script = """
import socket
import sys
import unittest

def deny(*args, **kwargs):
    raise RuntimeError("OFFLINE_SOURCE_TEST_NETWORK_DENIED")

socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny
suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:])
result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
"""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MICROGEN_OFFLINE_SOURCE_REGRESSION"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, "-B", "-c", script, *modules],
            cwd=repo, env=env, capture_output=True, text=True,
            errors="replace", timeout=150, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "LOCAL_TEST_OPERATION_BLOCKED",
            "error_type": type(exc).__name__,
            "exit_code": None,
            "reported_test_count": 0,
            "reported_skip_count": 0,
            "captured_output_sha256": None,
            "success": False,
        }
    out = (proc.stdout + "\n" + proc.stderr).encode("utf-8")
    require(len(out) <= MAX_LOG_BYTES, "Offline test output too large")
    run = re.search(r"Ran (\d+) tests? in", proc.stderr)
    skipped = re.search(r"skipped=(\d+)", proc.stderr)
    passed = (proc.returncode == 0 and run is not None
              and int(run.group(1)) > (int(skipped.group(1)) if skipped else 0)
              and re.search(r"^OK\b", proc.stderr, re.M) is not None
              and "FAILED" not in proc.stderr)
    return {
        "status": ("OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING" if passed
                   else "OFFLINE_SOURCE_REGRESSION_FAILED_QUARANTINED"),
        "exit_code": proc.returncode,
        "reported_test_count": int(run.group(1)) if run else 0,
        "reported_skip_count": int(skipped.group(1)) if skipped else 0,
        "captured_output_sha256": _sha(out),
        "success": passed,
    }


def _folder(repo: Path, head: str) -> Path:
    require(re.fullmatch(r"[a-f0-9]{40}", head) is not None,
            "Unsafe development HEAD")
    local = Path(os.environ["LOCALAPPDATA"]).absolute()
    own = _sha(Path(__file__).read_bytes())
    ident = _sha(str(repo).lower().encode("utf-8"))[:16]
    home = (local / "MicroGen_AI_Web_Checkpoints"
            / "offline_development_autoforward_v1")
    require(not home.is_symlink() and not home.parent.is_symlink(),
            "Linked developer task receipt directory")
    home.mkdir(parents=True, exist_ok=True)
    dest = home / (ident + "_" + head[:20] + "_" + own[:12])
    require(not dest.is_symlink(),
            "Unsafe source-bound development task checkpoint")
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def _ensure_roadmap(repo: Path, head: str, folder: Path) -> Path:
    """Write-once, exact-source executable task roadmap for restart checks."""
    roadmap = folder / "roadmap.json"
    record = {
        "schema_version": SCHEMA,
        "status": "CURATED_OFFLINE_DEVELOPMENT_ROADMAP_ACTIVE",
        "repository_path": str(repo),
        "exact_source_head_sha": head,
        "tasks": [{
            "task_id": task["id"],
            "historical_batch_number": task["batch"],
            "dependencies": [],
            "accepted_result": "OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING",
            "provider_or_paid_operations_authorized": False,
            "automatic_merge_authorized": False,
            "student_publication_authorized": False,
        } for task in TASKS],
        "selection": "SOURCE_LOCKED_ORDER_NEXT_UNCOMPLETED_AFTER_VERIFIED_CHECK",
        "roadmap_complete_implies_scientific_acceptance": False,
    }
    if roadmap.exists():
        old = _check_envelope(roadmap, record)
        require(old == _enveloped(record),
                "Persisted roadmap differs from executable source policy")
    else:
        _atomic_create(roadmap, record)
    return roadmap


def _task_identity(repo: Path, head: str, batch: dict,
                   task: dict, tests: list[dict]) -> dict:
    return {
        "schema_version": SCHEMA,
        "source_head_sha": head,
        "repository_path": str(repo),
        "task_id": task["id"],
        "batch_number": task["batch"],
        "first_commit_sha": batch["first_commit_sha"],
        "last_commit_sha": batch["end_inclusive_sha"],
        "batch_changed_paths_sha256": batch["all_touched_paths_sha256"],
        "reviewed_test_sources": tests,
        "network_or_provider_sends_authorized": False,
        "automatic_merge_authorized": False,
        "student_publication_authorized": False,
        "historical_semantic_review_completed": False,
    }


def _execute_task(repo: Path, head: str, batch: dict, task: dict,
                  folder: Path, runner) -> dict:
    require(batch["batch_number"] == task["batch"]
            and batch["first_commit_sha"].startswith(
                task["first_commit_prefix"])
            and batch["end_inclusive_sha"].startswith(
                task["last_commit_prefix"]),
            "Developer task does not belong to original SHA-bound history")
    modules = _source_modules(repo, task)
    identity = _task_identity(repo, head, batch, task, modules)
    intent = folder / (task["id"] + ".intent.json")
    result = folder / (task["id"] + ".result.json")
    if intent.exists():
        _check_envelope(intent, {
            **identity, "status": "PENDING_OFFLINE_SOURCE_CODE_REGRESSION",
        })
        intent_reused = True
    else:
        _atomic_create(intent, {
            **identity, "status": "PENDING_OFFLINE_SOURCE_CODE_REGRESSION",
        })
        intent_reused = False
    if result.exists():
        saved = _check_envelope(result, identity)
        require(saved.get("status") in (
                    "OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING",
                    "OFFLINE_SOURCE_REGRESSION_FAILED_QUARANTINED",
                    "OFFLINE_SOURCE_REGRESSION_EXHAUSTED_QUARANTINED")
                and type(saved.get("success")) is bool
                and saved["success"] == (
                    saved["status"] == "OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING")
                and type(saved.get("attempt_count")) is int
                and 1 <= saved["attempt_count"] <= MAX_ATTEMPTS
                and type(saved.get("reported_test_count")) is int
                and type(saved.get("reported_skip_count")) is int
                and 0 <= saved["reported_skip_count"] <= saved["reported_test_count"]
                and (not saved["success"] or (
                    saved.get("exit_code") == 0
                    and saved["reported_test_count"] > saved["reported_skip_count"]
                    and re.fullmatch(r"[a-f0-9]{64}", str(
                        saved.get("captured_output_sha256"))) is not None)),
                "Saved task result conflicts with executable acceptance policy")
        return {**saved, "receipt_reused_after_restart": True,
                "result_receipt_path": str(result)}
    # A real process might have died after writing an intent or attempt.
    # Only offline, source-whitelisted tests may be retried after such death.
    attempts = []
    for ix in range(1, MAX_ATTEMPTS + 1):
        path = folder / (task["id"] + f".attempt{ix}.json")
        if path.exists():
            _check_envelope(path, {
                **identity, "status": "OFFLINE_TEST_ATTEMPT_CLAIMED",
                "attempt_number": ix,
            })
            attempts.append(ix)
    remaining = next((n for n in range(1, MAX_ATTEMPTS + 1)
                      if n not in attempts), None)
    if remaining is None:
        test_result = {
            "status": "OFFLINE_SOURCE_REGRESSION_EXHAUSTED_QUARANTINED",
            "success": False, "exit_code": None,
            "reported_test_count": 0, "reported_skip_count": 0,
            "captured_output_sha256": None,
        }
        count = MAX_ATTEMPTS
    else:
        _atomic_create(
            folder / (task["id"] + f".attempt{remaining}.json"),
            {**identity, "status": "OFFLINE_TEST_ATTEMPT_CLAIMED",
             "attempt_number": remaining},
        )
        try:
            test_result = runner(repo, task["modules"])
        except (Exception, KeyboardInterrupt):
            # A dying worker consumes one test-only attempt claim; the next
            # invocation can safely restart remaining offline work.
            raise
        require(type(test_result) is dict
                and type(test_result.get("success")) is bool
                and test_result.get("status") in (
                    "OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING",
                    "OFFLINE_SOURCE_REGRESSION_FAILED_QUARANTINED",
                    "LOCAL_TEST_OPERATION_BLOCKED",
                )
                and type(test_result.get("reported_test_count")) is int
                and type(test_result.get("reported_skip_count")) is int
                and 0 <= test_result["reported_skip_count"]
                    <= test_result["reported_test_count"]
                and (not test_result["success"] or (
                    test_result["status"]
                    == "OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING"
                    and test_result.get("exit_code") == 0
                    and test_result["reported_test_count"] > test_result["reported_skip_count"])),
                "Unrecognized or inconsistent offline test receipt")
        if test_result["status"] == "LOCAL_TEST_OPERATION_BLOCKED":
            test_result = {**test_result,
                           "status": "OFFLINE_SOURCE_REGRESSION_FAILED_QUARANTINED"}
        count = remaining
    _verify_repo(repo)
    # No change to historical source or published lecture files on success.
    complete = {
        **identity, **test_result,
        "attempt_count": count,
        "prior_crash_attempt_resumed": bool(attempts),
        "intent_reused": intent_reused,
        "previous_historical_patch_findings_retained": True,
    }
    _atomic_create(result, complete)
    return {**complete, "receipt_reused_after_restart": False,
            "result_receipt_path": str(result)}


def advance_offline(*, repo: Path, max_steps: int = MAX_STEPS,
                    runner=None) -> dict:
    """Select each eligible historical task and continue in the same process."""
    from .recovery_registry import lookup_mechanism
    from .three_pc_worker import LocalInstanceLock
    require(lookup_mechanism(
        "offline_dev_autoforward", SIGNATURE) == MECHANISM,
        "Continuous offline code-review recovery mechanism disabled")
    require(type(max_steps) is int and 1 <= max_steps <= MAX_STEPS,
            "Bounded development runner requires 1–3 tasks per invocation")
    repo = Path(repo).absolute()
    _verify_repo(repo)
    plan = plan_stack(repo=repo)
    require(plan["status"] == "HISTORICAL_STACK_READ_ONLY_BATCH_PLAN_AVAILABLE"
            and plan["local_worktree_clean"] is True
            and plan["commits_behind_origin_main"] == 0,
            "Historical offline roadmap requires verified exact source stack")
    head = plan["exact_head_sha"]
    require(len(plan["batches"]) >= TASKS[-1]["batch"],
            "Bounded roadmap is missing historical commit membership")
    folder = _folder(repo, head)
    lock = _sha(str(repo).lower().encode("utf-8"))[:20]
    reports = []
    with LocalInstanceLock(
        "autoforward_" + lock, folder.parent / "locks",
    ):
        # Recheck after acquiring exclusive OS lock; multiple invocations
        # cannot reserve competing attempts against the same source task.
        _verify_repo(repo)
        roadmap_path = _ensure_roadmap(repo, head, folder)
        new_tasks_this_process = 0
        for task in TASKS:
            if new_tasks_this_process >= max_steps:
                break
            batch = plan["batches"][task["batch"] - 1]
            patches = execute_batches(
                repo=repo,
                first_batch=task["batch"],
                last_batch=task["batch"],
            )
            require(patches["exact_head_sha"] == head
                    and patches["batch_count_completed"] == 1
                    and patches["student_publication_authorized"] is False,
                    "Historical check not independently verified for task")
            # Formatting findings retain their original quarantine, even if
            # a separate code-test suite succeeds.
            report = _execute_task(
                repo, head, batch, task, folder,
                runner or _subprocess_offline_tests,
            )
            if not report["receipt_reused_after_restart"]:
                new_tasks_this_process += 1
            reports.append({
                **report,
                "historical_patch_quarantine_retained":
                    patches["quarantined_batch_numbers"],
                "next_eligible_task": (
                    TASKS[len(reports)]["id"]
                    if len(reports) < len(TASKS) else None),
            })
            _verify_repo(repo)
    passing = sum(r["success"] for r in reports)
    return {
        "schema_version": SCHEMA,
        "status": ("BOUNDED_OFFLINE_DEVELOPMENT_QUEUE_ADVANCED_REVIEW_PENDING"
                   if passing == len(reports) else
                   "BOUNDED_OFFLINE_DEVELOPMENT_WITH_QUARANTINED_TASKS"),
        "exact_source_head_sha": head,
        "persistent_roadmap_path": str(roadmap_path),
        "tasks_executed_or_reused": len(reports),
        "new_tasks_completed_this_process": new_tasks_this_process,
        "offline_source_regression_pass_count": passing,
        "pending_roadmap_task_count": len(TASKS) - len(reports),
        "tasks": reports,
        "automatic_forward_on_verified_task": True,
        "continuation_across_process_end_requires_authorized_runner": True,
        "automatic_merge_authorized": False,
        "historical_semantic_review_completed": False,
        "independent_academic_qa_accepted": False,
        "new_paid_or_model_requests_made": False,
        "student_publication_authorized": False,
    }


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--repo", type=Path,
                     default=Path(__file__).resolve().parent.parent)
    cli.add_argument("--max-steps", type=int, default=MAX_STEPS)
    args = cli.parse_args(argv)
    try:
        result = advance_offline(repo=args.repo, max_steps=args.max_steps)
    except (CampaignRecoveryBlocked, OSError, ValueError, KeyError,
            RuntimeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({
            "status": "OFFLINE_CODE_DEVELOPMENT_BLOCKED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "automatic_merge_authorized": False,
            "student_publication_authorized": False,
        }, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["offline_source_regression_pass_count"] == len(
        result["tasks"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
