"""Exact Git ancestry evidence for a prior native CREATE, never new install."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

import pytest

from selenium_pipeline import windows_development_daemon_install_v71 as installer


def git(repo,*args):
    result=subprocess.run(["git","-C",str(repo),*args],
                          check=True,text=True,capture_output=True)
    return result.stdout.strip()


@pytest.fixture
def ancestry(tmp_path):
    repo=tmp_path/"repo"
    repo.mkdir()
    git(repo,"init","-q")
    git(repo,"config","user.name","Isolated Admission Test")
    git(repo,"config","user.email","test@example.invalid")
    (repo/"source.txt").write_text("main original")
    git(repo,"add",".")
    git(repo,"commit","-qm","first verified main")
    first=git(repo,"rev-parse","HEAD")
    (repo/"source.txt").write_text("second source revision")
    git(repo,"commit","-am","second main revision","-q")
    second=git(repo,"rev-parse","HEAD")
    git(repo,"checkout","-qb","separate",first)
    (repo/"source.txt").write_text("incompatible branch")
    git(repo,"commit","-am","divergent candidate","-q")
    divergent=git(repo,"rev-parse","HEAD")
    return repo,first,second,divergent


def check(repo,a,b,policy):
    return installer._preview_git_admission(
        repo=repo,preview_sha=a,current_sha=b,existing_policy=policy)


def test_same_sha_accepted_for_normal_install(ancestry):
    repo,first,second,other=ancestry
    assert check(repo,first,first,"must_be_absent") is True


def test_previous_main_ancestor_accepted_only_for_reconciliation(ancestry):
    repo,first,second,other=ancestry
    assert check(repo,first,second,"must_be_disabled") is True
    assert check(repo,first,second,"must_be_absent") is False


def test_prior_source_cannot_be_created_again_by_mode_confusion(ancestry):
    repo,first,second,other=ancestry
    assert check(repo,first,second,"must_be_disabled_OR_must_be_absent") is False


def test_non_ancestor_reverse_and_diverged_sources_rejected(ancestry):
    repo,first,second,other=ancestry
    assert check(repo,second,first,"must_be_disabled") is False
    assert check(repo,second,other,"must_be_disabled") is False


@pytest.mark.parametrize("bad",["","garbage","e"*64,"../.git/config",None])
def test_malformed_previous_source_hash_refused(ancestry,bad):
    repo,first,second,other=ancestry
    assert check(repo,bad,second,"must_be_disabled") is False


def test_nonexistent_hash_fails_closed(ancestry):
    repo,first,second,other=ancestry
    assert check(repo,"a"*40,second,"must_be_disabled") is False


def test_registry_disables_source_ancestor_bypass_if_tampered(ancestry,tmp_path):
    repo,first,second,other=ancestry
    original=installer.REGISTRY
    cfg=json.loads(original.read_text())
    cfg["partial_create_ancestor_admission"]="IGNORE_SOURCE_GIT_AND_RETRY_CREATE"
    bad=tmp_path/"bad_registry.json"
    bad.write_text(json.dumps(cfg))
    with pytest.raises(ValueError):
        installer.require_install_registry(path=bad)


def test_helper_does_not_modify_git_repo_or_files(ancestry):
    repo,first,second,other=ancestry
    before=git(repo,"status","--porcelain")
    assert check(repo,first,second,"must_be_disabled")
    assert git(repo,"status","--porcelain")==before
