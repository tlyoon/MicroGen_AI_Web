"""v7.1 code repair: one sandboxed model call, pinned allowlist, no replay."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

from selenium_pipeline.development_coding_job_v71 import (
    admit_job, run_once, _codex_command, require_recovery, REGISTRY,
    reconcile_existing_response,
)


def git(repo,*args):
    return subprocess.run(["git","-C",str(repo),*args],check=True,
                          capture_output=True,text=True).stdout.strip()


@pytest.fixture
def isolated(tmp_path):
    root=tmp_path/"MicroGen_AI_Web_Checkpoints"
    repo=root/"job1"/"repo"
    repo.mkdir(parents=True)
    git(repo,"init","-q")
    git(repo,"config","user.name","safe tester")
    git(repo,"config","user.email","safe@example.invalid")
    (repo/"tests").mkdir()
    (repo/"tests"/"test_safe.py").write_text(
        "def test_safe():\n    assert 1 == 1\n")
    git(repo,"add",".")
    git(repo,"commit","-qm","base")
    git(repo,"switch","-c","feature/pr584-bounded-safe-candidate")
    main=git(repo,"rev-parse","HEAD")
    manifest={
        "schema_version":1,"project":"MicroGen_AI_Web",
        "job_id":"case01","main_sha":main,
        "branch":"feature/pr584-bounded-safe-candidate",
        "instruction":"Repair only a harmless independent regression test while keeping source policies unchanged.",
        "allowed_files":["tests/generated_safe.py"],
        "required_tests":["tests/test_safe.py"],
        "max_seconds":180,"authorized":True,
    }
    job=root/"job.json"
    job.write_text(json.dumps(manifest),encoding="utf8")
    agent=root/"codex.cmd"
    agent.write_bytes(b"bounded command placeholder")
    manifest["codex_sha256"]=hashlib.sha256(agent.read_bytes()).hexdigest()
    job.write_text(json.dumps(manifest),encoding="utf8")
    return {"root":root,"repo":repo,"job":job,"manifest":manifest,
            "codex":agent,"state":root/"state"}


def dispatch(f,model=None,tests=None):
    return run_once(job_path=f["job"],repo=f["repo"],state_dir=f["state"],
                    checkpoint_root=f["root"],codex_path=f["codex"],
                    model_runner=model,test_runner=tests,verify_remote=False)


def good_model(f, count):
    def run(command,prompt,*,cwd,timeout):
        count.append((command,prompt,timeout))
        assert "--sandbox" in command
        assert "workspace-write" in command
        assert "sandbox_workspace_write.network_access=false" in command
        assert "Git pushes" in prompt
        assert timeout == 180
        (cwd/"tests"/"generated_safe.py").write_text(
            "def test_generated():\n    assert True\n")
        return subprocess.CompletedProcess(command,0,stdout="generated")
    return run


def fake_test(command,*,cwd,capture_output,text,timeout):
    assert command[:4]==[sys.executable,"-m","pytest","-q"]
    assert command[-1]=="tests/test_safe.py"
    return subprocess.CompletedProcess(command,0,stdout="1 passed")


def test_coding_job_admission_requires_clean_branch_and_explicit_allowlist(isolated):
    row=admit_job(job_path=isolated["job"],repo=isolated["repo"],
                  state_dir=isolated["state"],
                  checkpoint_root=isolated["root"],verify_remote=False)
    assert row["job_sha256"] and row["job"]["authorized"] is True


def test_exact_single_model_send_and_local_tests(isolated):
    sends=[]
    result=dispatch(isolated,good_model(isolated,sends),fake_test)
    assert result["status"]=="LOCAL_CODING_CANDIDATE_VERIFIED"
    assert result["model_invocations_claimed"]==1
    assert result["candidate_pr_pushed"] is False
    assert result["student_release"] is False
    assert result["evidence"]["changed_files"]==["tests/generated_safe.py"]
    assert len(sends)==1
    state=json.loads((isolated["state"]/"coding_job_state.json").read_text())
    assert state["status"]==result["status"]


def test_repeated_run_returns_exact_existing_acceptance_never_resends(isolated):
    sends=[]
    first=dispatch(isolated,good_model(isolated,sends),fake_test)
    second=dispatch(isolated,good_model(isolated,sends),fake_test)
    assert first==second
    assert len(sends)==1


def test_changed_authorized_coding_cli_hash_fails_before_claim(isolated):
    isolated["codex"].write_bytes(b"new unapproved CLI binary")
    with pytest.raises(ValueError,match="Codex CLI"):
        dispatch(isolated,good_model(isolated,[]),fake_test)
    assert not (isolated["state"]/"coding_job_state.json").exists()


def test_accepted_checkpoint_rejects_subsequent_code_tampering(isolated):
    sends=[]
    dispatch(isolated,good_model(isolated,sends),fake_test)
    (isolated["repo"]/"tests"/"generated_safe.py").write_text(
        "def test_generated():\n    assert False\n")
    with pytest.raises(ValueError,match="changed after checkpoint"):
        dispatch(isolated,good_model(isolated,sends),fake_test)
    assert len(sends)==1


def test_new_required_test_is_admitted_only_if_exactly_allowlisted(isolated):
    job=dict(isolated["manifest"])
    job["required_tests"]=["tests/generated_safe.py"]
    isolated["job"].write_text(json.dumps(job),encoding="utf8")
    row=admit_job(job_path=isolated["job"],repo=isolated["repo"],
                  state_dir=isolated["state"],
                  checkpoint_root=isolated["root"],verify_remote=False)
    assert row["job"]["required_tests"]==["tests/generated_safe.py"]
    job["allowed_files"]=["docs/allowed.md"]
    isolated["job"].write_text(json.dumps(job),encoding="utf8")
    with pytest.raises(ValueError):
        admit_job(job_path=isolated["job"],repo=isolated["repo"],
                  state_dir=isolated["state"],
                  checkpoint_root=isolated["root"],verify_remote=False)


def test_uncertain_model_failure_is_persisted_and_never_replayed(isolated):
    calls=[]
    def uncertain(command,prompt,*,cwd,timeout):
        calls.append(1)
        raise subprocess.TimeoutExpired(command,timeout)
    with pytest.raises(RuntimeError,match="uncertain"):
        dispatch(isolated,uncertain,fake_test)
    state=json.loads((isolated["state"]/"coding_job_state.json").read_text())
    assert state["status"]=="EXTERNAL_MODEL_RESULT_UNCERTAIN"
    with pytest.raises(RuntimeError,match="never resend"):
        dispatch(isolated,uncertain,fake_test)
    assert len(calls)==1


def test_successful_model_with_crash_after_response_reuses_saved_code(isolated):
    sends=[]
    def failed_test(command,*,cwd,capture_output,text,timeout):
        return subprocess.CompletedProcess(command,1,stdout="real regression")
    with pytest.raises(ValueError,match="regressions"):
        dispatch(isolated,good_model(isolated,sends),failed_test)
    state=json.loads((isolated["state"]/"coding_job_state.json").read_text())
    assert state["status"]=="MODEL_RESPONDED_UNVERIFIED"
    result=dispatch(isolated,good_model(isolated,sends),fake_test)
    assert result["status"]=="LOCAL_CODING_CANDIDATE_VERIFIED"
    assert len(sends)==1


def test_worker_modifies_disallowed_source_and_is_not_accepted(isolated):
    def bad(command,prompt,*,cwd,timeout):
        (cwd/"outside.py").write_text("danger")
        return subprocess.CompletedProcess(command,0,stdout="oops")
    state=dispatch(isolated,bad,fake_test)
    assert state["status"]=="MODEL_SOURCE_CHANGE_QUARANTINED"
    assert state["failure_class"]=="MODEL_MODIFIED_UNAPPROVED_FILES"
    assert state["candidate_pr_pushed"] is False
    assert state["next_independent_workstream_eligible"] is True


def test_empty_model_change_not_accepted(isolated):
    def no_change(command,prompt,*,cwd,timeout):
        return subprocess.CompletedProcess(command,0,stdout="done")
    seen=[]
    def tracked(command,prompt,*,cwd,timeout):
        seen.append(1)
        return no_change(command,prompt,cwd=cwd,timeout=timeout)
    result=dispatch(isolated,tracked,fake_test)
    assert result["status"]=="MODEL_NO_SOURCE_DIFF_QUARANTINED"
    assert result["failure_class"]=="MODEL_RESPONDED_NO_SOURCE_DIFF"
    assert result["model_invocations_claimed"]==1
    assert result["candidate_pr_pushed"] is False
    second=dispatch(isolated,tracked,fake_test)
    assert second==result and len(seen)==1


def test_changed_original_manifest_cannot_reissue_model(isolated):
    sends=[]
    dispatch(isolated,good_model(isolated,sends),fake_test)
    altered=isolated["manifest"].copy()
    altered["instruction"]="Different user instruction may consume another code-generation request."
    isolated["job"].write_text(json.dumps(altered))
    with pytest.raises(ValueError,match="changed"):
        dispatch(isolated,good_model(isolated,sends),fake_test)
    assert len(sends)==1


@pytest.mark.parametrize("defect",[
    ("authorized",False),
    ("branch","main"),
    ("job_id","../evil"),
    ("max_seconds",6000),
    ("allowed_files",["../secrets.json"]),
    ("allowed_files",["selenium_pipeline/../../private.py"]),
    ("allowed_files",[".github/workflows/release.yml"]),
    ("allowed_files",["tests/test_safe.py","../../unsafe.py"]),
    ("required_tests",["-x","tests/test_safe.py"]),
])
def test_invalid_job_fails_before_model_claim(isolated,defect):
    a,b=defect
    job=dict(isolated["manifest"])
    job[a]=b
    isolated["job"].write_text(json.dumps(job))
    with pytest.raises(ValueError):
        dispatch(isolated,good_model(isolated,[]),fake_test)
    assert not (isolated["state"]/"coding_job_state.json").exists()


def test_dirty_start_repository_is_refused(isolated):
    (isolated["repo"]/"private.txt").write_text("untracked")
    with pytest.raises(ValueError,match="source-pinned"):
        dispatch(isolated,good_model(isolated,[]),fake_test)


@pytest.mark.parametrize("tamper",[
    ("enabled",False),
    ("max_additional_model_calls",1),
    ("may_create_or_merge_pr",True),
    ("may_release_students",True),
    ("handlers",{}),
])
def test_noop_recovery_registry_fails_closed_when_modified(tmp_path,tamper):
    data=json.loads(REGISTRY.read_text(encoding="utf8"))
    data[tamper[0]]=tamper[1]
    path=tmp_path/"unsafe_recovery.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="Unregistered"):
        require_recovery("MODEL_RESPONDED_NO_SOURCE_DIFF",registry=path)


def test_registered_noop_handler_preserves_original_provider_claim():
    assert require_recovery("MODEL_RESPONDED_NO_SOURCE_DIFF")==(
        "QUARANTINE_NOOP_PRESERVE_RESPONSE_AND_ADVANCE_OFFLINE_BACKLOG")


def test_coding_model_test_failure_records_no_resend_recovery(isolated):
    sends=[]
    def failing(command,*,cwd,capture_output,text,timeout):
        return subprocess.CompletedProcess(command,1,stdout="error")
    with pytest.raises(ValueError,match="regressions"):
        dispatch(isolated,good_model(isolated,sends),failing)
    state=json.loads((isolated["state"]/"coding_job_state.json").read_text())
    assert state["recovery_action"]==(
        "RETEST_EXISTING_RESPONSE_WITH_ZERO_MODEL_REPLAY")
    assert state["next_model_send_authorized"] is False
    accepted=dispatch(isolated,good_model(isolated,sends),fake_test)
    assert accepted["status"]=="LOCAL_CODING_CANDIDATE_VERIFIED"
    assert len(sends)==1


def test_completed_noop_response_can_reconcile_on_new_main_without_model_send(
        isolated):
    calls=[]
    def original_model(command,prompt,*,cwd,timeout):
        calls.append(1)
        return subprocess.CompletedProcess(command,0,stdout="no change")
    result=dispatch(isolated,original_model,fake_test)
    assert result["status"]=="MODEL_NO_SOURCE_DIFF_QUARANTINED"
    prior=reconcile_existing_response(
        job_path=isolated["job"],repo=isolated["repo"],
        state_dir=isolated["state"],checkpoint_root=isolated["root"],
        codex_path=isolated["codex"],test_runner=fake_test)
    assert prior==result
    assert len(calls)==1
    assert prior["model_invocations_claimed"]==1
    assert prior["candidate_pr_pushed"] is False


def test_reconcile_only_refuses_uncertain_model_request_without_replay(
        isolated):
    calls=[]
    def ambiguous(command,prompt,*,cwd,timeout):
        calls.append(1)
        raise subprocess.TimeoutExpired(command,timeout)
    with pytest.raises(RuntimeError):
        dispatch(isolated,ambiguous,fake_test)
    with pytest.raises(ValueError,match="known completed model"):
        reconcile_existing_response(
            job_path=isolated["job"],repo=isolated["repo"],
            state_dir=isolated["state"],checkpoint_root=isolated["root"],
            codex_path=isolated["codex"],test_runner=fake_test)
    assert len(calls)==1


def test_reconcile_only_requires_existing_response_checkpoint(isolated):
    with pytest.raises(ValueError,match="No original"):
        reconcile_existing_response(
            job_path=isolated["job"],repo=isolated["repo"],
            state_dir=isolated["state"],checkpoint_root=isolated["root"],
            codex_path=isolated["codex"],test_runner=fake_test)


def test_non_model_script_cannot_be_coding_program(isolated):
    exe=isolated["root"]/"agent.ps1"
    exe.write_text("Write-Output evil")
    with pytest.raises(ValueError,match="Untrusted"):
        _codex_command(exe,isolated["repo"])


def test_no_code_job_may_edit_git_configuration_or_task_scheduler(isolated):
    isolated["manifest"]["allowed_files"]=[".git/config"]
    isolated["job"].write_text(json.dumps(isolated["manifest"]))
    with pytest.raises(ValueError):
        dispatch(isolated,good_model(isolated,[]),fake_test)
