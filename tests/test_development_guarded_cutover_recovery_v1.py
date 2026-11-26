"""Historical Dell Windows cutover: safe rollback, bounded retry, no model sends."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest
from selenium_pipeline import development_guarded_cutover_recovery_v1 as cut


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup(tmp_path):
    root=tmp_path/"RECONCILE"
    root.mkdir()
    old=root/"post_pr654_main"
    new=root/"post_pr655_main"
    state=root/"live_state_migrated_v1"
    state.mkdir()
    for repo in (old,new):
        p=repo/"selenium_pipeline"/"development_continuity_executor_v71.py"
        p.parent.mkdir(parents=True)
        p.write_text("pinned executor 422c")
    script=root/"guarded_cutover_after_pr655.ps1"
    script.write_text(
        "$oldRepo=Join-Path $root 'post_pr654_main'\n"
        "$newRepo=Join-Path $root 'post_pr655_main'\n"
        "GUARDED_CUTOVER_SUCCESS\n"
        "ORIGINAL_DAEMON_RESTART_REQUESTED\n"
        "provider_sends\nstudent_publication_authorized\nGet-CimInstance\n"
    )
    plan=tmp_path/"original_v71_plan.json"
    plan.write_text('{"task":"frozen"}')
    manifest=root/"manifest.json"
    payload={"schema_version":1,
             "task_name":cut.TASK,
             "root":str(root),
             "old_repo":str(old),
             "new_repo":str(new),
             "state_dir":str(state),
             "original_plan":str(plan),
             "guard_script":str(script),
             "guard_script_sha256":_sha(script),
             "expected_main_sha":"a"*40,
             "new_provider_sends_allowed":False,
             "student_publication_authorized":False}
    manifest.write_text(json.dumps(payload))
    return manifest, root/"report", payload


def owner(m,which="old_repo",pid=23,run_id="original_owner_123456"):
    repo=str(Path(m[which]).resolve())
    return {
        "task_state":"Running",
        "repo_root":repo,
        "action_args":"--repo-root "+repo+" --state-dir "+m["state_dir"],
        "multiple_instances":"IgnoreNew",
        "logon_type":"Interactive",
        "run_level":"Limited",
        "process_alive":True,
        "process_cmdline":"python -m selenium_pipeline.development_continuity_daemon_v71 --repo-root "+repo,
        "owner_pid":pid,
        "run_id":run_id,
        "heartbeat_age_seconds":3.0,
        "provider_sends":0,
        "student_publication_authorized":False,
        "running":True,
    }


def test_registry_is_executable():
    from selenium_pipeline.recovery_registry import lookup_mechanism
    assert lookup_mechanism(cut.KIND,cut.SIGNATURE)==cut.MECHANISM


def test_first_failed_owner_rolls_back_second_success(tmp_path):
    manifest,report,m=setup(tmp_path)
    calls=[]
    sequence=[
      owner(m,"old_repo",23,"original_owner_123456"),
      owner(m,"old_repo",47,"rollback_owner_123456"),
      owner(m,"new_repo",51,"new_owner_123456789")
    ]
    def read(_):
        return sequence.pop(0)
    def invoke(_):
        calls.append("called")
        if len(calls)==1:
            return CompletedProcess([],1,"CUTOVER_ERROR New daemon owner not independently attested","")
        return CompletedProcess([],0,"GUARDED_CUTOVER_SUCCESS","")
    result=cut.resume(manifest=manifest,report_root=report,
                      readback_fn=read,invoke_fn=invoke,
                      main_fn=lambda m:True)
    assert result["status"]==cut.COMPLETE
    assert result["attempt_count"]==2
    assert result["attempts"][0]["postowner_status"]=="VERIFIED_SAFE_ROLLBACK"
    assert result["attempts"][1]["postowner_status"]=="NEW_OWNER_ATTESTED"
    assert len(calls)==2
    assert result["new_provider_sends"]==0
    assert result["student_publication_authorized"] is False


def test_missing_new_owner_does_not_retry(tmp_path):
    manifest,report,m=setup(tmp_path)
    original=owner(m,"old_repo")
    bad=owner(m,"new_repo")
    bad["process_alive"]=False
    queue=[original,bad]
    tries=[]
    result=cut.resume(manifest=manifest,report_root=report,
                      readback_fn=lambda m:queue.pop(0),
                      invoke_fn=lambda m:tries.append(1) or
                        CompletedProcess([],1,"UNVERIFIED",""),
                      main_fn=lambda m:True)
    assert result["status"]==cut.HOLD
    assert len(tries)==1
    assert result["attempts"][0]["postowner_status"]=="UNATTESTED_OR_PARTIAL_ROLLBACK"


def test_two_failures_stop_with_original_running(tmp_path):
    manifest,report,m=setup(tmp_path)
    queue=[owner(m,"old_repo"),owner(m,"old_repo",40,"rollback_00000000"),
           owner(m,"old_repo",42,"rollback_22222222")]
    call=[]
    result=cut.resume(manifest=manifest,report_root=report,
                      readback_fn=lambda m:queue.pop(0),
                      invoke_fn=lambda m:call.append(1) or CompletedProcess([],1,"",""),
                      main_fn=lambda m:True)
    assert result["status"]==cut.HOLD
    assert result["attempt_count"]==2
    assert len(call)==2


def test_successful_existing_new_owner_does_not_dispatch(tmp_path):
    manifest,report,m=setup(tmp_path)
    never=[]
    result=cut.resume(manifest=manifest,report_root=report,
                      readback_fn=lambda m:owner(m,"new_repo",51,"new_owner_0001234"),
                      invoke_fn=lambda m:never.append(1),
                      main_fn=lambda m:True)
    assert result["status"]==cut.COMPLETE
    assert result["attempt_count"]==0
    assert never==[]


def test_verify_only_avoids_cutover(tmp_path):
    manifest,report,m=setup(tmp_path)
    never=[]
    result=cut.resume(manifest=manifest,report_root=report,
                      verify_only=True,
                      readback_fn=lambda m:owner(m,"old_repo"),
                      invoke_fn=lambda m:never.append(1),
                      main_fn=lambda m:True)
    assert result["status"]=="GUARDED_MAIN_CUTOVER_AWAITING_EXECUTION"
    assert never==[]


def test_server_side_nonzero_but_new_pid_verified_is_success(tmp_path):
    manifest,report,m=setup(tmp_path)
    queue=[owner(m,"old_repo"),owner(m,"new_repo",51,"new_owner_123456789")]
    result=cut.resume(manifest=manifest,report_root=report,
                      readback_fn=lambda m:queue.pop(0),
                      invoke_fn=lambda m:CompletedProcess([],1,"Client failed", ""),
                      main_fn=lambda m:True)
    assert result["status"]==cut.COMPLETE
    assert result["attempt_count"]==1
    assert not result["attempts"][0]["guard_reported_success"]


@pytest.mark.parametrize("corrupt",[
    "script","plan","new_exec","wrong_sha","changed_task","sends","publish"])
def test_untrusted_manifest_does_not_invoke_task(corrupt,tmp_path):
    manifest,report,m=setup(tmp_path)
    if corrupt=="script":
        Path(m["guard_script"]).write_text("new script no rollback")
    if corrupt=="plan":
        Path(m["original_plan"]).unlink()
    if corrupt=="new_exec":
        (Path(m["new_repo"])/"selenium_pipeline"/
         "development_continuity_executor_v71.py").write_text("different")
    if corrupt=="wrong_sha":
        m["expected_main_sha"]="bad"
    if corrupt=="changed_task":
        m["task_name"]="Another task"
    if corrupt=="sends":
        m["new_provider_sends_allowed"]=True
    if corrupt=="publish":
        m["student_publication_authorized"]=True
    manifest.write_text(json.dumps(m))
    calls=[]
    with pytest.raises(ValueError):
        cut.resume(manifest=manifest,report_root=report,
                   readback_fn=lambda m:owner(m,"old_repo"),
                   invoke_fn=lambda m:calls.append(1),
                   main_fn=lambda m:True)
    assert calls==[]


def test_forged_new_owner_cannot_pass(tmp_path):
    manifest,report,m=setup(tmp_path)
    original=owner(m,"old_repo")
    invalid=owner(m,"new_repo",51,"new_owner_12345678")
    invalid["provider_sends"]=1
    queue=[original,invalid]
    result=cut.resume(manifest=manifest,report_root=report,
                      readback_fn=lambda m:queue.pop(0),
                      invoke_fn=lambda m:CompletedProcess([],0,"GUARDED_CUTOVER_SUCCESS",""),
                      main_fn=lambda m:True)
    assert result["status"]==cut.HOLD


def test_report_is_restart_atomic(tmp_path):
    manifest,report,m=setup(tmp_path)
    result=cut.resume(manifest=manifest,report_root=report,
                      verify_only=True,main_fn=lambda m:True,
                      readback_fn=lambda m:owner(m,"old_repo"))
    final=report/"guarded_main_cutover_recovery.json"
    assert json.loads(final.read_text("utf8"))==result
    assert not final.with_suffix(".pending").exists()


def test_max_two_attempts_and_main_drift_fails_closed(tmp_path):
    manifest,report,m=setup(tmp_path)
    with pytest.raises(ValueError,match="unbounded"):
        cut.resume(manifest=manifest,report_root=report,
                   max_attempts=99,main_fn=lambda m:True)
    with pytest.raises(ValueError):
        cut.resume(manifest=manifest,report_root=report,
                   readback_fn=lambda m:owner(m,"old_repo"),
                   main_fn=lambda m:(_ for _ in ()).throw(ValueError("main moved")),
                   invoke_fn=lambda m:None)




def test_drifted_unprotected_main_is_blocked_even_with_clean_git_checkout():
    m={"new_repo":"C:/safe/project","expected_main_sha":"a"*40}
    from subprocess import CompletedProcess
    def fake(args,*,timeout):
        if args[:2]==["gh","api"]:
            return CompletedProcess(args,0,json.dumps({
              "required_status_checks":{"strict":False,"contexts":[]},
              "enforce_admins":{"enabled":False}}),"")
        if "rev-parse" in args:
            return CompletedProcess(args,0,"a"*40+"\n","")
        if "ls-remote" in args:
            return CompletedProcess(args,0,"a"*40+"  refs/heads/main\n","")
        return CompletedProcess(args,0,"","")
    with pytest.raises(ValueError,match="no longer enforces"):
        cut.git_main(m,executor=fake)


def test_valid_main_and_strict_windows_branch_protection_pass():
    m={"new_repo":"C:/safe/project","expected_main_sha":"a"*40}
    from subprocess import CompletedProcess
    checks={"required_status_checks":{"strict":True,"contexts":[
       "offline-regressions","Full offline suite (Windows, Python 3.12)"]},
       "enforce_admins":{"enabled":True},
       "required_linear_history":{"enabled":True},
       "allow_force_pushes":{"enabled":False},
       "allow_deletions":{"enabled":False}}
    def fake(args,*,timeout):
        if args[:2]==["gh","api"]:
            return CompletedProcess(args,0,json.dumps(checks),"")
        if "rev-parse" in args:
            return CompletedProcess(args,0,"a"*40+"\n","")
        if "ls-remote" in args:
            return CompletedProcess(args,0,"a"*40+"  refs/heads/main\n","")
        return CompletedProcess(args,0,"","")
    assert cut.git_main(m,executor=fake)
