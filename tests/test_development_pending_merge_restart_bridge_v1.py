"""No-network fault injection of the exact CI-merged old-daemon bridge."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from selenium_pipeline import development_pending_merge_restart_bridge_v1 as bridge
from selenium_pipeline.recovery_registry import lookup_mechanism

OLD = "a" * 40
NEW = "b" * 40
HEAD = "c" * 40
TREE = "d" * 40
BRANCH = "auto/promote_g2_two_pass_source_provenance_v1_abcd1234"
PREFIX = "repos/tlyoon/MicroGen_AI_Web/"


@pytest.fixture
def source(tmp_path):
    old = tmp_path / "RECONCILE_20261125" / "post_pr675_main"
    old.mkdir(parents=True)
    root = tmp_path / "AUTONOMOUS_CODE_PROMOTION_V1_20261127"
    (root / "promotions").mkdir(parents=True)
    state = {
        "schema_version": 1,
        "status": "MERGED_AWAITING_GUARDED_CUTOVER",
        "job_id": "g2_two_pass_source_provenance_v1",
        "pr_number": 676,
        "branch": BRANCH,
        "promotion_base_sha": OLD,
        "promotion_commit_sha": HEAD,
        "merge_commit_sha": NEW,
        "merge_claimed": True,
        "model_sends": 0,
        "paid_api_requests": 0,
        "student_publication_authorized": False,
    }
    path = root / "promotions" / (state["job_id"] + ".json")
    path.write_text(json.dumps(state), encoding="utf8")
    payload = {
        PREFIX + "pulls/676": {
            "number": 676, "state": "closed", "merged_at": "2026-11-27T10:00:00Z",
            "merge_commit_sha": NEW, "created_at": "2026-11-27T09:40:00Z",
            "head": {"sha": HEAD, "ref": BRANCH,
                     "repo": {"full_name": "tlyoon/MicroGen_AI_Web"}},
            "base": {"ref": "main"},
        },
        PREFIX + "commits/main": {"sha": NEW},
        PREFIX + "git/commits/" + NEW: {
            "tree": {"sha": TREE}, "parents": [{"sha": OLD}]},
        PREFIX + "git/commits/" + HEAD: {"tree": {"sha": TREE}},
        PREFIX + ("actions/runs?head_sha=" + HEAD
                  + "&event=pull_request&per_page=100"): {
            "total_count": 1,
            "workflow_runs": [{
                "id": 1234, "run_attempt": 1,
                "workflow_id": 5678,
                "created_at": "2026-11-27T09:41:00Z",
                "head_sha": HEAD, "head_branch": BRANCH,
                "event": "pull_request",
                "path": bridge.WORKFLOW_PATH,
                "name": bridge.WORKFLOW_NAME,
                "status": "completed", "conclusion": "success",
            }],
        },
        PREFIX + "actions/runs/1234/attempts/1/jobs?per_page=100": {
            "total_count": 2,
            "jobs": [
                {"name": name, "head_sha": HEAD,
                 "workflow_name": bridge.WORKFLOW_NAME,
                 "status": "completed", "conclusion": "success",
                 "run_id": 1234}
                for name in sorted(bridge.REQUIRED_WINDOWS_JOBS)]
        },
    }
    def runner(argv, *, capture_output, text, timeout):
        if argv[:3] == ["git", "-C", str(old)]:
            if argv[-2:] == ["rev-parse", "HEAD"]:
                return SimpleNamespace(returncode=0, stdout=OLD + "\n")
            if argv[-2:] == ["status", "--porcelain"]:
                return SimpleNamespace(returncode=0, stdout="")
        if argv[:2] == ["gh", "api"] and argv[-2:] == ["--jq", ".sha"]:
            return SimpleNamespace(returncode=0, stdout=NEW + "\n")
        return SimpleNamespace(returncode=1, stdout="")
    def fetch(path):
        return copy.deepcopy(payload[path])
    return {"root": root, "old": old, "payload": payload, "fetch": fetch,
            "runner": runner, "file": path, "state": state}


def call(src, *, fetch=None, runner=None):
    return bridge.verify(old_repo=src["old"], controller_root=src["root"],
                         fetch=fetch or src["fetch"],
                         runner=runner or src["runner"])


def test_registered_recovery_and_proved_exact_ci_merger(source):
    assert lookup_mechanism(bridge.KIND, bridge.SIGNATURE) == bridge.MECHANISM
    result = call(source)
    assert result["status"] == bridge.STATUS
    assert result["old_sha"] == OLD and result["merged_sha"] == NEW
    assert result["original_pr_number"] == 676
    assert result["exact_head_windows_ci_run_id"] == 1234
    assert result["provider_sends"] == result["paid_api_requests"] == 0
    assert result["student_publication_authorized"] is False


def test_no_cached_or_old_worktree_reentry_without_claim(source):
    source["file"].unlink()
    with pytest.raises(ValueError, match="inventory"):
        call(source)


def test_original_github_merge_provenance_and_tree_tamper_fail(source):
    for changed, value in (
        ("merge_commit_sha", OLD),
        ("merge_claimed", False),
        ("promotion_base_sha", NEW),
        ("student_publication_authorized", True),
        ("paid_api_requests", 1),
        ("model_sends", 1),
    ):
        old = dict(source["state"])
        old[changed] = value
        source["file"].write_text(json.dumps(old))
        with pytest.raises(ValueError):
            call(source)
    source["file"].write_text(json.dumps(source["state"]))
    original = source["payload"][PREFIX + "git/commits/" + NEW]["tree"]
    source["payload"][PREFIX + "git/commits/" + NEW]["tree"] = {"sha": OLD}
    with pytest.raises(ValueError, match="tree or parent"):
        call(source)
    source["payload"][PREFIX + "git/commits/" + NEW]["tree"] = original


def test_source_changed_or_git_main_identity_unavailable_fails(source):
    def bad_runner(args, **kwargs):
        answer = source["runner"](args, **kwargs)
        if args[-2:] == ["status", "--porcelain"]:
            return SimpleNamespace(returncode=0, stdout=" M tampered.py")
        return answer
    with pytest.raises(ValueError, match="not clean"):
        call(source, runner=bad_runner)


@pytest.mark.parametrize("mutation", [
    ("conclusion", "failure"),
    ("status", "in_progress"),
    ("head_sha", OLD),
])
def test_stale_failed_or_wrong_sha_ci_does_not_unlock_old_daemon(
        source, mutation):
    key = PREFIX + "actions/runs?head_sha=" + HEAD + "&event=pull_request&per_page=100"
    source["payload"][key]["workflow_runs"][0][mutation[0]] = mutation[1]
    with pytest.raises(ValueError):
        call(source)


def test_unverified_second_workflow_fails(source):
    key = PREFIX + "actions/runs?head_sha=" + HEAD + "&event=pull_request&per_page=100"
    listing = source["payload"][key]
    other = dict(listing["workflow_runs"][0])
    other.update(id=2244, workflow_id=2245, path=".github/workflows/other.yml",
                 name="Unrelated failure", conclusion="failure")
    listing["workflow_runs"].append(other)
    listing["total_count"] += 1
    with pytest.raises(ValueError, match="other exact-source"):
        call(source)


def test_missing_ci_job_and_duplicate_claim_fails(source):
    jobs = source["payload"][
        PREFIX + "actions/runs/1234/attempts/1/jobs?per_page=100"]
    jobs["jobs"][0]["conclusion"] = "failure"
    with pytest.raises(ValueError, match="Windows CI job"):
        call(source)
    jobs["jobs"][0]["conclusion"] = "success"
    row = dict(source["state"])
    row["job_id"] = "g3_highlight_speech_timing_v1"
    (source["root"] / "promotions" / (row["job_id"] + ".json")).write_text(
        json.dumps(row))
    with pytest.raises(ValueError, match="exactly one"):
        call(source)


def test_no_original_model_send_mutations_or_files_written(source):
    before = source["file"].read_bytes()
    assert call(source)["status"] == bridge.STATUS
    assert source["file"].read_bytes() == before
