"""WMI Win32_Process invalid-class recovery, using the REAL OS process.

This does not authorize new provider calls or replace source/ownership proof.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess

import pytest

from test_development_continuity_daemon_v71 import (
    _command, _plan, _wait_for_heartbeat)
from selenium_pipeline import development_continuity_daemon_v71 as daemon
from selenium_pipeline import recovery_registry


@pytest.mark.skipif(os.name!="nt",reason="HP Windows WMI failure is platform-specific")
def test_original_real_daemon_attested_with_get_process_when_cim_invalid(
        tmp_path,monkeypatch):
    plan,state=_plan(tmp_path)
    first=subprocess.Popen(_command(plan,state,cycles=0),cwd=daemon.Path(
        __file__).resolve().parents[1],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    original=subprocess.run
    calls=[]
    def simulate_hp_win32_process_invalid_class(argv,**kwargs):
        command=argv[-1] if argv else ""
        if "Get-CimInstance" in command:
            calls.append("wmi_invalid")
            return subprocess.CompletedProcess(argv,0,"","Invalid class")
        if "Get-Process" in command:
            calls.append("native_get_process")
        return original(argv,**kwargs)
    monkeypatch.setattr(daemon.subprocess,"run",
                        simulate_hp_win32_process_invalid_class)
    try:
        original_heartbeat=_wait_for_heartbeat(state)
        result=daemon.attest_live_daemon(state_dir=state)
        assert result["running_verified"] is True,result
        assert result["owner_pid"]==first.pid
        assert result["identity_attestation_method"]==(
            "WINDOWS_NATIVE_PID_EXE_STARTTIME")
        assert result["code_authoring_executor"] is False
        assert result["paid_model_sends"]==0
        assert calls.count("wmi_invalid")==1
        assert calls.count("native_get_process")==1
    finally:
        first.kill()
        first.wait(timeout=10)
    assert daemon.attest_live_daemon(state_dir=state)[
        "running_verified"] is False


@pytest.mark.skipif(os.name!="nt",reason="HP Windows WMI failure is platform-specific")
def test_native_starttime_attestation_refuses_pid_reuse_and_registry_disable(
        tmp_path,monkeypatch):
    plan,state=_plan(tmp_path)
    first=subprocess.Popen(_command(plan,state,cycles=0),
                           cwd=Path(__file__).resolve().parents[1],
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    original_run=subprocess.run
    def simulate_hp(argv,**kwargs):
        if "Get-CimInstance" in argv[-1]:
            return subprocess.CompletedProcess(argv,0,"","Invalid class")
        return original_run(argv,**kwargs)
    monkeypatch.setattr(daemon.subprocess,"run",simulate_hp)
    try:
        original_heartbeat=_wait_for_heartbeat(state)
        saved=state/"daemon_heartbeat.json"
        # Pretend this SAME numeric PID began a minute later; native OS
        # process birth does not match, so the heartbeat cannot attest.
        forged=dict(original_heartbeat)
        old=datetime.fromisoformat(
            forged["started_utc"].replace("Z","+00:00"))
        forged["started_utc"]=(old+timedelta(minutes=2)).isoformat()
        saved.write_text(json.dumps(forged),encoding="utf8")
        assert daemon.attest_live_daemon(state_dir=state)[
            "running_verified"] is False
        # Reconcile original fresh heartbeat; disable mechanism and assert
        # native Get-Process cannot silently bypass policy.
        saved.write_text(json.dumps(original_heartbeat),encoding="utf8")
        reg=json.loads(recovery_registry.REGISTRY_PATH.read_text(encoding="utf8"))
        for row in reg["entries"]:
            if row["signature"]=="V71_WINDOWS_WMI_PROCESS_CLASS_UNAVAILABLE":
                row["enabled"]=False
                break
        else:
            pytest.fail("Missing registered HP WMI recovery")
        alternate=tmp_path/"disabled_registry.json"
        alternate.write_text(json.dumps(reg),encoding="utf8")
        monkeypatch.setattr(recovery_registry,"REGISTRY_PATH",alternate)
        assert daemon.attest_live_daemon(state_dir=state)[
            "running_verified"] is False
    finally:
        first.kill()
        first.wait(timeout=10)
