"""Restart-safe Windows guarded main cutover, with bounded post-rollback retry.

Addresses the real Dell-115 PR655 incident: the first guarded task handoff
started a new daemon but its PID disappeared and its original rollback was
verified. A second deployment attempt succeeded. The historical one-shot
script already guarded credentials, state pins, owner and task policy; this
module adds durable, independent result reconciliation and a maximum one
automatic retry after a verified healthy rollback.

It cannot generate content, make paid calls, authorize student publication,
write code, bypass CI/branch protection or replay G2/G3 model requests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from .recovery_registry import lookup_mechanism
from .three_pc_worker import LocalInstanceLock

KIND="development_guarded_revision_cutover"
SIGNATURE="WINDOWS_SCHEDULED_DAEMON_NEW_PID_DIED_DURING_CI_CERTIFIED_CUTOVER"
MECHANISM="RECONCILE_ROLLBACK_OWNER_AND_RETRY_ONE_SHA_PINNED_GUARDED_CUTOVER"
COMPLETE="GUARDED_MAIN_REVISION_CUTOVER_COMPLETED"
HOLD="GUARDED_MAIN_REVISION_CUTOVER_HELD"
SHA=re.compile(r"^[a-f0-9]{40}$")
SHA256=re.compile(r"^[a-f0-9]{64}$")
TASK="MicroGen_AI_Web_v71_OfflineDevelopment"


def require(condition,reason):
    if not condition:
        raise ValueError(reason)


def _sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_manifest(path:Path)->dict:
    require(path.is_file() and not path.is_symlink()
            and 0<path.stat().st_size<15000,"Untrusted guarded-cutover manifest")
    m=json.loads(path.read_text(encoding="utf-8-sig"))
    require(type(m) is dict and m.get("schema_version")==1
            and m.get("task_name")==TASK
            and m.get("new_provider_sends_allowed") is False
            and m.get("student_publication_authorized") is False
            and type(m.get("expected_main_sha")) is str
            and SHA.fullmatch(m["expected_main_sha"])
            and type(m.get("guard_script_sha256")) is str
            and SHA256.fullmatch(m["guard_script_sha256"]),
            "Guarded-cutover manifest cannot authorize unpinned execution")
    for name in ("old_repo","new_repo","state_dir","guard_script",
                 "root","original_plan"):
        require(type(m.get(name)) is str and Path(m[name]).is_absolute(),
                "Manifest contains relative/empty paths")
    root=Path(m["root"]).resolve()
    require(root.is_dir() and not root.is_symlink(),"Missing trusted cutover root")
    old=Path(m["old_repo"]).resolve()
    new=Path(m["new_repo"]).resolve()
    state=Path(m["state_dir"]).resolve()
    script=Path(m["guard_script"]).resolve()
    need_under=lambda path:path.is_relative_to(root) and path!=root
    require(all(need_under(x) and x.is_relative_to(root) for x in
                (old,new,state,script))
            and old!=new and old.is_dir() and new.is_dir()
            and state.is_dir() and script.is_file()
            and not script.is_symlink() and _sha(script)==m["guard_script_sha256"],
            "Source/script/state identity changed; do not execute unknown cutover")
    text=script.read_text(encoding="utf-8-sig")
    require(("$oldRepo=Join-Path $root '"+old.name+"'") in text
            and ("$newRepo=Join-Path $root '"+new.name+"'") in text
            and "GUARDED_CUTOVER_SUCCESS" in text
            and "ORIGINAL_DAEMON_RESTART_REQUESTED" in text
            and "provider_sends" in text
            and "student_publication_authorized" in text
            and "Get-CimInstance" in text,
            "Historical guard script no longer contains protected rollback policy")
    require(Path(m["original_plan"]).is_file() and
            not Path(m["original_plan"]).is_symlink(),
            "Original pinned development plan unavailable")
    require(_sha(old/"selenium_pipeline"/"development_continuity_executor_v71.py")
            == _sha(new/"selenium_pipeline"/"development_continuity_executor_v71.py"),
            "Pinned v7.1 executor was changed; explicit migration required")
    return m


def git_main(m:dict,*,executor=None)->bool:
    execute=executor or _run
    repo=m["new_repo"]
    want=m["expected_main_sha"]
    commands=[
        ["git","-C",repo,"rev-parse","HEAD"],
        ["git","-C",repo,"ls-remote","origin","refs/heads/main"],
        ["git","-C",repo,"status","--porcelain"],
    ]
    answers=[execute(cmd,timeout=30) for cmd in commands]
    require(all(p.returncode==0 for p in answers),
            "Main candidate git identity unavailable")
    require(answers[0].stdout.strip()==want
            and answers[1].stdout.split()[0]==want
            and answers[2].stdout.strip()=="",
            "Candidate checkout does not exactly match certified GitHub main")
    # Never trust a local "certified" label if GitHub main's server-side
    # required Windows check protection has been silently removed.
    protected=execute(
        ["gh","api",
         "repos/tlyoon/MicroGen_AI_Web/branches/main/protection"],
        timeout=30)
    require(protected.returncode==0 and len(protected.stdout)<40000,
            "GitHub main branch protection not independently readable")
    proof=json.loads(protected.stdout)
    checks=proof.get("required_status_checks") or {}
    actual=set(checks.get("contexts") or [])
    admins=proof.get("enforce_admins") or {}
    history=proof.get("required_linear_history") or {}
    force=proof.get("allow_force_pushes") or {}
    deletion=proof.get("allow_deletions") or {}
    require(checks.get("strict") is True
            and {"offline-regressions",
                 "Full offline suite (Windows, Python 3.12)"}<=actual
            and admins.get("enabled") is True
            and history.get("enabled") is True
            and force.get("enabled") is False
            and deletion.get("enabled") is False,
            "Main branch no longer enforces exact-head Windows CI")
    return True


def _run(argv,*,timeout:int):
    return subprocess.run(argv,text=True,capture_output=True,
                          timeout=timeout,check=False)


def readback(m:dict,*,executor=None)->dict:
    execute=executor or _run
    # Fixed task and pinned state directory; no untrusted PowerShell arguments.
    state=Path(m["state_dir"])
    path=str(state/"daemon_heartbeat.json").replace("'","''")
    ps=(
       "$ErrorActionPreference='Stop';"
       "$t=Get-ScheduledTask -TaskName '"+TASK+"';"
       "$h=Get-Content -Raw -LiteralPath '"+path+"'|ConvertFrom-Json;"
       "$p=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$h.owner_pid);"
       "$alive=($null -ne $p -and $p.CommandLine -like '*development_continuity_daemon_v71*');"
       "$age=([DateTimeOffset]::UtcNow-[DateTimeOffset]::Parse($h.heartbeat_utc)).TotalSeconds;"
       "[ordered]@{"
       "task_state=[string]$t.State;"
       "repo_root=[string]$t.Actions[0].WorkingDirectory;"
       "action_args=[string]$t.Actions[0].Arguments;"
       "multiple_instances=[string]$t.Settings.MultipleInstances;"
       "logon_type=[string]$t.Principal.LogonType;"
       "run_level=[string]$t.Principal.RunLevel;"
       "process_alive=[bool]$alive;"
       "process_cmdline=if($null -eq $p){''}else{[string]$p.CommandLine};"
       "owner_pid=[int]$h.owner_pid;"
       "run_id=[string]$h.run_id;"
       "heartbeat_age_seconds=[double]$age;"
       "provider_sends=[int]$h.provider_sends;"
       "student_publication_authorized=[bool]$h.student_publication_authorized;"
       "running=[bool]$h.running;"
       "plan_sha=[string]$h.plan_sha256"
       "}|ConvertTo-Json -Compress"
    )
    result=execute(["powershell.exe","-NoProfile","-NonInteractive",
                    "-Command",ps],timeout=25)
    require(result.returncode==0
            and len(result.stdout)<20000 and result.stdout.strip(),
            "Cannot independently attest Scheduled Task owner process")
    obj=json.loads(result.stdout)
    require(type(obj) is dict,"Task owner data malformed")
    return obj


def owner_valid(m:dict,observed:dict,repo:str)->bool:
    try:
        expected=Path(m[repo]).resolve()
        return (
            observed["task_state"]=="Running"
            and Path(observed["repo_root"]).resolve()==expected
            and observed["multiple_instances"]=="IgnoreNew"
            and observed["logon_type"]=="Interactive"
            and observed["run_level"]=="Limited"
            and observed["process_alive"] is True
            and str(expected).lower() in observed["process_cmdline"].lower()
            and observed["action_args"].lower().find(str(expected).lower())>=0
            and type(observed["owner_pid"]) is int
            and observed["owner_pid"]>0
            and type(observed["run_id"]) is str
            and len(observed["run_id"])>12
            and observed["running"] is True
            and 0<=observed["heartbeat_age_seconds"]<=60
            and observed["provider_sends"]==0
            and observed["student_publication_authorized"] is False
        )
    except (KeyError,TypeError,ValueError,OSError):
        return False


def persist(path:Path,value:dict):
    path=Path(path).absolute()
    require(path.suffix==".json" and not path.is_symlink()
            and not path.parent.is_symlink(),"Redirected cutover result")
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".pending")
    require(not temp.is_symlink(),"Redirected pending cutover result")
    body=(json.dumps(value,sort_keys=True,indent=2,
                     ensure_ascii=False,allow_nan=False)+"\n").encode("utf8")
    with temp.open("wb") as file:
        file.write(body)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temp,path)


def resume(*,manifest:Path,report_root:Path,verify_only:bool=False,
           max_attempts:int=2,readback_fn=readback,
           invoke_fn=None,main_fn=git_main)->dict:
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "Cutover recovery not in executable registry")
    require(type(max_attempts) is int and 1<=max_attempts<=2,
            "No unbounded scheduled-task restarts")
    m=_read_manifest(Path(manifest).absolute())
    report_root=Path(report_root).absolute()
    require(not report_root.is_symlink() and
            report_root.is_relative_to(Path(m["root"]).resolve()),
            "Cutover evidence path outside owned checkpoint")
    report_root.mkdir(parents=True,exist_ok=True)
    invoke=invoke_fn or (lambda manifest: _run(
        ["powershell.exe","-NoProfile","-NonInteractive",
         "-ExecutionPolicy","Bypass","-File",manifest["guard_script"]],
        timeout=150))
    with LocalInstanceLock("guarded_main_cutover_recovery_v1",report_root):
        start=readback_fn(m)
        old=owner_valid(m,start,"old_repo")
        new=owner_valid(m,start,"new_repo")
        results=[]
        def write(status):
            out={"schema_version":1,"status":status,
                 "task_name":TASK,
                 "certified_main_sha":m["expected_main_sha"],
                 "guard_script_sha256":m["guard_script_sha256"],
                 "attempts":results,
                 "attempt_count":len(results),
                 "source_checkpoint_preserved":True,
                 "source_scientific_QA_complete":False,
                 "new_provider_sends":0,
                 "new_paid_gemini_API_calls":0,
                 "student_publication_authorized":False}
            persist(report_root/"guarded_main_cutover_recovery.json",out)
            return out
        main_fn(m)
        if new:return write(COMPLETE)
        if verify_only:
            return write("GUARDED_MAIN_CUTOVER_AWAITING_EXECUTION" if old else HOLD)
        if not old:return write(HOLD)
        initial_pid=start["owner_pid"]
        initial_run=start["run_id"]
        for attempt in range(max_attempts):
            m=_read_manifest(Path(manifest).absolute())
            main_fn(m)
            try:
                process=invoke(m)
                detail={"exit_code":process.returncode,
                        "guard_reported_success":"GUARDED_CUTOVER_SUCCESS"
                         in process.stdout}
            except (OSError,subprocess.TimeoutExpired) as error:
                detail={"error_class":type(error).__name__,
                        "guard_reported_success":False}
            try:
                seen=readback_fn(m)
            except (OSError,ValueError,TypeError,KeyError) as error:
                results.append({**detail,"postowner_status":"UNATTESTED",
                                "error_class":type(error).__name__})
                return write(HOLD)
            if owner_valid(m,seen,"new_repo"):
                # A client may have exited nonzero after an actual successful
                # handoff. The real OS owner and checkpoint policy prevail.
                require(seen["owner_pid"]!=initial_pid
                        and seen["run_id"]!=initial_run,
                        "Cannot fabricate a new daemon from old heartbeat")
                results.append({**detail,"postowner_status":"NEW_OWNER_ATTESTED"})
                return write(COMPLETE)
            rolled=owner_valid(m,seen,"old_repo")
            results.append({**detail,"postowner_status":
                            "VERIFIED_SAFE_ROLLBACK" if rolled else
                            "UNATTESTED_OR_PARTIAL_ROLLBACK"})
            write(HOLD)
            if not rolled:
                return write(HOLD)
            # One additional attempt after confirmed old owner/zero Sends.
        return write(HOLD)


def main(argv=None):
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--manifest",required=True,type=Path)
    a.add_argument("--report-root",required=True,type=Path)
    a.add_argument("--verify-only",action="store_true")
    x=a.parse_args(argv)
    try:
        result=resume(manifest=x.manifest,report_root=x.report_root,
                      verify_only=x.verify_only)
    except (ValueError,KeyError,TypeError,OSError,subprocess.TimeoutExpired) as e:
        print(json.dumps({"status":HOLD,
                          "reason_class":type(e).__name__,
                          "reason":str(e)[:220]},indent=2))
        return 2
    print(json.dumps(result,indent=2))
    return 0 if result["status"]==COMPLETE else 2


if __name__=="__main__":
    raise SystemExit(main())

