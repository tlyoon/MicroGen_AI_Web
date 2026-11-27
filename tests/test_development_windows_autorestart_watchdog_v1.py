"""No-provider watchdog fault injection: task identity, restart, and no-op."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from selenium_pipeline import development_windows_autorestart_watchdog_v1 as wd
from selenium_pipeline.recovery_registry import lookup_mechanism


@pytest.fixture
def env(tmp_path,monkeypatch):
    cutover=tmp_path/"RECONCILE_20261125"
    repo=cutover/"post_pr673_main"
    repo.mkdir(parents=True)
    old=cutover/"post_pr662_main"
    old.mkdir()
    daemon={
        "name":wd.TASK_DAEMON,
        "task_enabled":True,
        "logon":"Interactive",
        "runlevel":"Limited",
        "multiple":"IgnoreNew",
        "principal_sid":"S-1-5-21-1001",
        "current_sid":"S-1-5-21-1001",
        "state":"Running",
        "action":str(tmp_path/"miniconda3"/"python.exe"),
        "arguments":(
            '-B -m selenium_pipeline.development_continuity_daemon_v71'
            +' --repo-root "'+str(repo)+'"'
            +' --max-cycles "0"'),
        "workdir":str(repo),
    }
    promote={
        "name":wd.TASK_PROMOTE,
        "task_enabled":True,
        "logon":"Interactive",
        "runlevel":"Limited",
        "multiple":"IgnoreNew",
        "principal_sid":"S-1-5-21-1001",
        "current_sid":"S-1-5-21-1001",
        "state":"Running",
        "action":str(tmp_path/"Windows"/"powershell.exe"),
        "arguments":(
            '-File "'+str(old/"scripts"/
                "start_microgen_autonomous_code_promotion_v1.ps1")+'"'),
        "workdir":str(old),
    }
    monkeypatch.setattr(wd,"CUTOVER_ROOT",cutover)
    now=dt.datetime.now(dt.timezone.utc)
    state={
        "heartbeat_utc":now.isoformat(),
        "running":True,
        "provider_sends":0,
        "student_publication_authorized":False,
        "status":"G2_G3_INDEPENDENT_ACCEPTANCE_EVIDENCE_REQUIRED",
    }
    state_dir=cutover/"live_state_migrated_v1"
    state_dir.mkdir()
    beat=state_dir/"daemon_heartbeat.json"
    beat.write_text(json.dumps(state))
    ctl=tmp_path/"AUTONOMOUS_CODE_PROMOTION_V1_20261127"
    ctl.mkdir()
    monkeypatch.setattr(wd,"CONTROLLER_ROOT",ctl)
    monkeypatch.setattr(wd,"LOCAL_ROOT",tmp_path)
    return dict(tmp=tmp_path,native={wd.TASK_DAEMON:daemon,
                        wd.TASK_PROMOTE:promote},
                now=now,heartbeat=state,beat=beat,control=ctl)


def test_executable_registry_contains_self_heal():
    assert lookup_mechanism(wd.KIND,wd.SIGNATURE)==wd.MECHANISM


def test_fresh_live_controllers_are_never_restarted(env):
    outcome,repo=wd.eligible(env["native"],env["heartbeat"],env["now"])
    assert outcome=="BOTH_CONTROLLERS_RUNNING"
    assert repo.name=="post_pr673_main"


def test_stale_offline_daemon_is_eligible_once(env):
    hb=env["heartbeat"].copy()
    hb["heartbeat_utc"]=(env["now"]-dt.timedelta(minutes=8)).isoformat()
    hb["running"]=False
    env["native"][wd.TASK_DAEMON]["state"]="Ready"
    assert wd.eligible(env["native"],hb,env["now"])[0] == (
        "START_ORIGINAL_OFFLINE_DAEMON")


def test_recent_exit_is_not_restarted_during_guarded_deploy(env):
    env["native"][wd.TASK_DAEMON]["state"]="Ready"
    assert wd.eligible(env["native"],env["heartbeat"],env["now"])[0] == (
        "RECENT_DAEMON_EXIT_RECHECK_NEXT_TICK")


def test_only_missing_promotion_controller_can_resume(env):
    env["native"][wd.TASK_PROMOTE]["state"]="Ready"
    assert wd.eligible(env["native"],env["heartbeat"],env["now"])[0] == (
        "START_ORIGINAL_PROMOTION_CONTROLLER")


def test_running_but_nonfresh_daemon_not_killed_or_replaced(env):
    hb=env["heartbeat"].copy()
    hb["heartbeat_utc"]=(env["now"]-dt.timedelta(minutes=10)).isoformat()
    env["native"][wd.TASK_PROMOTE]["state"]="Ready"
    assert wd.eligible(env["native"],hb,env["now"])[0] == (
        "LIVE_DAEMON_STATE_UNVERIFIED_HOLD")


@pytest.mark.parametrize("path,value", [
    ((wd.TASK_DAEMON,"runlevel"),"Highest"),
    ((wd.TASK_PROMOTE,"logon"),"Password"),
    ((wd.TASK_DAEMON,"multiple"),"Parallel"),
    ((wd.TASK_DAEMON,"principal_sid"),"S-1-5-21-9999"),
    ((wd.TASK_PROMOTE,"task_enabled"),False),
    ((wd.TASK_DAEMON,"state"),"Disabled"),
    ((wd.TASK_PROMOTE,"action"),"malicious.exe"),
    ((wd.TASK_DAEMON,"arguments"),"-B -m unauthorized.startup"),
])
def test_wrong_original_native_task_identity_fails_closed(env,path,value):
    env["native"][path[0]][path[1]]=value
    with pytest.raises(ValueError):
        wd.eligible(env["native"],env["heartbeat"],env["now"])


def test_corrupt_or_future_heartbeat_never_admits_restarts(env):
    env["native"][wd.TASK_DAEMON]["state"]="Ready"
    for hb in (None,[],{},{"heartbeat_utc":"unknown"},
               {"heartbeat_utc":(env["now"]+dt.timedelta(hours=2)).isoformat()}):
        with pytest.raises(ValueError):
            wd.eligible(env["native"],hb,env["now"])


def test_heartbeat_student_publication_is_fatal(env):
    env["heartbeat"]["student_publication_authorized"]=True
    env["beat"].write_text(json.dumps(env["heartbeat"]))
    with pytest.raises(ValueError,match="Untrusted original academic"):
        wd._read_heartbeat(env["beat"])


def test_watchdog_starts_only_exact_two_tasks_and_reads_back_new_heartbeat(
        env,monkeypatch):
    env["native"][wd.TASK_DAEMON]["state"]="Ready"
    env["native"][wd.TASK_PROMOTE]["state"]="Ready"
    hb=env["heartbeat"].copy()
    hb["heartbeat_utc"]=(env["now"]-dt.timedelta(minutes=6)).isoformat()
    hb["running"]=False
    env["beat"].write_text(json.dumps(hb))
    calls=[]
    monkeypatch.setattr(wd,"native_snapshot",
        lambda ps=None:env["native"])
    monkeypatch.setattr(wd,"_verified_main",
        lambda repo,runner:"a"*40)
    monkeypatch.setattr(wd,"attest_live_daemon",
        lambda **kwargs:{"running_verified":True})
    def start(name,ps=None):
        assert name in wd.TASKS
        assert env["native"][name]["state"]=="Ready"
        env["native"][name]["state"]="Running"
        calls.append(name)
    monkeypatch.setattr(wd,"_start_exact_task",start)
    def refresh(sec):
        assert sec==10
        restored=env["heartbeat"].copy()
        restored["heartbeat_utc"]=dt.datetime.now(dt.timezone.utc).isoformat()
        env["beat"].write_text(json.dumps(restored))
    result=wd.tick(now=env["now"],sleep=refresh,root=env["tmp"])
    assert result["status"]=="RECOVERED_BOTH_NATIVE_DEVELOPMENT_TASKS"
    assert calls==list(wd.TASKS)
    assert result["native_task_starts"]==list(wd.TASKS)
    assert result["provider_sends"]==result["paid_api_requests"]==0
    assert result["student_publication_authorized"] is False
    assert json.loads((env["control"]/"native_health_watchdog_v1.json")
                      .read_text())["status"]==result["status"]
    another=wd.tick(now=dt.datetime.now(dt.timezone.utc),
                    sleep=lambda _:None,root=env["tmp"])
    assert another["status"]=="BOTH_CONTROLLERS_RUNNING"
    assert calls==list(wd.TASKS)


def test_unknown_action_is_never_started():
    with pytest.raises(ValueError,match="explicitly pinned"):
        wd._start_exact_task("MicroGen_ZCA101_Ch11_Dell115")


def test_one_overdue_daemon_with_unverifiable_process_does_not_start_controller(
        env,monkeypatch):
    env["native"][wd.TASK_DAEMON]["state"]="Ready"
    env["native"][wd.TASK_PROMOTE]["state"]="Ready"
    beat=env["heartbeat"].copy()
    beat["running"]=False
    beat["heartbeat_utc"]=(env["now"]-dt.timedelta(minutes=6)).isoformat()
    env["beat"].write_text(json.dumps(beat))
    monkeypatch.setattr(wd,"native_snapshot",lambda ps=None:env["native"])
    monkeypatch.setattr(wd,"_verified_main",lambda repo,runner:"b"*40)
    calls=[]
    def start(name,ps=None):
        calls.append(name)
        env["native"][name]["state"]="Running"
    monkeypatch.setattr(wd,"_start_exact_task",start)
    monkeypatch.setattr(wd,"attest_live_daemon",
                        lambda **kwargs:{"running_verified":False})
    result=wd.tick(root=env["tmp"],now=env["now"],sleep=lambda _:None)
    assert calls==[wd.TASK_DAEMON]
    assert result["status"]=="DAEMON_START_NOT_ATTESTED_DEPENDENT_HOLD"


def test_native_schedule_scripts_never_have_broad_task_kill_or_model_sends():
    scripts=Path(__file__).parent.parent/"scripts"
    setup=(scripts/"install_microgen_long_horizon_watchdog_v1.ps1").read_text()
    run=(scripts/"run_microgen_long_horizon_watchdog_v1.ps1").read_text()
    assert "RepetitionInterval (New-TimeSpan -Minutes 5)" in setup
    assert "Register-ScheduledTask -TaskName $watch" in setup
    assert "get-ScheduledTask -TaskName" in run.lower().replace("get-","get-") or (
        "Get-ScheduledTask -TaskName" in run)
    for item in (setup,run):
        assert "Stop-ScheduledTask" not in item
        assert "Unregister-ScheduledTask" not in item
        assert "SendKeys" not in item
        assert "GeminiAPI" not in item
    assert "development_windows_autorestart_watchdog_v1 --tick" in run
