"""Idempotent guarded Windows deployment of a verified merged auto-code PR.

Requires original real GitHub PR merge provenance, source tree identity, both
original protected Windows CI checks and the authorized named tasks. Uses
the existing tested main-daemon cutover controller and original PowerShell
guard scripts as SHA-pinned templates. Original CodeAuthor request journals
are never changed by this module. A crash requires real owner reconciliation,
never blind replay of ambiguous remote GitHub or Windows cutover operations.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from datetime import datetime, timezone

from .development_guarded_cutover_recovery_v1 import resume, COMPLETE
from .development_ci_gated_merge_v1 import api, MERGED, PASS
from .development_verified_candidate_promotion_v1 import run, save, need
from .recovery_registry import lookup_mechanism

KIND="autonomous_certified_code_candidate_deployment"
SIGNATURE="MERGED_AND_WINDOWS_CI_CERTIFIED_MODEL_CODE_AWAITS_GUARDED_PRODUCTION_CUTOVER"
MECHANISM="PIN_MERGED_TREE_GUARD_BOTH_WINDOWS_DAEMONS_AND_CONTINUE"
REPO="tlyoon/MicroGen_AI_Web"
SHA40=re.compile(r"^[a-f0-9]{40}$")
MAIN_TEMPLATE="guarded_main_autopromotion_template_v1.ps1"
AUTHOR_TEMPLATE="guarded_author_autopromotion_template_v1.ps1"


def checksum(file:Path)->str:
    need(file.is_file() and not file.is_symlink(),
         "Missing signed original guarded deployment template")
    return hashlib.sha256(file.read_bytes()).hexdigest()


def original_main_pr(*,number,expected_head,fetch=api):
    need(type(number) is int and 1<=number<1000000
         and type(expected_head) is str and SHA40.fullmatch(expected_head),
         "No original certifiable GitHub PR identity")
    pr=fetch(f"repos/{REPO}/pulls/{number}")
    main=fetch(f"repos/{REPO}/commits/main")
    need(pr.get("head",{}).get("sha")==expected_head
         and pr.get("state")=="closed"
         and pr.get("merged_at")
         and pr.get("merge_commit_sha")==main.get("sha")
         and SHA40.fullmatch(main["sha"]),
         "Do not deploy a non-main, unmerged or ambiguous code branch")
    commit=fetch(f"repos/{REPO}/git/commits/{main['sha']}")
    head=fetch(f"repos/{REPO}/git/commits/{expected_head}")
    need(commit.get("tree",{}).get("sha")==head.get("tree",{}).get("sha")
         and len(commit.get("parents",[]))==1,
         "GitHub merged commit tree does not equal reviewed model source")
    return main["sha"]


def template(source:Path,replacements:dict,dest:Path):
    need(source.is_file() and not source.is_symlink()
         and dest.parent.is_dir() and not dest.is_symlink(),
         "Unverified guarded Windows template path")
    original=source.read_text(encoding="utf8")
    required=frozenset(replacements)
    need(required <= frozenset({
        "__OLD_REPO__","__NEW_REPO__","__TASK_BEFORE__",
        "__MAIN_RECEIPT__","__AUTHOR_RECEIPT__"}),
        "Unknown power-shell substitution")
    for key,value in replacements.items():
        need(key in original and re.fullmatch(r"[A-Za-z0-9_.-]{6,100}",value),
             "Unexpected substitution inside security-critical guard")
        original=original.replace(key,value)
    need(not re.search(r"__[A-Z_]{6,}__",original),
         "Guarded deployment contains unresolved old path placeholders")
    payload=original.encode("utf8")
    if dest.exists():
        need(dest.is_file() and dest.read_bytes()==payload,
             "Original certified Windows guard script changed after admission")
    else:
        with dest.open("xb") as stream:
            stream.write(payload);stream.flush()
    return checksum(dest)


def attested_task(task,checkout):
    # Only readback, NO restart or mutation. Guard scripts themselves own
    # Windows task rollback and process identity verification.
    need(task in {
        "MicroGen_AI_Web_v71_OfflineDevelopment",
        "MicroGen_AI_Web_v1_PersistentCodeAuthor"},
        "Unrecognized Windows worker task")
    ps=(
       "$ErrorActionPreference='Stop';"
       "$t=Get-ScheduledTask -TaskName '"+task+"';"
       "[ordered]@{state=[string]$t.State;"
       "repo=[string]$t.Actions[0].WorkingDirectory;"
       "logon_type=[string]$t.Principal.LogonType;"
       "run_level=[string]$t.Principal.RunLevel;"
       "multiple=[string]$t.Settings.MultipleInstances}"
       "|ConvertTo-Json -Compress"
    )
    obj=json.loads(run(["powershell.exe","-NoProfile",
                        "-NonInteractive","-Command",ps],timeout=30))
    valid=(obj.get("state")=="Running"
           and Path(obj.get("repo","")).resolve()==checkout.resolve()
           and obj.get("logon_type")=="Interactive"
           and obj.get("run_level")=="Limited"
           and obj.get("multiple")=="IgnoreNew")
    if not valid:return False
    # Also attest the actual live process and fresh immutable heartbeat.
    # Windows Task Scheduler's Running label alone is insufficient.
    root=Path("C:/Users/tlyoon/AppData/Local/MicroGen_AI_Web_Checkpoints")
    is_writer=task.endswith("PersistentCodeAuthor")
    heartbeat=(root/"LONG_HORIZON_CODE_AUTHOR_V1_20261126"/
               "worker_heartbeat.json" if is_writer else
               root/"RECONCILE_20261125"/"live_state_migrated_v1"/
               "daemon_heartbeat.json")
    if not heartbeat.is_file() or heartbeat.is_symlink():return False
    try:
        h=json.loads(heartbeat.read_text(encoding="utf8"))
        pid=h["worker_pid"] if is_writer else h["owner_pid"]
        need(type(pid) is int and pid>0,"Original task PID missing")
        epoch=(h["heartbeat_epoch"] if is_writer
               else datetime.fromisoformat(
                   h["heartbeat_utc"].replace("Z","+00:00")
               ).timestamp())
        if not 0<=time.time()-float(epoch)<=95:return False
        if h.get("student_publication_authorized") is not False:return False
        if is_writer:
            if h.get("new_paid_api_requests")!=0:return False
            module="development_persistent_selenium_author_v1"
        else:
            if h.get("provider_sends")!=0 or h.get("running") is not True:
                return False
            module="development_continuity_daemon_v71"
        query=("$p=Get-CimInstance Win32_Process -Filter ('ProcessId="+
               str(pid)+
               "');if($p){$parent=Get-CimInstance Win32_Process -Filter "+
               "('ProcessId='+[int]$p.ParentProcessId);"+
               "[ordered]@{cmd=[string]$p.CommandLine;"+
               "parent=if($parent){[string]$parent.CommandLine}else{''}}"+
               "|ConvertTo-Json -Compress}")
        process=json.loads(run(["powershell.exe","-NoProfile",
                                "-NonInteractive","-Command",query],timeout=25))
        if module not in process["cmd"]:return False
        if str(checkout).lower() not in (
                process["cmd"]+" "+process["parent"]).lower():
            return False
        return True
    except (KeyError,TypeError,ValueError,OSError,subprocess.TimeoutExpired):
        return False


def deploy(*,number:int,head_sha:str,cutover_root:Path,
           current_repo:Path,template_root:Path,record_root:Path,
           fetch=api,run_cmd=run,main_owner=None,writer_owner=None,
           cutover_fn=resume):
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "Autonomous guarded code deployment not in executable registry")
    cutover_root=Path(cutover_root).absolute()
    current_repo=Path(current_repo).absolute()
    template_root=Path(template_root).absolute()
    record_root=Path(record_root).absolute()
    need(cutover_root.is_dir() and not cutover_root.is_symlink()
         and current_repo.is_dir() and not current_repo.is_symlink()
         and template_root.is_dir() and not template_root.is_symlink()
         and record_root.is_dir() and not record_root.is_symlink(),
         "Independent certified template/receipt/production roots required")
    target_sha=original_main_pr(
        number=number,expected_head=head_sha,fetch=fetch)
    old=Path(current_repo)
    new=cutover_root/("post_pr"+str(number)+"_main")
    mstate=record_root/("pr"+str(number)+"_deployment.json")
    state=json.loads(mstate.read_text()) if mstate.exists() else {
        "schema_version":1,"status":"CERTIFIED_MERGE_VERIFIED",
        "pr_number":number,"head_sha":head_sha,
        "merge_sha":target_sha,"new_browser_sends":0,
        "paid_api_requests":0,"student_publication_authorized":False}
    need(state["pr_number"]==number and state["head_sha"]==head_sha
         and state["merge_sha"]==target_sha,
         "Deployment resumed with different GitHub source identity")
    if state["status"]=="GUARDED_DEPLOYED":return state
    need(not new.is_symlink(),"New production checkout must not redirect")
    if not new.exists():
        run_cmd(["git","clone","--filter=blob:none","--branch","main",
                 "https://github.com/tlyoon/MicroGen_AI_Web.git",
                 str(new)],timeout=180)
    need(new.is_dir()
         and run_cmd(["git","-C",str(new),"rev-parse","HEAD"])==target_sha
         and run_cmd(["git","-C",str(new),"status","--porcelain"])=="",
         "Source checkout not identical to independently verified GitHub main")
    need(checksum(old/"selenium_pipeline"/"development_continuity_executor_v71.py")
         ==checksum(new/"selenium_pipeline"/"development_continuity_executor_v71.py"),
         "Protected old v7.1 executor changed during software release")
    old_name=old.name
    new_name=new.name
    main_script=cutover_root/("guarded_cutover_after_pr"+str(number)+".ps1")
    author_script=cutover_root/(
        "guarded_persistent_author_cutover_after_pr"+str(number)+".ps1")
    base={
        "__OLD_REPO__":old_name,
        "__NEW_REPO__":new_name,
        "__TASK_BEFORE__":"task_before_pr"+str(number)+"_cutover.xml",
        "__MAIN_RECEIPT__":"post_pr"+str(number)+"_cutover_receipt.json",
    }
    main_sha=template(template_root/MAIN_TEMPLATE,base,main_script)
    writer_sha=template(template_root/AUTHOR_TEMPLATE,{
        "__OLD_REPO__":old_name,"__NEW_REPO__":new_name,
        "__TASK_BEFORE__":"task_before_pr"+str(number)+
            "_persistent_author_cutover.xml",
        "__AUTHOR_RECEIPT__":"PR"+str(number)+
            "_PERSISTENT_CODE_WRITER_CUTOVER_RECEIPT.json",
    },author_script)
    need(state.get("main_guard_sha256") in (None,main_sha)
         and state.get("writer_guard_sha256") in (None,writer_sha),
         "Old certified deployment script was substituted")
    state["main_guard_sha256"]=main_sha
    state["writer_guard_sha256"]=writer_sha
    if state["status"]=="CERTIFIED_MERGE_VERIFIED":
        state["status"]="GUARDED_MAIN_CUTOVER_PREPARED"
    save(mstate,state)

    is_main_owner=main_owner or attested_task
    is_writer_owner=writer_owner or attested_task
    daemon="MicroGen_AI_Web_v71_OfflineDevelopment"
    writer="MicroGen_AI_Web_v1_PersistentCodeAuthor"
    if not is_main_owner(daemon,new):
        need(state.get("status")!="GUARDED_DAEMON_CUTOVER_CLAIMED",
             "Previous main-daemon cutover uncertain: verify source owner, no retry")
        need(is_main_owner(daemon,old),
             "Original read-only daemon is neither safe old nor new owner")
        manifest={
          "schema_version":1,"task_name":daemon,
          "root":str(cutover_root),"old_repo":str(old),"new_repo":str(new),
          "state_dir":str(cutover_root/"live_state_migrated_v1"),
          "original_plan":(
            "C:\\Users\\tlyoon\\AppData\\Local\\MicroGen_AI_Web_Checkpoints"
            "\\CONTINUITY_EXECUTOR_V71_20261121\\real_offline_roadmap_20261121.json"),
          "guard_script":str(main_script),
          "guard_script_sha256":main_sha,
          "expected_main_sha":target_sha,
          "new_provider_sends_allowed":False,
          "student_publication_authorized":False,
        }
        manifest_file=cutover_root/(
            "PR"+str(number)+"_CUTO_AUTONOMOUS_MANIFEST.json")
        blob=(json.dumps(manifest,sort_keys=True,indent=2)+"\n").encode("utf8")
        if manifest_file.exists():
            need(manifest_file.read_bytes()==blob,
                 "Changed previously claimed guarded daemon manifest")
        else:
            with manifest_file.open("xb") as stream:stream.write(blob)
        state["status"]="GUARDED_DAEMON_CUTOVER_CLAIMED"
        save(mstate,state)
        output=cutover_fn(
            manifest=manifest_file,
            report_root=cutover_root/("PR"+str(number)+"_AUTO_GUARDED_RECOVERY"))
        need(output.get("status")==COMPLETE and is_main_owner(daemon,new),
             "Original daemon cutover outcome not independently proven")
    if state["status"]!="GUARDED_WRITER_CUTOVER_CLAIMED":
        state["status"]="GUARDED_DAEMON_DEPLOYED"
    save(mstate,state)

    if not is_writer_owner(writer,new):
        need(state.get("status")!="GUARDED_WRITER_CUTOVER_CLAIMED",
             "Previous model-writer cutover uncertain: no repeat without owner proof")
        need(is_writer_owner(writer,old),
             "Original model-code writer owner not attested: HOLD")
        # Any failure is ambiguous until fresh Scheduled Task owner readback;
        # the original proven PowerShell guard includes native rollback.
        state["status"]="GUARDED_WRITER_CUTOVER_CLAIMED"
        save(mstate,state)
        try:
            run_cmd(["powershell.exe","-NoProfile","-NonInteractive",
                     "-ExecutionPolicy","Bypass","-File",
                     str(author_script)],timeout=200)
        except (ValueError,OSError,subprocess.TimeoutExpired):
            pass
        need(is_writer_owner(writer,new),
             "Original code writer guarded cutover not independently verified")
    state["status"]="GUARDED_DEPLOYED"
    state["deployed_main_sha"]=target_sha
    save(mstate,state)
    return state
