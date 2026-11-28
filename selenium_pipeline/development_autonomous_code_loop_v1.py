"""Persistent, restart-safe code generation -> PR/CI -> guarded deploy loop.

This controller never makes model requests itself. A separate authenticated
Selenium Windows worker generates SHA-bound source files after one durable
Send claim. This controller promotes only independent-test-verified results,
verifies GitHub's protected Windows CI, and delegates deployment to the
original guarded Windows task recovery mechanisms.

Code promotion is deterministic and fail-closed; incomplete/uncertain work
cannot stop independent next-source task selection.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from .development_verified_candidate_promotion_v1 import promote
from .development_certified_candidate_deploy_v1 import deploy
from .development_source_pinned_next_job_v1 import select
from .development_ci_merged_main_autocutover_v1 import catch_up
from .three_pc_worker import LocalInstanceLock

STATUS="MICROGEN_AUTONOMOUS_SOURCE_TO_PRODUCTION_V1"
HOLD=frozenset({
    "REMOTE_MUTATION_UNCERTAIN_NO_RETRY",
    "GITHUB_WINDOWS_CI_AWAITING_EVIDENCE",
    "GITHUB_PR_VERIFIED",
})


def _owner_repo():
    ps=(
        "$ErrorActionPreference='Stop';"
        "$t=Get-ScheduledTask -TaskName 'MicroGen_AI_Web_v71_OfflineDevelopment';"
        "[ordered]@{state=[string]$t.State;"
        "working_dir=[string]$t.Actions[0].WorkingDirectory;"
        "logon_type=[string]$t.Principal.LogonType;"
        "run_level=[string]$t.Principal.RunLevel}"
        "|ConvertTo-Json -Compress"
    )
    v=subprocess.run(["powershell.exe","-NoProfile",
                      "-NonInteractive","-Command",ps],
                     capture_output=True,text=True,timeout=20)
    if v.returncode:
        raise ValueError("Original protected Windows daemon task unavailable")
    state=json.loads(v.stdout)
    if (state.get("state")!="Running"
            or state.get("logon_type")!="Interactive"
            or state.get("run_level")!="Limited"):
        raise ValueError("Original offline daemon policy not certified")
    path=Path(state["working_dir"]).absolute()
    if not path.is_dir() or path.is_symlink():
        raise ValueError("Original daemon code checkout inaccessible")
    return path


def cycle(*,backlog_root:Path,control_root:Path,catalog_path:Path,
          template_root:Path,cutover_root:Path,main_repo:Path|None=None,
          promote_fn=promote,deploy_fn=deploy,select_fn=select,
          source_sync_fn=catch_up):
    backlog_root=Path(backlog_root).absolute()
    control_root=Path(control_root).absolute()
    template_root=Path(template_root).absolute()
    cutover_root=Path(cutover_root).absolute()
    catalog_path=Path(catalog_path).absolute()
    if not all(p.is_dir() and not p.is_symlink()
               for p in (backlog_root,control_root,template_root,cutover_root)):
        raise ValueError("Original safe continuation storage missing")
    native_source_owner=main_repo is None
    if main_repo is None:
        main_repo=_owner_repo()
    else:
        main_repo=Path(main_repo).absolute()
    if not main_repo.is_dir() or main_repo.is_symlink():
        raise ValueError("Current main checkout not certified")
    inbox=backlog_root/"inbox"
    promotion_states=control_root/"promotions"
    worktrees=promotion_states/"worktrees"
    if not all(x.is_dir() and not x.is_symlink()
               for x in (inbox,promotion_states,worktrees)):
        raise ValueError("Work inbox / protected promoter state missing")
    jobs=sorted(inbox.glob("*.json"))
    if len(jobs)>16:
        raise ValueError("Too many original coding jobs")
    result={"schema_version":1,"status":STATUS,"main_repo":str(main_repo),
            "observed_jobs":len(jobs),"jobs":[],"new_model_sends":0,
            "new_paid_gemini_API_calls":0,
            "student_publication_authorized":False}
    # Deployment first: a merged PR blocks starting another candidate from
    # a stale main until the original Windows tasks have the new source.
    for job in jobs:
        previous=promotion_states/(job.stem+".json")
        if not previous.is_file():
            continue
        saved=json.loads(previous.read_text(encoding="utf8"))
        if saved.get("status")!="MERGED_AWAITING_GUARDED_CUTOVER":
            continue
        # The guarded cutover switches the read-only daemon FIRST. After a
        # crash, the next cycle sees the NEW checkout from Task Scheduler,
        # while the code writer might still be on the OLD checkout. Pin the
        # old owner before any Windows side effect, and keep it across
        # restarts until both workers are independently attested.
        from .development_verified_candidate_promotion_v1 import save
        if "deployment_original_repo" not in saved:
            saved["deployment_original_repo"]=str(main_repo)
            save(previous,saved)
        old=Path(saved["deployment_original_repo"]).absolute()
        if (not old.is_dir() or old.is_symlink()
                or not old.is_relative_to(cutover_root)
                or old==cutover_root):
            raise ValueError("Original guarded deployment checkout was lost")
        item=deploy_fn(
            number=saved["pr_number"],
            head_sha=saved["promotion_commit_sha"],
            cutover_root=cutover_root,current_repo=old,
            template_root=template_root,record_root=control_root)
        result["jobs"].append({"id":job.stem,
                               "status":item["status"],
                               "stage":"PROTECTED_DEPLOY"})
        if item["status"]=="GUARDED_DEPLOYED":
            saved["status"]="GUARDED_DEPLOYED"
            from .development_verified_candidate_promotion_v1 import save
            save(previous,saved)
        return result
    # Before staging code from a stale revision, reconcile unrelated,
    # independently Windows-CI-certified protected GitHub main merges.
    # The original source-tested model PR deployment above keeps priority.
    if native_source_owner:
        try:
            upgrade=source_sync_fn(
                old_repo=main_repo, controller_root=control_root,
                cutover_root=cutover_root, template_root=template_root)
        except (ValueError,KeyError,OSError,TypeError,
                subprocess.TimeoutExpired) as exc:
            result["source_sync"]={
                "status":"CERTIFIED_MAIN_SOURCE_CUTOVER_HELD",
                "error_class":type(exc).__name__, "model_sends":0,
                "student_publication_authorized":False}
            return result
        result["source_sync"]=upgrade
        if upgrade["status"]=="CERTIFIED_MAIN_SOURCE_AUTO_CUTOVER_DEPLOYED":
            return result
    # Exactly one live PR per cycle. Avoid racing a new source commit with
    # pending exact-head Windows CI or a remote GitHub ambiguity.
    for job in jobs:
        record=promotion_states/(job.stem+".json")
        if record.is_file():
            saved=json.loads(record.read_text(encoding="utf8"))
            if saved["status"] in ("GUARDED_DEPLOYED",
                                  "ALREADY_ON_VERIFIED_MAIN"):
                continue
            if saved["status"] in ("REMOTE_MUTATION_UNCERTAIN_NO_RETRY",
                                   "GITHUB_WINDOWS_CI_FAILED_HELD"):
                # Quarantine only that original PR, other eligible sources
                # can proceed independently. Never replay its mutation.
                result["jobs"].append({"id":job.stem,
                    "status":saved["status"]})
                continue
        original=backlog_root/"state"/job.stem/"coding_state.json"
        if not original.is_file():
            result["jobs"].append({"id":job.stem,
                                   "status":"NEW_JOB_AWAITING_FIRST_WORKER_CLAIM"})
            return result
        source=json.loads(original.read_text(encoding="utf8"))
        if source.get("status") in ("SEND_CLAIMED_UNCERTAIN",
                                    "MODEL_REPLY_SAVED",
                                    "SOURCE_APPLIED_CANDIDATE"):
            result["jobs"].append({"id":job.stem,
                                   "status":"ELIGIBLE_CODE_WORKER_STILL_ACTIVE"})
            return result
        if source.get("status")!="SOURCE_CANDIDATE_TESTED_NO_PUBLICATION":
            result["jobs"].append({"id":job.stem,
                                  "status":source.get("status","UNKNOWN")})
            continue
        try:
            promoted=promote_fn(job_path=job,root=backlog_root,
                                main_repo=main_repo,
                                promotions=promotion_states)
        except (ValueError,KeyError,OSError,TypeError,
                subprocess.TimeoutExpired) as exc:
            result["jobs"].append({"id":job.stem,
                    "status":"SOURCE_PROMOTION_HELD",
                    "error_class":type(exc).__name__})
            continue
        result["jobs"].append({"id":job.stem,"status":promoted["status"]})
        if promoted["status"] not in (
                "ALREADY_ON_VERIFIED_MAIN","GUARDED_DEPLOYED",
                "GITHUB_WINDOWS_CI_FAILED_HELD"):
            return result

    # Admit ONE new original job from a pre-authored, independently tested
    # catalogue. The separate Selenium worker notices it on its next poll.
    try:
        added=select_fn(catalog_path=catalog_path,
                        backlog_root=backlog_root,repo_root=main_repo)
        result["new_job"]=added
    except (ValueError,KeyError,OSError,TypeError,
            subprocess.TimeoutExpired) as exc:
        result["new_job"]={"status":"NEW_SOURCE_JOB_ADMISSION_HELD",
                           "error_class":type(exc).__name__,
                           "model_sends":0}
    return result


def serve(*,backlog_root:Path,control_root:Path,catalog_path:Path,
          template_root:Path,cutover_root:Path,
          cycles:int=0,poll_seconds:int=45,
          cycle_fn=cycle):
    if not isinstance(cycles,int) or not 0<=cycles<=10000:
        raise ValueError("Invalid bounded restart test cycles")
    if not isinstance(poll_seconds,int) or not 5<=poll_seconds<=300:
        raise ValueError("Invalid persistent polling interval")
    root=Path(control_root).absolute()
    if not root.is_dir() or root.is_symlink():
        raise ValueError("No persistent original controller checkpoint root")
    count=0
    while True:
        with LocalInstanceLock("autonomous_model_code_promotion_v1",root):
            # Each cycle obtains the CURRENT source checkout from the
            # protected original Windows task, not stale installation.
            try:
                summary=cycle_fn(
                    backlog_root=backlog_root,control_root=root,
                    catalog_path=catalog_path,template_root=template_root,
                    cutover_root=cutover_root)
            except (ValueError,KeyError,OSError,TypeError,
                    subprocess.TimeoutExpired) as exc:
                summary={"schema_version":1,
                    "status":"AUTONOMOUS_CODE_CYCLE_HELD",
                    "error_class":type(exc).__name__,
                    "new_model_sends":0,
                    "student_publication_authorized":False}
            count+=1
            heartbeat={
                **summary,"controller_pid":os.getpid(),
                "cycle":count,"heartbeat_epoch":time.time(),
                "new_paid_gemini_API_calls":0,
                "student_publication_authorized":False,
            }
            from .development_continuity_executor_v71 import _atomic_json
            _atomic_json(root/"autonomous_controller_heartbeat.json",
                         heartbeat)
        if cycles and count>=cycles:
            return heartbeat
        time.sleep(poll_seconds)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backlog-root",required=True,type=Path)
    p.add_argument("--control-root",required=True,type=Path)
    p.add_argument("--catalog",required=True,type=Path)
    p.add_argument("--template-root",required=True,type=Path)
    p.add_argument("--cutover-root",required=True,type=Path)
    p.add_argument("--cycles",type=int,default=0)
    p.add_argument("--poll-seconds",type=int,default=45)
    a=p.parse_args(argv)
    result=serve(backlog_root=a.backlog_root,control_root=a.control_root,
                 catalog_path=a.catalog,template_root=a.template_root,
                 cutover_root=a.cutover_root,cycles=a.cycles,
                 poll_seconds=a.poll_seconds)
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
