"""No-Send, restart/CI/cutover regression for autonomous source promotion."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from selenium_pipeline import development_source_pinned_next_job_v1 as selector
from selenium_pipeline import development_verified_candidate_promotion_v1 as promoter
from selenium_pipeline import development_certified_candidate_deploy_v1 as deployer
from selenium_pipeline import development_autonomous_code_loop_v1 as controller
from selenium_pipeline.recovery_registry import lookup_mechanism


def git(repo,*args):
    r=subprocess.run(["git","-C",str(repo),*args],
                     capture_output=True,text=True,check=True)
    return r.stdout.strip()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@pytest.fixture
def env(tmp_path):
    main=tmp_path/"main"
    main.mkdir()
    git(main,"init","-b","main")
    git(main,"config","user.name","MicroGen safe test")
    git(main,"config","user.email","source-only@example.invalid")
    (main/"selenium_pipeline").mkdir()
    (main/"selenium_pipeline"/"__init__.py").write_text("")
    (main/"tests").mkdir()
    (main/".gitignore").write_text(
        "__pycache__/\n.pytest_cache/\n*.pyc\n")
    git(main,"add",".")
    git(main,"commit","-m","original source")
    base=git(main,"rev-parse","HEAD")
    backlog=tmp_path/"model_backlog"
    (backlog/"inbox").mkdir(parents=True)
    (backlog/"state").mkdir()
    (tmp_path/"MICROGEN_AUTONOMOUS_CODE_WORKTREES_V1").mkdir()
    control=tmp_path/"control"
    (control/"promotions"/"worktrees").mkdir(parents=True)
    (control/"specs").mkdir()
    spec=(control/"specs"/"g3_captioned_png_asset_coverage_v1.py")
    original=(Path(__file__).parent.parent/"development_specs"/
              "g3_captioned_png_asset_coverage_v1.py")
    shutil.copyfile(original,spec)
    entry={
        "job_id":"g3_png_asset_coverage_v1",
        "spec_path":"specs/g3_captioned_png_asset_coverage_v1.py",
        "spec_sha256":sha(spec),
        "test":"tests/test_g3_captioned_png_asset_coverage_v1.py",
        "target":"selenium_pipeline/g3_captioned_png_asset_coverage_v1.py",
        "instruction":"Implement the source and rendered caption IDs comparison "
            "without any API, subprocess, disk IO or publishing. Return the "
            "exact evidence flags from each independent test. Technical only.",
        "selenium_mode":"hydrogen",
    }
    catalog=control/"approved.json"
    catalog.write_text(json.dumps({
        "schema_version":1,"status":selector.SCHEMA,
        "paid_api_authorized":False,"student_publication_authorized":False,
        "jobs":[entry]}))
    # Tests have independent original catalogs; the live deployment pins
    # the exact Git-reviewed SHA rather than allowing arbitrary additions.
    selector.CATALOG_SHA256=sha(catalog)
    return dict(main=main,backlog=backlog,control=control,
                catalog=catalog,spec=spec,entry=entry,base=base)


def fake_git(main):
    def runner(args,timeout=60):
        if args[:2]==["gh","api"]:
            return git(main,"rev-parse","HEAD")
        r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        if r.returncode:
            raise ValueError(r.stderr[-250:])
        return r.stdout.strip()
    return runner


def test_three_recoveries_must_be_registered():
    assert lookup_mechanism(
        selector.KIND,selector.SIGNATURE)==selector.MECHANISM
    assert lookup_mechanism(
        promoter.KIND,promoter.SIGNATURE)==promoter.MECHANISM
    assert lookup_mechanism(
        deployer.KIND,deployer.SIGNATURE)==deployer.MECHANISM


def test_real_local_git_task_selection_and_restart_no_second_job(env):
    a=selector.select(catalog_path=env["catalog"],
                      backlog_root=env["backlog"],
                      repo_root=env["main"],
                      git=fake_git(env["main"]))
    assert a["status"]=="NEW_ELIGIBLE_CODING_JOB_STAGED"
    assert a["model_sends"]==0
    assert a["paid_api_requests"]==0
    job=env["backlog"]/"inbox"/(a["job"]+".json")
    saved=job.read_bytes()
    again=selector.select(catalog_path=env["catalog"],
                          backlog_root=env["backlog"],
                          repo_root=env["main"],
                          git=fake_git(env["main"]))
    assert again["status"]=="NO_NEW_APPROVED_SOURCE_TEST_JOBS"
    assert job.read_bytes()==saved
    assert len(list((env["backlog"]/"inbox").glob("*.json")))==1


def test_modified_original_independent_tests_cannot_stage(env):
    env["spec"].write_text("forged original independent test")
    with pytest.raises(ValueError,match="test specimen changed"):
        selector.select(catalog_path=env["catalog"],
                        backlog_root=env["backlog"],
                        repo_root=env["main"],git=fake_git(env["main"]))
    assert not list((env["backlog"]/"inbox").glob("*.json"))


def test_catalog_with_paid_api_authorization_cannot_stage(env):
    c=json.loads(env["catalog"].read_text())
    c["paid_api_authorized"]=True
    env["catalog"].write_text(json.dumps(c))
    # Simulate a newly signed but invalid original catalogue to test both
    # cryptographic and independent semantic admissions.
    selector.CATALOG_SHA256=sha(env["catalog"])
    with pytest.raises(ValueError,match="not safely admitted"):
        selector.select(catalog_path=env["catalog"],
                        backlog_root=env["backlog"],
                        repo_root=env["main"],git=fake_git(env["main"]))


def test_catalog_rejects_invented_remote_executable_path(env):
    c=json.loads(env["catalog"].read_text())
    c["jobs"][0]["target"]="scripts/erase_history.py"
    env["catalog"].write_text(json.dumps(c))
    selector.CATALOG_SHA256=sha(env["catalog"])
    with pytest.raises(ValueError,match="task contract"):
        selector.select(catalog_path=env["catalog"],
                        backlog_root=env["backlog"],
                        repo_root=env["main"],git=fake_git(env["main"]))


def _accepted_original_model(env):
    # Real local Git worktree and independent test; original reply and
    # candidate SHA kept under distinct durable directories.
    work=env["control"]/"original_candidate"
    git(env["main"],"worktree","add","-b","feature/original_candidate",
        str(work),"HEAD")
    spec=Path(__file__).parent.parent/"tests"/"test_windows_pytest_result_v1.py"
    test=work/"tests"/spec.name
    test.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(spec,test)
    git(work,"add",str(Path("tests")/spec.name))
    git(work,"commit","-m","independent test before model")
    base=git(work,"rev-parse","HEAD")
    good='''"""Source-pinned pytest classification."""
def classify_pytest_result(return_code, stdout, stderr):
    return {"passed": type(return_code) is int and return_code == 0,
            "return_code": return_code, "stdout":stdout,"stderr":stderr}
'''
    target=work/"selenium_pipeline"/"windows_pytest_result_v1.py"
    target.write_bytes(good.encode("utf8"))
    ident="windows_pytest_promotable_v1"
    job={
        "schema_version":1,"project":"MicroGen_AI_Web",
        "job_id":ident,"authorized":True,
        "repo":str(work),"base_sha":base,
        "branch":"feature/original_candidate",
        "target":"selenium_pipeline/windows_pytest_result_v1.py",
        "target_original_sha256":None,
        "test":"tests/test_windows_pytest_result_v1.py",
        "test_sha256":sha(test),
        "context_path":"tests/test_windows_pytest_result_v1.py",
        "context_sha256":sha(test),
        "instruction":"Implement an integer-code-only pytest status "
          "classifier and preserve both log strings unchanged without paid "
          "Gemini API access or any student-facing publication.",
        "selenium_mode":"hydrogen","max_wait_seconds":150,
        "browser_model_claims":1,"paid_api":False,"student_publication":False,
    }
    path=env["backlog"]/"inbox"/(ident+".json")
    path.write_text(json.dumps(job))
    state=env["backlog"]/"state"/ident
    state.mkdir()
    reply=state/"original_model_reply.txt"
    reply.write_bytes(good.encode("utf8"))
    (state/"coding_state.json").write_text(json.dumps({
        "schema_version":1,
        "status":"SOURCE_CANDIDATE_TESTED_NO_PUBLICATION",
        "job_id":ident,"job_sha256":sha(path),
        "model_reply_sha256":sha(reply),
        "candidate_sha256":sha(target),"pytest_exit_code":0,
        "model_claims":1,"model_sends":1,
        "paid_api_requests":0,
        "student_publication_authorized":False,
        "candidate_merged":False,
    }))
    return path


def test_source_test_candidate_gets_real_git_commit_but_not_double_push(env,monkeypatch):
    path=_accepted_original_model(env)
    remote={"sha":None,"pr":None,"pushes":0,"pr_creates":0,"merged":False}
    def command(args,timeout=90):
        if args[:2]==["gh","pr"] and args[2]=="create":
            remote["pr_creates"]+=1
            remote["pr"]={"number":75,"state":"OPEN",
                          "headRefOid":remote["sha"],
                          "baseRefName":"main"}
            return "https://github.com/test/pull/75"
        if "ls-remote" in args:
            return ((remote["sha"]+"\trefs/heads/"+args[-1])
                    if remote["sha"] else "")
        if "push" in args:
            remote["pushes"]+=1
            remote["sha"]=args[-1].split(":")[0]
            return ""
        r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        if r.returncode:raise ValueError(r.stderr)
        return r.stdout.strip()
    def look(branch,sha):
        return remote["pr"]
    def fetch(path):
        if "/actions/runs?" in path:
            return {"workflow_runs":[{"head_sha":remote["sha"],
                                      "status":"in_progress",
                                      "conclusion":None}]}
        assert path.endswith("/commits/main")
        return {"sha":git(env["main"],"rev-parse","HEAD")}
    def pending(*,pr_number):
        raise ValueError("Windows CI still running")
    monkeypatch.setattr(promoter,"exact_ci_inspect",pending)
    a=promoter.promote(job_path=path,root=env["backlog"],
                       main_repo=env["main"],
                       promotions=env["control"]/"promotions",
                       run_cmd=command,fetch=fetch,lookup=look)
    assert a["status"]=="GITHUB_WINDOWS_CI_AWAITING_EVIDENCE"
    assert a["pr_number"]==75
    assert remote["pushes"]==1 and remote["pr_creates"]==1
    b=promoter.promote(job_path=path,root=env["backlog"],
                       main_repo=env["main"],
                       promotions=env["control"]/"promotions",
                       run_cmd=command,fetch=fetch,lookup=look)
    assert b["status"]=="GITHUB_WINDOWS_CI_AWAITING_EVIDENCE"
    assert remote["pushes"]==1 and remote["pr_creates"]==1


def test_uncertain_original_push_is_never_repeated(env):
    path=_accepted_original_model(env)
    remote_calls={"push":0}
    def failpush(args,timeout=90):
        if "ls-remote" in args:return ""
        if "push" in args:
            remote_calls["push"]+=1
            raise ValueError("Network timeout after possible GitHub push")
        r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        if r.returncode:raise ValueError(r.stderr)
        return r.stdout.strip()
    def fetch(path):return {"sha":git(env["main"],"rev-parse","HEAD")}
    opts=dict(job_path=path,root=env["backlog"],
              main_repo=env["main"],
              promotions=env["control"]/"promotions",
              run_cmd=failpush,fetch=fetch)
    first=promoter.promote(**opts)
    second=promoter.promote(**opts)
    assert first["status"]==promoter.REMOTE_HOLD
    assert second["status"]==promoter.REMOTE_HOLD
    assert remote_calls["push"]==1


def test_merged_pr_provenance_rejects_wrong_source_tree():
    desired="1"*40
    merged="2"*40
    def fake(path):
        if path.endswith("/pulls/77"):
            return {"state":"closed","merged_at":"2026-11-27T01:00:00Z",
                    "head":{"sha":desired},"merge_commit_sha":merged}
        if path.endswith("/commits/main"):
            return {"sha":merged}
        if path.endswith("/git/commits/"+merged):
            return {"tree":{"sha":"3"*40},"parents":[{"sha":"5"*40}]}
        if path.endswith("/git/commits/"+desired):
            return {"tree":{"sha":"4"*40},"parents":[{"sha":"5"*40}]}
        raise ValueError(path)
    with pytest.raises(ValueError,match="tree does not equal"):
        deployer.original_main_pr(number=77,expected_head=desired,fetch=fake)


def test_exact_signed_cutover_template_substitutes_only_named_paths(tmp_path):
    file=Path(__file__).parent.parent/"scripts"/(
        "guarded_main_autopromotion_template_v1.ps1")
    target=tmp_path/"guarded_ps_test.ps1"
    replacements={
        "__OLD_REPO__":"post_pr661_main",
        "__NEW_REPO__":"post_pr999_main",
        "__TASK_BEFORE__":"task_before_pr999_cutover.xml",
        "__MAIN_RECEIPT__":"post_pr999_cutover_receipt.json",
    }
    expected=deployer.template(file,replacements,target)
    assert expected==sha(target)
    assert "__NEW_REPO__" not in target.read_text()
    assert "GUARDED_CUTOVER_SUCCESS" in target.read_text()
    assert deployer.template(file,replacements,target)==expected
    with pytest.raises(ValueError,match="changed after admission"):
        target.write_text("tampered")
        deployer.template(file,replacements,target)


def test_controller_held_one_source_continues_another_eligible_lane(env):
    job=env["backlog"]/"inbox"/"g3_caption_held_v1.json"
    job.write_text('{"historical":"no-replay"}')
    state=env["backlog"]/"state"/job.stem
    state.mkdir()
    (state/"coding_state.json").write_text(json.dumps({
        "status":"UNSAFE_MODEL_REPLY_QUARANTINED",
        "model_claims":1}))
    candidates=[]
    def next_job(**kw):
        candidates.append(kw)
        return {"status":"NEW_ELIGIBLE_CODING_JOB_STAGED",
                "job":"different_source_job"}
    r=controller.cycle(
        backlog_root=env["backlog"],control_root=env["control"],
        catalog_path=env["catalog"],
        template_root=Path(__file__).parent.parent/"scripts",
        cutover_root=env["control"],main_repo=env["main"],
        select_fn=next_job)
    assert r["new_job"]["job"]=="different_source_job"
    assert len(candidates)==1
    assert r["jobs"][0]["status"]=="UNSAFE_MODEL_REPLY_QUARANTINED"


def test_newly_staged_job_in_flight_prevents_next_model_send(env):
    job=env["backlog"]/"inbox"/"new_source_queued_v1.json"
    job.write_text('{"schema_version":1}')
    called=[]
    result=controller.cycle(
        backlog_root=env["backlog"],control_root=env["control"],
        catalog_path=env["catalog"],
        template_root=Path(__file__).parent.parent/"scripts",
        cutover_root=env["control"],main_repo=env["main"],
        select_fn=lambda **kw:called.append(kw))
    assert not called
    assert result["jobs"][0]["status"]=="NEW_JOB_AWAITING_FIRST_WORKER_CLAIM"


def _deploy_fixture(tmp_path):
    root=tmp_path/"cutover"
    root.mkdir()
    old=root/"post_pr76_main"
    new=root/"post_pr77_main"
    for path in (old,new):
        (path/"selenium_pipeline").mkdir(parents=True)
        (path/"selenium_pipeline"/"development_continuity_executor_v71.py"
        ).write_bytes(b"PINNED_V71_EXECUTOR_NEVER_REPLACE")
    record=tmp_path/"receipts"
    record.mkdir()
    return root,old,new,record


def _merged_github_fake(number,head,merge):
    def fetch(path):
        if path.endswith("/pulls/"+str(number)):
            return {"state":"closed","merged_at":"2026-11-27T03:00:00Z",
                    "head":{"sha":head},"merge_commit_sha":merge}
        if path.endswith("/commits/main"):
            return {"sha":merge}
        if path.endswith("/git/commits/"+merge):
            return {"tree":{"sha":"e"*40},"parents":[{"sha":"a"*40}]}
        if path.endswith("/git/commits/"+head):
            return {"tree":{"sha":"e"*40},"parents":[{"sha":"a"*40}]}
        raise ValueError(path)
    return fetch


def test_guarded_dual_windows_deploy_with_real_template_and_restart(tmp_path):
    root,old,new,record=_deploy_fixture(tmp_path)
    owners={"daemon":old,"writer":old,"cutovers":0,"writer_calls":0}
    def main_owner(task,path):
        return path==owners["daemon"]
    def writer_owner(task,path):
        return path==owners["writer"]
    def verified_main(manifest,report_root):
        assert manifest.is_file()
        owners["cutovers"]+=1
        owners["daemon"]=new
        return {"status":deployer.COMPLETE}
    def commands(args,timeout=90):
        if args[0]=="git":
            if args[-2:]==["rev-parse","HEAD"]:return "c"*40
            if args[-2:]==["status","--porcelain"]:return ""
        if args[0]=="powershell.exe":
            owners["writer_calls"]+=1
            owners["writer"]=new
            return "PERSISTENT_WRITER_GUARDED_CUTOVER_SUCCESS"
        raise ValueError("unexpected operation: "+str(args))
    options=dict(number=77,head_sha="b"*40,cutover_root=root,
                 current_repo=old,
                 template_root=Path(__file__).parent.parent/"scripts",
                 record_root=record,
                 fetch=_merged_github_fake(77,"b"*40,"c"*40),
                 run_cmd=commands,main_owner=main_owner,
                 writer_owner=writer_owner,cutover_fn=verified_main)
    output=deployer.deploy(**options)
    assert output["status"]=="GUARDED_DEPLOYED"
    assert owners["cutovers"]==1 and owners["writer_calls"]==1
    assert output["paid_api_requests"]==0
    assert deployer.deploy(**options)==output
    assert owners["cutovers"]==1 and owners["writer_calls"]==1


def test_ambiguous_writer_cutover_is_never_reissued_without_owner_proof(tmp_path):
    root,old,new,record=_deploy_fixture(tmp_path)
    owners={"daemon":old,"writer":old,"writer_calls":0}
    def commands(args,timeout=90):
        if args[0]=="git":
            if args[-2:]==["rev-parse","HEAD"]:return "c"*40
            if args[-2:]==["status","--porcelain"]:return ""
        if args[0]=="powershell.exe":
            owners["writer_calls"]+=1
            raise ValueError("Uncertain timeout after a possible task mutation")
        raise ValueError(str(args))
    def guarded(manifest,report_root):
        owners["daemon"]=new
        return {"status":deployer.COMPLETE}
    kwargs=dict(number=77,head_sha="b"*40,
                cutover_root=root,current_repo=old,
                template_root=Path(__file__).parent.parent/"scripts",
                record_root=record,
                fetch=_merged_github_fake(77,"b"*40,"c"*40),
                run_cmd=commands,
                main_owner=lambda t,p:p==owners["daemon"],
                writer_owner=lambda t,p:p==owners["writer"],
                cutover_fn=guarded)
    with pytest.raises(ValueError,match="not independently verified"):
        deployer.deploy(**kwargs)
    assert owners["writer_calls"]==1
    with pytest.raises(ValueError,match="Previous model-writer cutover uncertain"):
        deployer.deploy(**kwargs)
    assert owners["writer_calls"]==1


def test_ci_failure_classified_separately_from_ci_pending():
    head="a"*40
    def fail(path):
        return {"workflow_runs":[{
            "head_sha":head,"status":"completed","conclusion":"failure"}]}
    def wait(path):
        return {"workflow_runs":[{
            "head_sha":head,"status":"in_progress","conclusion":None}]}
    assert promoter._failed_exact_head_ci(head,fail) is True
    assert promoter._failed_exact_head_ci(head,wait) is False


def test_forged_candidate_checkpoint_cannot_replace_original_model_text(env):
    path=_accepted_original_model(env)
    evidence=env["backlog"]/"state"/path.stem
    reply=evidence/"original_model_reply.txt"
    reply.write_text('''"""Different model response."""
def classify_pytest_result(return_code, stdout, stderr):
    return {"passed": True, "return_code": return_code,
            "stdout": stdout, "stderr": stderr}
''')
    saved=evidence/"coding_state.json"
    record=json.loads(saved.read_text())
    record["model_reply_sha256"]=sha(reply)
    saved.write_text(json.dumps(record))
    with pytest.raises(ValueError,match="not reproducible"):
        promoter._original(path,env["backlog"])


def test_catalog_changed_after_original_source_review_holds_without_git(env):
    env["catalog"].write_text(env["catalog"].read_text()+" ")
    with pytest.raises(ValueError,match="SHA differs"):
        selector.select(catalog_path=env["catalog"],
                        backlog_root=env["backlog"],
                        repo_root=env["main"],git=fake_git(env["main"]))
    assert not list((env["backlog"]/"inbox").glob("*.json"))


def test_windows_checkout_retains_exact_approved_catalog_and_spec_sha():
    """Actual cloned Windows worktree must not CRLF-mutate source identities."""
    base=Path(__file__).parent.parent
    spec_dir=base/"development_specs"
    catalog=spec_dir/"approved_source_jobs_v1.json"
    expected="cbec12b6286e0d9225cb8b7ca8933f6c71dd31b21810e4f074f569ac6ca46a7c"
    assert sha(catalog)==expected
    cfg=json.loads(catalog.read_text())
    for row in cfg["jobs"]:
        source=spec_dir/Path(row["spec_path"]).name
        assert sha(source)==row["spec_sha256"]
        attr=git(base,"check-attr","text","--",
                 "development_specs/"+source.name)
        assert attr.endswith("text: unset")


def test_partial_guarded_cutover_restart_preserves_original_repo_identity(env):
    """First task switched, next cycle must NOT call new main its old repo."""
    cutoff=env["control"]
    original=cutoff/"post_pr801_main"
    new=cutoff/"post_pr802_main"
    original.mkdir()
    new.mkdir()
    job=env["backlog"]/"inbox"/"partial_deploy_v1.json"
    job.write_text('{"source_pinned":true}')
    receipt=cutoff/"promotions"/"partial_deploy_v1.json"
    receipt.write_text(json.dumps({
        "status":"MERGED_AWAITING_GUARDED_CUTOVER",
        "pr_number":802,"promotion_commit_sha":"c"*40}))
    observed=[]
    def deploy(**kw):
        observed.append(kw["current_repo"])
        return {"status":("DAEMON_SWITCHED_WRITER_PENDING"
                          if len(observed)==1 else "GUARDED_DEPLOYED")}
    kw=dict(backlog_root=env["backlog"],control_root=cutoff,
            catalog_path=env["catalog"],template_root=cutoff,
            cutover_root=cutoff,deploy_fn=deploy,
            select_fn=lambda **kw:pytest.fail("Unexpected new code job"))
    a=controller.cycle(**kw,main_repo=original)
    assert a["jobs"][0]["status"]=="DAEMON_SWITCHED_WRITER_PENDING"
    assert json.loads(receipt.read_text())["deployment_original_repo"] == str(original)
    b=controller.cycle(**kw,main_repo=new)
    assert b["jobs"][0]["status"]=="GUARDED_DEPLOYED"
    assert observed==[original,original]
    assert json.loads(receipt.read_text())["status"]=="GUARDED_DEPLOYED"
