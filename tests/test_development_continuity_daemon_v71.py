"""Live on-demand persistence, heartbeat, and process ownership tests."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
MODULE="selenium_pipeline.development_continuity_daemon_v71"


def _source(tmp):
    f=tmp/"known.pdf"
    f.write_bytes(b"immutable offline source witness")
    return f


def _plan(tmp,*,authorized=True):
    f=_source(tmp)
    obj={
      "schema_version":1,"project":"MicroGen_AI_Web",
      "tasks":[{
          "id":"first","workstream":"figures",
          "action":"verify_file_sha256",
          "params":{"path":str(f),"sha256":hashlib.sha256(f.read_bytes()).hexdigest()},
          "depends_on":[],"max_attempts":1,"authorized":authorized,
      }]
    }
    plan=tmp/"plan.json"
    plan.write_text(json.dumps(obj),encoding="utf8")
    return plan,tmp/"state"


def _command(plan,state,*,cycles=2,poll=1):
    return [sys.executable,"-m",MODULE,
        "--plan",str(plan),"--state-dir",str(state),
        "--repo-root",str(ROOT),"--poll-seconds",str(poll),
        "--heartbeat-seconds","0.5","--max-cycles",str(cycles)]


def _state(path):
    return json.loads((path/"state.json").read_text(encoding="utf8"))


def _heartbeat(path):
    return json.loads((path/"daemon_heartbeat.json").read_text(encoding="utf8"))


def _wait_for_heartbeat(path):
    for _ in range(100):
        if (path/"daemon_heartbeat.json").is_file():
            return _heartbeat(path)
        time.sleep(.05)
    raise AssertionError("Real daemon did not start or persist heartbeat")


def test_daemon_runs_multiple_real_cycles_without_duplicate_child(tmp_path):
    plan,state=_plan(tmp_path)
    r=subprocess.run(_command(plan,state,cycles=2),cwd=ROOT,
                     capture_output=True,text=True,timeout=60)
    assert r.returncode==0,r.stderr
    h=_heartbeat(state)
    s=_state(state)
    assert h["status"]=="STOPPED"
    assert h["running"] is False
    assert h["cycles"]==2
    assert h["provider_sends"]==0
    assert h["student_publication_authorized"] is False
    assert s["project_complete"]
    starts=[x for x in s["events"] if x["event"]=="worker_started"]
    assert len(starts)==1


def test_killed_daemon_restart_uses_previous_receipt_and_new_owner(tmp_path):
    plan,state=_plan(tmp_path)
    first=subprocess.Popen(_command(plan,state,cycles=0),cwd=ROOT,
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        old=_wait_for_heartbeat(state)
        assert old["owner_pid"]==first.pid
        assert old["running"]
        from selenium_pipeline.development_continuity_daemon_v71 import attest_live_daemon
        observed=attest_live_daemon(state_dir=state)
        assert observed["running_verified"],observed
        assert observed["owner_pid"]==first.pid
        assert observed["code_authoring_executor"] is False
        for _ in range(100):
            if (state/"state.json").is_file() and _state(state)["project_complete"]:
                break
            time.sleep(.05)
        assert _state(state)["project_complete"]
    finally:
        first.kill()
        first.wait(timeout=10)
    assert not attest_live_daemon(state_dir=state)["running_verified"]
    resumed=subprocess.run(_command(plan,state,cycles=2),cwd=ROOT,
                          capture_output=True,text=True,timeout=60)
    assert resumed.returncode==0,resumed.stderr
    new=_heartbeat(state)
    assert new["owner_pid"]!=old["owner_pid"]
    assert new["run_id"]!=old["run_id"]
    assert new["running"] is False
    assert new["status"]=="STOPPED"
    starts=[x for x in _state(state)["events"] if x["event"]=="worker_started"]
    assert len(starts)==1,"Orphaned original task was started again"


def test_second_concurrent_daemon_denied_by_os_lock(tmp_path):
    plan,state=_plan(tmp_path)
    first=subprocess.Popen(_command(plan,state,cycles=0),cwd=ROOT,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        _wait_for_heartbeat(state)
        other=subprocess.run(_command(plan,state,cycles=1),cwd=ROOT,
                             capture_output=True,text=True,timeout=30)
        assert other.returncode!=0
        assert "already owns this roadmap" in other.stderr
    finally:
        first.kill()
        first.wait(timeout=10)


def test_persistent_cycles_never_execute_unauthorized_release(tmp_path):
    plan,state=_plan(tmp_path,authorized=False)
    r=subprocess.run(_command(plan,state,cycles=2),cwd=ROOT,
                     capture_output=True,text=True,timeout=60)
    assert r.returncode==0,r.stderr
    s=_state(state)
    assert not s["project_complete"]
    assert s["tasks"]["first"]["status"]=="awaiting_authorization"
    assert not [x for x in s["events"] if x["event"]=="worker_started"]
    assert _heartbeat(state)["status"]=="STOPPED"


def test_forged_or_missing_heartbeat_does_not_look_like_running_daemon(tmp_path):
    from selenium_pipeline.development_continuity_daemon_v71 import attest_live_daemon
    _,state=_plan(tmp_path)
    assert not attest_live_daemon(state_dir=state)["running_verified"]
    state.mkdir()
    file=state/"daemon_heartbeat.json"
    file.write_text('{"running":true,"owner_pid":999999,"heartbeat_utc":"2099-01-01"}')
    assert not attest_live_daemon(state_dir=state)["running_verified"]
    file.write_text('{"malformed":',encoding="utf8")
    assert not attest_live_daemon(state_dir=state)["running_verified"]
