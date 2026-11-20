"""Install and verify one limited-user Dell-115 STATUS-ONLY Windows task.

Never replace an unrelated task, enable a disabled source-only task, upload
private sources, send Gemini requests, alter TTS, merge, or publish to students.
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

from .project_development_status import MONITOR_TASK, SAFE_CHECKPOINT, require


def _wrap(repo: Path, python: Path) -> bytes:
    require(repo.is_absolute() and python.is_absolute()
            and repo.is_dir() and python.is_file()
            and all('"' not in str(p) and "\n" not in str(p)
                    for p in (repo, python)), "Untrusted launcher paths")
    return (
        "@echo off\r\n"
        f'cd /d "{repo}"\r\n'
        f'"{python}" -B -m selenium_pipeline.project_development_status\r\n'
        "exit /b %errorlevel%\r\n"
    ).encode("utf8")


def _native_inspect(task_name: str) -> dict | None:
    require(task_name == MONITOR_TASK, "Only known monitor task inspectable")
    if os.name != "nt":
        return None
    command=(
        "$t=Get-ScheduledTask -TaskName 'MicroGen_AI_Web_v71_StatusMonitor' "
        "-ErrorAction SilentlyContinue;"
        "if($null -eq $t){'null';exit 0};"
        "$i=Get-ScheduledTaskInfo -TaskName $t.TaskName;"
        "[ordered]@{name=[string]$t.TaskName;state=[string]$t.State;"
        "action=[string]$t.Actions[0].Execute;"
        "user=[string]$t.Principal.UserId;"
        "run_level=[string]$t.Principal.RunLevel;"
        "logon=[string]$t.Principal.LogonType;"
        "last_result=[int]$i.LastTaskResult;"
        "last_run=$i.LastRunTime.ToUniversalTime().ToString('o')"
        "} | ConvertTo-Json -Compress"
    )
    p = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, timeout=30)
    require(p.returncode == 0 and 0 < len(p.stdout) <= 9000,
            "Cannot verify native monitor task")
    return json.loads(p.stdout)


def _verify_task(snapshot: dict, wrapper: Path) -> None:
    require(type(snapshot) is dict
            and snapshot.get("name") == MONITOR_TASK
            and snapshot.get("state") in ("Ready", "Running")
            and snapshot.get("run_level") == "Limited"
            and snapshot.get("logon") == "Interactive"
            and Path(snapshot.get("action", "")).resolve() == wrapper.resolve(),
            "Native monitor task action or user privilege differs")
    current = os.environ.get("USERNAME", "").casefold()
    user = str(snapshot.get("user", "")).casefold()
    require(bool(current) and user in (
        current, (os.environ.get("USERDOMAIN", "").casefold()
                  + "\\" + current)),
        "Monitor task belongs to another Windows user")


def install(repo: Path, *, python: Path | None = None) -> dict:
    require(os.name == "nt" and
            os.environ.get("COMPUTERNAME", "").casefold() == "dell-115",
            "Native monitor install is Dell-115 only")
    repo = Path(repo).resolve()
    local = Path(os.environ["LOCALAPPDATA"]).resolve()
    require(repo.is_relative_to(local)
            and re.fullmatch(r"MicroGen_PR\d+_20\d{6}", repo.name)
            and (repo / ".git").exists(), "Only clean isolated source worktree")
    git = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True, text=True, timeout=30, check=True)
    require(not git.stdout.strip(), "Only verified committed source is installable")
    # Exact source must contain the watchdog and persist a real policy contract.
    script = repo / "selenium_pipeline" / "project_development_status.py"
    require(script.is_file() and not script.is_symlink(),
            "Watchdog module not present")
    python = Path(python or sys.executable).resolve()
    check = local / SAFE_CHECKPOINT
    require(check.is_dir() and not check.is_symlink(), "No authentic checkpoint root")
    folder = check / "development_status_v1"
    folder.mkdir(parents=True, exist_ok=True)
    require(not folder.is_symlink(), "Unsafe monitor task home")
    wrapper = folder / "status_monitor.cmd"
    expected = _wrap(repo, python)
    if wrapper.exists():
        require(wrapper.is_file() and not wrapper.is_symlink()
                and wrapper.read_bytes() == expected,
                "Refuse to replace a monitor owned by another source")
    else:
        with wrapper.open("xb") as fd:
            fd.write(expected)
            fd.flush()
            os.fsync(fd.fileno())
    current = _native_inspect(MONITOR_TASK)
    installed_now = False
    if current is None:
        user = os.environ.get("USERDOMAIN", "") + "\\" + os.environ.get("USERNAME", "")
        require(re.fullmatch(r"[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+", user),
                "Current limited interactive principal not proved")
        p = subprocess.run(
            ["schtasks.exe", "/Create", "/SC", "MINUTE", "/MO", "15",
             "/TN", MONITOR_TASK, "/TR", str(wrapper), "/RU", user,
             "/IT", "/RL", "LIMITED"], capture_output=True,
            text=True, timeout=30)
        require(p.returncode == 0, "Native status task creation failed")
        installed_now = True
        current = _native_inspect(MONITOR_TASK)
    _verify_task(current, wrapper)
    # Attestation is a write-once installation receipt. It is NOT
    # permission to enable/overwrite any other task or provider request.
    manifest = folder / "installed_monitor_attestation.json"
    stamp = {
        "schema_version": 1,
        "status": "NATIVE_LIMITED_USER_MONITOR_TASK_VERIFIED",
        "task": MONITOR_TASK, "repository": str(repo),
        "wrapper_sha256": hashlib.sha256(expected).hexdigest(),
        "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
        "interval_minutes": 15, "source_only": True,
        "automated_code_development_authorized": False,
        "provider_sends_authorized": False,
        "student_publication_authorized": False,
    }
    if manifest.exists():
        old = json.loads(manifest.read_text(encoding="utf8"))
        require(old == stamp, "Existing monitor attestation differs")
    else:
        with manifest.open("x", encoding="utf8") as fd:
            json.dump(stamp, fd, indent=2, sort_keys=True)
            fd.write("\n")
    return {**stamp, "newly_installed": installed_now,
            "native_state": current["state"],
            "drive_status_mirror": "G:/My Drive/MicroGen_AI_Web_Development_Status/STATUS.md"}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--install", action="store_true", required=True)
    args = p.parse_args(argv)
    try:
        result = install(args.repo)
        print(json.dumps(result, indent=2))
        return 0
    except (RuntimeError, OSError, ValueError, KeyError,
            subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(json.dumps({"status": "MONITOR_INSTALL_REFUSED",
                          "reason_type": type(e).__name__,
                          "project_complete_claimed": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
