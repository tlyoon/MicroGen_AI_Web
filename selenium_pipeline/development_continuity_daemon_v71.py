"""On-demand persistent *offline-only* MicroGen v7.1 roadmap daemon.

A real live process can own a pinned roadmap and poll for original receipt
resolution after an interactive conversation ends. The daemon itself cannot
send Gemini requests, edit code, merge PRs, alter scheduled tasks or release
lecture material. No Windows scheduled task is installed by this module.

A heartbeat alone is NOT proof of liveness: external status viewers must
also establish actual OS PID ownership and freshness.
"""
from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from datetime import datetime, timezone
import os
import subprocess
from pathlib import Path
import threading
import uuid

from .development_continuity_executor_v71 import (
    _atomic_json,_exclusive,_plan,_read_json,_sha,execute,require_recovery,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def attest_live_daemon(*,state_dir:Path,max_age_seconds:float=90)->dict:
    """Confirm process ownership, not merely a stale heartbeat JSON file."""
    path=Path(state_dir).absolute()/"daemon_heartbeat.json"
    missing={"status":"OFFLINE_OR_UNVERIFIED","running_verified":False}
    if not path.is_file() or path.is_symlink() or not 1<=path.stat().st_size<=5000:
        return missing
    try:
        saved=_read_json(path)
        pid=saved["owner_pid"]
        last=datetime.fromisoformat(saved["heartbeat_utc"].replace("Z","+00:00"))
        age=(datetime.now(timezone.utc)-last).total_seconds()
        if (type(pid) is not int or pid<=0
            or saved.get("schema_version")!=1
            or saved.get("running") is not True
            or not 0<=age<=max_age_seconds
            or saved.get("provider_sends")!=0
            or saved.get("student_publication_authorized") is not False):
            return missing
        attestation_method="UNVERIFIED"
        if os.name=="nt":
            cmd=(
                "$p=Get-CimInstance Win32_Process -Filter 'ProcessId = "
                +str(pid)+"';if($null -ne $p){$p.CommandLine}")
            proc=subprocess.run(["powershell.exe","-NoProfile",
                                 "-NonInteractive","-Command",cmd],
                                capture_output=True,text=True,timeout=12)
            live=(proc.returncode==0
                  and "development_continuity_daemon_v71" in proc.stdout)
            if live:
                attestation_method="WINDOWS_CIM_COMMAND_LINE"
            elif "invalid class" in (proc.stderr+" "+proc.stdout).casefold():
                # On HP, the Windows WMI Win32_Process class is unavailable.
                # Do NOT substitute PID existence or a heartbeat alone:
                # prove this is the same real python.exe PROCESS CREATION
                # as the independently persisted initial daemon heartbeat.
                from .recovery_registry import lookup_mechanism
                if lookup_mechanism(
                    "daemon_owner_attestation",
                    "V71_WINDOWS_WMI_PROCESS_CLASS_UNAVAILABLE"
                ) != "VERIFY_NATIVE_PID_EXE_AND_STARTTIME_WITHOUT_MODEL_SEND":
                    return missing
                native=(
                    "$ErrorActionPreference='Stop';"
                    "$p=Get-Process -Id "+str(pid)+" -ErrorAction Stop;"
                    "@{name=[string]$p.ProcessName;"
                    "exe=[string]$p.Path;"
                    "started_utc=$p.StartTime.ToUniversalTime().ToString('o')}"
                    "|ConvertTo-Json -Compress")
                os_process=subprocess.run([
                    "powershell.exe","-NoProfile","-NonInteractive",
                    "-Command",native],capture_output=True,text=True,
                    timeout=12)
                if os_process.returncode!=0 or not os_process.stdout.strip():
                    return missing
                observed=json.loads(os_process.stdout)
                started=datetime.fromisoformat(
                    saved["started_utc"].replace("Z","+00:00"))
                os_started=datetime.fromisoformat(
                    observed["started_utc"].replace("Z","+00:00"))
                difference=(started-os_started).total_seconds()
                live=(observed.get("name","").casefold() in {"python","pythonw"}
                      and Path(observed.get("exe","")).name.casefold()
                      in {"python.exe","pythonw.exe"}
                      and -2<=difference<=30)
                if live:
                    attestation_method="WINDOWS_NATIVE_PID_EXE_STARTTIME"
        else:
            cmdline=Path("/proc")/str(pid)/"cmdline"
            live=(cmdline.is_file()
                  and b"development_continuity_daemon_v71" in cmdline.read_bytes())
            if live:
                attestation_method="LINUX_PROCFS_COMMAND_LINE"
        if not live:
            return missing
        return {"status":"LIVE_OFFLINE_EXECUTOR_ATTESTED",
                "running_verified":True,
                "identity_attestation_method":attestation_method,
                "owner_pid":pid,
                "run_id":saved["run_id"],
                "heartbeat_age_seconds":round(age,2),
                "code_authoring_executor":False,
                "paid_model_sends":0,
                "student_publication_authorized":False}
    except (ValueError,KeyError,OSError,subprocess.TimeoutExpired,
            TypeError,OverflowError):
        return missing


@contextmanager
def _daemon_lock(directory: Path):
    """A second exclusive OS lock, distinct from the worker dispatch lock."""
    directory.mkdir(parents=True, exist_ok=True)
    lockfile=directory/"daemon.lock"
    if lockfile.is_symlink():
        raise ValueError("Linked daemon lock")
    lockfile.touch(exist_ok=True)
    try:
        stream = lockfile.open("r+b")
    except PermissionError as exc:
        require_recovery("CONCURRENT_DAEMON_OWNER")
        # Windows may deny opening a byte-range locked file before a
        # second process reaches msvcrt.locking. This is an owned-lock
        # observation, never permission to start a duplicate daemon.
        raise RuntimeError(
            "A persistent MicroGen controller already owns this roadmap") from exc
    with stream as out:
        # Only initialize an empty lock file. On Windows, writing to an
        # already locked first byte raises PermissionError *before* the
        # attempt to acquire a competing byte lock.
        if out.seek(0,os.SEEK_END)==0:
            out.write(b"1")
            out.flush()
        out.seek(0)
        try:
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(out.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(out.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:
            require_recovery("CONCURRENT_DAEMON_OWNER")
            raise RuntimeError("A persistent MicroGen controller already owns this roadmap") from exc
        try:
            yield
        finally:
            if os.name=="nt":
                out.seek(0)
                msvcrt.locking(out.fileno(),msvcrt.LK_UNLCK,1)
            else:
                fcntl.flock(out.fileno(),fcntl.LOCK_UN)


def daemon(*,plan_path: Path,state_dir: Path,repo_root: Path,
           poll_seconds:float=120.0,heartbeat_seconds:float=5.0,
           max_cycles:int=0,handoff_dir:Path|None=None)->dict:
    """Explicitly invoked persistent process. max_cycles=0 means indefinite."""
    if (not 1<=poll_seconds<=3600
        or not .5<=heartbeat_seconds<=600
        or not 0<=max_cycles<=100000):
        raise ValueError("Unsafe daemon poll or heartbeat interval")
    plan_path=Path(plan_path).absolute()
    state_dir=Path(state_dir).absolute()
    repo_root=Path(repo_root).resolve()
    _plan(plan_path)
    plan_sha=_sha(plan_path)
    if handoff_dir is not None:
        handoff_dir=Path(handoff_dir).absolute()
        if not handoff_dir.is_dir() or handoff_dir.is_symlink():
            raise ValueError("Explicit immutable handoff intake directory missing")
    state_dir.mkdir(parents=True,exist_ok=True)
    if state_dir.is_symlink():
        raise ValueError("Linked daemon checkpoint directory")
    report_file=state_dir/"daemon_heartbeat.json"
    run_id=uuid.uuid4().hex
    stop=threading.Event()
    state={
        "schema_version":1,
        "status":"INITIALIZING",
        "running":True,
        "owner_pid":os.getpid(),
        "run_id":run_id,
        "plan_sha256":plan_sha,
        "started_utc":_now(),
        "heartbeat_utc":_now(),
        "last_controller_status":None,
        "last_controller_completed":False,
        "cycles":0,
        "provider_sends":0,
        "student_publication_authorized":False,
        "existing_scheduled_tasks_modified":False,
        "handoff_dir":str(handoff_dir) if handoff_dir is not None else None,
        "last_handoff_status":"NOT_CONFIGURED",
        "last_source_eligibility_status":"NOT_CONFIGURED",
        "last_source_eligibility_slides":[],
        "last_g3_source_status":"NOT_CONFIGURED",
        "source_eligibility_error_class":None,
        "last_historical_g2_disposition":"NOT_CONFIGURED",
        "last_historical_g2_receipt_sha256":None,
        "historical_g2_disposition_error_class":None,
        "handoff_worker_starts_total":0,
        "code_authoring_executor":False,
        "last_journal_recovery_status":"NOT_REQUIRED",
        "original_journals_archived":0,
    }
    guard=threading.Lock()

    def report(status: str | None = None):
        with guard:
            if status is not None:
                state["status"]=status
            state["heartbeat_utc"]=_now()
            _atomic_json(report_file,dict(state))

    def heartbeat():
        while not stop.wait(heartbeat_seconds):
            try:
                report()
            except OSError:
                # Missing shared disk cannot manufacture acceptance.
                stop.set()
                break

    with _daemon_lock(state_dir):
        report("RUNNING")
        thread=threading.Thread(target=heartbeat,name="v71-heartbeat",daemon=True)
        thread.start()
        try:
            while not stop.is_set():
                if _sha(plan_path)!=plan_sha:
                    raise ValueError("Roadmap mutated while persistent supervisor active")
                # Before every offline cycle, repair repeated idle events
                # using an OS-locked SHA-preserved original journal archive.
                # This does not modify the pinned task executor (its hash
                # lives in the historical checkpoint), initiate any Send,
                # or change plan/task acceptance or release authorization.
                from .development_continuity_journal_recovery_v71 import (
                    recover_journal)
                journal=recover_journal(
                    state_dir=state_dir,plan_path=plan_path)
                with guard:
                    state["last_journal_recovery_status"]=journal["status"]
                    if journal["status"]==(
                        "ORIGINAL_POLLING_JOURNAL_SHA_ARCHIVED_AND_COMPACTED"):
                        state["original_journals_archived"]+=1
                outcome=execute(plan_path=plan_path,state_dir=state_dir,
                                repo_root=repo_root)
                # The fixed source plan may be blocked at a release gate.
                # Do not stop there: discover newly placed, explicitly
                # authored *offline-only* independent work in the same
                # live daemon execution opportunity.
                handoff=None
                admission=None
                historical=None
                if handoff_dir is not None:
                    from .development_g2g3_eligible_dispatch_v1 import (
                        discover)
                    try:
                        admission=discover(
                            handoff_dir=handoff_dir,state_dir=state_dir)
                    except (ValueError, OSError, KeyError, TypeError) as exc:
                        # A malformed or changed source is confined to this
                        # lane; independent already-pinned plans still run.
                        admission={
                            "status":"SOURCE_PINNED_DISCOVERY_HELD",
                            "g3_status":"SOURCE_IDENTITY_UNVERIFIED",
                            "source_g2_slides":[],
                            "error_class":type(exc).__name__,
                            "new_browser_sends":0,
                            "new_paid_gemini_API_calls":0,
                            "student_publication_authorized":False,
                        }
                    from .development_continuity_handoff_v71 import (
                        scan_and_dispatch)
                    handoff=scan_and_dispatch(
                        handoff_dir=handoff_dir,state_dir=state_dir,
                        repo_root=repo_root)
                    from .g2_owned_request_outcome_reconciliation_v1 import (
                        auto_audit_completed_handoff)
                    try:
                        historical=auto_audit_completed_handoff(
                            handoff_dir=handoff_dir,state_dir=state_dir)
                    except (ValueError,OSError,KeyError,TypeError) as exc:
                        # This original owned-model-response lane is
                        # evidence-only. Hold it without stopping independent
                        # accepted source workers or replaying an old request.
                        historical={
                            "status":"HISTORICAL_G2_OWNED_EVIDENCE_HELD",
                            "error_class":type(exc).__name__,
                            "new_browser_sends":0,
                            "new_paid_gemini_API_calls":0,
                            "student_publication_authorized":False,
                        }
                with guard:
                    state["last_controller_status"]=outcome["status"]
                    state["last_controller_completed"]=outcome["project_complete"]
                    state["cycles"]+=1
                    if admission is not None:
                        state["last_source_eligibility_status"]=admission["status"]
                        state["last_source_eligibility_slides"]=admission.get(
                            "source_g2_slides",[])
                        state["last_g3_source_status"]=admission["g3_status"]
                        state["source_eligibility_error_class"]=admission.get(
                            "error_class")
                    if historical is not None:
                        state["last_historical_g2_disposition"]=historical["status"]
                        state["last_historical_g2_receipt_sha256"]=historical.get(
                            "receipt_sha256")
                        state["historical_g2_disposition_error_class"]=historical.get(
                            "error_class")
                    if handoff is not None:
                        state["last_handoff_status"]=handoff["status"]
                        state["handoff_worker_starts_total"]+=handoff[
                            "new_worker_starts"]
                report("HANDOFF_DISPATCH_VERIFIED"
                       if handoff is not None and handoff[
                           "new_worker_starts"]>0 else
                       "SOURCE_PINNED_DISCOVERY_HELD"
                       if admission is not None and admission["status"]==
                           "SOURCE_PINNED_DISCOVERY_HELD" else
                       "HANDOFF_CANDIDATE_QUARANTINED"
                       if handoff is not None and any(
                           x["status"] in {"CHANGED_PLAN_CONSUMED_NO_REPLAY",
                               "QUARANTINED_INVALID_PLAN"}
                           for x in handoff["outcomes"]) else
                       "G2_G3_INDEPENDENT_ACCEPTANCE_EVIDENCE_REQUIRED"
                       if admission is not None and admission["g3_status"]==
                           "G3_ORIGINAL_SOURCE_COMPLETE_SCIENCE_AUDIO_VIDEO_OPEN"
                       else "WAITING_FOR_ELIGIBLE_WORK"
                       if not outcome["project_complete"]
                       else "LOCAL_PLAN_COMPLETE_MONITORING")
                if max_cycles and state["cycles"]>=max_cycles:
                    break
                stop.wait(poll_seconds)
        finally:
            stop.set()
            thread.join(timeout=2)
            with guard:
                state["running"]=False
                state["stopped_utc"]=_now()
            report("STOPPED")
    return dict(state)


def main(argv:list[str]|None=None)->int:
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--plan",type=Path,required=True)
    a.add_argument("--state-dir",type=Path,required=True)
    a.add_argument("--repo-root",type=Path,default=Path.cwd())
    a.add_argument("--poll-seconds",type=float,default=120)
    a.add_argument("--heartbeat-seconds",type=float,default=5)
    a.add_argument("--max-cycles",type=int,default=0)
    a.add_argument("--handoff-dir",type=Path,default=None,
                   help="Explicit source-pinned next_*.json offline plan inbox")
    arg=a.parse_args(argv)
    final=daemon(plan_path=arg.plan,state_dir=arg.state_dir,
                 repo_root=arg.repo_root,
                 poll_seconds=arg.poll_seconds,
                 heartbeat_seconds=arg.heartbeat_seconds,
                 max_cycles=arg.max_cycles,handoff_dir=arg.handoff_dir)
    print("MicroGen v7.1 offline supervisor stopped; cycles:",
          final["cycles"],"last:",final["last_controller_status"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
