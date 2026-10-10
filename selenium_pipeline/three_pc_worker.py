"""Sequential per-PC worker for distributed, resumable MicroGen production.

Each PC owns disjoint chapters from an immutable manifest. It runs each
subchapter's stages strictly in order, defers any blocked subchapter, then
revisits deferred work after the first full pass through its own queue.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import queue
import re
import socket
import subprocess
import sys
import threading
import time

if os.name == "nt":
    import msvcrt
else:
    import fcntl

from datetime import datetime, timezone
from pathlib import Path

from .cleanup import completed_lecture

# Avoid a worker crash when old template scripts emit Unicode status symbols
# into a Windows terminal whose default code page is cp1252.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')

STAGES = ("figures", "slides", "narration", "script_qa", "tts", "tts_qa", "video")
RUNNER_ID = re.compile(r"^[A-Za-z0-9_-]+$")
SOURCE_RE = re.compile(r"^[0-9]+[.][0-9]+$")


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def assigned_jobs(root: Path, chapters: list[int]) -> list[str]:
    jobs: list[str] = []
    for chapter in chapters:
        directory = root / str(chapter)
        if not directory.is_dir():
            raise FileNotFoundError(f"Assigned chapter is unavailable: {directory}")
        for subfolder in sorted(directory.iterdir(), key=lambda p: tuple(int(x) for x in p.name.split(".")) if SOURCE_RE.fullmatch(p.name) else (9999,)):
            if (subfolder.is_dir() and SOURCE_RE.fullmatch(subfolder.name)
                    and subfolder.name.split(".", 1)[0] == str(chapter)
                    and (subfolder / "source.pdf").is_file()):
                jobs.append(subfolder.name)
    return jobs


def validate_manifest(path: Path, worker: str, chapters: list[int], root: Path | None = None) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    roles = manifest.get("assignments")
    if not isinstance(roles, dict):
        raise ValueError("Missing run assignment manifest")
    occupied: set[int] = set()
    for name, values in roles.items():
        if not isinstance(values, list) or not all(type(v) is int for v in values):
            raise ValueError(f"Invalid chapter assignment for {name}")
        for ch in values:
            if ch in occupied:
                raise ValueError(f"Chapter {ch} has two owners: racing job assignments")
            occupied.add(ch)
    if roles.get(worker) != chapters:
        raise ValueError(f"{worker} expected {roles.get(worker)!r}, received {chapters!r}")
    if not chapters:
        raise ValueError("Worker has no chapters")
    local_root = root or path.parent.parent.parent
    mapping = manifest.get("source_roots")
    if mapping is not None:
        if not isinstance(mapping, dict) or not isinstance(mapping.get(worker), str):
            raise ValueError(f"Manifest missing source root for {worker}")
        assigned_root = Path(mapping[worker])
    else:
        if not isinstance(manifest.get("source_root"), str):
            raise ValueError("Manifest lacks source_root or source_roots")
        assigned_root = Path(manifest["source_root"])
    if os.path.normcase(os.path.abspath(str(assigned_root))) != os.path.normcase(os.path.abspath(str(local_root))):
        raise ValueError("Manifest source root differs from worker's actual root")


class LocalInstanceLock:
    """A Windows per-user lock preventing duplicate workers on a single PC."""

    def __init__(self, worker: str, local_base: Path):
        self.path = local_base / (worker.lower().replace("-", "_") + ".lock")
        self.stream = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("a+b")
        self.stream.seek(0)
        self.stream.write(b"X")
        self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == "nt":
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.stream.close()
            raise RuntimeError(f"A {self.path.name} worker is already active") from exc
        return self

    def __exit__(self, *_args):
        if self.stream is not None:
            self.stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
            self.stream.close()


def kill_descendants(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    # This kills the stalled stage and child Python processes, rather than
    # orphaning a browser automation task that might overwrite later output.
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, timeout=20, check=False)
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        proc.kill()
        proc.wait(timeout=10)


def remove_own_stale_ticket(lane: Path, pid: int) -> None:
    """Recover ONLY a known killed wrapper's ticket, never another worker's."""
    for ticket in (lane / "queue").glob(f"*__{pid}__*.ticket.json"):
        try:
            info = json.loads(ticket.read_text(encoding="utf-8"))
            if (info.get("pid") == pid and
                    str(info.get("host", "")).lower() == socket.gethostname().lower()):
                ticket.unlink(missing_ok=True)
        except (OSError, json.JSONDecodeError):
            continue


def run_stage(
    root: Path, subchapter: str, stage: str, chrome_port: int,
    logfile: Path, lane: Path, idle_seconds: float, hard_seconds: float,
) -> tuple[bool, str]:
    cmd = [sys.executable, "-u", "-m", "selenium_pipeline.distributed_stage",
           "--source-root", str(root), "--subchapter", subchapter,
           "--stage", stage, "--chrome-port", str(chrome_port)]
    env = os.environ.copy()
    env.update({
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "MICROGEN_SOURCE_ROOT": str(root),
        # Google Drive virtual mounts do not implement a globally atomic
        # mutex. Per-PC browsers and non-overlapping chapters prevent file
        # races; the experimental Drive ticket system is OFF by default.
        "MICROGEN_GEMINI_LANE_DIR": os.getenv("MICROGEN_WORKER_SHARED_LANE", ""),
        # Use each PC's own installed environments, not a Drive-shared venv.
        "MICROGEN_PIPELINE_PYTHON": os.getenv("MICROGEN_WORKER_PIPELINE_PYTHON", sys.executable),
        "MICROGEN_TTS_PYTHON": os.getenv("MICROGEN_WORKER_TTS_PYTHON", sys.executable),
        "MICROGEN_GEMINI_LANE_STALE_SECONDS": "1800",
    })
    logfile.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    last_child_output = start
    stream: queue.Queue[str] = queue.Queue()
    with logfile.open("a", encoding="utf-8") as log:
        log.write(f"\n[{timestamp()}] START {subchapter}/{stage} CMD={cmd!r}\n")
        log.flush()
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            cwd=str(Path(__file__).resolve().parent.parent), env=env,
            encoding="utf-8", errors="replace", text=True, bufsize=1,
            start_new_session=(os.name != "nt"),
        )
        def read_output() -> None:
            assert proc.stdout is not None
            for line in proc.stdout:
                stream.put(line)
        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        reason = ""
        while True:
            try:
                line = stream.get(timeout=1.0)
                last_child_output = time.monotonic()
                log.write(line)
                log.flush()
                print(f"[{subchapter}/{stage}] {line}", end="", flush=True)
            except queue.Empty:
                pass
            now = time.monotonic()
            if proc.poll() is not None and not reader.is_alive() and stream.empty():
                break
            if now - last_child_output > idle_seconds:
                reason = f"stalled: no stage output for {now-last_child_output:.0f}s"
                break
            if now - start > hard_seconds:
                reason = f"over time limit: elapsed {now-start:.0f}s"
                break
        if reason:
            kill_descendants(proc)
            if proc.stdout is not None:
                proc.stdout.close()
            reader.join(timeout=2)
            remove_own_stale_ticket(lane, proc.pid)
            log.write(f"\n[{timestamp()}] ABORTED {reason}\n")
            print(f"[{subchapter}/{stage}] {reason}; preserving incomplete checkpoint", flush=True)
            return False, reason
        exit_code = proc.wait()
        if proc.stdout is not None:
            proc.stdout.close()
        if exit_code:
            error = f"stage exited {exit_code}; see {logfile}"
            log.write(f"\n[{timestamp()}] FAILED {error}\n")
            return False, error
        return True, ""


def stage_recorded(source: Path, stage: str) -> bool:
    if stage == "video":
        return completed_lecture(source)
    stamp = source.parent / ".microgen_work" / ".selenium_pipeline_state.json"
    if not stamp.is_file():
        return False
    try:
        completed = json.loads(stamp.read_text(encoding="utf-8")).get("completed", {})
        return isinstance(completed.get(stage), dict)
    except (json.JSONDecodeError, OSError, AttributeError):
        return False


def write_status(path: Path, data: dict) -> None:
    """Best-effort shared status; do not kill production on Drive sync hiccups."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2) + "\n"
    for attempt in range(3):
        scratch = path.with_name(path.name + f".{os.getpid()}.tmp")
        try:
            scratch.write_text(payload, encoding="utf-8")
            scratch.replace(path)
            return
        except OSError as exc:
            print(f"[worker] status sync delayed: {exc}", flush=True)
            time.sleep(2 * (attempt + 1))
        finally:
            scratch.unlink(missing_ok=True)


def process_job(
    root: Path, key: str, chrome_port: int, attempt: int,
    logs: Path, lane: Path, idle: float, hard: float, report: dict,
    persist,
) -> bool:
    source = root / key.split(".")[0] / key / "source.pdf"
    if completed_lecture(source):
        report[key] = {"status": "complete", "stage": "video",
                       "round": attempt, "verified": True, "updated_utc": timestamp()}
        persist()
        return True
    for stage in STAGES:
        report[key] = {"status": "running", "stage": stage, "round": attempt,
                       "updated_utc": timestamp()}
        persist()
        logfile = logs / f"{key}_round{attempt}_{stage}.log"
        try:
            ok, error = run_stage(root, key, stage, chrome_port, logfile, lane, idle, hard)
            if ok and not stage_recorded(source, stage):
                ok, error = False, f"stage {stage} missing valid completion checkpoint"
        except Exception as exc:
            ok, error = False, f"{type(exc).__name__}: {exc}"
        if not ok:
            report[key] = {"status": "deferred" if attempt == 1 else "unfinished",
                           "stage": stage, "round": attempt, "error": error,
                           "updated_utc": timestamp()}
            persist()
            print(f"[worker] DEFERRING {key} at {stage}: {error}", flush=True)
            return False
    report[key] = {"status": "complete", "stage": "video",
                   "round": attempt, "verified": True, "updated_utc": timestamp()}
    persist()
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--worker", required=True, help="Unique worker ID from manifest")
    parser.add_argument("--chapters", required=True, help="Comma-separated non-overlapping chapters")
    parser.add_argument("--subchapters", help="Optional pilot targets, must match manifest.targets for this worker")
    parser.add_argument("--chrome-port", type=int, default=9222)
    parser.add_argument("--pipeline-python", type=Path,
                        help="Per-PC local Python with docling, selenium and pypdf")
    parser.add_argument("--tts-python", type=Path,
                        help="Per-PC local Python with google.genai")
    parser.add_argument("--shared-gemini-lane", action="store_true",
                        help="EXPERIMENTAL Google Drive tickets; no atomic lock guarantee")
    parser.add_argument("--idle-seconds", type=float, default=900)
    parser.add_argument("--hard-seconds", type=float, default=3600)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not RUNNER_ID.fullmatch(args.run_id):
        parser.error("Use an alphanumeric run ID")
    if not RUNNER_ID.fullmatch(args.worker):
        parser.error("Worker ID accepts letters, numbers, hyphens and underscores")
    root = args.source_root.resolve()
    chapters = [int(s.strip()) for s in args.chapters.split(",")]
    if len(chapters) != len(set(chapters)):
        parser.error("Duplicate chapter")
    control = root / ".microgen_coordination" / args.run_id
    manifest = control / "assignments.json"
    deadline = time.monotonic() + 120
    while not manifest.is_file() and time.monotonic() < deadline:
        print("[worker] waiting for shared assignment manifest", flush=True)
        time.sleep(5)
    validate_manifest(manifest, args.worker, chapters, root=root)
    jobs = assigned_jobs(root, chapters)
    manifest_content = json.loads(manifest.read_text(encoding="utf-8"))
    targets = manifest_content.get("targets")
    if targets is not None:
        if not isinstance(targets, dict) or not isinstance(targets.get(args.worker), list):
            raise ValueError(f"Invalid pilot targets for {args.worker}")
        selected = targets[args.worker]
        if len(selected) != len(set(selected)) or any(not isinstance(t, str) or t not in jobs for t in selected):
            raise ValueError(f"Pilot targets not within assigned chapters: {selected}")
        jobs = [job for job in jobs if job in selected]
        if args.subchapters and args.subchapters.split(",") != jobs:
            raise ValueError("Pilot --subchapters must match manifest.targets")
    elif args.subchapters:
        raise ValueError("--subchapters requires signed-off targets in the run manifest")
    if not jobs:
        raise RuntimeError(f"No source.pdf jobs for {args.worker}")
    print(f"[worker] {args.worker}: {len(jobs)} jobs = {', '.join(jobs)}", flush=True)
    if args.dry_run:
        return 0
    pipeline_py = args.pipeline_python or Path(sys.executable)
    tts_py = args.tts_python or Path(sys.executable)
    if not pipeline_py.is_file() or not tts_py.is_file():
        raise FileNotFoundError(f"Invalid local Python(s): {pipeline_py}; {tts_py}")
    os.environ["MICROGEN_WORKER_PIPELINE_PYTHON"] = str(pipeline_py)
    os.environ["MICROGEN_WORKER_TTS_PYTHON"] = str(tts_py)
    os.environ["MICROGEN_WORKER_SHARED_LANE"] = (
        str(control / "gemini_lane") if args.shared_gemini_lane else ""
    )
    print(f"[worker] local stage Python: {pipeline_py}; TTS Python: {tts_py}", flush=True)
    if not args.shared_gemini_lane:
        print("[worker] Drive mutex disabled: separate PCs use independent "
              "Chrome sessions and distinct chapters; Gemini quota throttling "
              "may still defer individual jobs", flush=True)
    local_base = Path(os.getenv("LOCALAPPDATA") or (Path.home() / ".cache")) / "Microvid"
    local_logs = local_base / "worker_runs" / args.run_id / args.worker
    status_path = control / (args.worker + ".json")
    state: dict = {"run_id": args.run_id, "worker": args.worker,
                   "chapters": chapters, "assigned": jobs,
                   "pipeline_python": str(pipeline_py), "tts_python": str(tts_py),
                   "gemini_lane_experimental": bool(args.shared_gemini_lane),
                   "phase": "first_pass",
                   "started_utc": timestamp(), "jobs": {}}
    def persist():
        state["updated_utc"] = timestamp()
        write_status(status_path, state)
    with LocalInstanceLock(args.worker, local_base / "worker_locks"):
        persist()
        deferred: list[str] = []
        lane = control / "gemini_lane"
        for job in jobs:
            if not process_job(root, job, args.chrome_port, 1, local_logs, lane,
                               args.idle_seconds, args.hard_seconds, state["jobs"], persist):
                deferred.append(job)
        state["phase"] = "second_pass"
        state["deferred_from_first_pass"] = deferred
        persist()
        for job in deferred:
            process_job(root, job, args.chrome_port, 2, local_logs, lane,
                        args.idle_seconds, args.hard_seconds, state["jobs"], persist)
        unfinished = [j for j in jobs if state["jobs"].get(j, {}).get("status") != "complete"]
        state["phase"] = "finished"
        state["unfinished"] = unfinished
        state["finished_utc"] = timestamp()
        persist()
        print(f"[worker] FINISHED {args.worker}: complete={len(jobs)-len(unfinished)} unfinished={len(unfinished)}", flush=True)
        return 2 if unfinished else 0


if __name__ == "__main__":
    raise SystemExit(main())
