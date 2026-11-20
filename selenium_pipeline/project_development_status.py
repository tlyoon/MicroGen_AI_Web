"""Fail-closed project-wide status evidence, NOT an autonomous coding agent.

The v7.1 six-stage source-only supervisor cannot author scientific reviews or
software changes. A verified Task Scheduler success is not project completion.
All status evidence is read-only, with atomic, restart-safe status/alert files.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

SCHEMA = 1
SOURCE_TASK = "MicroGen_AI_Web_v71_SourceOnly"
MONITOR_TASK = "MicroGen_AI_Web_v71_StatusMonitor"
SAFE_CHECKPOINT = "MicroGen_AI_Web_Checkpoints"
MAX_AGE_SECONDS = 75 * 60
PROJECT_DEPENDENCIES = (
    "software_and_recovery_integration",
    "original_g2_scientific_two_pass",
    "independent_g3_acoustic_video_second_subsection",
    "independent_release_and_publication_gates",
)


def require(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError(why)


def _utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_size <= 150_000, "Unsafe status input")
    result = json.loads(path.read_text(encoding="utf8"))
    require(type(result) is dict, "Status input is not an object")
    return result


def _utc_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, OverflowError):
        return None


def _task_snapshot() -> dict:
    """Native task state and exact source-only provenance; zero state changes."""
    if os.name != "nt":
        return {"source": {"state": "UNAVAILABLE"},
                "monitor": {"state": "UNAVAILABLE"}}
    script = (
        "$ErrorActionPreference='Stop';$r=@();"
        "foreach($n in @('MicroGen_AI_Web_v71_SourceOnly',"
        "'MicroGen_AI_Web_v71_StatusMonitor')){"
        "$t=Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue;"
        "if($null -eq $t){$r+=@{name=$n;state='MISSING'};continue};"
        "$i=Get-ScheduledTaskInfo -TaskName $n -ErrorAction Stop;"
        "$r+=@{name=$n;state=[string]$t.State;"
        "last_result=[int]$i.LastTaskResult;"
        "last_run=$i.LastRunTime.ToUniversalTime().ToString('o');"
        "next_run=$i.NextRunTime.ToUniversalTime().ToString('o');"
        "action=[string]$t.Actions[0].Execute;"
        "user=[string]$t.Principal.UserId;"
        "run_level=[string]$t.Principal.RunLevel;"
        "logon=[string]$t.Principal.LogonType}};"
        "@($r)|ConvertTo-Json -Compress -Depth 3"
    )
    p = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=25)
    require(p.returncode == 0 and 0 < len(p.stdout) <= 12000,
            "Native Task Scheduler inspection failed")
    raw = json.loads(p.stdout)
    require(type(raw) is list and len(raw) == 2,
            "Cannot attribute native task identities")
    mapped = {x["name"]: x for x in raw}
    require(set(mapped) == {SOURCE_TASK, MONITOR_TASK}, "Wrong native tasks")
    return {"source": mapped[SOURCE_TASK], "monitor": mapped[MONITOR_TASK]}


def _local_sourceonly_cycle(checkpoint: Path) -> dict:
    folder = checkpoint / "v71_scheduled_resume_v1"
    require(not folder.is_symlink(), "Linked task run directory")
    if not folder.is_dir():
        return {"status": "NO_CYCLE_RECEIPT"}
    paths = sorted(folder.glob("run_*.json"), reverse=True)
    if not paths:
        return {"status": "NO_CYCLE_RECEIPT"}
    receipt = _safe_json(paths[0])
    require(receipt is not None and receipt.get("status") in {
        "PERSISTENT_SOURCE_ONLY_CHECKPOINT_CYCLE_RECONCILED",
        "PERSISTENT_SOURCE_ONLY_CYCLE_BLOCKED",
    }, "Malformed latest source-only receipt")
    return {
        "status": receipt["status"], "receipt": paths[0].name,
        "last_receipt_unix": paths[0].stat().st_mtime,
        "verified_stage_receipts": receipt.get("verified_stage_receipts"),
        "new_stage_dispatches": receipt.get("new_stage_dispatches"),
        "pending_stages": receipt.get("pending_stages"),
        "source_head_sha": receipt.get("source_head_sha"),
    }


def _g2_progress(checkpoint: Path) -> dict:
    """Independently reconcile the REAL original review queue, never guess."""
    queue = checkpoint / "G2_20261115_SERWAY13_AI_ACADEMIC_REVIEW"
    if not queue.is_dir() or queue.is_symlink():
        return {"status": "G2_EVIDENCE_UNAVAILABLE", "accepted": None,
                "total": None, "complete": False}
    try:
        from .ai_academic_review_consensus import reconcile_actual_review_queue
        plan = _safe_json(queue / "queue.json")
        require(plan is not None and
                plan.get("status") == "IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
                "Wrong original G2 queue")
        folder = Path(plan["original_source_folder"]).absolute()
        result = reconcile_actual_review_queue(queue_root=queue, folder=folder)
        accepted = len(result["accepted_ai_evidence"])
        total = result["original_utterances"]
        remaining = result["pending_or_disputed"]
        require(result["status"] ==
                "INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE"
                and type(accepted) is int and type(total) is int
                and type(remaining) is int and total > 0
                and accepted + remaining == total,
                "Invalid independent G2 consensus count")
        return {"status": "SOURCE_REVIEW_UNFINISHED" if remaining else
                "TWO_PASS_SOURCE_REVIEW_RECORDED_NOT_G3",
                "accepted": accepted, "total": total, "pending": remaining,
                "complete": False}
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        return {"status": "G2_EVIDENCE_UNVERIFIABLE",
                "error_type": type(exc).__name__,
                "accepted": None, "total": None, "complete": False}


def _heartbeat(checkpoint: Path) -> dict | None:
    return _safe_json(checkpoint / "development_status_v1" /
                      "sourceonly_supervisor_heartbeat.json")


def evaluate(*, now: float, tasks: dict, cycle: dict,
             g2: dict, heartbeat: dict | None,
             development_worker_attested: bool = False) -> dict:
    """Pure classifier; failures take precedence over optimistic completion."""
    require(type(now) in (float, int) and 0 < now < 1e12,
            "Invalid observation timestamp")
    source = tasks.get("source") or {}
    monitor = tasks.get("monitor") or {}
    problems = []
    if source.get("state") not in ("Ready", "Running"):
        problems.append("SOURCE_ONLY_SCHEDULE_NOT_ENABLED")
    if source.get("state") in ("Ready", "Running") and (
            source.get("run_level") != "Limited"
            or source.get("logon") != "Interactive"):
        problems.append("SOURCE_ONLY_TASK_PRINCIPAL_UNVERIFIED")
    if source.get("last_result") not in (0, None):
        problems.append("SOURCE_ONLY_LAST_RUN_FAILED")
    if cycle.get("status") == "PERSISTENT_SOURCE_ONLY_CYCLE_BLOCKED":
        problems.append("SOURCE_ONLY_RUN_RECEIPT_BLOCKED")
    last = _utc_seconds(source.get("last_run"))
    # Native tasks with no prior run often report year 1899 or year 1.
    if (source.get("state") in ("Ready", "Running")
            and last is not None and last > 1577836800
            and now-last > MAX_AGE_SECONDS):
        problems.append("SOURCE_ONLY_MISSED_MORE_THAN_TWO_INTERVALS")
    if heartbeat is not None:
        require(heartbeat.get("schema_version") == 1
                and heartbeat.get("worker_kind") == "source_only"
                and heartbeat.get("phase") in ("RUNNING", "IDLE", "BLOCKED")
                and type(heartbeat.get("updated_unix")) in (int, float),
                "Invalid supervisor heartbeat provenance")
        age = now - heartbeat["updated_unix"]
        if (heartbeat["phase"] == "RUNNING"
                and age > MAX_AGE_SECONDS):
            problems.append("SOURCE_ONLY_SUPERVISOR_HEARTBEAT_STALE")
    if monitor.get("state") not in ("Ready", "Running"):
        problems.append("STATUS_WATCHDOG_TASK_NOT_ENABLED")
    if g2.get("status") == "G2_EVIDENCE_UNVERIFIABLE":
        problems.append("G2_SOURCE_CONSENSUS_UNVERIFIABLE")
    # No current installed worker has demonstrably claimed persistent,
    # permissioned code development. The finite six-stage source-only worker
    # can never satisfy this condition or a project's final acceptance.
    if not development_worker_attested:
        problems.append("AUTONOMOUS_DEVELOPMENT_EXECUTOR_NOT_VERIFIED")
    if any("MISSED_MORE_THAN" in p or "HEARTBEAT_STALE" in p
           for p in problems):
        status = "STALLED"
    elif any(p for p in problems if p != "AUTONOMOUS_DEVELOPMENT_EXECUTOR_NOT_VERIFIED"):
        status = "BLOCKED"
    elif development_worker_attested:
        # Future full-development supervisor must establish independent
        # process/heartbeat/job evidence BEFORE setting this flag.
        status = "RUNNING"
    else:
        status = "PENDING"  # no verified ongoing development worker
    return {
        "schema_version": SCHEMA, "status": status,
        "observed_utc": _utc(now),
        "project_complete": False,
        "project_completion_verified": False,
        "g2": g2,
        "g3_acoustic_video_verified": False,
        "student_release_authorized": False,
        "development_worker_attested": development_worker_attested,
        "monitor_task": monitor.get("state", "UNKNOWN"),
        "source_only_task": source.get("state", "UNKNOWN"),
        "source_only_last_result": source.get("last_result"),
        "source_only_last_run_utc": source.get("last_run"),
        "source_only_next_run_utc": source.get("next_run"),
        "source_only_cycle": cycle,
        "source_only_worker_heartbeat": (
            heartbeat.get("phase") if heartbeat else "NOT_RECORDED"),
        "blockers": problems,
        "unresolved_project_workstreams": list(PROJECT_DEPENDENCIES),
        "next_authorized_action": (
            "Investigate reported scheduler/source evidence; preserve original claims"
            if status in ("STALLED", "BLOCKED") else
            "Continue the verified running development worker and monitor its heartbeat"
            if status == "RUNNING" else
            "Dispatch eligible roadmap work through a real authorized development worker"),
        "no_provider_sends_or_automatic_merge_or_publication": True,
        "source_only_completion_is_not_project_completion": True,
    }


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.parent.is_symlink()
            and not path.is_symlink(), "Unsafe report destination")
    tmp = path.with_name(path.name + "." + str(os.getpid()) + ".tmp")
    require(not tmp.exists() and not tmp.is_symlink(),
            "Competing status update in progress")
    with tmp.open("xb") as fd:
        fd.write(payload)
        fd.flush()
        os.fsync(fd.fileno())
    os.replace(tmp, path)


def _report_md(state: dict) -> str:
    g2 = state["g2"]
    count = (f'{g2.get("accepted")}/{g2.get("total")} accepted'
             if g2.get("accepted") is not None else 'unverified')
    blockers = "\n".join("- " + b for b in state["blockers"]) or "- None identified"
    return (
        "# MicroGen_AI_Web — Development Status\n\n"
        f'**Observed:** {state["observed_utc"]}\n\n'
        f'**Operational state:** {state["status"]}\n\n'
        "**Project complete:** NO — source-only success is not G2/G3/release.\n\n"
        f'**Source-only Windows task:** {state["source_only_task"]}'
        f' (last result {state["source_only_last_result"]})\n\n'
        f'**Status monitor task:** {state["monitor_task"]}\n\n' +
        ("**Persistent autonomous development worker:** VERIFIED.\n\n"
         if state["development_worker_attested"] else
         "**Persistent autonomous development worker:** NOT VERIFIED.\n\n") +
        f'**Original G2:** {count}; independent source agreement only.\n\n'
        "**G3:** not independently accepted. **Student release:** not authorized.\n\n"
        "## Blockers and missing capabilities\n\n" + blockers +
        "\n\n## Next action\n\n" +
        state["next_authorized_action"] +
        "\n\nThis file is a read-only monitoring report, not proof that code "
        "development, paid model calls, or scientific QA are running.\n"
    )


def publish(checkpoint: Path, state: dict, *, drive_root: Path | None) -> dict:
    home = checkpoint / "development_status_v1"
    home.mkdir(parents=True, exist_ok=True)
    require(not home.is_symlink(), "Linked watchdog report directory")
    raw = (json.dumps(state, indent=2, sort_keys=True) + "\n").encode()
    md = _report_md(state).encode()
    previous = _safe_json(home / "STATUS.json")
    if previous is not None and (
        previous.get("status") != state["status"]
        or previous.get("blockers") != state["blockers"]
    ):
        # Durable deduplicated local status-change notice for a separate
        # notification adapter. Never claim a push notification was sent.
        notice = {
            "time_utc": state["observed_utc"], "old": previous.get("status"),
            "new": state["status"], "blockers": state["blockers"],
            "notification_delivered": False,
        }
        path = home / "ALERT_STATUS_CHANGE.json"
        _atomic_write(path, (json.dumps(notice, indent=2) + "\n").encode())
    _atomic_write(home / "STATUS.json", raw)
    _atomic_write(home / "STATUS.md", md)
    drive_written = False
    if drive_root is not None and drive_root.is_dir() and (
        str(drive_root).lower().endswith("my drive")):
        external = drive_root / "MicroGen_AI_Web_Development_Status"
        require(not external.is_symlink() and
                not (external / "STATUS.md").is_symlink(),
                "Unsafe Drive-synced destination")
        _atomic_write(external / "STATUS.json", raw)
        _atomic_write(external / "STATUS.md", md)
        drive_written = (
            (external / "STATUS.json").read_bytes() == raw and
            (external / "STATUS.md").read_bytes() == md)
    return {"status": "MONITOR_REPORT_ATOMICALLY_WRITTEN",
            "local_path": str(home / "STATUS.md"),
            "drive_mirror_written_locally": drive_written,
            "drive_sync_to_cloud_independently_verified": False,
            "new_model_requests": 0, "project_complete_claimed": False}


def report_once(*, checkpoint: Path, drive_root: Path | None = None,
                now: float | None = None, task_reader=None) -> dict:
    from .recovery_registry import lookup_mechanism
    require(lookup_mechanism(
        "development_status_watchdog",
        "V71_PROJECT_TASK_DISABLED_STALE_OR_HEARTBEAT_MISSING") ==
        "INSPECT_NATIVE_TASK_AND_REPORT_VERIFIED_STALL_WITHOUT_UNSAFE_REPLAY",
        "Project status watchdog recovery not registered")
    checkpoint = Path(checkpoint).absolute()
    require(checkpoint.name == SAFE_CHECKPOINT
            and checkpoint.is_dir() and not checkpoint.is_symlink(),
            "Watchdog may inspect only existing MicroGen checkpoints")
    from .three_pc_worker import LocalInstanceLock
    home = checkpoint / "development_status_v1"
    home.mkdir(parents=True, exist_ok=True)
    with LocalInstanceLock("v71_project_status_watchdog",
                           home / "locks"):
        tasks = (task_reader or _task_snapshot)()
        state = evaluate(
            now=time.time() if now is None else now,
            tasks=tasks, cycle=_local_sourceonly_cycle(checkpoint),
            g2=_g2_progress(checkpoint), heartbeat=_heartbeat(checkpoint))
        out = publish(checkpoint, state, drive_root=drive_root)
    return {"status": state["status"],
            "observed_utc": state["observed_utc"],
            "blockers": state["blockers"], "g2": state["g2"],
            **out}


def record_sourceonly_heartbeat(*, checkpoint: Path, head: str,
                                phase: str, stage: str) -> None:
    """Advisory only; never allow monitoring failure to weaken QA."""
    require(phase in ("RUNNING", "IDLE", "BLOCKED") and
            re.fullmatch(r"[a-f0-9]{40}", head) and
            type(stage) is str and len(stage) <= 90,
            "Invalid source-only progress evidence")
    payload = {
        "schema_version": SCHEMA, "worker_kind": "source_only",
        "worker_pid": os.getpid(), "source_head_sha": head,
        "updated_unix": time.time(), "phase": phase, "stage": stage,
        "no_provider_sends": True, "project_complete": False,
    }
    _atomic_write(
        Path(checkpoint) / "development_status_v1" /
        "sourceonly_supervisor_heartbeat.json",
        (json.dumps(payload, sort_keys=True) + "\n").encode())


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path)
    p.add_argument("--drive-root", type=Path)
    args = p.parse_args(argv)
    try:
        require(os.name == "nt" and
                os.environ.get("COMPUTERNAME", "").casefold() == "dell-115",
                "Status monitoring confined to Dell-115")
        root = args.checkpoint or (
            Path(os.environ["LOCALAPPDATA"]) / SAFE_CHECKPOINT)
        drive = args.drive_root or Path("G:/My Drive")
        result = report_once(checkpoint=root, drive_root=drive)
        print(json.dumps(result, indent=2))
        return 0  # BLOCKED/STALLED are valid watchdog observations
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as e:
        print(json.dumps({
            "status": "WATCHDOG_INSPECTION_FAILED",
            "reason_type": type(e).__name__,
            "project_complete_claimed": False,
        }))
        return 2


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(main())
