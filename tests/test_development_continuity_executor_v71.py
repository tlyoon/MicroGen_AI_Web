"""v7.1 checkpoint-to-action executable continuity, real child processes."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from selenium_pipeline.development_continuity_executor_v71 import (
    _plan,execute,
)


ROOT = Path(__file__).resolve().parents[1]


def task(name, file, *, deps=(), authorized=True, sha=None, attempts=1,
         workstream="figure"):
    return {
        "id": name, "workstream":workstream,
        "action":"verify_file_sha256",
        "params":{"path":str(file),
                  "sha256":sha or hashlib.sha256(file.read_bytes()).hexdigest()},
        "depends_on":list(deps),
        "max_attempts":attempts,"authorized":authorized,
    }


def build(tmp, tasks):
    plan=tmp/"plan.json"
    plan.write_text(json.dumps({
        "schema_version":1,"project":"MicroGen_AI_Web","tasks":tasks,
    },indent=2),encoding="utf8")
    return plan,tmp/"state"


def shell(plan, state, *, fault=None, worker_fault=None, dispatch=None):
    env=os.environ.copy()
    env.pop("MICROGEN_V71_TEST_EXIT_AFTER_CLAIM",None)
    if fault:env["MICROGEN_V71_TEST_EXIT_AFTER_CLAIM"]=fault
    env.pop("MICROGEN_V71_TEST_EXIT_AFTER_CHILD_START",None)
    if worker_fault:env["MICROGEN_V71_TEST_EXIT_AFTER_CHILD_START"]=worker_fault
    cmd=[sys.executable,"-m",
         "selenium_pipeline.development_continuity_executor_v71",
         "run","--plan",str(plan),"--state-dir",str(state),
         "--repo-root",str(ROOT)]
    if dispatch is not None:cmd+=["--max-dispatch",str(dispatch)]
    return subprocess.run(cmd,cwd=ROOT,env=env,
                          capture_output=True,text=True,timeout=65)


def read(state):
    return json.loads((state/"state.json").read_text(encoding="utf8"))


def events(state, kind):
    return [row for row in read(state)["events"] if row["event"]==kind]


def sample(tmp):
    f=tmp/"source.txt"
    f.write_text("SHA-locked source witness",encoding="utf8")
    return f


def test_success_hands_off_to_next_task_in_same_real_invocation(tmp_path):
    f=sample(tmp_path)
    p,s=build(tmp_path,[
        task("figure",f),
        task("scientific",f,deps=["figure"],workstream="science"),
        task("acoustic",f,deps=["scientific"],workstream="acoustic"),
    ])
    r=shell(p,s)
    assert r.returncode==0,r.stderr+"\n"+r.stdout
    v=read(s)
    assert v["project_complete"] is True
    assert [x["task"] for x in events(s,"worker_started")]==[
        "figure","scientific","acoustic"]
    assert [x["task"] for x in events(s,"task_accepted")]==[
        "figure","scientific","acoustic"]


def test_local_workstream_exhaustion_discovers_independent_queue(tmp_path):
    f=sample(tmp_path)
    p,s=build(tmp_path,[
        task("crop",f,workstream="figure"),
        task("release_preflight",f,workstream="release"),
    ])
    r=shell(p,s)
    assert r.returncode==0,r.stderr
    assert [e["task"] for e in events(s,"worker_started")]==[
        "crop","release_preflight"]


def test_quarantined_failure_fans_out_without_replaying_unknown_claim(tmp_path):
    f=sample(tmp_path)
    p,s=build(tmp_path,[
        task("bad_source",f,sha="f"*64,workstream="science"),
        task("independent_qa",f,workstream="qa"),
    ])
    r=shell(p,s)
    assert r.returncode==2,r.stderr
    v=read(s)["tasks"]
    assert v["bad_source"]["status"]=="quarantined"
    assert v["independent_qa"]["status"]=="passed"
    assert events(s,"task_quarantined")
    assert events(s,"task_accepted")[-1]["task"]=="independent_qa"


def test_recoverable_offline_failure_bounded_retry_then_fan_out(tmp_path):
    f=sample(tmp_path)
    p,s=build(tmp_path,[
        task("broken",f,sha="f"*64,attempts=2),
        task("independent",f),
    ])
    r=shell(p,s)
    assert r.returncode==2
    assert read(s)["tasks"]["broken"]["attempts"]==2
    assert read(s)["tasks"]["independent"]["status"]=="passed"
    assert len([x for x in events(s,"next_task_dispatched")
                if x["task"]=="broken"])==2


def test_restart_after_checkpoint_before_child_launch_executes_once(tmp_path):
    f=sample(tmp_path)
    p,s=build(tmp_path,[
        task("first",f),
        task("after_restart",f,deps=["first"],workstream="g2"),
    ])
    crash=shell(p,s,fault="first")
    assert crash.returncode==86,crash.stderr
    v=read(s)
    assert v["tasks"]["first"]["status"]=="dispatched"
    assert v["tasks"]["first"]["active"]["worker_pid"] is None
    assert not events(s,"worker_started")
    resumed=shell(p,s)
    assert resumed.returncode==0,resumed.stderr+"\n"+resumed.stdout
    v=read(s)
    assert v["project_complete"]
    assert len([x for x in events(s,"worker_started")
                if x["task"]=="first"])==1
    assert len([x for x in events(s,"task_accepted")
                if x["task"]=="first"])==1
    assert [x["task"] for x in events(s,"worker_started")]==[
        "first","after_restart"]


def test_unspecified_external_send_action_is_rejected_before_claim(tmp_path):
    f=sample(tmp_path)
    invalid=task("provider_send",f)
    invalid["action"]="gemini_api_send"
    p,s=build(tmp_path,[invalid])
    with pytest.raises(ValueError,match="Unsupported"):
        _plan(p)
    run=shell(p,s)
    assert run.returncode!=0
    assert not (s/"state.json").exists()
    assert not (s/"results").exists()


def test_authorization_gate_does_not_block_other_workstreams(tmp_path):
    f=sample(tmp_path)
    p,s=build(tmp_path,[
        task("needs_consent",f,authorized=False,workstream="release"),
        task("safe_offline",f,workstream="science"),
    ])
    r=shell(p,s)
    assert r.returncode==2
    v=read(s)["tasks"]
    assert v["needs_consent"]["status"]=="awaiting_authorization"
    assert v["safe_offline"]["status"]=="passed"
    assert not read(s)["project_complete"]
    assert [e["task"] for e in events(s,"worker_started")]==[
        "safe_offline"]


def test_no_imaginary_runner_and_checkpointed_no_running_claim(tmp_path):
    f=sample(tmp_path)
    p,s=build(tmp_path,[task("check",f)])
    r=shell(p,s)
    assert r.returncode==0
    v=read(s)
    assert v["status"]=="VERIFIED_TASK_PLAN_COMPLETE"
    assert all(x["status"]!="dispatched" for x in v["tasks"].values())
    assert "background_running" not in v
    again=shell(p,s)
    assert again.returncode==0
    assert len(events(s,"worker_started"))==1


def test_malformed_manifest_and_unknown_dependency_fail_closed(tmp_path):
    f=sample(tmp_path)
    p,s=build(tmp_path,[
        task("first",f,deps=["missing"]),
    ])
    with pytest.raises(ValueError,match="Unknown"):
        _plan(p)
    v=json.loads(p.read_text())
    v["tasks"][0]["depends_on"]=[]
    v["tasks"].append(task("second",f,deps=["first"]))
    v["tasks"][0]["depends_on"]=["second"]
    p.write_text(json.dumps(v),encoding="utf8")
    with pytest.raises(ValueError,match="Cycle"):
        _plan(p)


def test_modified_plan_refused_after_checkpoint(tmp_path):
    f=sample(tmp_path)
    p,s=build(tmp_path,[task("original",f)])
    assert shell(p,s).returncode==0
    plan=json.loads(p.read_text())
    plan["tasks"].append(task("injected",f))
    p.write_text(json.dumps(plan),encoding="utf8")
    r=shell(p,s)
    assert r.returncode!=0
    assert "Changed roadmap" in r.stderr
    assert len(events(s,"worker_started"))==1


def test_worker_failure_evidence_is_not_accepted_as_success(tmp_path):
    f=sample(tmp_path)
    p,s=build(tmp_path,[
        task("wrong",f,sha="0"*64),
    ])
    r=shell(p,s)
    assert r.returncode==2
    record=read(s)["tasks"]["wrong"]
    assert record["status"]=="quarantined"
    assert record["evidence"]["error_class"]=="ValueError"
    assert record["attempts"]==1


def test_restart_after_child_started_reconciles_exact_original_result(tmp_path):
    import time
    f=sample(tmp_path)
    p,s=build(tmp_path,[
        task("started_child",f,workstream="figure"),
        task("independent_followup",f,deps=["started_child"],workstream="g2"),
    ])
    crashed=shell(p,s,worker_fault="started_child")
    assert crashed.returncode==87,crashed.stderr
    initial=read(s)
    assert initial["tasks"]["started_child"]["status"]=="dispatched"
    token=initial["tasks"]["started_child"]["active"]["token"]
    assert initial["tasks"]["started_child"]["active"]["worker_pid"]
    assert len(events(s,"worker_started"))==1
    expected=s/"results"/(token+".json")
    for _ in range(80):
        if expected.is_file():break
        time.sleep(0.05)
    assert expected.is_file(),"Original worker did not return its receipt"
    resumed=shell(p,s)
    assert resumed.returncode==0,resumed.stderr
    assert read(s)["project_complete"]
    assert len([e for e in events(s,"worker_started")
                if e["task"]=="started_child"])==1
    assert len([e for e in events(s,"worker_started")
                if e["task"]=="independent_followup"])==1
    assert events(s,"orphaned_worker_result_reconciled")


def test_unknown_started_child_is_held_while_other_work_proceeds(tmp_path):
    f=sample(tmp_path)
    p,s=build(tmp_path,[
        task("maybe_started",f,workstream="g2"),
        task("safe_other_workstream",f,workstream="figure"),
    ])
    crashed=shell(p,s,fault="maybe_started")
    assert crashed.returncode==86
    data=read(s)
    data["tasks"]["maybe_started"]["active"]["worker_pid"]=987654321
    (s/"state.json").write_text(json.dumps(data),encoding="utf8")
    resumed=shell(p,s)
    assert resumed.returncode==2,resumed.stderr
    now=read(s)
    assert now["tasks"]["maybe_started"]["status"]=="awaiting_receipt"
    assert now["tasks"]["safe_other_workstream"]["status"]=="passed"
    assert not any(e["task"]=="maybe_started"
                   for e in events(s,"worker_started"))
    assert events(s,"uncertain_worker_pending_receipt")
    assert not now["project_complete"]


def test_forged_orphan_result_is_never_admitted(tmp_path):
    f=sample(tmp_path)
    p,s=build(tmp_path,[task("one",f)])
    crashed=shell(p,s,fault="one")
    assert crashed.returncode==86
    token=read(s)["tasks"]["one"]["active"]["token"]
    proof=s/"results"/(token+".json")
    proof.parent.mkdir()
    proof.write_text(json.dumps({
        "status":"passed","task":"wrong",
        "token":token,"action":"verify_file_sha256",
        "evidence":{} }),encoding="utf8")
    r=shell(p,s)
    assert r.returncode!=0
    assert "Corrupted or misattributed child result receipt" in r.stderr
    assert not events(s,"task_accepted")


def test_registered_recovery_only_permits_exact_no_send_handlers(tmp_path):
    from selenium_pipeline.development_continuity_executor_v71 import (
        require_recovery,RECOVERY_FILE,RECOVERY_ACTIONS)
    for signature,action in RECOVERY_ACTIONS.items():
        assert require_recovery(signature)==action
    with pytest.raises(ValueError):
        require_recovery("UNKNOWN_SEND_OLD_GEMINI_REQUEST")
    original=json.loads(RECOVERY_FILE.read_text(encoding="utf8"))
    tampered=tmp_path/"tampered_registry.json"
    for field,value in [
        ("enabled",False),
        ("paid_model_sends_allowed",True),
        ("publication_allowed",True),
    ]:
        item=json.loads(json.dumps(original))
        item[field]=value
        tampered.write_text(json.dumps(item),encoding="utf8")
        with pytest.raises(ValueError):
            require_recovery("ORPHANED_CHILD_RESULT",registry=tampered)
    item=json.loads(json.dumps(original))
    item["handlers"]["UNKNOWN_SEND_OLD_GEMINI_REQUEST"]="SEND"
    tampered.write_text(json.dumps(item),encoding="utf8")
    with pytest.raises(ValueError):
        require_recovery("ORPHANED_CHILD_RESULT",registry=tampered)


def test_plan_and_executor_sha_are_pinned_in_committed_state(tmp_path):
    from selenium_pipeline.development_continuity_executor_v71 import _sha
    f=sample(tmp_path)
    p,s=build(tmp_path,[task("sha_locked",f)])
    assert shell(p,s).returncode==0
    v=read(s)
    assert v["plan_sha256"]==_sha(p)
    assert v["executor_sha256"]==_sha(
        ROOT/"selenium_pipeline"/"development_continuity_executor_v71.py")


def test_concurrent_executor_byte_lock_fails_closed_without_second_dispatch(tmp_path):
    import time
    from selenium_pipeline.development_continuity_executor_v71 import _exclusive
    state=tmp_path/"lockcase"
    state.mkdir()
    witness=state/"first_owner_ready"
    child_code=(
        "import sys,time;from pathlib import Path;"
        "from selenium_pipeline.development_continuity_executor_v71 import _exclusive;"
        "p=Path(sys.argv[1]);"
        "with _exclusive(p):\\n"
        "  (p/'first_owner_ready').write_text('owned');time.sleep(5)\\n"
    )
    # Construct an actual executable child source: use exec() to avoid a
    # compound with statement after a semicolon on Windows/Python 3.12.
    child_code="from pathlib import Path\\nfrom selenium_pipeline.development_continuity_executor_v71 import _exclusive\\nimport time,sys\\np=Path(sys.argv[1])\\nwith _exclusive(p):\\n (p/'first_owner_ready').write_text('owned')\\n time.sleep(5)\\n"
    child_code=child_code.replace("\\n","\n")
    proc=subprocess.Popen([sys.executable,"-c",child_code,str(state)],
                          cwd=ROOT,stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            if witness.exists():break
            time.sleep(.05)
        assert witness.is_file(),"Actual first executor lock never acquired"
        with pytest.raises(RuntimeError,match="already running"):
            with _exclusive(state):
                raise AssertionError("Second executor should never own lock")
    finally:
        proc.kill()
        proc.wait(timeout=10)
