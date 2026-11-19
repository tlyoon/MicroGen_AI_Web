"""v7.1: durable, observable handoff across safe project workstreams.

This *outer* controller, unlike a one-stage worker, must dispatch a genuinely
eligible subsequent workstream after a checkpoint. It has four fixed,
read-only/offline tasks and explicit source/QA/release blocks. No provider Send,
paid API, automatic merge, student publication, or invisible background claim.
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
import time

from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, require,
)
from .three_pc_worker import LocalInstanceLock, kill_descendants
from .windows_offline_development_forward_controller import (
    MAX_STEPS, TASKS, advance_offline, _verify_repo,
    _atomic_create, _check_envelope,
)
from .windows_historical_stack_batch_plan import plan_stack

SCHEMA = 1
SIGNATURE = "V71_CHECKPOINT_WITHOUT_VERIFIED_PROJECT_NEXT_DISPATCH"
MECHANISM = "OBSERVABLE_GLOBAL_STAGE_HANDOFF_WITH_SOURCE_LOCKED_EVENTS"
STAGES = (
    {"id": "curated_offline_source_regressions", "deps": (), "timeout": 2400},
    {"id": "global_historical_source_gap_inventory", "deps": (), "timeout": 180},
    {"id": "independent_readonly_release_board", "deps": (
        "curated_offline_source_regressions",
        "global_historical_source_gap_inventory"), "timeout": 600},
    {"id": "original_g2_readonly_claim_reconciliation", "deps": (), "timeout": 180},
)
MAX_EVENTS_BYTES = 2_000_000
LONG_QUEUE_TIMEOUT_SIGNATURE = "V71_LONG_OFFLINE_QUEUE_PREMATURE_TIMEOUT"
LONG_QUEUE_TIMEOUT_MECHANISM = "BOUNDED_LONG_OFFLINE_QUEUE_AND_DESCENDANT_CLEANUP"

BLOCKED_WORKSTREAMS = (
    {"id": "historical_semantic_review", "reason": "selected tests do not constitute independent review of all historical changes"},
    {"id": "g2_original_scientific_review", "reason": "unresolved source-bearing provider results must be reconciled, not resent"},
    {"id": "g3_independent_voice_video_acceptance", "reason": "original scientific/acoustic/video evidence not fully accepted"},
    {"id": "student_release", "reason": "requires independent acceptance and separate release authorization"},
)


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _policy_hash() -> str:
    return _hash(Path(__file__).read_bytes())


def _state_dir(repo: Path, head: str) -> Path:
    local = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    require(os.name == "nt" and local.is_dir()
            and repo.resolve().is_relative_to(local.resolve())
            and re.fullmatch(r"[a-f0-9]{40}", head) is not None,
            "v7.1 supervisor requires native isolated Dell source checkout")
    base = local / "MicroGen_AI_Web_Checkpoints" / "v71_project_supervisor"
    require(not base.is_symlink() and not base.parent.is_symlink(),
            "Linked v7.1 checkpoint parent")
    base.mkdir(parents=True, exist_ok=True)
    key = (_hash(str(repo.resolve()).lower().encode())[:16] + "_"
           + head[:16] + "_" + _policy_hash()[:12])
    result = base / key
    require(not result.is_symlink(), "Linked v7.1 supervisor state")
    result.mkdir(parents=True, exist_ok=True)
    return result


def _identity(repo: Path, head: str, stage: str) -> dict:
    return {
        "schema_version": SCHEMA,
        "repository_path": str(repo),
        "source_head_sha": head,
        "supervisor_policy_sha256": _policy_hash(),
        "stage_id": stage,
        "provider_sends_authorized": False,
        "automatic_merge_authorized": False,
        "student_publication_authorized": False,
        "scientific_qa_approved": False,
    }


def _validated_log(path: Path) -> tuple[int, str]:
    if not path.exists():
        return 0, "0" * 64
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_size <= MAX_EVENTS_BYTES,
            "Unsafe persistent supervisor event log")
    count, previous = 0, "0" * 64
    for line in path.read_bytes().splitlines():
        require(line and len(line) <= 4096, "Malformed supervisor event")
        record = json.loads(line.decode("utf8"))
        claimed = record.pop("hash", None)
        require(record.get("sequence") == count + 1
                and record.get("previous_sha256") == previous
                and record.get("event") in (
                    "next_task_dispatched", "checkpoint_committed",
                    "mandatory_stop", "quarantined_uncertain_dispatch"
                )
                and claimed == _hash(json.dumps(
                    record, sort_keys=True, separators=(",", ":")
                ).encode("utf8")),
                "Supervisor event chain altered or incomplete")
        previous, count = claimed, count + 1
    return count, previous


def _event(path: Path, event: str, stage: str, **extras) -> dict:
    count, prev = _validated_log(path)
    obj = {
        "sequence": count + 1, "previous_sha256": prev,
        "event": event, "stage": stage, **extras,
    }
    obj["hash"] = _hash(json.dumps(
        obj, sort_keys=True, separators=(",", ":")
    ).encode("utf8"))
    raw = (json.dumps(obj, sort_keys=True, separators=(",", ":"))
           + "\n").encode()
    require(len(raw) < 4096
            and (path.stat().st_size if path.exists() else 0)
            + len(raw) <= MAX_EVENTS_BYTES,
            "Bounded supervisor event log exhausted")
    require(not path.is_symlink(), "Linked supervisor event log")
    with path.open("ab") as fd:
        fd.write(raw)
        fd.flush()
        os.fsync(fd.fileno())
    return obj


def _verified_result(state: Path, repo: Path, head: str, task: dict) -> dict | None:
    result_file = state / (task["id"] + ".result.json")
    if not result_file.exists():
        return None
    data = _check_envelope(result_file, _identity(repo, head, task["id"]))
    require(data.get("status") in (
                "SUPERVISOR_STAGE_CHECK_ACCEPTED_REVIEW_PENDING",
                "SUPERVISOR_STAGE_QUARANTINED",
                "SUPERVISOR_EXTERNAL_DISPATCH_UNCERTAIN")
            and type(data.get("accepted")) is bool
            and data["accepted"] == (
                data["status"] == "SUPERVISOR_STAGE_CHECK_ACCEPTED_REVIEW_PENDING")
            and type(data.get("observed_pid")) is int
            and data["observed_pid"] >= 0
            and data.get("scientific_qa_approved") is False
            and data.get("student_publication_authorized") is False,
            "Saved v7.1 task receipt cannot confer project approval")
    return data


def _board_ci_verified(repo: Path, head: str) -> bool:
    """Only real hosted exact-HEAD CI can enable the read-only board stage."""
    from .windows_exact_head_github_ci import inspect_ci
    evidence = inspect_ci(repository="tlyoon/MicroGen_AI_Web",
                          head_sha=head)
    require(evidence.get("student_publication_authorized") is False
            and evidence.get("head_sha") == head,
            "Untrusted exact-head CI evidence")
    return evidence.get("exact_head_windows_ci_verified") is True


def _worker_stage(stage: str, repo: Path) -> dict:
    """Fixed allowlist only; all stages are read-only or offline."""
    _verify_repo(repo)
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True, timeout=30,
    ).stdout.strip()
    if stage == "curated_offline_source_regressions":
        r = advance_offline(repo=repo, max_steps=MAX_STEPS)
        success = (r["offline_source_regression_pass_count"] == len(TASKS)
                   and r["pending_roadmap_task_count"] == 0)
        return {
            "accepted": success, "status": "OFFLINE_QUEUE_CHECKED",
            "selected_tasks": len(TASKS), "passed": r["offline_source_regression_pass_count"],
            "newly_executed": r["new_tasks_completed_this_process"],
            "queue_exhausted": r["pending_roadmap_task_count"] == 0,
            "local_queue_exhausted_does_not_mean_project_complete": True,
        }
    if stage == "global_historical_source_gap_inventory":
        p = plan_stack(repo=repo)
        require(p["status"] == "HISTORICAL_STACK_READ_ONLY_BATCH_PLAN_AVAILABLE"
                and p["exact_head_sha"] == head
                and p["local_worktree_clean"] is True,
                "Original source historical plan not independently established")
        selected = {t["batch"] for t in TASKS}
        all_batches = {b["batch_number"] for b in p["batches"]}
        require(selected.issubset(all_batches),
                "Queued task claimed nonexistent historical batch")
        gaps = sorted(all_batches - selected)
        return {
            "accepted": True, "status": "PROJECT_SOURCE_GAP_CATALOGUED_NOT_APPROVED",
            "historical_batch_count": len(all_batches),
            "curated_batches": len(selected),
            "uncovered_historical_batch_numbers": gaps,
            "independent_semantic_review_completed": False,
        }
    if stage == "original_g2_readonly_claim_reconciliation":
        # Original Serway 1.3 source is independently pinned; never browse or
        # resend a previous dual-PDF Gemini claim to force G2 progress.
        # This stage ONLY reconciles existing immutable source/queue evidence.
        from .g2_forward_recovery_engine import run as inspect_g2
        from .recovery_registry import lookup_mechanism
        require(lookup_mechanism(
            "global_checkpoint_handoff",
            "V71_ORIGINAL_G2_READONLY_HANDOFF_NOT_ENROLLED") == MECHANISM,
            "Original G2 no-Send handoff recovery missing or disabled")
        base = Path(os.environ["LOCALAPPDATA"]).absolute()
        checkpoint = base / "MicroGen_AI_Web_Checkpoints"
        folder = (checkpoint /
                  "auto_captionless_6528f3cfd9929c3706de" /
                  "source_tree" / "1" / "1.3")
        queue = checkpoint / "G2_20261115_SERWAY13_AI_ACADEMIC_REVIEW"
        require(folder.is_dir() and queue.is_dir()
                and not folder.is_symlink() and not queue.is_symlink()
                and folder.resolve().is_relative_to(checkpoint.resolve())
                and queue.resolve().is_relative_to(checkpoint.resolve()),
                "Original G2 source/claim inventory not safely accessible")
        checked = inspect_g2(
            folder=folder, queue_root=queue, work_root=checkpoint,
            execute=False, max_cycles=1, health_family="pro",
            auto_media=False)
        report = checked.get("current_report")
        require(checked.get("status") == "READONLY_G2_FORWARD_RECOVERY_PLAN"
                and checked.get("new_provider_requests") is False
                and checked.get("new_paid_tts_dispatched") is False
                and type(report) is dict
                and report.get("original_source_sha256")
                == "181f0f361809d90daf72fce1bf50bcf2b88fbf37fc59ed181411266b53cb5ae8"
                and report.get("student_publication_authorized") is False
                and report.get("G2_academic_scientific_acceptance_claimed") is False,
                "G2 reconciliation cannot send, modify source or approve science")
        accepted = report.get("two_pass_ai_source_agreed_segments")
        pending = report.get("pending_or_disputed_segments")
        total = report.get("expected_original_utterances")
        require(type(accepted) is int and type(pending) is int
                and type(total) is int
                and accepted >= 0 and pending >= 0
                and total == accepted + pending and total == 85,
                "Incomplete or inconsistent original G2 evidence; cannot promote")
        action = report.get("next_safe_academic_action") or {}
        require(type(action) is dict, "Unrecognized G2 source-recovery selection")
        return {
            "accepted": True,
            "status": "ORIGINAL_G2_READONLY_RECONCILED_NOT_ACADEMIC_APPROVED",
            "source_sha256": report["original_source_sha256"],
            "original_utterances": total,
            "two_pass_agreed": accepted,
            "pending_or_disputed": pending,
            "next_eligibility": action.get("status"),
            "new_model_or_paid_requests": False,
            "original_claim_replayed": False,
            "g2_academic_acceptance": False,
            "student_publication_authorized": False,
        }
    if stage == "independent_readonly_release_board":
        from .windows_release_readiness_board import inspect_release
        base = Path(os.environ["LOCALAPPDATA"]).absolute()
        checkpoint = base / "MicroGen_AI_Web_Checkpoints"
        worker = base / "MicroGen_AI_Web" / "pr493_clean_pypi_20261104" / "Scripts" / "python.exe"
        jobs = checkpoint / "20261104_PR489_WINDOWS_MULTISOURCE_JOBS_V1"
        trial = checkpoint / "20261104_PR490_FRESH_SERWAY22_1_V1"
        require(worker.is_file() and jobs.is_dir() and trial.is_dir(),
                "Existing verified local board evidence unavailable")
        board = inspect_release(
            repo=repo, jobs_dir=jobs, fresh_trial_dir=trial,
            worker_python=worker, reuse_scoped_pr362=True,
            include_stack_batches=True, execute_historical_batch_checks=True,
            classify_historical_format_findings=True,
            verify_exact_head_ci_online=True, audit_open_pr_stack_online=True,
        )
        require(board["repository_head_sha"] == head
                and board["student_publication_authorized"] is False,
                "Read-only board source or release contract changed")
        return {
            "accepted": True, "status": "READONLY_RELEASE_BOARD_EXECUTED_NOT_RELEASED",
            "board_status": board["status"],
            "engineering_technical_ready": board.get(
                "engineering_technical_release_candidate_ready"),
            "release_candidate_ready": board["release_candidate_ready"],
            "verified_source_sha": board["repository_head_sha"],
            "not_an_authorization_to_publish": True,
        }
    raise CampaignRecoveryBlocked("Unknown supervisor worker stage refused")


def _child_entry(repo: Path, stage: str, target: Path) -> int:
    try:
        outcome = _worker_stage(stage, repo)
        require(type(outcome.get("accepted")) is bool,
                "Worker omitted stage acceptance verdict")
        status = "WORKER_SOURCE_STAGE_RECORDED"
        exit_code = 0
    except (CampaignRecoveryBlocked, OSError, ValueError,
            subprocess.TimeoutExpired, KeyError, RuntimeError) as exc:
        outcome = {"accepted": False, "reason": str(exc),
                   "error_type": type(exc).__name__}
        status = "WORKER_SOURCE_STAGE_BLOCKED"
        exit_code = 2
    data = {
        "schema_version": SCHEMA, "status": status, "stage_id": stage,
        "worker_source_policy_sha256": _policy_hash(),
        "outcome": outcome,
        "student_publication_authorized": False,
    }
    _atomic_create(target, data)
    return exit_code


def _reconcile_worker_result(path: Path, stage: str) -> dict | None:
    if not path.exists():
        return None
    data = _check_envelope(path, {
        "schema_version": SCHEMA, "stage_id": stage,
        "worker_source_policy_sha256": _policy_hash(),
        "student_publication_authorized": False,
    })
    require(data["status"] in ("WORKER_SOURCE_STAGE_RECORDED",
                               "WORKER_SOURCE_STAGE_BLOCKED")
            and type(data["outcome"]) is dict
            and type(data["outcome"].get("accepted")) is bool,
            "Unexpected worker result evidence")
    return data


def _commit_stage(state: Path, repo: Path, head: str, task: dict,
                  outcome: dict, pid: int, event_file: Path) -> dict:
    result_file = state / (task["id"] + ".result.json")
    ok = (outcome.get("accepted") is True
          and outcome.get("student_publication_authorized") is not True)
    payload = {
        **_identity(repo, head, task["id"]),
        "status": ("SUPERVISOR_STAGE_CHECK_ACCEPTED_REVIEW_PENDING" if ok
                   else "SUPERVISOR_STAGE_QUARANTINED"),
        "accepted": ok, "observed_pid": pid,
        "stage_evidence": outcome,
    }
    _atomic_create(result_file, payload)
    _event(event_file, "checkpoint_committed", task["id"],
           accepted=ok, observed_pid=pid)
    return payload


def _admit_long_source_queue_timeout(task: dict) -> None:
    """Registered source-only recovery after 47/48 tasks hit the old 900-s limit.

    This changes a bounded no-network *local* wait, not any Gemini/TTS Send,
    academic approval, original-source claim, or student release boundary.
    """
    if task["id"] != "curated_offline_source_regressions":
        return
    from .recovery_registry import lookup_mechanism
    require(lookup_mechanism("global_checkpoint_handoff",
                             LONG_QUEUE_TIMEOUT_SIGNATURE)
            == LONG_QUEUE_TIMEOUT_MECHANISM
            and type(task["timeout"]) is int
            and 900 < task["timeout"] <= 3600,
            "Long offline source-queue watchdog absent or outside finite bounds")


def _dispatch(repo: Path, state: Path, head: str, task: dict,
              event_file: Path, *, launcher=subprocess.Popen) -> dict:
    _admit_long_source_queue_timeout(task)
    identity = _identity(repo, head, task["id"])
    intent = state / (task["id"] + ".intent.json")
    worker_result = state / (task["id"] + ".worker-result.json")
    old = _verified_result(state, repo, head, task)
    if old is not None:
        return old
    if intent.exists():
        _check_envelope(intent, {**identity,
            "status": "SUPERVISOR_STAGE_DISPATCH_INTENT"})
        observed = _reconcile_worker_result(worker_result, task["id"])
        if observed is None:
            # Process may still be running, or completion/Send may be
            # uncertain. Never silently replay a claimed operation.
            result_file = state / (task["id"] + ".result.json")
            data = {**identity, "status": "SUPERVISOR_EXTERNAL_DISPATCH_UNCERTAIN",
                    "accepted": False, "observed_pid": 0,
                    "stage_evidence": {"reason": "claimed operation has no verified worker result; not replayed"}}
            _atomic_create(result_file, data)
            _event(event_file, "quarantined_uncertain_dispatch", task["id"])
            return data
        return _commit_stage(
            state, repo, head, task, observed["outcome"], 0, event_file)
    _atomic_create(intent, {
        **identity, "status": "SUPERVISOR_STAGE_DISPATCH_INTENT",
    })
    log = state / (task["id"] + ".worker-log.txt")
    require(not log.exists() and not log.is_symlink(),
            "Would overwrite worker start evidence")
    command = [
        sys.executable, "-B", "-m",
        "selenium_pipeline.windows_v71_project_supervisor",
        "--worker-stage", task["id"], "--repo", str(repo),
        "--worker-result", str(worker_result),
    ]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with log.open("xb") as output:
        proc = launcher(command, cwd=repo, env=env,
                        stdin=subprocess.DEVNULL,
                        stdout=output, stderr=subprocess.STDOUT)
        require(type(proc.pid) is int and proc.pid > 0,
                "Supervisor did not actually dispatch a Windows child worker")
        _event(event_file, "next_task_dispatched", task["id"],
               observed_pid=proc.pid)
        try:
            code = proc.wait(timeout=task["timeout"])
        except subprocess.TimeoutExpired:
            # Historical 900-s failure killed the outer worker while its
            # final source-only test child was still outstanding. Reuse
            # the existing Windows process-tree cleanup, not PID-only kill.
            kill_descendants(proc)
            code = 124
    _verify_repo(repo)
    verified = _reconcile_worker_result(worker_result, task["id"])
    if verified is None:
        outcome = {"accepted": False,
                   "status": "WORKER_DID_NOT_RECORD_OUTCOME",
                   "exit_code": code}
    else:
        outcome = verified["outcome"]
        require((code == 0) == (verified["status"] == "WORKER_SOURCE_STAGE_RECORDED"),
                "Child process exit disagrees with verified result receipt")
    return _commit_stage(state, repo, head, task, outcome, proc.pid, event_file)


def supervise(repo: Path, *, max_new_dispatches: int = len(STAGES)) -> dict:
    from .recovery_registry import lookup_mechanism
    require(lookup_mechanism("global_checkpoint_handoff", SIGNATURE)
            == MECHANISM,
            "v7.1 executable global supervisor disabled")
    require(type(max_new_dispatches) is int
            and 1 <= max_new_dispatches <= len(STAGES),
            "v7.1 max dispatched stages must be finite")
    repo = Path(repo).absolute()
    _verify_repo(repo)
    plan = plan_stack(repo=repo)
    require(plan["status"] == "HISTORICAL_STACK_READ_ONLY_BATCH_PLAN_AVAILABLE"
            and plan["local_worktree_clean"] is True,
            "Global source roadmap needs exact clean Git history")
    head = plan["exact_head_sha"]
    state = _state_dir(repo, head)
    event_file = state / "events.jsonl"
    lock_id = _hash(str(repo.resolve()).lower().encode())[:20]
    executed, prior = [], []
    with LocalInstanceLock("v71_supervisor_" + lock_id,
                           state.parent / "locks"):
        _verify_repo(repo)
        _validated_log(event_file)
        # GLOBAL scan: independent stages are eligible even when a local
        # queue is exhausted or another independent source task failed.
        for task in STAGES:
            saved = _verified_result(state, repo, head, task)
            if saved is not None:
                prior.append(saved)
                continue
            dependencies = [s for s in (*prior, *executed)
                            if s["stage_id"] in task["deps"]]
            if len(dependencies) != len(task["deps"]) or any(
                    not s["accepted"] for s in dependencies):
                continue
            if (task["id"] == "independent_readonly_release_board"
                    and not _board_ci_verified(repo, head)):
                # Future CI completion is an external dependency, not a
                # pretext to checkpoint a stale or falsely green board.
                continue
            if len(executed) >= max_new_dispatches:
                break
            record = _dispatch(repo, state, head, task, event_file)
            executed.append(record)
        _verify_repo(repo)
        all_records = [
            _verified_result(state, repo, head, task)
            for task in STAGES
        ]
        next_pending = [
            task["id"] for task, receipt in zip(STAGES, all_records)
            if receipt is None
        ]
        # Never label current project COMPLETE just because the local queue
        # or read-only preview finished; source science/voice/PR/release remain.
        reason = (
            "EXECUTION_WINDOW_LIMIT_NEXT_STAGE_NOT_STARTED"
            if next_pending and len(executed) >= max_new_dispatches else
            "EXTERNAL_CI_OR_DEPENDENCIES_BLOCK_NEXT_STAGE_NOT_STARTED"
            if next_pending else
            "LOCAL_SAFE_ROADMAP_EXHAUSTED_PROJECT_QA_REMAINS_BLOCKED"
        )
        if not next_pending or len(executed) >= max_new_dispatches or next_pending:
            _event(event_file, "mandatory_stop", "project_wide_backlog",
                   reason=reason, pending_stages=next_pending)
    return {
        "status": "V71_GLOBAL_HANDOFF_VERIFIED_REVIEW_PENDING",
        "source_head_sha": head,
        "current_roadmap_stage_count": len(STAGES),
        "verified_stage_receipts": sum(r is not None for r in all_records),
        "new_stage_dispatches_this_process": len(executed),
        "observable_dispatch_pids": [
            r["observed_pid"] for r in executed if r["observed_pid"] > 0
        ],
        "next_not_started_stages": next_pending,
        "blocked_project_workstreams": BLOCKED_WORKSTREAMS,
        "events_file": str(event_file),
        "persistent_supervisor_installed_and_running_after_exit": False,
        "background_continuation_verified": False,
        "current_local_queue_completion_is_not_project_completion": True,
        "automatic_merge_authorized": False,
        "scientific_qa_approved": False,
        "student_publication_authorized": False,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path,
                    default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--max-new-dispatches", type=int, default=len(STAGES))
    ap.add_argument("--worker-stage", choices=[s["id"] for s in STAGES])
    ap.add_argument("--worker-result", type=Path)
    a = ap.parse_args(argv)
    try:
        if a.worker_stage:
            require(a.worker_result is not None
                    and a.worker_result.parent.is_dir()
                    and a.worker_result.name ==
                    a.worker_stage + ".worker-result.json",
                    "Only supervisor-owned finite worker receipts supported")
            repo = a.repo.absolute()
            _verify_repo(repo)
            githead = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True, timeout=30,
            ).stdout.strip()
            require(a.worker_result.parent.resolve()
                    == _state_dir(repo, githead).resolve(),
                    "Worker evidence directory is not source/HEAD-owned")
            return _child_entry(a.repo.absolute(), a.worker_stage,
                                a.worker_result)
        require(a.worker_result is None, "Untrusted worker receipt argument")
        result = supervise(a.repo, max_new_dispatches=a.max_new_dispatches)
    except (CampaignRecoveryBlocked, OSError, ValueError, KeyError,
            subprocess.TimeoutExpired, subprocess.CalledProcessError,
            RuntimeError) as exc:
        result = {
            "status": "V71_GLOBAL_SUPERVISOR_BLOCKED",
            "reason": str(exc),
            "persistent_supervisor_installed_and_running_after_exit": False,
            "next_action_started": False,
            "automatic_merge_authorized": False,
            "student_publication_authorized": False,
        }
        print(json.dumps(result, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if not result["next_not_started_stages"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
