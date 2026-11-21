"""Prepare a *disabled* logon startup artifact for v7.1 OFFLINE daemon.

No scheduled task is created, enabled, or modified by this module.
Registration/activation and reboot acceptance are separate, explicitly
authorized actions. SourceOnly and StatusMonitor tasks are never touched.
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
import xml.etree.ElementTree as ET

from .development_continuity_executor_v71 import _plan
from .development_continuity_daemon_v71 import attest_live_daemon

TASK_NAME = "MicroGen_AI_Web_v71_OfflineDevelopment"
NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
REGISTRY = Path(__file__).with_name("windows_development_startup_preview_registry_v71.json")
HANDLER = "GENERATE_DISABLED_LOGON_XML_REQUIRING_SEPARATE_APPROVAL"
BASE = "MICROGEN_V71_DISABLED_STARTUP_PREVIEW"
ET.register_namespace("", NS)


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def require_preview_registry(*, path: Path | None = None) -> None:
    p = Path(path or REGISTRY)
    _require(p.is_file() and not p.is_symlink()
             and 1 <= p.stat().st_size <= 4096, "Unsafe startup preview registry")
    x = json.loads(p.read_text(encoding="utf8"))
    expected = {
        "schema_version": 1, "status": BASE,
        "enabled": True,
        "handler": HANDLER,
        "may_register_or_enable_task": False,
        "may_modify_existing_tasks": False,
        "may_send_model_requests": False,
        "may_publish_students": False,
    }
    _require(x == expected, "Unregistered or modified startup recovery")


def _safe_string(s: str) -> str:
    _require(bool(s) and all(ord(c) >= 32 and c not in '"\r\n' for c in s),
             "Untrusted Windows launcher string")
    return s


def _q(s: str) -> str:
    return '"' + _safe_string(s) + '"'


def render_disabled_task_xml(*, repo: Path, python: Path, plan: Path,
                             state_dir: Path, user: str) -> bytes:
    """Pure, testable XML renderer. All native registration is prohibited."""
    for p in (repo, python, plan, state_dir):
        _require(Path(p).is_absolute(), "Absolute launcher paths required")
        _safe_string(str(p))
    _require(bool(re.fullmatch(r"[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+", user)),
             "Untrusted interactive Windows user")
    q = lambda tag, parent: ET.SubElement(parent, "{" + NS + "}" + tag)
    task = ET.Element("{" + NS + "}Task", {"version": "1.2"})
    registration = q("RegistrationInfo", task)
    q("Description", registration).text = (
        "DISABLED PREVIEW: source-bound MicroGen v7.1 offline verification only; "
        "never code-author, send Gemini, publish or change other tasks.")
    triggers = q("Triggers", task)
    logon = q("LogonTrigger", triggers)
    q("Enabled", logon).text = "false"
    q("UserId", logon).text = user
    principals = q("Principals", task)
    principal = ET.SubElement(principals, "{" + NS + "}Principal", {"id":"Author"})
    q("UserId", principal).text = user
    q("LogonType", principal).text = "InteractiveToken"
    q("RunLevel", principal).text = "LeastPrivilege"
    settings = q("Settings", task)
    for key, value in (
        ("MultipleInstancesPolicy","IgnoreNew"),
        ("DisallowStartIfOnBatteries","false"),
        ("StopIfGoingOnBatteries","false"),
        ("AllowStartOnDemand","true"),
        ("StartWhenAvailable","false"),
        ("Enabled","false"),
        ("ExecutionTimeLimit","PT0S"),
    ):
        q(key, settings).text = value
    restarts = q("RestartOnFailure", settings)
    q("Interval", restarts).text = "PT5M"
    q("Count", restarts).text = "3"
    actions = ET.SubElement(task, "{" + NS + "}Actions", {"Context":"Author"})
    exec_ = q("Exec", actions)
    q("Command", exec_).text = _safe_string(str(python))
    args = ["-B","-m","selenium_pipeline.development_continuity_daemon_v71",
            "--plan",str(plan),"--state-dir",str(state_dir),
            "--repo-root",str(repo),"--poll-seconds","120",
            "--heartbeat-seconds","5","--max-cycles","0"]
    q("Arguments", exec_).text = " ".join(
        _q(a) if i > 3 and i % 2 == 0 else _safe_string(a)
        for i,a in enumerate(args))
    q("WorkingDirectory", exec_).text = _safe_string(str(repo))
    return ET.tostring(task, encoding="utf-8", xml_declaration=True)


def _native_task_exists() -> bool:
    if os.name != "nt":
        return False
    command = (
        "$t=Get-ScheduledTask -TaskName '"
        + TASK_NAME
        + "' -ErrorAction SilentlyContinue; "
        "if($null -eq $t){'ABSENT'}else{'PRESENT'}")
    p = subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
                        "-Command",command],capture_output=True,text=True,
                       timeout=25)
    _require(p.returncode == 0 and p.stdout.strip() in ("ABSENT","PRESENT"),
             "Cannot establish existing startup task ownership")
    return p.stdout.strip() == "PRESENT"


def _git_clean_head(repo: Path) -> str:
    def cmd(*args: str) -> str:
        result = subprocess.run(["git","-C",str(repo),*args],
                                capture_output=True,text=True,timeout=30,check=True)
        return result.stdout.strip()
    _require(not cmd("status","--porcelain"),
             "Only clean, committed source can be staged for startup")
    sha=cmd("rev-parse","HEAD")
    _require(bool(re.fullmatch("[0-9a-f]{40}",sha)),
             "Unknown source revision")
    return sha


def _write_once(path: Path, content: bytes) -> None:
    _require(not path.is_symlink(), "Unsafe startup preview path")
    if path.exists():
        _require(path.is_file() and path.read_bytes() == content,
                 "Existing startup preview differs; refuse overwrite")
        return
    with path.open("xb") as out:
        out.write(content)
        out.flush()
        os.fsync(out.fileno())


def prepare(*,repo:Path,plan:Path,state_dir:Path,
            output_dir:Path,python:Path|None=None)->dict:
    """Reviewable, disabled startup artifact. No install code path exists."""
    require_preview_registry()
    _require(os.name == "nt"
             and os.environ.get("COMPUTERNAME","").casefold()=="dell-115",
             "Only actual Dell-115 may prepare Windows startup")
    local=Path(os.environ["LOCALAPPDATA"]).resolve()
    repo=Path(repo).resolve()
    plan=Path(plan).resolve()
    # Canonicalize parent aliases as well as the final path: a parent
    # symlink or '..' must not escape LOCALAPPDATA security boundaries.
    state_dir=Path(state_dir).resolve()
    output_dir=Path(output_dir).resolve()
    python=Path(python or sys.executable).resolve()
    for p in (repo,plan,state_dir,output_dir,python):
        _safe_string(str(p))
    _require(repo.is_dir() and (repo/".git").exists()
             and repo.is_relative_to(local)
             and plan.is_file() and not plan.is_symlink()
             and plan.is_relative_to(local)
             and python.is_file() and not python.is_symlink()
             and state_dir.is_relative_to(local)
             and output_dir.is_relative_to(local)
             and not state_dir.is_symlink()
             and not output_dir.is_symlink()
             and not output_dir.is_relative_to(repo)
             and not state_dir.is_relative_to(repo),
             "Startup paths must be pinned to approved local files")
    _require((repo/"selenium_pipeline"/"development_continuity_daemon_v71.py").is_file(),
             "Verified merged daemon implementation is absent")
    _plan(plan)
    head=_git_clean_head(repo)
    _require(not _native_task_exists(),
             "Existing startup task ownership unknown; refuse overwrite")
    _require(not attest_live_daemon(state_dir=state_dir)["running_verified"],
             "Do not stage startup while the daemon owns this state")
    user=(os.environ.get("USERDOMAIN","")+"\\"+
          os.environ.get("USERNAME",""))
    xml=render_disabled_task_xml(repo=repo,python=python,plan=plan,
                                 state_dir=state_dir,user=user)
    output_dir.mkdir(parents=True,exist_ok=True)
    _require(not output_dir.is_symlink(),
             "Unsafe generated task preview root")
    manifest={
        "schema_version":1,
        "status":"DISABLED_STARTUP_PREVIEW_ONLY",
        "project":"MicroGen_AI_Web",
        "task":TASK_NAME,
        "source_git_sha":head,
        "daemon_sha256":_sha(repo/"selenium_pipeline"/"development_continuity_daemon_v71.py"),
        "source_plan_sha256":_sha(plan),
        "python_sha256":_sha(python),
        "task_xml_sha256":hashlib.sha256(xml).hexdigest(),
        "task_enabled":False,
        "native_task_installed":False,
        "startup_or_reboot_test_passed":False,
        "existing_tasks_changed":False,
        "provider_requests":0,
        "code_authoring_enabled":False,
        "student_release":False,
        "next_step":"EXPLICIT_APPROVAL_FOR_NATIVE_STARTUP_INSTALL_AND_REBOOT_TEST",
    }
    content=(json.dumps(manifest,sort_keys=True,indent=2)+"\n").encode()
    _write_once(output_dir/"offline_daemon_DISABLED.xml",xml)
    _write_once(output_dir/"startup_preview_attestation.json",content)
    return manifest


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepare",action="store_true",required=True)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--plan",type=Path,required=True)
    p.add_argument("--state-dir",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(prepare(repo=a.repo,plan=a.plan,state_dir=a.state_dir,
                                 output_dir=a.output_dir),indent=2))
        return 0
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as e:
        print(json.dumps({"status":"STARTUP_PREVIEW_REFUSED",
                          "reason":type(e).__name__,
                          "native_task_installed":False,
                          "project_complete":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
