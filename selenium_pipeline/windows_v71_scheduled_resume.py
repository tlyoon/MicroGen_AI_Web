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
import xml.etree.ElementTree as ElementTree
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

def _native_xml_optional_enabled_after_live_enabled_state(xml_text: str) -> dict:
    """Audit the XML view only AFTER the native live task is verified Enabled.

    Windows Task Scheduler XML uses Enabled=true as the schema default.
    Several genuine Ready tasks omit this element. An explicitly false,
    missing principal or malformed XML still blocks installation/restart.
    """
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as error:
        raise RuntimeError("Native scheduler XML invalid") from error
    _require(root.tag in ("Task", "{http://schemas.microsoft.com/windows/2004/02/mit/task}Task"),
             "Unexpected native scheduler XML root")
    entries = root.findall("./{*}Settings/{*}Enabled")
    _require(len(entries) <= 1, "Ambiguous scheduler XML Enabled fields")
    if entries:
        _require((entries[0].text or "").strip().casefold() == "true",
                 "Scheduler XML explicitly disabled or malformed")
    logons = root.findall("./{*}Principals/{*}Principal/{*}LogonType")
    _require(len(logons) == 1
             and (logons[0].text or "").strip() == "InteractiveToken",
             "Scheduler XML not a limited interactive account")
    return {"native_state_verified": "Enabled",
            "xml_enabled": ("EXPLICIT_TRUE" if entries
                            else "OMITTED_DEFAULT_TRUE"),
            "model_or_paid_operations_authorized": False,
            "student_publication_authorized": False}


def _audit_installed(repo: Path, home: Path) -> None:
    """No schedule claim without the real enabled limited-user task."""
    from selenium_pipeline.recovery_registry import lookup_mechanism
    _require(lookup_mechanism(
        "global_checkpoint_handoff",
        "V71_NATIVE_CMD_DIRECT_SCRIPT_RELATIVE_IMPORT_CRASH") ==
        "ABSOLUTE_REGISTRY_IMPORT_FOR_NATIVE_SCHEDULED_SCRIPT_ENTRY",
        "Native direct-script scheduler recovery missing from registry")
    _require(lookup_mechanism(
        "global_checkpoint_handoff",
        "V71_WINDOWS_SCHEDULE_TASK_ACTION_PATH_ALIAS_UNVERIFIED") ==
        "RESOLVE_EXACT_SCHEDULE_ACTION_PATH_WITH_NO_ARGUMENTS",
        "Scheduled native path-alias recovery missing from executable registry")
    wrapper = home / "sourceonly_v71.cmd"
    _require(wrapper.is_file() and not wrapper.is_symlink()
             and wrapper.read_bytes() ==
                 _wrapper_content(repo, Path(sys.executable).resolve()).encode("utf8"),
             "Source-only scheduled wrapper modified or missing")
    audit = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", TASK_NAME, "/V", "/FO", "LIST"],
        capture_output=True, text=True, timeout=30)
    from selenium_pipeline.recovery_registry import lookup_mechanism
    _require(lookup_mechanism(
        "global_checkpoint_handoff",
        "V71_WINDOWS_SCHEDULED_TASK_STATE_PADDED_VALUE_UNREADABLE") ==
        "PARSE_EXACT_NATIVE_TASK_STATE_KEY_VALUE_INSTEAD_OF_SPACED_LITERAL",
        "Native Windows scheduler status parser recovery not registered")
    # Real schtasks.exe emits padded values (e.g. 'Scheduled Task State:\n'
    # on some displays or many spaces before 'Enabled'). Never compare the
    # entire human-formatted line to a hardcoded single-space string.
    fields = [tuple(x.strip() for x in line.partition(":")[::2])
              for line in audit.stdout.splitlines() if ":" in line]
    states = [value.casefold() for key, value in fields
              if key.casefold() == "scheduled task state"]
    names = [value.casefold() for key, value in fields
             if key.casefold() == "taskname"]
    _require(audit.returncode == 0
             and states == ["enabled"]
             and names in ([TASK_NAME.casefold()],
                           ["\\" + TASK_NAME.casefold()]),
             "Source-only scheduled task not independently enabled and verified")
    actions = [value for key, value in fields
               if key.casefold() == "task to run"]
    # Hosted Windows Temp and Task Scheduler may report different lexical
    # aliases for the SAME actual file. A raw substring check falsely
    # rejects the genuine action; canonicalize BOTH paths and demand equality.
    # Never accept a command with extra arguments or an unrelated executable.
    if len(actions) != 1:
        _require(False, "Missing or ambiguous scheduled task action")
    action = actions[0]
    if action.startswith('"') and action.endswith('"'):
        action = action[1:-1]
    actual = Path(action)
    _require(audit.returncode == 0
             and actual.is_absolute() and not actual.is_symlink()
             and actual.resolve() == wrapper.resolve(),
             "Source-only scheduled task action is not exact and enabled")
    # On real Windows, an enabled task may OMIT <Enabled> from its XML.
    # Trust neither an absent XML field alone nor a raw lexical comparison:
    # require the authenticated native state above AND strictly scoped XML.
    _require(lookup_mechanism(
        "global_checkpoint_handoff",
        "V71_NATIVE_TASK_XML_ENABLED_OPTIONAL_DEFAULT_TRUE") ==
        "ACCEPT_OMITTED_XML_ENABLED_ONLY_AFTER_NATIVE_ENABLED_STATE_VERIFIED",
        "Native task optional XML Enabled recovery missing from registry")
    xml = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", TASK_NAME, "/XML"],
        capture_output=True, text=True, timeout=30)
    _require(xml.returncode == 0, "Native Task Scheduler XML unavailable")
    _native_xml_optional_enabled_after_live_enabled_state(xml.stdout)


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
