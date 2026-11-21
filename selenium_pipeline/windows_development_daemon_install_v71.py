"""Explicitly authorized Dell-115-only native logon registration for OFFLINE v7.1.

Must be called on a clean checkout at the exact remote main commit. The
existing source-only and status monitor tasks remain disabled and untouched.
No arbitrary commands, code-writing agent, model Sends, student publication
or reboot are supported by this module. Native installation and controlled
on-demand start are distinct operations with explicit caller flags.
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

from .development_continuity_daemon_v71 import attest_live_daemon
from .windows_development_daemon_startup_preview_v71 import (
    TASK_NAME, NS, _git_clean_head, _safe_string, _sha,
    require_preview_registry, _write_once, _validate_disabled_xml_with_task_scheduler,
)
from .development_continuity_executor_v71 import _plan

REGISTRY = Path(__file__).with_name("windows_development_daemon_install_registry_v71.json")
ALLOWED_TASKS = ("MicroGen_AI_Web_v71_SourceOnly", "MicroGen_AI_Web_v71_StatusMonitor")


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def require_install_registry(*, path: Path | None = None) -> None:
    p=Path(path or REGISTRY)
    _require(p.is_file() and not p.is_symlink() and 1 <= p.stat().st_size <= 4096,
             "Native installation registry absent or unsafe")
    actual=json.loads(p.read_text(encoding="utf8"))
    expected={
        "schema_version":1,
        "status":"MICROGEN_V71_SINGLE_NATIVE_OFFLINE_STARTUP_V1",
        "task_name":TASK_NAME,
        "computer":"DELL-115",
        "allowed_role":"interactive_limited_current_user",
        "can_create_only_when_absent":True,
        "may_modify_existing_v71_tasks":False,
        "may_send_model_requests":False,
        "may_author_code_changes":False,
        "may_release_students":False,
        "installer_action":"INSTALL_EXACT_PINNED_NEW_OFFLINE_LOGON_TASK",
        "start_action":"START_ONLY_EXACT_OWNED_OFFLINE_TASK",
    }
    _require(actual==expected,"Unregistered/modified native installation policy")


def enabled_xml_from_disabled_preview(xml: bytes) -> bytes:
    """Produce enabled task ONLY from the verified, disabled preview schema."""
    tree=ET.fromstring(xml)
    ns={"t":NS}
    _require(tree.tag=="{"+NS+"}Task"
             and len(tree.findall(".//t:Actions/t:Exec",ns))==1
             and len(tree.findall(".//t:Triggers/t:LogonTrigger",ns))==1
             and tree.findtext("t:Settings/t:Enabled",namespaces=ns)=="false"
             and tree.findtext("t:Triggers/t:LogonTrigger/t:Enabled",namespaces=ns)=="false"
             and tree.findtext("t:Settings/t:MultipleInstancesPolicy",namespaces=ns)=="IgnoreNew"
             and tree.findtext("t:Principals/t:Principal/t:RunLevel",namespaces=ns)=="LeastPrivilege"
             and tree.findtext("t:Principals/t:Principal/t:LogonType",namespaces=ns)=="InteractiveToken",
             "Preview must be exactly one disabled limited-user logon task")
    command=tree.findtext("t:Actions/t:Exec/t:Command",namespaces=ns)
    arguments=tree.findtext("t:Actions/t:Exec/t:Arguments",namespaces=ns)
    _require(command and Path(command).name.casefold() in ("python.exe","pythonw.exe")
             and arguments and "selenium_pipeline.development_continuity_daemon_v71"
             in arguments and "--max-cycles \"0\"" in arguments
             and "powershell" not in arguments.casefold()
             and "schtasks" not in arguments.casefold(),
             "Preview is not the restricted offline daemon")
    tree.find("t:Settings/t:Enabled",ns).text="true"
    tree.find("t:Triggers/t:LogonTrigger/t:Enabled",ns).text="true"
    tree.find("t:RegistrationInfo/t:Description",ns).text=(
        "Source-bound, user-authorized, OFFLINE read-only MicroGen v7.1 "
        "checkpoint verification daemon. No Gemini Sends, code editing or release.")
    return ET.tostring(tree,encoding="utf-8",xml_declaration=True)


def _powershell(script: str, *, env: dict | None = None, timeout: int = 45) -> str:
    p=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
                      "-Command",script],env=env,capture_output=True,
                     text=True,timeout=timeout)
    _require(p.returncode==0,"Native Windows task operation failed: "+p.stderr[-600:])
    return p.stdout.strip()


def _native_snapshot()->dict:
    if os.name!="nt":
        raise ValueError("Only Windows owns the native task")
    script=(
        "$ErrorActionPreference='Stop';"
        "$names=@('MicroGen_AI_Web_v71_OfflineDevelopment',"
        "'MicroGen_AI_Web_v71_SourceOnly','MicroGen_AI_Web_v71_StatusMonitor');"
        "$rows=@();foreach($n in $names){"
        "$t=Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue;"
        "if($null -eq $t){$rows+=@{name=$n;state='Absent'};continue};"
        "$i=Get-ScheduledTaskInfo -TaskName $n;"
        "$rows+=@{name=$n;state=[string]$t.State;"
        "action=[string]$t.Actions[0].Execute;"
        "arguments=[string]$t.Actions[0].Arguments;"
        "principal=[string]$t.Principal.UserId;"
        "run_level=[string]$t.Principal.RunLevel;"
        "logon=[string]$t.Principal.LogonType;"
        "last_result=[int]$i.LastTaskResult};}"
        "$rows | ConvertTo-Json -Compress -Depth 4")
    result=_powershell(script)
    data=json.loads(result)
    if isinstance(data,dict):
        data=[data]
    _require(type(data) is list and len(data)==3,"Native task snapshot malformed")
    return {v["name"]:v for v in data}


def _security_preflight(preview_dir: Path,repo: Path,plan: Path,
                        state_dir: Path,python: Path)->tuple[dict,bytes,str,dict]:
    require_preview_registry()
    require_install_registry()
    _require(os.name=="nt" and os.environ.get("COMPUTERNAME","").casefold()=="dell-115",
             "This installer is restricted to Dell-115")
    local=Path(os.environ["LOCALAPPDATA"]).resolve()
    preview_dir=Path(preview_dir).resolve()
    repo=Path(repo).resolve()
    plan=Path(plan).resolve()
    state_dir=Path(state_dir).resolve()
    python=Path(python).resolve()
    _require(all(p.is_relative_to(local) for p in
                 (preview_dir,repo,plan,state_dir,python))
             and preview_dir.is_dir() and (repo/".git").exists()
             and plan.is_file() and not plan.is_symlink()
             and python.is_file() and not python.is_symlink()
             and not state_dir.is_symlink(),
             "Installer input escapes the source-bound local account")
    for p in (preview_dir,repo,plan,state_dir,python):
        _safe_string(str(p))
    sha=_git_clean_head(repo)
    remote=subprocess.run(["git","-C",str(repo),"ls-remote","origin",
                           "refs/heads/main"],capture_output=True,text=True,
                          timeout=30,check=True).stdout.split()
    _require(bool(remote) and remote[0]==sha,
             "Only the currently verified merged main may install a native task")
    manifest_path=preview_dir/"startup_preview_attestation.json"
    xml_path=preview_dir/"offline_daemon_DISABLED.xml"
    _require(manifest_path.is_file() and xml_path.is_file()
             and not manifest_path.is_symlink() and not xml_path.is_symlink(),
             "No original, intact disabled preview")
    receipt=json.loads(manifest_path.read_text(encoding="utf8"))
    _require(receipt.get("status")=="DISABLED_STARTUP_PREVIEW_ONLY"
             and receipt.get("task")==TASK_NAME
             and receipt.get("source_git_sha")==sha
             and receipt.get("source_plan_sha256")==_sha(plan)
             and receipt.get("daemon_sha256")==_sha(
                 repo/"selenium_pipeline"/"development_continuity_daemon_v71.py")
             and receipt.get("python_sha256")==_sha(python)
             and receipt.get("task_xml_sha256")==_sha(xml_path)
             and receipt.get("native_task_installed") is False
             and receipt.get("task_enabled") is False
             and receipt.get("native_xml_schema_validated_without_registration") is True,
             "Disabled preview must match the exact admitted source and roadmap")
    _plan(plan)
    _require(not attest_live_daemon(state_dir=state_dir)["running_verified"],
             "Live daemon already owns the intended checkpoint")
    xml=xml_path.read_bytes()
    _validate_disabled_xml_with_task_scheduler(xml_path)
    enabled=enabled_xml_from_disabled_preview(xml)
    account=chr(92).join((os.environ.get("USERDOMAIN",""),
                          os.environ.get("USERNAME","")))
    _require(bool(re.fullmatch(r"[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+",account)),
             "Installer requires the current named interactive account")
    tree=ET.fromstring(enabled); ns={"t":NS}
    _require(tree.findtext("t:Principals/t:Principal/t:UserId",namespaces=ns)
             .casefold()==account.casefold()
             and tree.findtext("t:Triggers/t:LogonTrigger/t:UserId",namespaces=ns)
             .casefold()==account.casefold(),
             "Preview is owned by another user")
    actual=_native_snapshot()
    _require(actual[TASK_NAME]["state"]=="Absent",
             "An existing native offline task cannot be overwritten")
    _require(all(actual[n]["state"]=="Disabled" for n in ALLOWED_TASKS),
             "Original v7.1 task state changed; refuse installation")
    return receipt,enabled,account,actual


def _register_new_native_task(enabled_xml_path: Path,account: str)->None:
    """Create exactly once; refuses an existing task, no later task mutation."""
    env=dict(os.environ)
    env["MICROGEN_V71_ENABLED_TASK_XML"]=str(enabled_xml_path)
    env["MICROGEN_V71_TASK_USER"]=account
    script=(
        "$ErrorActionPreference='Stop';"
        "$s=New-Object -ComObject Schedule.Service;$s.Connect();"
        "$root=$s.GetFolder('\\');"
        "$existing=$null;"
        "try{$existing=$root.GetTask('MicroGen_AI_Web_v71_OfflineDevelopment')}"
        "catch{if($_.Exception.HResult -ne -2147024894){throw}};"
        "if($null -ne $existing){throw 'Existing task may not be replaced'};"
        "$raw=[IO.File]::ReadAllText($env:MICROGEN_V71_ENABLED_TASK_XML,"
        "[Text.Encoding]::UTF8);"
        "$raw=[regex]::Replace($raw,'^<\\?xml[^>]*\\?>\\s*','');"
        "$def=$s.NewTask(0);$def.XmlText=$raw;"
        "if(-not $def.Settings.Enabled -or -not $def.Triggers.Item(1).Enabled "
        "-or $def.Principal.RunLevel -ne 0 -or $def.Principal.LogonType -ne 3)"
        "{throw 'Bad ownership in enabled task XML'};"
        "$null=$root.RegisterTaskDefinition("
        "'MicroGen_AI_Web_v71_OfflineDevelopment',$def,2,"
        "$env:MICROGEN_V71_TASK_USER,$null,3,$null);"
        "'EXACT_NEW_OFFLINE_TASK_REGISTERED'")
    response=_powershell(script,env=env)
    _require(response=="EXACT_NEW_OFFLINE_TASK_REGISTERED",
             "Native scheduler did not acknowledge task registration")


def install(*,preview_dir:Path,repo:Path,plan:Path,state_dir:Path,
            output_dir:Path,python:Path|None=None)->dict:
    _require(os.name=="nt" and
             os.environ.get("COMPUTERNAME","").casefold()=="dell-115",
             "Native startup registration is authorized on Dell-115 only")
    python=Path(python or sys.executable).resolve()
    preview_dir=Path(preview_dir).resolve()
    repo=Path(repo).resolve()
    plan=Path(plan).resolve()
    state_dir=Path(state_dir).resolve()
    output_dir=Path(output_dir).resolve()
    _require(output_dir.is_relative_to(Path(os.environ["LOCALAPPDATA"]).resolve())
             and not output_dir.is_relative_to(repo) and not output_dir.is_symlink(),
             "Unsafe native installation receipt path")
    old,xml,owner,before=_security_preflight(
        preview_dir,repo,plan,state_dir,python)
    output_dir.mkdir(parents=True,exist_ok=True)
    task_xml=output_dir/"offline_daemon_ENABLED_approved.xml"
    _write_once(task_xml,xml)
    _register_new_native_task(task_xml,owner)
    after=_native_snapshot()
    own=after[TASK_NAME]
    _require(own.get("state") in ("Ready","Running")
             and Path(own.get("action","")).resolve()==python
             and own.get("principal","").casefold()==owner.casefold()
             and own.get("run_level")=="Limited"
             and own.get("logon")=="Interactive"
             and all(after[n]["state"]==before[n]["state"]=="Disabled"
                     and after[n]["action"]==before[n]["action"] for n in ALLOWED_TASKS),
             "Native task cannot be attested after registration")
    result={
        "schema_version":1,
        "status":"NATIVE_OFFLINE_LOGON_TASK_INSTALLED",
        "task":TASK_NAME,
        "git_sha":old["source_git_sha"],
        "approved_roadmap_sha256":old["source_plan_sha256"],
        "enabled_xml_sha256":_sha(task_xml),
        "user":owner,
        "task_state":own["state"],
        "repository":str(repo),
        "source_plan":str(plan),
        "state_dir":str(state_dir),
        "python":str(python),
        "daemon_sha256":old["daemon_sha256"],
        "python_sha256":old["python_sha256"],
        "registered_action":own["action"],
        "registered_arguments":own["arguments"],
        "other_tasks_unchanged":True,
        "native_reboot_acceptance":False,
        "run_actually_started":own["state"]=="Running",
        "model_sends":0,
        "code_writing":False,
        "student_release":False,
    }
    _write_once(output_dir/"native_installed_attestation.json",
                (json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
    return result


def start_approved(*,installation_dir:Path,state_dir:Path)->dict:
    """Start only already-attested exact task, never create or overwrite it."""
    require_install_registry()
    installation_dir=Path(installation_dir).resolve()
    manifest=installation_dir/"native_installed_attestation.json"
    _require(manifest.is_file() and not manifest.is_symlink(),
             "No authenticated native installation attestation")
    saved=json.loads(manifest.read_text(encoding="utf8"))
    _require(saved.get("status")=="NATIVE_OFFLINE_LOGON_TASK_INSTALLED"
             and saved.get("task")==TASK_NAME
             and type(saved.get("git_sha")) is str
             and bool(re.fullmatch(r"[0-9a-f]{40}",saved["git_sha"])),
             "Could not attest the original native install receipt")
    repo=Path(saved["repository"]).resolve()
    plan=Path(saved["source_plan"]).resolve()
    python=Path(saved["python"]).resolve()
    state_dir=Path(state_dir).resolve()
    xml_file=installation_dir/"offline_daemon_ENABLED_approved.xml"
    _require(repo.is_dir() and plan.is_file()
             and python.is_file() and xml_file.is_file()
             and not plan.is_symlink() and not xml_file.is_symlink()
             and state_dir==Path(saved["state_dir"]).resolve()
             and _git_clean_head(repo)==saved["git_sha"]
             and _sha(plan)==saved["approved_roadmap_sha256"]
             and _sha(python)==saved["python_sha256"]
             and _sha(repo/"selenium_pipeline"/
                     "development_continuity_daemon_v71.py")==saved["daemon_sha256"]
             and _sha(xml_file)==saved["enabled_xml_sha256"],
             "Pinned code/roadmap/owner drift; no re-start authorization")
    ns={"t":NS}
    doc=ET.fromstring(xml_file.read_bytes())
    expected_arg=doc.findtext("t:Actions/t:Exec/t:Arguments",namespaces=ns)
    expected_cmd=doc.findtext("t:Actions/t:Exec/t:Command",namespaces=ns)
    snapshot=_native_snapshot()
    current=snapshot[TASK_NAME]
    _require(current.get("state") in ("Ready","Running")
             and saved["registered_action"]==current.get("action")==expected_cmd
             and saved["registered_arguments"]==current.get("arguments")==expected_arg
             and current.get("principal","").casefold()==saved["user"].casefold()
             and current.get("run_level")=="Limited"
             and current.get("logon")=="Interactive"
             and all(snapshot[n]["state"]=="Disabled" for n in ALLOWED_TASKS),
             "Existing native task no longer matches approved offline action")
    if snapshot[TASK_NAME]["state"]=="Ready":
        output=_powershell("$ErrorActionPreference='Stop';"
                           "Start-ScheduledTask -TaskName '"
                           +TASK_NAME+"';'OFFLINE_TASK_START_REQUESTED'")
        _require(output=="OFFLINE_TASK_START_REQUESTED",
                 "Native task start not accepted")
    return {
        "status":"NATIVE_OFFLINE_TASK_START_REQUESTED",
        "task":TASK_NAME,
        "previous_state":snapshot[TASK_NAME]["state"],
        "live_attestation":attest_live_daemon(state_dir=Path(state_dir)),
        "model_sends":0,
        "student_publication":False,
    }


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    a=p.add_mutually_exclusive_group(required=True)
    a.add_argument("--install",action="store_true")
    a.add_argument("--start",action="store_true")
    p.add_argument("--preview-dir",type=Path)
    p.add_argument("--repo",type=Path)
    p.add_argument("--plan",type=Path)
    p.add_argument("--state-dir",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    arg=p.parse_args(argv)
    try:
        if arg.install:
            _require(all((arg.preview_dir,arg.repo,arg.plan)),
                     "Install needs exact preview, repo and roadmap")
            result=install(preview_dir=arg.preview_dir,repo=arg.repo,
                           plan=arg.plan,state_dir=arg.state_dir,
                           output_dir=arg.output_dir)
        else:
            result=start_approved(installation_dir=arg.output_dir,
                                  state_dir=arg.state_dir)
        print(json.dumps(result,indent=2))
        return 0
    except (RuntimeError,OSError,ValueError,KeyError,
            subprocess.CalledProcessError,subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status":"NATIVE_OFFLINE_TASK_ACTION_REFUSED",
                          "error_type":type(exc).__name__,
                          "reason":str(exc)[:300],
                          "project_complete":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
