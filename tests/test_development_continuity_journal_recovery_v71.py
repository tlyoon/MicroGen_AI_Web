"""Actual v7.1 overflow, archive atomicity, and no worker-replay regression."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import pytest

from selenium_pipeline import development_continuity_journal_recovery_v71 as jr
from selenium_pipeline.development_continuity_executor_v71 import (
    _atomic_json, _event, execute, _sha, _read_json,
)


ROOT=Path(__file__).resolve().parents[1]


def real_plan(tmp_path):
    witness=tmp_path/"lecture_source.pdf"
    witness.write_bytes(b"exact offline proof")
    tasks=[
        {"id":"source_accepted","workstream":"source",
         "action":"verify_file_sha256",
         "params":{"path":str(witness),
                   "sha256":hashlib.sha256(witness.read_bytes()).hexdigest()},
         "depends_on":[],"max_attempts":1,"authorized":True},
        {"id":"student_release","workstream":"release",
         "action":"verify_file_sha256",
         "params":{"path":str(witness),
                   "sha256":hashlib.sha256(witness.read_bytes()).hexdigest()},
         "depends_on":["source_accepted"],
         "max_attempts":1,"authorized":False},
    ]
    plan=tmp_path/"plan.json"
    plan.write_text(json.dumps({
        "schema_version":1,"project":"MicroGen_AI_Web","tasks":tasks
    }),encoding="utf8")
    state=tmp_path/"live_state"
    before=execute(plan_path=plan,state_dir=state,repo_root=ROOT)
    assert before["status"]=="BLOCKED_OR_AWAITING_EVIDENCE"
    return plan,state


def overflow(tmp_path, *, groups=950):
    plan,state=real_plan(tmp_path)
    path=state/"state.json"
    before=_read_json(path)
    for _ in range(groups):
        _event(before,"execution_checkpoint",detail={
            "completed":1,"dispatch_count":0,"remaining":1,
            "status":"BLOCKED_OR_AWAITING_EVIDENCE"})
    _atomic_json(path,before)
    assert path.stat().st_size>jr.INPUT_LIMIT_BYTES
    return plan,state,before


def test_repair_mechanism_is_in_executable_registry():
    assert jr.lookup_mechanism(jr.KIND,jr.SIGNATURE)==jr.REMEDY


def test_real_oversize_unreadable_old_state_archived_and_resumes_no_worker_replay(
        tmp_path):
    plan,state,before=overflow(tmp_path)
    path=state/"state.json"
    original=path.read_bytes()
    initial_result_files=sorted((state/"results").glob("*.json"))
    assert len(initial_result_files)==1
    with pytest.raises(ValueError,match="Unbounded JSON input"):
        execute(plan_path=plan,state_dir=state,repo_root=ROOT)
    report=jr.recover_journal(state_dir=state,plan_path=plan)
    assert report["status"]=="ORIGINAL_POLLING_JOURNAL_SHA_ARCHIVED_AND_COMPACTED"
    assert report["input_bytes"]==len(original)
    assert report["removed_duplicate_idle_events"]>=900
    assert Path(report["archive_path"]).read_bytes()==original
    after=_read_json(path)
    assert after["tasks"]==before["tasks"]
    assert after["plan_sha256"]==before["plan_sha256"]
    assert after["executor_sha256"]==before["executor_sha256"]
    assert after["project_complete"]==before["project_complete"]
    assert after["events"][0]["event"]=="roadmap_admitted"
    assert len(after["events"])<30
    assert [x["seq"] for x in after["events"]]==list(
        range(1,len(after["events"])+1))
    assert after["idle_journal_archive"]["original_state_sha256"]==(
        hashlib.sha256(original).hexdigest())
    resumed=execute(plan_path=plan,state_dir=state,repo_root=ROOT)
    assert resumed["status"]=="BLOCKED_OR_AWAITING_EVIDENCE"
    current=_read_json(path)
    assert current["tasks"]["source_accepted"]["attempts"]==1
    assert current["tasks"]["student_release"]["attempts"]==0
    assert len(list((state/"results").glob("*.json")))==1
    assert len([x for x in current["events"]
                if x["event"]=="worker_started"])==1
    assert len([x for x in current["events"]
                if x["event"]=="task_accepted"])==1
    assert report["paid_model_sends"]==0
    assert report["student_publication_authorized"] is False


def test_under_threshold_state_never_modified(tmp_path):
    plan,state=real_plan(tmp_path)
    path=state/"state.json"
    original=path.read_bytes()
    result=jr.recover_journal(state_dir=state,plan_path=plan)
    assert result=={"status":"JOURNAL_UNDER_THRESHOLD","provider_sends":0}
    assert path.read_bytes()==original
    assert not (state/"journal_archive").exists()


def test_crash_after_write_once_archive_before_atomic_replace_can_resume(
        tmp_path,monkeypatch):
    plan,state,before=overflow(tmp_path)
    path=state/"state.json"
    original=path.read_bytes()
    old=jr._atomic_json
    def power_failure(*args,**kwargs):
        raise OSError("fault-injected crash before atomic checkpoint replacement")
    monkeypatch.setattr(jr,"_atomic_json",power_failure)
    with pytest.raises(OSError,match="fault-injected"):
        jr.recover_journal(state_dir=state,plan_path=plan)
    assert path.read_bytes()==original
    archives=list((state/"journal_archive").glob("state_*.json"))
    assert len(archives)==1 and archives[0].read_bytes()==original
    monkeypatch.setattr(jr,"_atomic_json",old)
    recovery=jr.recover_journal(state_dir=state,plan_path=plan)
    assert recovery["original_state_sha256"]==hashlib.sha256(
        original).hexdigest()
    assert archives[0].read_bytes()==original


def test_forged_archive_will_not_overwrite_original_or_compact(tmp_path):
    plan,state,before=overflow(tmp_path)
    original=(state/"state.json").read_bytes()
    folder=state/"journal_archive"
    folder.mkdir()
    witness=hashlib.sha256(original).hexdigest()
    (folder/("state_"+witness+".json")).write_text("forged",encoding="utf8")
    with pytest.raises(ValueError,match="archive conflicts"):
        jr.recover_journal(state_dir=state,plan_path=plan)
    assert (state/"state.json").read_bytes()==original


def test_plan_change_refused_before_archive(tmp_path):
    plan,state,before=overflow(tmp_path)
    original=(state/"state.json").read_bytes()
    value=json.loads(plan.read_text(encoding="utf8"))
    value["tasks"].reverse()
    plan.write_text(json.dumps(value),encoding="utf8")
    with pytest.raises(ValueError,match="identity changed"):
        jr.recover_journal(state_dir=state,plan_path=plan)
    assert (state/"state.json").read_bytes()==original
    assert not (state/"journal_archive").exists()


def test_executor_sha_changed_refused_without_loss(tmp_path):
    plan,state,before=overflow(tmp_path)
    path=state/"state.json"
    before["executor_sha256"]="0"*64
    _atomic_json(path,before)
    original=path.read_bytes()
    with pytest.raises(ValueError,match="identity changed"):
        jr.recover_journal(state_dir=state,plan_path=plan)
    assert path.read_bytes()==original


def test_invalid_history_sequence_refused_without_loss(tmp_path):
    plan,state,before=overflow(tmp_path)
    path=state/"state.json"
    before["events"][7]["seq"]=88
    _atomic_json(path,before)
    original=path.read_bytes()
    with pytest.raises(ValueError,match="event sequence"):
        jr.recover_journal(state_dir=state,plan_path=plan)
    assert path.read_bytes()==original


def test_only_identical_adjacent_idle_events_compacted(tmp_path):
    plan,state=real_plan(tmp_path)
    path=state/"state.json"
    before=_read_json(path)
    for mark in ("A","A","B","B","A"):
        _event(before,"execution_checkpoint",
               detail={"status":mark,"dispatch_count":0})
    _event(before,"unexpected_new_failure",task="source_accepted",
           detail={"reason":"must survive"})
    for _ in range(10):
        _event(before,"execution_checkpoint",
               detail={"status":"C","dispatch_count":0})
    _atomic_json(path,before)
    result=jr.recover_journal(state_dir=state,plan_path=plan,trigger_bytes=1)
    assert result["removed_duplicate_idle_events"]==11
    after=_read_json(path)
    rows=[x for x in after["events"] if x["event"]=="execution_checkpoint"]
    assert [x["detail"]["status"] for x in rows]==[
        "BLOCKED_OR_AWAITING_EVIDENCE","A","B","A","C"]
    assert any(x["event"]=="unexpected_new_failure" for x in after["events"])


def test_no_duplicate_event_storm_does_not_silently_discard_evidence(
        tmp_path):
    plan,state=real_plan(tmp_path)
    path=state/"state.json"
    original=path.read_bytes()
    with pytest.raises(ValueError,match="No redundant"):
        jr.recover_journal(state_dir=state,plan_path=plan,trigger_bytes=1)
    assert path.read_bytes()==original


@pytest.mark.parametrize("trigger",[0,-1,True,180001])
def test_unbounded_or_invalid_trigger_denied(tmp_path,trigger):
    plan,state=real_plan(tmp_path)
    with pytest.raises(ValueError,match="Invalid bounded"):
        jr.recover_journal(state_dir=state,plan_path=plan,trigger_bytes=trigger)


def test_live_daemon_invokes_journal_recovery_before_each_poll(tmp_path):
    from selenium_pipeline.development_continuity_daemon_v71 import daemon
    plan,state=real_plan(tmp_path)
    original=_read_json(state/"state.json")
    for _ in range(950):
        _event(original,"execution_checkpoint",
               detail={"completed":1,"dispatch_count":0,"remaining":1,
                       "status":"BLOCKED_OR_AWAITING_EVIDENCE"})
    _atomic_json(state/"state.json",original)
    result=daemon(plan_path=plan,state_dir=state,repo_root=ROOT,
                  poll_seconds=1,heartbeat_seconds=.5,max_cycles=1)
    assert result["cycles"]==1
    assert result["original_journals_archived"]==1
    assert result["last_journal_recovery_status"]==(
        "ORIGINAL_POLLING_JOURNAL_SHA_ARCHIVED_AND_COMPACTED")
    assert result["provider_sends"]==0
    assert result["student_publication_authorized"] is False
    assert _read_json(state/"state.json")["tasks"]==original["tasks"]



def test_missing_prior_immutable_history_blocks_future_polling(tmp_path):
    plan,state,_=overflow(tmp_path)
    report=jr.recover_journal(state_dir=state,plan_path=plan)
    archived=Path(report["archive_path"])
    archived.unlink()
    with pytest.raises(ValueError,match="not an ordinary file"):
        jr.recover_journal(state_dir=state,plan_path=plan)
    assert _read_json(state/"state.json")["tasks"]["student_release"][
        "status"]=="awaiting_authorization"


def test_archive_link_failed_during_commit_keeps_original_journal(
        tmp_path,monkeypatch):
    plan,state,_=overflow(tmp_path)
    before=(state/"state.json").read_bytes()
    def broken_link(*args,**kwargs):
        raise OSError("fault injected archive atomic link failure")
    monkeypatch.setattr(jr.os,"link",broken_link)
    with pytest.raises(OSError,match="archive atomic"):
        jr.recover_journal(state_dir=state,plan_path=plan)
    assert (state/"state.json").read_bytes()==before
    assert not list((state/"journal_archive").glob("state_*.json"))


def test_deleting_archive_directory_is_not_silent(tmp_path):
    plan,state,_=overflow(tmp_path)
    result=jr.recover_journal(state_dir=state,plan_path=plan)
    archive=Path(result["archive_path"])
    archive.unlink()
    archive.parent.rmdir()
    with pytest.raises(ValueError,match="not an ordinary file"):
        jr.recover_journal(state_dir=state,plan_path=plan)
