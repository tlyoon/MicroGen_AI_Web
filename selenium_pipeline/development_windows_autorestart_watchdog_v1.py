"""Dell-115 bounded watchdog for the two non-provider MicroGen development tasks.

A separate native five-minute time trigger calls this module once per run.
Never write application source, issue Gemini Sends, perform GitHub merges or
publish. Resume *only* the exact original offline daemon and the guarded
promotion controller, after independent native, source and heartbeat checks.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from .development_continuity_daemon_v71 import attest_live_daemon
from .recovery_registry import lookup_mechanism

TASK_DAEMON = "MicroGen_AI_Web_v71_OfflineDevelopment"
TASK_PROMOTE = "MicroGen_AI_Web_v1_CodePromotionOrchestrator"
TASK_AUTHOR = "MicroGen_AI_Web_v1_PersistentCodeAuthor"
WATCHDOG_NAME = "MicroGen_AI_Web_v1_RecoveryWatchdog"
KIND = "long_horizon_windows_task_self_heal"
SIGNATURE = "NATIVE_LOGON_ONLY_DEVELOPMENT_TASKS_EXHAUST_RESTARTS_AND_STOP"
MECHANISM = "SOURCE_GUARDED_FIVE_MINUTE_RECONCILE_ONLY_STOPPED_TASKS"
STALE_SECONDS = 180
LOCAL_ROOT = Path.home() / "AppData" / "Local" / "MicroGen_AI_Web_Checkpoints"
CONTROLLER_ROOT = LOCAL_ROOT / "AUTONOMOUS_CODE_PROMOTION_V1_20261127"
CUTOVER_ROOT = LOCAL_ROOT / "RECONCILE_20261125"
REPO_NAME = re.compile(r"post_pr[0-9]{3,5}_main\Z")
RECEIPT = CONTROLLER_ROOT / "native_health_watchdog_v1.json"
TASKS = (TASK_DAEMON, TASK_PROMOTE)

def require(ok, message):
    if not ok:
        raise ValueError(message)

def native_ps(script, timeout=50):
    process = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=timeout)
    require(process.returncode == 0,
            "Windows Task Scheduler readback/action failed (exit="
            + str(process.returncode) + "): " + process.stderr[-200:])
    return process.stdout.strip()

def native_snapshot(ps=native_ps):
    """Do not infer task ownership or run state from user-editable files."""
    code = r"""
$ErrorActionPreference='Stop'
$own=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$rows=@()
foreach($n in @('MicroGen_AI_Web_v71_OfflineDevelopment','MicroGen_AI_Web_v1_CodePromotionOrchestrator')){
    $t=Get-ScheduledTask -TaskName $n -ErrorAction Stop
    if(@($t.Actions).Count -ne 1){throw "Unexpected action count"}
    $sid=(New-Object Security.Principal.NTAccount($t.Principal.UserId)).Translate(
       [Security.Principal.SecurityIdentifier]).Value
    $rows+=@{
       name=[string]$n;state=[string]$t.State
       action=[string]$t.Actions[0].Execute
       arguments=[string]$t.Actions[0].Arguments
       workdir=[string]$t.Actions[0].WorkingDirectory
       task_enabled=[bool]$t.Settings.Enabled
       logon=[string]$t.Principal.LogonType
       runlevel=[string]$t.Principal.RunLevel
       multiple=[string]$t.Settings.MultipleInstances
       principal_sid=[string]$sid;current_sid=[string]$own
    }
}
ConvertTo-Json -InputObject $rows -Compress -Depth 4
"""
    data = json.loads(ps(code))
    require(type(data) is list and len(data) == 2
            and {x.get("name") for x in data} == set(TASKS),
            "Native trusted task snapshot missing/ambiguous")
    return {x["name"]:x for x in data}

def _owner_verified(native):
    require(set(native) == set(TASKS),
            "Only exact original offline and promotion tasks are eligible")
    for key, task in native.items():
        require(type(task) is dict and task.get("name") == key
                and task.get("task_enabled") is True
                and task.get("logon") == "Interactive"
                and task.get("runlevel") == "Limited"
                and task.get("multiple") == "IgnoreNew"
                and task.get("principal_sid") == task.get("current_sid")
                and type(task.get("principal_sid")) is str
                and bool(re.fullmatch(r"S-1-[0-9-]+",
                                      task["principal_sid"]))
                and task.get("state") in ("Ready", "Running"),
                "Untrusted task principal, configuration or task state")
    d = native[TASK_DAEMON]
    p = native[TASK_PROMOTE]
    require(Path(d["action"]).name.lower() == "python.exe"
            and "-m selenium_pipeline.development_continuity_daemon_v71" in
                d["arguments"]
            and '--max-cycles "0"' in d["arguments"]
            and Path(p["action"]).name.lower() == "powershell.exe"
            and "start_microgen_autonomous_code_promotion_v1.ps1" in
                p["arguments"],
            "Non-original task action or bounded daemon altered")
    repo = Path(d["workdir"])
    require(repo.name and REPO_NAME.fullmatch(repo.name)
            and repo.parent == CUTOVER_ROOT
            and repo.is_dir() and not repo.is_symlink()
            and ('--repo-root "' + str(repo) + '"') in d["arguments"]
            and Path(p["workdir"]).is_dir(),
            "Original daemon source checkout identity unresolved")
    return repo

def _verified_main(repo, runner):
    require(os.name == "nt"
            and os.environ.get("COMPUTERNAME", "").casefold() == "dell-115",
            "Watchdog limited to Dell-115 Windows")
    def gitcmd(args):
        res = runner(args, capture_output=True, text=True, timeout=45)
        require(res.returncode == 0,
                "Current protected GitHub main cannot be verified")
        return res.stdout.strip()
    current = gitcmd(["git","-C",str(repo),"rev-parse","HEAD"])
    remote = gitcmd(["gh","api",
            "repos/tlyoon/MicroGen_AI_Web/commits/main","--jq",".sha"])
    clean = gitcmd(["git","-C",str(repo),"status","--porcelain"])
    require(re.fullmatch(r"[0-9a-f]{40}",current) and current == remote
            and clean == "",
            "Only clean exact-current protected GitHub main may be resumed")
    return current

def _beat_age(heartbeat, now):
    if type(heartbeat) is not dict:
        return None
    when=heartbeat.get("heartbeat_utc")
    if type(when) is not str:
        return None
    try:
        timestamp=dt.datetime.fromisoformat(when.replace("Z","+00:00"))
        if timestamp.tzinfo is None:
            return None
        age=(now-timestamp.astimezone(dt.timezone.utc)).total_seconds()
        if age < 0 or age > 86400 * 30:
            return None
        return age
    except (ValueError, OverflowError):
        return None

def eligible(native, heartbeat, now):
    """Pure fail-closed decision used in tests and actual Windows watchdog."""
    repo=_owner_verified(native)
    require(type(now) is dt.datetime and now.tzinfo is not None,
            "Time with explicit timezone required")
    age=_beat_age(heartbeat,now)
    require(age is not None,
            "Original heartbeat missing or clock not reconcilable")
    d=native[TASK_DAEMON]["state"]
    p=native[TASK_PROMOTE]["state"]
    if d == "Ready":
        if age < STALE_SECONDS:
            return "RECENT_DAEMON_EXIT_RECHECK_NEXT_TICK",repo
        return "START_ORIGINAL_OFFLINE_DAEMON",repo
    if d == "Running":
        if heartbeat.get("running") is not True or age > STALE_SECONDS:
            return "LIVE_DAEMON_STATE_UNVERIFIED_HOLD",repo
        if p == "Ready":
            return "START_ORIGINAL_PROMOTION_CONTROLLER",repo
        return "BOTH_CONTROLLERS_RUNNING",repo
    raise ValueError("Unsupported daemon task state")

def _record(path, payload):
    require(path.parent.is_dir() and not path.parent.is_symlink(),
            "Original watchdog receipt directory absent")
    encoded=(json.dumps(payload,sort_keys=True,indent=2)+"\n").encode("utf8")
    tmp=path.with_suffix(".tmp")
    require(not tmp.is_symlink() and not path.is_symlink(),
            "Watchdog receipt redirected")
    with tmp.open("wb") as out:
        out.write(encoded)
        out.flush()
        os.fsync(out.fileno())
    tmp.replace(path)

def _read_heartbeat(path):
    require(path.is_file() and not path.is_symlink()
            and 1 <= path.stat().st_size <= 10000,
            "Original daemon heartbeat missing or unsafe")
    obj=json.loads(path.read_text(encoding="utf8"))
    require(type(obj) is dict and
            obj.get("student_publication_authorized") is False
            and obj.get("provider_sends") == 0,
            "Untrusted original academic release/provider checkpoint")
    return obj

def _start_exact_task(name, ps=native_ps):
    require(name in TASKS,
            "Watchdog may only restart two explicitly pinned tasks")
    # Race-safe native readback, no Stop-ScheduledTask or task modification.
    cmd=("$ErrorActionPreference='Stop';"
         "$t=Get-ScheduledTask -TaskName '" + name + "';"
         "if($t.State.ToString() -ne 'Ready'){throw 'Task not ready'};"
         "Start-ScheduledTask -TaskName '" + name + "'")
    ps(cmd)

def tick(*, ps=native_ps, runner=subprocess.run,
         now=None, sleep=time.sleep, root=LOCAL_ROOT):
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "Native long-horizon watchdog recovery not registered")
    root=Path(root)
    require(root == LOCAL_ROOT and root.is_dir() and not root.is_symlink(),
            "Watchdog checkpoint root not owned by local account")
    native=native_snapshot(ps=ps)
    repo=_owner_verified(native)
    main_sha=_verified_main(repo,runner)
    beat_file=root/"RECONCILE_20261125"/"live_state_migrated_v1"/"daemon_heartbeat.json"
    hb=_read_heartbeat(beat_file)
    instant=now if now is not None else dt.datetime.now(dt.timezone.utc)
    decision,_=eligible(native,hb,instant)
    acted=[]
    if decision == "START_ORIGINAL_OFFLINE_DAEMON":
        _start_exact_task(TASK_DAEMON,ps=ps)
        acted.append(TASK_DAEMON)
        # Never start the dependent controller based only on a launch request.
        # It must have a genuinely new native process + heartbeat.
        sleep(10)
        native=native_snapshot(ps=ps)
        current=_read_heartbeat(beat_file)
        fresh=_beat_age(current,dt.datetime.now(dt.timezone.utc))
        if (native[TASK_DAEMON]["state"] == "Running"
                and current.get("running") is True
                and fresh is not None and fresh <= 30
                and attest_live_daemon(state_dir=beat_file.parent)
                .get("running_verified") is True):
            if native[TASK_PROMOTE]["state"] == "Ready":
                _start_exact_task(TASK_PROMOTE,ps=ps)
                acted.append(TASK_PROMOTE)
                decision="RECOVERED_BOTH_NATIVE_DEVELOPMENT_TASKS"
            else:
                decision="RECOVERED_ORIGINAL_OFFLINE_DAEMON"
        else:
            decision="DAEMON_START_NOT_ATTESTED_DEPENDENT_HOLD"
    elif decision == "START_ORIGINAL_PROMOTION_CONTROLLER":
        require(attest_live_daemon(state_dir=beat_file.parent)
                .get("running_verified") is True,
                "Native daemon running process attestation not established")
        _start_exact_task(TASK_PROMOTE,ps=ps)
        acted.append(TASK_PROMOTE)
        decision="RECOVERED_ORIGINAL_PROMOTION_CONTROLLER"
    status={"schema_version":1,"status":decision,"protected_main_sha":main_sha,
            "native_task_starts":acted,"provider_sends":0,"paid_api_requests":0,
            "student_publication_authorized":False,
            "checked_utc":dt.datetime.now(dt.timezone.utc).isoformat()}
    _record(CONTROLLER_ROOT/"native_health_watchdog_v1.json",status)
    return status

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tick",action="store_true")
    args=parser.parse_args(argv)
    require(args.tick,"Only one bounded watchdog tick supported")
    outcome=tick()
    print(json.dumps(outcome,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
