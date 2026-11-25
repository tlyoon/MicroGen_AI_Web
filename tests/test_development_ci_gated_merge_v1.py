"""Exact-commit GitHub CI gate must fail closed on stale or missing evidence."""
from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
import pytest

from selenium_pipeline import development_ci_gated_merge_v1 as gate


class GitHubFixture:
    def __init__(self):
        self.h="a"*40
        self.main="b"*40
        self.branch="fix/microgen-ci-merge"
        self.pr={
            "number":654,"state":"open","merged_at":None,"draft":False,
            "mergeable":True,"created_at":"2026-11-25T13:00:00Z",
            "head":{"sha":self.h,"ref":self.branch,
                    "repo":{"full_name":gate.REPO}},
            "base":{"sha":self.main,"ref":"main",
                    "repo":{"full_name":gate.REPO}}}
        self.main_obj={"name":"main","commit":{"sha":self.main}}
        self.workflow={"id":44,"path":gate.WORKFLOW_PATH,
                       "name":gate.WORKFLOW_NAME,"state":"active"}
        self.runs=[{
            "id":94,"workflow_id":44,"path":gate.WORKFLOW_PATH,
            "name":gate.WORKFLOW_NAME,"head_sha":self.h,
            "head_branch":self.branch,"event":"pull_request",
            "repository":{"full_name":gate.REPO},
            "head_repository":{"full_name":gate.REPO},
            "created_at":"2026-11-25T13:01:00Z","run_attempt":1,
            "status":"completed","conclusion":"success"}]
        self.jobs=[
            {"id":101,"name":"offline-regressions","status":"completed",
             "conclusion":"success","head_sha":self.h,"run_id":94,
             "workflow_name":gate.WORKFLOW_NAME},
            {"id":102,"name":"Full offline suite (Windows, Python 3.12)",
             "status":"completed","conclusion":"success",
             "head_sha":self.h,"run_id":94,
             "workflow_name":gate.WORKFLOW_NAME}]
        self.calls=[]
        self.check_count=0
        self.merges=[]

    def fetch(self,path):
        self.calls.append(path)
        if path==f"repos/{gate.REPO}/pulls/654":
            self.check_count+=1
            return copy.deepcopy(self.pr)
        if path==f"repos/{gate.REPO}/branches/main":
            return copy.deepcopy(self.main_obj)
        if path==f"repos/{gate.REPO}/actions/workflows/microgen-reliability-tests.yml":
            return copy.deepcopy(self.workflow)
        if path.startswith(f"repos/{gate.REPO}/actions/runs?"):
            return {"workflow_runs":copy.deepcopy(self.runs),
                    "total_count":len(self.runs)}
        if path.startswith(f"repos/{gate.REPO}/actions/runs/94/attempts/"):
            return {"jobs":copy.deepcopy(self.jobs),
                    "total_count":len(self.jobs)}
        raise AssertionError("Unexpected external API read "+path)

    def merge(self,n,sha):
        self.merges.append((n,sha))
        self.pr.update(state="closed",merged_at="2026-11-25T13:15:00Z",
                       merge_commit_sha="f"*40)


def test_registered_exact_head_gate_and_windows_workflow_on_all_prs():
    from selenium_pipeline.recovery_registry import lookup_mechanism
    assert lookup_mechanism(gate.KIND,gate.SIGNATURE)==gate.MECHANISM
    wf=Path(__file__).resolve().parents[1]/".github/workflows/microgen-reliability-tests.yml"
    txt=wf.read_text("utf8").split("on:",1)[1].split("jobs:",1)[0]
    assert "pull_request:" in txt
    assert "paths:" not in txt
    assert "runs-on: windows-latest" in wf.read_text("utf8")
    assert "ubuntu" not in wf.read_text("utf8").casefold()


def test_realistic_successful_exact_head_preflight_reads_all_required_jobs():
    g=GitHubFixture()
    result=gate.gate(pr_number=654,fetch=g.fetch)
    assert result["status"]==gate.PASS
    assert result["head_sha"]==g.h
    assert result["workflow_run_id"]==94
    assert len(result["verified_jobs"])==2
    assert g.merges==[]
    assert g.check_count==1
    assert result["student_publication_authorized"] is False


def test_realistic_guarded_merge_checks_evidence_twice_and_pins_head():
    g=GitHubFixture()
    result=gate.gate(pr_number=654,fetch=g.fetch,
                     perform_merge=True,merge_fn=g.merge)
    assert result["status"]==gate.MERGED
    assert g.merges==[(654,g.h)]
    assert g.check_count==3
    assert result["automatic_merge_used"] is False


@pytest.mark.parametrize("mode",[
    "pending_run","failed_run","cancelled_run","missing_run",
    "wrong_workflow","wrong_branch","old_head_run","in_progress_rerun",
    "no_required_job","failed_job","pending_job","cancelled_extra_job",
    "mismatched_job_sha","wrong_job_run","wrong_job_workflow",
    "duplicate_job","truncated_jobs","stale_base","mismatched_repo",
    "draft_pr","merged_pr","unmergeable","old_ci_before_pr",
])
def test_never_merge_when_gate_not_proven(mode):
    g=GitHubFixture()
    if mode=="pending_run":g.runs[0]["status"]="in_progress"
    if mode=="failed_run":g.runs[0]["conclusion"]="failure"
    if mode=="cancelled_run":g.runs[0]["conclusion"]="cancelled"
    if mode=="missing_run":g.runs=[]
    if mode=="wrong_workflow":g.runs[0]["workflow_id"]=88
    if mode=="wrong_branch":g.runs[0]["head_branch"]="other"
    if mode=="old_head_run":g.runs[0]["head_sha"]="c"*40
    if mode=="in_progress_rerun":
        g.runs[0]["run_attempt"]=2
        g.runs[0]["status"]="in_progress"
    if mode=="no_required_job":g.jobs[1]["name"]="unknown-job"
    if mode=="failed_job":g.jobs[0]["conclusion"]="failure"
    if mode=="pending_job":g.jobs[0]["status"]="in_progress"
    if mode=="cancelled_extra_job":
        g.jobs.append(dict(g.jobs[0],id=123,name="third-required-by-workflow",
                           conclusion="cancelled"))
    if mode=="mismatched_job_sha":g.jobs[0]["head_sha"]="d"*40
    if mode=="wrong_job_run":g.jobs[0]["run_id"]=222
    if mode=="wrong_job_workflow":g.jobs[0]["workflow_name"]="Evil CI"
    if mode=="duplicate_job":g.jobs[1]["name"]=g.jobs[0]["name"]
    if mode=="truncated_jobs":
        real=g.fetch
        def broken(path):
            result=real(path)
            if "attempts/" in path:result["total_count"]=3
            return result
        g.fetch=broken
    if mode=="stale_base":g.main_obj["commit"]["sha"]="d"*40
    if mode=="mismatched_repo":g.pr["head"]["repo"]["full_name"]="stranger/evil"
    if mode=="draft_pr":g.pr["draft"]=True
    if mode=="merged_pr":g.pr.update(state="closed",merged_at="date")
    if mode=="unmergeable":g.pr["mergeable"]=None
    if mode=="old_ci_before_pr":g.runs[0]["created_at"]="2026-11-24T13:00:00Z"
    with pytest.raises((ValueError,TypeError)):
        gate.gate(pr_number=654,fetch=g.fetch,perform_merge=True,merge_fn=g.merge)
    assert not g.merges


def test_older_success_cannot_mask_latest_failed_or_pending_attempt():
    g=GitHubFixture()
    newer=dict(g.runs[0],id=97,created_at="2026-11-25T13:02:00Z",
               status="in_progress",conclusion=None)
    g.runs.append(newer)
    with pytest.raises(ValueError,match="pending or failed"):
        gate.inspect(pr_number=654,fetch=g.fetch)


def test_head_mutated_between_two_validations_cannot_merge():
    g=GitHubFixture()
    original=g.fetch
    def switch(path):
        if path.endswith("/pulls/654") and g.check_count==1:
            g.pr["head"]["sha"]="f"*40
        return original(path)
    with pytest.raises(ValueError):
        gate.gate(pr_number=654,fetch=switch,merge_fn=g.merge,
                  perform_merge=True)
    assert g.merges==[]


def test_ci_run_purpose_and_workflow_path_identity_are_strict():
    g=GitHubFixture()
    g.runs[0]["path"]=".github/workflows/forged.yml"
    with pytest.raises(ValueError,match="No exact"):
        gate.inspect(pr_number=654,fetch=g.fetch)


def test_cli_merge_uses_git_hub_commit_cas_without_auto_admin(monkeypatch):
    seen=[]
    def dummy(args,**kwargs):
        seen.append(args)
        return subprocess.CompletedProcess(args,0,stdout="merged",stderr="")
    monkeypatch.setattr(gate.subprocess,"run",dummy)
    gate.issue_merge(654,"a"*40)
    assert len(seen)==1
    assert "--squash" in seen[0]
    assert "--match-head-commit" in seen[0]
    assert "--auto" not in seen[0] and "--admin" not in seen[0]
    assert seen[0][-1]=="a"*40


def test_write_audit_receipt_is_atomic_and_immutable_to_source(tmp_path):
    data=gate.gate(pr_number=654,fetch=GitHubFixture().fetch)
    path=tmp_path/"audit.json"
    gate.persist(path,data)
    assert json.loads(path.read_text())==data
    assert not path.with_suffix(".pending").exists()
    if hasattr(path,"symlink_to"):
        link=tmp_path/"external.json"
        try:link.symlink_to(path)
        except OSError:return
        with pytest.raises(ValueError,match="redirected"):
            gate.persist(link,data)


def test_malformed_number_is_held():
    with pytest.raises(ValueError):
        gate.inspect(pr_number=-1,fetch=GitHubFixture().fetch)



def test_unrelated_relevant_workflow_failure_blocks_merge():
    g=GitHubFixture()
    g.runs.append(dict(g.runs[0],id=123,workflow_id=777,
                       path=".github/workflows/source-adjacent-output-tests.yml",
                       name="Source-adjacent publication tests",
                       conclusion="failure"))
    with pytest.raises(ValueError,match="Another applicable"):
        gate.gate(pr_number=654,fetch=g.fetch,perform_merge=True,merge_fn=g.merge)
    assert not g.merges


def test_latest_same_head_other_workflow_success_supersedes_old_failure():
    g=GitHubFixture()
    old=dict(g.runs[0],id=123,workflow_id=777,
             path=".github/workflows/source-adjacent-output-tests.yml",
             name="Source-adjacent publication tests",conclusion="failure")
    new=dict(old,id=124,created_at="2026-11-25T13:03:00Z",
             conclusion="success",run_attempt=2)
    g.runs.extend([old,new])
    result=gate.inspect(pr_number=654,fetch=g.fetch)
    assert result["status"]==gate.PASS


def test_new_pending_other_workflow_does_not_get_ignored():
    g=GitHubFixture()
    g.runs.append(dict(g.runs[0],id=123,workflow_id=777,
                       path=".github/workflows/source-adjacent-output-tests.yml",
                       name="Source-adjacent publication tests",
                       status="in_progress",conclusion=None))
    with pytest.raises(ValueError,match="Another applicable"):
        gate.inspect(pr_number=654,fetch=g.fetch)


def test_failed_github_merge_surfaces_bounded_redacted_failure_reason(monkeypatch):
    def fake(args,**kw):
        return subprocess.CompletedProcess(
            args,1,stdout="",stderr="GraphQL: Branch protection pending ghp_"
            +"A"*40+"; retry after status")
    monkeypatch.setattr(gate.subprocess,"run",fake)
    with pytest.raises(ValueError,match="GitHub exact-head merge refused") as error:
        gate.issue_merge(654,"a"*40)
    assert "GraphQL" in str(error.value)
    assert "ghp_" not in str(error.value)
    assert len(str(error.value))<310
