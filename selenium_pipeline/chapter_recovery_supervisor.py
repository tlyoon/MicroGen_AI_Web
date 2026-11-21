"""Persistent single-PC chapter recovery coordinator.

Never infer success from a completed *attempt*: verify every source-bound
lecture receipt. Defer unresolved jobs with finite, increasing backoff while
continuing to monitor them without a ChatGPT conversation or background API.
The child worker has per-stage timeouts, per-PC locks, and send-claim guards.
"""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from .cleanup import completed_lecture
from .three_pc_worker import LocalInstanceLock, assigned_jobs


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _read(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scratch = path.with_name(path.name + ".pending")
    scratch.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
    scratch.replace(path)


def _publish_status(state_path: Path, root: Path, worker: str,
                    chapter: int, state: dict) -> None:
    """Keep local checkpoint authoritative; mirror status to shared Drive."""
    _write(state_path, state)
    shared = root / ".microgen_coordination" / (
        f"{worker.lower()}_chapter_{chapter}_supervisor.json")
    try:
        _write(shared, state)
    except OSError as exc:
        print("[chapter-supervisor] shared status mirror delayed: "
              f"{type(exc).__name__}", flush=True)


def _code_fingerprint() -> str:
    """A verified code repair wakes deferred jobs without waiting for cadence."""
    package = Path(__file__).resolve().parent
    names = (
        "three_pc_worker.py", "chapter_recovery_supervisor.py",
        "vendor_template_v2/gen_slides_selenium_v11.py",
        "source_caption_figure_chain_v1.py", "source_crop_overrides_v1.json",
        "slide_transport_guard.py",
    )
    digest = hashlib.sha256()
    for name in names:
        file = package / name
        digest.update(name.encode("utf-8"))
        if file.is_file():
            digest.update(file.read_bytes())
    return digest.hexdigest()


def _next_delay_hours(stalled: int, base_hours: float) -> float:
    """Repeated unchanged failures back off instead of pounding Gemini."""
    if stalled >= 4:
        return max(base_hours, 72.0)
    if stalled >= 2:
        return max(base_hours, 24.0)
    return base_hours


def _verified(root: Path, chapter: int) -> tuple[list[str], list[str]]:
    all_jobs = assigned_jobs(root, [chapter])
    completed = []
    for sub in all_jobs:
        try:
            if completed_lecture(root / str(chapter) / sub / "source.pdf"):
                completed.append(sub)
        except Exception:
            pass
    return all_jobs, completed


def _signature(report: dict) -> str:
    jobs = report.get("jobs", {})
    if not isinstance(jobs, dict):
        return "UNREADABLE_WORKER_REPORT"
    failed = sorted((name, info.get("stage", ""),
                     str(info.get("error", "")).split("; see", 1)[0])
                    for name, info in jobs.items()
                    if isinstance(info, dict) and info.get("status") != "complete")
    return json.dumps(failed, sort_keys=True)


def cycle(*, source_root: Path, chapter: int, worker: str, run_prefix: str,
          python: Path, state_dir: Path, base_retry_hours: float = 6,
          chrome_port: int = 9222, now=None, launch=None) -> dict:
    """Run exactly one chapter pass; unit tests may inject a fake worker."""
    root = source_root.resolve()
    if not root.is_dir() or not python.is_file():
        raise FileNotFoundError("Chapter source root or selected Python missing")
    stamp = now or utc_now()
    state_path = state_dir / "supervisor.json"
    state = _read(state_path)
    all_jobs, complete_before = _verified(root, chapter)
    if not all_jobs:
        raise RuntimeError("No source PDFs in requested chapter")
    if len(complete_before) == len(all_jobs):
        state.update(phase="completed", completed=complete_before, unfinished=[],
                     updated_utc=stamp.isoformat())
        _publish_status(state_path, root, worker, chapter, state)
        return state
    code_sha = _code_fingerprint()
    previous_code_sha = state.get("code_fingerprint")
    next_retry = state.get("next_retry_utc")
    if (next_retry and state.get("phase") == "recovery_pending"
            and state.get("code_fingerprint") == code_sha):
        try:
            when = datetime.fromisoformat(next_retry)
        except (ValueError, TypeError):
            when = stamp
        if when > stamp:
            return state
    # A crashed worker may have an incomplete active run; reuse its identity.
    if state.get("phase") == "running" and state.get("active_run_id"):
        run_id = state["active_run_id"]
        attempt = int(state.get("attempt", 1))
    else:
        attempt = int(state.get("attempt", 0)) + 1
        run_id = f"{run_prefix}_r{attempt:04d}"
    control = root / ".microgen_coordination" / run_id
    manifest = control / "assignments.json"
    mapping = {"run_id": run_id, "assignments": {worker: [chapter]},
               "source_roots": {worker: str(root)}}
    if manifest.exists():
        prior = _read(manifest)
        if prior != mapping:
            raise RuntimeError("Existing chapter assignment manifest differs")
    else:
        _write(manifest, mapping)
    state.update(phase="running", attempt=attempt, active_run_id=run_id,
                 chapter=chapter, worker=worker, assigned=all_jobs,
                 started_cycle_utc=stamp.isoformat(), code_fingerprint=code_sha)
    _publish_status(state_path, root, worker, chapter, state)
    command = [
        str(python), "-u", "-m", "selenium_pipeline.three_pc_worker",
        "--source-root", str(root), "--run-id", run_id, "--worker", worker,
        "--chapters", str(chapter), "--pipeline-python", str(python),
        "--tts-python", str(python), "--chrome-port", str(chrome_port),
        "--idle-seconds", "1800", "--hard-seconds", "7200",
    ]
    log_path = state_dir / (run_id + ".log")
    if launch is None:
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        with log_path.open("a", encoding="utf-8") as log:
            with subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL, env=env,
                                  cwd=str(Path(__file__).resolve().parents[1])) as proc:
                exit_code = proc.wait()
    else:
        exit_code = launch(command, manifest)
    report = _read(control / (worker + ".json"))
    _, verified_after = _verified(root, chapter)
    failed = [sub for sub in all_jobs if sub not in verified_after]
    signature = _signature(report)
    repeats = (int(state.get("unchanged_failure_rounds", 0)) + 1
               if (signature == state.get("previous_failure_signature")
                   and previous_code_sha == code_sha) else 0)
    state.update(
        completed=verified_after, unfinished=failed,
        last_worker_exit=int(exit_code), last_worker_phase=report.get("phase"),
        previous_failure_signature=signature, unchanged_failure_rounds=repeats,
        updated_utc=stamp.isoformat(), active_run_id=None,
    )
    if failed:
        state["phase"] = "recovery_pending"
        delay = _next_delay_hours(repeats, base_retry_hours)
        state["next_retry_utc"] = (stamp + timedelta(hours=delay)).isoformat()
    else:
        state["phase"] = "completed"
        state.pop("next_retry_utc", None)
    _publish_status(state_path, root, worker, chapter, state)
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--chapter", type=int, required=True)
    parser.add_argument("--worker", default="HP")
    parser.add_argument("--run-prefix", default="chapter_recovery")
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--chrome-port", type=int, default=9222)
    parser.add_argument("--retry-hours", type=float, default=6.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=120)
    args = parser.parse_args(argv)
    if not 1 <= args.chapter <= 99 or not 0.5 <= args.retry_hours <= 168:
        parser.error("Invalid chapter or recovery interval")
    if not args.run_prefix.replace("_", "").isalnum():
        parser.error("Run prefix must contain letters, digits and underscores")
    local = Path(os.getenv("LOCALAPPDATA") or (Path.home() / ".cache"))
    state_dir = args.state_dir or (
        local / "Microvid" / "chapter_supervisors" /
        f"{args.worker.lower()}_chapter_{args.chapter}")
    state_dir.mkdir(parents=True, exist_ok=True)
    with LocalInstanceLock(
        f"chapter_{args.worker}_{args.chapter}",
        local / "Microvid" / "worker_locks"
    ):
        while True:
            try:
                record = cycle(source_root=args.source_root, chapter=args.chapter,
                               worker=args.worker, run_prefix=args.run_prefix,
                               python=args.python, state_dir=state_dir,
                               base_retry_hours=args.retry_hours,
                               chrome_port=args.chrome_port)
            except Exception as exc:
                # A temporarily missing Drive mount or transient process
                # error must not silently dismantle the persistent executor.
                # Leave the authoritative stage/checkpoint receipts untouched.
                health = {"status": "RECOVERY_BLOCKED_RETRY_SCHEDULED",
                          "last_error_type": type(exc).__name__,
                          "updated_utc": utc_now().isoformat()}
                _write(state_dir / "supervisor_health.json", health)
                print(f"[chapter-supervisor] transient run blocker: "
                      f"{type(exc).__name__}; preserving checkpoints", flush=True)
                if args.once:
                    return 3
                time.sleep(max(120, min(1800, args.poll_seconds * 5)))
                continue
            print(f"[chapter-supervisor] phase={record['phase']} "
                  f"completed={len(record.get('completed', []))} "
                  f"unfinished={len(record.get('unfinished', []))} "
                  f"next={record.get('next_retry_utc', '-')}", flush=True)
            if record["phase"] == "completed":
                return 0
            if args.once:
                return 2
            time.sleep(max(30, min(1800, args.poll_seconds)))


if __name__ == "__main__":
    raise SystemExit(main())
