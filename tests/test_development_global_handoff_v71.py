"""Real local process evidence for immutable v7.1 cross-workstream handoff."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from selenium_pipeline.development_continuity_handoff_v71 import (
    scan_and_dispatch, LEDGER_NAME)

ROOT=Path(__file__).resolve().parents[1]


def source(tmp, name="source"):
    p=tmp/(name+".txt")
    p.write_bytes(("witness:"+name).encode())
    return p


def task(name, file, *, authorized=True, deps=()):
    return {"id":name,"workstream":"independent",
        "action":"verify_file_sha256",
        "params":{"path":str(file),
                  "sha256":hashlib.sha256(file.read_bytes()).hexdigest()},
        "depends_on":list(deps),
        "max_attempts":1,"authorized":authorized}


def plan(path, tasks):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({
        "schema_version":1,"project":"MicroGen_AI_Web","tasks":tasks}),
        encoding="utf8")
    return path


def run_handoff(tmp, plans=None):
    inbox=tmp/"handoffs"
    inbox.mkdir()
    state=tmp/"state"
    state.mkdir()
    if plans:
        for name,tasks in plans.items():
            plan(inbox/name,tasks)
    return inbox,state


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def started(state, stem):
    p=state/"handoffs"/stem/"state.json"
    if not p.is_file():
        return []
    return [e for e in load(p)["events"]
            if e["event"]=="worker_started"]


def test_real_durable_cross_workstream_dispatch_after_held_authorization(tmp_path):
    f=source(tmp_path)
    inbox,state=run_handoff(tmp_path,{
        "next_independent.json":[task("held",f,authorized=False),
                                 task("available",f)]})
    report=scan_and_dispatch(
        handoff_dir=inbox,state_dir=state,repo_root=ROOT)
    assert report["status"]=="HANDOFF_DISPATCH_VERIFIED"
    assert report["new_worker_starts"]==1
    assert len(started(state,"next_independent"))==1
    first=load(state/"handoffs"/"next_independent"/"state.json")
    assert first["tasks"]["held"]["status"]=="awaiting_authorization"
    assert first["tasks"]["available"]["status"]=="passed"
    assert report["student_publication_authorized"] is False
    assert report["paid_model_requests"]==0
    rerun=scan_and_dispatch(handoff_dir=inbox,state_dir=state,repo_root=ROOT)
    assert rerun["new_worker_starts"]==0
    assert len(started(state,"next_independent"))==1


def test_new_independent_plan_discovered_without_restarting_or_editing_main(tmp_path):
    a=source(tmp_path,"alpha")
    b=source(tmp_path,"beta")
    inbox,state=run_handoff(tmp_path,{
        "next_alpha.json":[task("a",a)]})
    first=scan_and_dispatch(handoff_dir=inbox,state_dir=state,repo_root=ROOT)
    assert first["new_worker_starts"]==1
    plan(inbox/"next_beta.json",[task("b",b)])
    second=scan_and_dispatch(handoff_dir=inbox,state_dir=state,repo_root=ROOT)
    assert second["new_worker_starts"]==1
    assert len(started(state,"next_alpha"))==1
    assert len(started(state,"next_beta"))==1
    assert scan_and_dispatch(
        handoff_dir=inbox,state_dir=state,repo_root=ROOT)["new_worker_starts"]==0


def test_consumed_plan_cannot_change_identity_or_replay_work(tmp_path):
    f=source(tmp_path)
    inbox,state=run_handoff(tmp_path,{"next_alpha.json":[task("a",f)]})
    assert scan_and_dispatch(handoff_dir=inbox,state_dir=state,
                             repo_root=ROOT)["new_worker_starts"]==1
    changed=load(inbox/"next_alpha.json")
    changed["tasks"][0]["authorized"]=False
    (inbox/"next_alpha.json").write_text(
        json.dumps(changed),encoding="utf8")
    again=scan_and_dispatch(handoff_dir=inbox,state_dir=state,repo_root=ROOT)
    assert again["new_worker_starts"]==0
    assert again["outcomes"][0]["status"]=="CHANGED_PLAN_CONSUMED_NO_REPLAY"
    assert len(started(state,"next_alpha"))==1


def test_invalid_candidate_quarantined_but_independent_worker_starts(tmp_path):
    f=source(tmp_path)
    inbox,state=run_handoff(tmp_path)
    (inbox/"next_bad.json").write_text('{"invalid":true}',encoding="utf8")
    plan(inbox/"next_good.json",[task("good",f)])
    r=scan_and_dispatch(handoff_dir=inbox,state_dir=state,repo_root=ROOT)
    assert r["new_worker_starts"]==1
    assert [x["status"] for x in r["outcomes"]]==[
        "QUARANTINED_INVALID_PLAN", "VERIFIED_TASK_PLAN_COMPLETE"]
    assert len(started(state,"next_good"))==1
    again=scan_and_dispatch(handoff_dir=inbox,state_dir=state,repo_root=ROOT)
    assert again["new_worker_starts"]==0
    assert again["outcomes"][0]["status"]=="PRIOR_INVALID_PLAN_QUARANTINED"


def test_untrusted_symlink_and_unbounded_intake_do_not_dispatch(tmp_path):
    f=source(tmp_path)
    inbox,state=run_handoff(tmp_path)
    outside=tmp_path/"outside.json"
    plan(outside,[task("outside",f)])
    alias=inbox/"next_redirect.json"
    try:
        alias.symlink_to(outside)
    except OSError:
        pytest.skip("Windows symlink permission unavailable")
    r=scan_and_dispatch(handoff_dir=inbox,state_dir=state,repo_root=ROOT)
    assert r["new_worker_starts"]==0
    assert r["outcomes"][0]["status"]=="INVALID_HANDOFF_FILE_NO_EXECUTION"


def test_real_daemon_handoffs_on_primary_held_release_and_restart_no_replay(tmp_path):
    f=source(tmp_path)
    inbox,state=run_handoff(tmp_path,{"next_figure.json":[task("figure",f)]})
    primary=plan(tmp_path/"primary.json",[
        task("release_gate",f,authorized=False)])
    cmd=[sys.executable,"-B","-m",
         "selenium_pipeline.development_continuity_daemon_v71",
         "--plan",str(primary),"--repo-root",str(ROOT),
         "--state-dir",str(state),"--handoff-dir",str(inbox),
         "--poll-seconds","1","--heartbeat-seconds","0.5",
         "--max-cycles","1"]
    first=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert first.returncode==0,first.stderr+first.stdout
    hb=load(state/"daemon_heartbeat.json")
    assert hb["handoff_worker_starts_total"]==1
    assert hb["last_handoff_status"]=="HANDOFF_DISPATCH_VERIFIED"
    assert hb["provider_sends"]==0
    assert hb["student_publication_authorized"] is False
    assert hb["code_authoring_executor"] is False
    assert load(state/"state.json")["tasks"]["release_gate"][
        "status"]=="awaiting_authorization"
    assert len(started(state,"next_figure"))==1
    second=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert second.returncode==0,second.stderr+second.stdout
    assert len(started(state,"next_figure"))==1
    assert load(state/"daemon_heartbeat.json")[
        "handoff_worker_starts_total"]==0


def test_invalid_registry_fails_closed_before_any_discovery(tmp_path,monkeypatch):
    from selenium_pipeline import development_continuity_executor_v71 as exe
    f=source(tmp_path)
    inbox,state=run_handoff(tmp_path,{"next_one.json":[task("one",f)]})
    wrong=tmp_path/"forged_registry.json"
    obj=load(exe.RECOVERY_FILE)
    del obj["handlers"]["IMMUTABLE_GLOBAL_OFFLINE_HANDOFF"]
    wrong.write_text(json.dumps(obj),encoding="utf8")
    monkeypatch.setattr(exe,"RECOVERY_FILE",wrong)
    with pytest.raises(ValueError,match="Unregistered or tampered"):
        scan_and_dispatch(handoff_dir=inbox,state_dir=state,repo_root=ROOT)
    assert not started(state,"next_one")


def test_actual_windows_powershell_bom_plan_preserves_raw_identity(tmp_path):
    from selenium_pipeline.development_continuity_executor_v71 import _sha
    f=source(tmp_path)
    inbox,state=run_handoff(tmp_path,{"next_powershell.json":[task("power",f)]})
    p=inbox/"next_powershell.json"
    original=p.read_bytes()
    p.write_bytes(b"\xef\xbb\xbf"+original)
    raw_hash=hashlib.sha256(p.read_bytes()).hexdigest()
    assert raw_hash==_sha(p)  # SHA is the bytes including the BOM
    first=scan_and_dispatch(handoff_dir=inbox,state_dir=state,repo_root=ROOT)
    assert first["new_worker_starts"]==1,first
    ledger=load(state/LEDGER_NAME)
    assert ledger["plans"]["next_powershell"]["sha256"]==raw_hash
    assert len(started(state,"next_powershell"))==1
    # Removing a BOM CHANGES the claimed input identity: never retry.
    p.write_bytes(original)
    blocked=scan_and_dispatch(handoff_dir=inbox,state_dir=state,repo_root=ROOT)
    assert blocked["outcomes"][0]["status"]=="CHANGED_PLAN_CONSUMED_NO_REPLAY"
    assert len(started(state,"next_powershell"))==1


def test_two_bom_headers_fail_closed_but_independent_plan_starts(tmp_path):
    f=source(tmp_path)
    inbox,state=run_handoff(tmp_path,{
        "next_bad.json":[task("b",f)],
        "next_good.json":[task("g",f)]})
    bad=inbox/"next_bad.json"
    bad.write_bytes(b"\xef\xbb\xbf"*2 + bad.read_bytes())
    out=scan_and_dispatch(handoff_dir=inbox,state_dir=state,repo_root=ROOT)
    assert out["new_worker_starts"]==1
    assert out["outcomes"][0]["status"]=="QUARANTINED_INVALID_PLAN"
    assert len(started(state,"next_bad"))==0
    assert len(started(state,"next_good"))==1


def test_disabled_bom_remedy_blocks_windows_authored_plan(tmp_path,monkeypatch):
    from selenium_pipeline import recovery_registry
    f=source(tmp_path)
    inbox,state=run_handoff(tmp_path,{"next_powershell.json":[task("p",f)]})
    p=inbox/"next_powershell.json"
    p.write_bytes(b"\xef\xbb\xbf"+p.read_bytes())
    obj=json.loads(recovery_registry.REGISTRY_PATH.read_text(encoding="utf8"))
    for entry in obj["entries"]:
        if entry["signature"]=="WINDOWS_SOURCE_PINNED_JSON_UTF8_BOM":
            entry["enabled"]=False
            break
    else:
        pytest.fail("Missing BOM recovery registry remedy")
    alternate=tmp_path/"disabled_registry.json"
    alternate.write_text(json.dumps(obj),encoding="utf8")
    monkeypatch.setattr(recovery_registry,"REGISTRY_PATH",alternate)
    report=scan_and_dispatch(handoff_dir=inbox,state_dir=state,repo_root=ROOT)
    assert report["new_worker_starts"]==0
    assert report["outcomes"][0]["status"]=="QUARANTINED_INVALID_PLAN"
    assert not started(state,"next_powershell")
