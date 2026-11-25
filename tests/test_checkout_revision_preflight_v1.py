"""Checkout-reconciliation acceptance and fault-injection tests."""
import subprocess
from pathlib import Path
import pytest
from selenium_pipeline.checkout_revision_preflight_v1 import audit, stage


def git(*args, cwd=None):
    p = subprocess.run(["git", *map(str, args)], cwd=cwd,
                       check=True, capture_output=True, text=True)
    return p.stdout.strip()


@pytest.fixture
def twin(tmp_path):
    origin=tmp_path/"origin.git"
    first=tmp_path/"first"
    git("init", "--bare", origin)
    git("clone", origin, first)
    git("config", "user.email", "qa@example.invalid", cwd=first)
    git("config", "user.name", "Test", cwd=first)
    git("checkout", "-b", "main", cwd=first)
    (first/"proof.txt").write_text("one")
    git("add", "proof.txt", cwd=first)
    git("commit", "-m", "one", cwd=first)
    git("push", "-u", "origin", "main", cwd=first)
    return origin,first


def test_synced_clean(twin):
    origin, first=twin
    actual=audit(first,expected_origin=str(origin))
    assert actual["status"]=="SYNCED_CLEAN"
    assert actual["safe_to_cutover"]


def test_stale_clean_without_checkout_mutation(twin):
    origin, first=twin
    stale=first.parent/"stale"
    git("clone","--branch","main",origin,stale)
    (first/"proof.txt").write_text("two")
    git("commit","-am","two",cwd=first)
    git("push",cwd=first)
    before=git("rev-parse","HEAD",cwd=stale)
    state=audit(stale,expected_origin=str(origin))
    assert state["status"]=="STALE_CLEAN"
    assert not state["safe_to_cutover"]
    assert git("rev-parse","HEAD",cwd=stale)==before


def test_dirty_preserved_even_when_upstream_matches(twin):
    origin,first=twin
    (first/"proof.txt").write_text("valuable local edits")
    state=audit(first,expected_origin=str(origin))
    assert state["status"]=="DIRTY_PRESERVE"
    assert not state["safe_to_cutover"]
    assert (first/"proof.txt").read_text()=="valuable local edits"


def test_unknown_remote_fails_closed(twin):
    origin,first=twin
    state=audit(first,expected_origin="https://github.com/wrong/other.git")
    assert state["status"]=="UNVERIFIED"
    assert not state["safe_to_cutover"]


def test_stage_refuses_existing_path_without_mutation(twin):
    origin,first=twin
    target=first.parent/"exists"
    target.mkdir()
    (target/"important").write_text("preserve")
    state=stage(first,target,expected_origin=str(origin))
    assert state["stage_status"]=="REFUSED_EXISTING_DESTINATION"
    assert (target/"important").read_text()=="preserve"



def test_stage_clean_new_destination(twin):
    origin, first=twin
    destination=first.parent/"fresh"
    result=stage(first,destination,expected_origin=str(origin))
    assert result["stage_status"]=="STAGED_CLEAN"
    assert git("rev-parse","HEAD",cwd=destination)==git("rev-parse","HEAD",cwd=first)
