"""Source-/Windows-CI-bound forward GitHub main cutover fault injection."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from selenium_pipeline import development_ci_merged_main_autocutover_v1 as source
from selenium_pipeline import development_autonomous_code_loop_v1 as controller
from selenium_pipeline.recovery_registry import lookup_mechanism

OLD = "a" * 40
PREVIOUS = "b" * 40
LATEST = "c" * 40
HEAD = "d" * 40
BRANCH = "feature/approved_new_g3"
PREFIX = "repos/tlyoon/MicroGen_AI_Web/"


@pytest.fixture
def env(tmp_path):
    parent = tmp_path / "RECONCILE_20261125"
    old = parent / "post_pr684_main"
    (old / "scripts").mkdir(parents=True)
    ctl = tmp_path / "AUTONOMOUS_CODE_PROMOTION_V1_20261127"
    ctl.mkdir()
    back = tmp_path / "LONG_HORIZON_CODE_AUTHOR_V1_20261126"
    back.mkdir()
    hb = back / "worker_heartbeat.json"
    hb.write_text(json.dumps({
        "jobs": [{"job": "old.json", "status": "UNSAFE_MODEL_REPLY_QUARANTINED",
                  "paid_api_requests": 0}],
        "student_publication_authorized": False,
        "new_paid_api_requests": 0,
    }))
    result = {
        PREFIX + "commits/main": {"sha": LATEST},
        PREFIX + "compare/" + OLD + "..." + LATEST: {
            "status": "ahead", "ahead_by": 2, "behind_by": 0,
            "commits": [{"sha": PREVIOUS}, {"sha": LATEST}]},
        PREFIX + "git/commits/" + LATEST: {
            "parents": [{"sha": PREVIOUS}]},
    }
    pr = {
        "number": 685, "state": "closed", "merged_at": "2026-11-28T09:05:00Z",
        "merge_commit_sha": LATEST,
        "base": {"ref": "main"},
        "head": {"sha": HEAD, "ref": BRANCH,
                 "repo": {"full_name": source.REPO}},
    }
    def git(repo, *args):
        assert repo == old
        return OLD if args == ("rev-parse", "HEAD") else ""
    def fetch(path):
        return result[path]
    return dict(old=old, control=ctl, cut=parent, back=back,
                hb=hb, result=result, pr=pr, git=git, fetch=fetch)


def verify(env, **kwargs):
    return source.verify(
        old_repo=env["old"], controller_root=env["control"],
        fetch=kwargs.get("fetch", env["fetch"]),
        pull_list=kwargs.get("pull_list", lambda x:[env["pr"]]),
        git=kwargs.get("git", env["git"]),
        ci=kwargs.get("ci", lambda **x:12345),
    )


def test_registry_required_and_bounded_new_main_ci_proof(env):
    assert lookup_mechanism(source.KIND,source.SIGNATURE)==source.MECHANISM
    actual=verify(env)
    assert actual["status"]=="LATEST_MAIN_CI_CERTIFIED_GUARDED_CUTOVER_ELIGIBLE"
    assert actual["old_sha"]==OLD and actual["merged_sha"]==LATEST
    assert actual["pr_number"]==685 and actual["head_sha"]==HEAD
    assert actual["forward_commits"]==2
    assert actual["provider_sends"]==actual["paid_api_requests"]==0
    assert actual["student_publication_authorized"] is False


def test_existing_current_main_is_noop_no_ci_or_pr_query(env):
    env["result"][PREFIX + "commits/main"]["sha"]=OLD
    result=verify(env, pull_list=lambda _:pytest.fail("must not query pull list"),
                  ci=lambda **_:pytest.fail("must not recheck CI on current source"))
    assert result["status"]=="EXACT_PROTECTED_MAIN_CURRENT"
    assert result["provider_sends"]==0


def test_different_lineage_and_changed_main_fail_closed(env):
    path=PREFIX + "compare/" + OLD + "..." + LATEST
    for name,wrong in (("status","diverged"),("behind_by",1),
                       ("ahead_by",51),("commits",[])):
        original=env["result"][path][name]
        env["result"][path][name]=wrong
        with pytest.raises(ValueError):
            verify(env)
        env["result"][path][name]=original
    count=[0]
    def changed(path):
        if path == PREFIX + "commits/main":
            count[0]+=1
            return {"sha": LATEST if count[0]==1 else PREVIOUS}
        return env["fetch"](path)
    with pytest.raises(ValueError,match="moved"):
        verify(env,fetch=changed)


def test_merged_pr_identity_ambiguous_or_missing(env):
    for fake in ([], [env["pr"],env["pr"]],
                 [dict(env["pr"], merged_at=None)],
                 [dict(env["pr"], merge_commit_sha=OLD)],
                 [dict(env["pr"], head={"repo":{"full_name":"malicious/repo"}})]):
        with pytest.raises(ValueError, match="exact merged"):
            verify(env,pull_list=lambda _:fake)


def test_missing_or_failed_ci_never_authorizes_cutover(env):
    with pytest.raises(ValueError,match="Windows CI"):
        verify(env, ci=lambda **_:0)
    def failing(**kwargs):
        assert kwargs["pr_number"]==685
        assert kwargs["head_sha"]==HEAD
        assert kwargs["base_sha"]==PREVIOUS
        raise ValueError("Independent Windows CI failed")
    with pytest.raises(ValueError,match="failed"):
        verify(env,ci=failing)


def test_dirty_old_checkout_fails(env):
    def dirty(_, *args):
        return OLD if args==("rev-parse","HEAD") else " M forged.py"
    with pytest.raises(ValueError,match="not clean"):
        verify(env,git=dirty)


def _certified():
    return {"status":"LATEST_MAIN_CI_CERTIFIED_GUARDED_CUTOVER_ELIGIBLE",
            "old_sha":OLD,"merged_sha":LATEST,"pr_number":685,
            "head_sha":HEAD,"provider_sends":0,"paid_api_requests":0,
            "student_publication_authorized":False}


def test_original_guarded_deployment_only_once_with_both_running_owners(env):
    calls=[]
    def owner(task,old):
        calls.append(("owner",task,str(old)))
        return True
    def deployed(**kwargs):
        calls.append(("deploy",kwargs))
        assert kwargs["number"]==685 and kwargs["head_sha"]==HEAD
        assert kwargs["current_repo"]==env["old"]
        assert kwargs["template_root"]==env["old"]/"scripts"
        return {"status":"GUARDED_DEPLOYED","deployed_main_sha":LATEST,
                "student_publication_authorized":False}
    result=source.catch_up(
        old_repo=env["old"],controller_root=env["control"],
        cutover_root=env["cut"],template_root=env["old"]/"scripts",
        verifier=lambda **_ :_certified(),deployed=deployed,owner=owner)
    assert result["status"]=="CERTIFIED_MAIN_SOURCE_AUTO_CUTOVER_DEPLOYED"
    assert len([x for x in calls if x[0]=="owner"])==2
    assert len([x for x in calls if x[0]=="deploy"])==1


def test_unsettled_model_send_never_interrupted_by_source_update(env):
    state=json.loads(env["hb"].read_text())
    state["jobs"][0]["status"]="SEND_CLAIMED_UNCERTAIN"
    env["hb"].write_text(json.dumps(state))
    called=[]
    with pytest.raises(ValueError,match="safely quiescent"):
        source.catch_up(
            old_repo=env["old"],controller_root=env["control"],
            cutover_root=env["cut"],template_root=env["old"]/"scripts",
            verifier=lambda **_ :_certified(),
            deployed=lambda **_:called.append("unsafe"),
            owner=lambda *args:True)
    assert called==[]


def test_wrong_native_owner_never_triggers_guards(env):
    called=[]
    with pytest.raises(ValueError,match="not independently attested"):
        source.catch_up(
            old_repo=env["old"],controller_root=env["control"],
            cutover_root=env["cut"],template_root=env["old"]/"scripts",
            verifier=lambda **_ :_certified(),
            deployed=lambda **_:called.append("unsafe"),
            owner=lambda *args:False)
    assert called==[]


def test_prod_controller_dispatches_verified_source_sync_before_new_job(
        env, monkeypatch):
    (env["back"]/"inbox").mkdir()
    (env["control"]/"promotions"/"worktrees").mkdir(parents=True)
    catalog=env["control"]/"approved.json"
    catalog.write_text("{}")
    monkeypatch.setattr(controller, "_owner_repo", lambda:env["old"])
    called=[]
    def sync(**kwargs):
        called.append(kwargs)
        return {"status":"CERTIFIED_MAIN_SOURCE_AUTO_CUTOVER_DEPLOYED",
                "old_sha":OLD,"merged_sha":LATEST,
                "student_publication_authorized":False}
    def forbidden(**kwargs):
        raise AssertionError("Do not start a source-coding job on stale main")
    result=controller.cycle(
        backlog_root=env["back"],control_root=env["control"],
        catalog_path=catalog,template_root=env["old"]/"scripts",
        cutover_root=env["cut"],main_repo=None,
        source_sync_fn=sync,select_fn=forbidden)
    assert result["source_sync"]["status"]=="CERTIFIED_MAIN_SOURCE_AUTO_CUTOVER_DEPLOYED"
    assert len(called)==1 and called[0]["old_repo"]==env["old"]


def test_prod_controller_holds_unverified_source_without_new_send(env, monkeypatch):
    (env["back"]/"inbox").mkdir()
    (env["control"]/"promotions"/"worktrees").mkdir(parents=True)
    catalog=env["control"]/"approved.json"
    catalog.write_text("{}")
    monkeypatch.setattr(controller,"_owner_repo",lambda:env["old"])
    def refused(**kwargs):
        raise ValueError("No exact-head Windows CI for later PR")
    result=controller.cycle(
        backlog_root=env["back"],control_root=env["control"],
        catalog_path=catalog,template_root=env["old"]/"scripts",
        cutover_root=env["cut"],main_repo=None,source_sync_fn=refused,
        select_fn=lambda **_:pytest.fail("model job must not be staged"))
    assert result["source_sync"]["status"]=="CERTIFIED_MAIN_SOURCE_CUTOVER_HELD"
    assert result["new_model_sends"]==0
    assert result["student_publication_authorized"] is False
