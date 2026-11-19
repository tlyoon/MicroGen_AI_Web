"""Dell-115 native, source-only periodic v7.1 checkpoint continuation.

A real Windows Task Scheduler action invokes this module in a *new* process.
The code itself cannot author future software changes, but it can safely
reconcile and dispatch already-registered offline/read-only project stages.
No provider Send, TTS, GUI academic model inspection or publication is allowed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

TASK_NAME = "MicroGen_AI_Web_v71_SourceOnly"
MAX_RUN_SECONDS = 4800
MAX_LOG_BYTES = 500_000
MAX_SAVED_REPORTS = 5000


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def _native_context(repo: Path) -> tuple[Path, Path]:
    local = Path(os.environ.get("LOCALAPPDATA", "")).resolve()
    repo = Path(repo).resolve()
    _require(
        os.name == "nt"
        and os.environ.get("COMPUTERNAME", "").casefold() == "dell-115"
        and local.is_dir() and repo.is_dir()
        and repo.is_relative_to(local)
        and re.fullmatch(r"MicroGen_PR\d+_20\d{6}", repo.name) is not None
        and (repo / ".git").exists()
        and not (local / "MicroGen_AI_Web_Checkpoints").is_symlink(),
        "Only exact Dell-115 isolated local Git worktrees are permitted")
    from selenium_pipeline.windows_offline_development_forward_controller import (
        _verify_repo)
    _verify_repo(repo)
    home = local / "MicroGen_AI_Web_Checkpoints" / "v71_scheduled_resume_v1"
    _require(not home.is_symlink(), "Linked scheduler checkpoint blocked")
    home.mkdir(parents=True, exist_ok=True)
    return repo, home


def _wrapper_content(repo: Path, py: Path) -> str:
    script = (Path(__file__).resolve())
    _require(py.is_file() and script.is_file()
             and script.is_relative_to(repo)
             and "\n" not in str(repo)
             and '"' not in str(repo), "Unsafe scheduled launch paths")
    return ('@echo off\r\n'
            f'"{py}" -B "{script}" --run --repo "{repo}"\r\n'
            'exit /b %errorlevel%\r\n')


def _audit_installed(repo: Path, home: Path) -> None:
    """No schedule claim without the real enabled limited-user task."""
    wrapper = home / "sourceonly_v71.cmd"
    _require(wrapper.is_file() and not wrapper.is_symlink()
             and wrapper.read_bytes() ==
                 _wrapper_content(repo, Path(sys.executable).resolve()).encode("utf8"),
             "Source-only scheduled wrapper modified or missing")
    audit = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", TASK_NAME, "/V", "/FO", "LIST"],
        capture_output=True, text=True, timeout=30)
    source = audit.stdout.casefold()
    _require(audit.returncode == 0
             and TASK_NAME.casefold() in source
             and str(wrapper).casefold() in source
             and "scheduled task state: enabled" in source,
             "Source-only scheduled task not independently enabled and verified")


def install(repo: Path) -> dict:
    from selenium_pipeline.recovery_registry import lookup_mechanism
    _require(lookup_mechanism(
        "global_checkpoint_handoff",
        "V71_PERSISTENT_SOURCE_ONLY_RUNNER_NOT_INSTALLED")
        == "SCHEDULED_SOURCE_LOCKED_WINDOWS_RESTART_WITH_NO_GUI",
        "Executable unattended recovery registry missing")
    repo, home = _native_context(repo)
    wrapper = home / "sourceonly_v71.cmd"
    expected = _wrapper_content(repo, Path(sys.executable).resolve())
    if wrapper.exists():
        _require(wrapper.is_file() and not wrapper.is_symlink()
                 and wrapper.read_bytes() == expected.encode("utf8"),
                 "Refuse to overwrite unknown scheduled action")
    else:
        with wrapper.open("xb") as f:
            f.write(expected.encode("utf8"))
            f.flush()
            os.fsync(f.fileno())
    # Never force-replace an unknown task or use SYSTEM/elevated credentials.
    check = subprocess.run(["schtasks.exe", "/Query", "/TN", TASK_NAME],
                           capture_output=True, text=True, timeout=20)
    if check.returncode == 0:
        _require(False, "Existing scheduler task requires independent action audit")
    user = (os.environ.get("USERDOMAIN", "") + "\\" +
            os.environ.get("USERNAME", ""))
    _require(re.fullmatch(r"[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+", user)
             is not None, "Current logged-in interactive account not verified")
    create = subprocess.run(
        ["schtasks.exe", "/Create", "/SC", "MINUTE", "/MO", "30",
         "/TN", TASK_NAME, "/TR", str(wrapper), "/RU", user,
         "/IT", "/RL", "LIMITED"], capture_output=True, text=True, timeout=30)
    _require(create.returncode == 0, "Windows limited user schedule not installed")
    _audit_installed(repo, home)
    return {"status": "NATIVE_WINDOWS_INTERACTIVE_USER_SCHEDULE_INSTALLED",
            "task": TASK_NAME, "every_minutes": 30,
            "running_after_logout_verified": False,
            "source_only": True, "provider_send_authorized": False}


def run(repo: Path, *, runner=subprocess.run) -> dict:
    """Run the same normal v7.1 CLI, never an alternate worker entrypoint."""
    from selenium_pipeline.windows_v71_project_supervisor import STAGES
    from selenium_pipeline.three_pc_worker import LocalInstanceLock
    repo, home = _native_context(repo)
    _audit_installed(repo, home)
    meta = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, timeout=30)
    sha = meta.stdout.strip()
    _require(meta.returncode == 0 and re.fullmatch(r"[a-f0-9]{40}", sha)
             is not None, "Cannot source-lock unattended Git HEAD")
    ident = (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
             + "_" + str(os.getpid()))
    record = home / ("run_" + ident + ".json")
    _require(len(list(home.glob("run_*.json"))) < MAX_SAVED_REPORTS,
             "Unattended source-only report budget exhausted")
    env = os.environ.copy()
    env["MICROGEN_V71_BACKGROUND_SOURCE_ONLY"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTHONPATH", None)
    cmd = [sys.executable, "-B", "-m",
           "selenium_pipeline.windows_historical_stack_batch_plan",
           "--repo", str(repo), "--supervise-project-v71",
           "--max-v71-new-dispatches", str(len(STAGES))]
    with LocalInstanceLock("v71_scheduled_sourceonly", home / "locks"):
        try:
            finished = runner(cmd, cwd=repo, env=env, capture_output=True,
                              text=True, timeout=MAX_RUN_SECONDS)
            out = finished.stdout or ""
            err = finished.stderr or ""
            _require(len(out.encode("utf8")) + len(err.encode("utf8"))
                     <= MAX_LOG_BYTES, "Unattended output too large")
            data = json.loads(out)
            _require(finished.returncode == 0
                     and data.get("status") ==
                         "V71_GLOBAL_HANDOFF_VERIFIED_REVIEW_PENDING"
                     and data.get("source_head_sha") == sha
                     and data.get("scientific_qa_approved") is False
                     and data.get("student_publication_authorized") is False
                     and data.get("persistent_supervisor_installed_and_running_after_exit")
                         is False,
                     "Unattended command returned unsupported acceptance/HEAD")
            result = {
                "status": "PERSISTENT_SOURCE_ONLY_CHECKPOINT_CYCLE_RECONCILED",
                "source_head_sha": sha,
                "verified_stage_receipts": data["verified_stage_receipts"],
                "new_stage_dispatches": data["new_stage_dispatches_this_process"],
                "pending_stages": data["next_not_started_stages"],
                "gui_source_review_disallowed": True,
                "background_continuation_verified": True,
                "scientific_qa_approved": False,
                "student_publication_authorized": False,
            }
        except (OSError, RuntimeError, ValueError, KeyError, TypeError,
                subprocess.TimeoutExpired) as error:
            result = {
                "status": "PERSISTENT_SOURCE_ONLY_CYCLE_BLOCKED",
                "source_head_sha": sha,
                "error_type": type(error).__name__,
                "scientific_qa_approved": False,
                "student_publication_authorized": False,
            }
        with record.open("x", encoding="utf8") as f:
            json.dump(result, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
    return result


def main(argv=None):
    cli = argparse.ArgumentParser()
    cli.add_argument("--repo", type=Path, required=True)
    actions = cli.add_mutually_exclusive_group(required=True)
    actions.add_argument("--install", action="store_true")
    actions.add_argument("--run", action="store_true")
    args = cli.parse_args(argv)
    try:
        result = install(args.repo) if args.install else run(args.repo)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] not in {
            "PERSISTENT_SOURCE_ONLY_CYCLE_BLOCKED"} else 2
    except (OSError, RuntimeError, ValueError) as error:
        print(json.dumps({
            "status": "PERSISTENT_SOURCE_ONLY_RESTART_REFUSED",
            "error_type": type(error).__name__,
            "scientific_qa_approved": False,
            "student_publication_authorized": False,
        }))
        return 2


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.exit(main())
