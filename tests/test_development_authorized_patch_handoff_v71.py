"""Offline native-Git tests for Codex-independent, bounded code handoff."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from selenium_pipeline.development_authorized_patch_handoff_v71 import run
from selenium_pipeline.recovery_registry import lookup_mechanism


def _git(root, *args):
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, check=True,
    )
    return p.stdout.strip()


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def job_factory(root: Path, *, content=None, destination="tests/test_written.py",
                old_sha=None):
    repo = root / "worktree"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "local-microgen-test@example.invalid")
    _git(repo, "config", "user.name", "MicroGen offline tests")
    (repo / "tests").mkdir()
    (repo / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n.pytest_cache/\n", encoding="utf-8")
    (repo / "tests" / "test_existing.py").write_text(
        "def test_existing():\n    assert 2 * 3 == 6\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "tests/test_existing.py")
    _git(repo, "commit", "-m", "base")
    _git(repo, "switch", "-c", "feature/verified-writer-test")
    base_sha = _git(repo, "rev-parse", "HEAD")
    if content is None:
        content = b"def test_added():\n    assert 2 + 5 == 7\n"
    payload = root / "payload"
    payload.mkdir()
    digest = _digest(content)
    (payload / (digest + ".blob")).write_bytes(content)
    job = {
        "schema_version": 1, "project": "MicroGen_AI_Web",
        "job_id": "safe_test_job", "base_sha": base_sha,
        "branch": "feature/verified-writer-test", "authorized": True,
        "source": "trusted_connected_coding_session",
        "files": [{"path": destination, "old_sha256": old_sha,
                   "new_sha256": digest}],
        "tests": [destination if destination.startswith("tests/")
                  else "tests/test_existing.py"],
    }
    file = root / "request.json"
    file.write_text(json.dumps(job), encoding="utf-8")
    state = root / "checkpoint"
    return repo, file, payload, state


def _run(bundle, **kwargs):
    repo, file, payload, state = bundle
    return run(job_path=file, payload_dir=payload,
               repo=repo, state_dir=state, **kwargs)


def test_exact_registered_alternate_no_host_bypass():
    assert lookup_mechanism(
        "code_authoring_handoff",
        "HOST_READONLY_USE_AUTHORIZED_ATOMIC_CODE_HANDOFF",
    ) == "ADMIT_PINNED_EXTERNAL_CODE_BLOBS_TEST_IN_ISOLATED_WORKTREE"


def test_actual_git_file_written_and_tested_no_model_or_pr(tmp_path):
    bundle = job_factory(tmp_path)
    (tmp_path / "microgen_coding_cli_policy_block_v71.json").write_text(
        '{"status":"CODING_CLI_EFFECTIVE_READONLY_BLOCKED"}', encoding="utf-8")
    got = _run(bundle)
    assert got["status"] == "VERIFIED_CANDIDATE_NO_PUBLICATION"
    assert got["model_requests"] == 0
    assert got["codex_host_denial_cleared"] is False
    assert got["candidate_pr_pushed"] is False
    assert got["student_release"] is False
    assert (bundle[0] / "tests/test_written.py").is_file()
    assert "test_written.py" in _git(bundle[0], "status", "--short")
    assert _run(bundle) == got  # restarts do not re-author or Send


def test_crash_after_atomic_write_recovers_without_duplicate(tmp_path):
    bundle = job_factory(tmp_path)
    with pytest.raises(RuntimeError, match="INJECTED_POST_WRITE_CRASH"):
        _run(bundle, fault_after_write=True)
    marker = bundle[0] / "tests/test_written.py"
    assert marker.is_file()
    old_hash = _digest(marker.read_bytes())
    state = json.loads((bundle[3] / "code_handoff_state.json").read_text())
    assert state["status"] == "APPLYING"
    got = _run(bundle)
    assert got["status"] == "VERIFIED_CANDIDATE_NO_PUBLICATION"
    assert _digest(marker.read_bytes()) == old_hash


def test_in_place_changed_manifest_denied_without_modification(tmp_path):
    bundle = job_factory(tmp_path)
    job = json.loads(bundle[1].read_text())
    job["authorized"] = False
    bundle[1].write_text(json.dumps(job))
    with pytest.raises(ValueError, match="authorization"):
        _run(bundle)
    assert not (bundle[0] / "tests/test_written.py").exists()


def test_changed_blob_is_rejected_before_claim(tmp_path):
    bundle = job_factory(tmp_path)
    (next(bundle[2].glob("*.blob"))).write_text("def altered(): pass\n")
    with pytest.raises(ValueError, match="payload changed"):
        _run(bundle)
    assert not bundle[3].exists()


def test_source_path_traversal_rejected(tmp_path):
    bundle = job_factory(tmp_path)
    job = json.loads(bundle[1].read_text())
    job["files"][0]["path"] = "tests/../../outside.py"
    bundle[1].write_text(json.dumps(job))
    with pytest.raises(ValueError, match="path"):
        _run(bundle)
    assert not (tmp_path / "outside.py").exists()


def test_foreign_unapproved_diff_blocks_resume(tmp_path):
    bundle = job_factory(tmp_path)
    with pytest.raises(RuntimeError, match="INJECTED"):
        _run(bundle, fault_after_write=True)
    (bundle[0] / "tests/test_foreign.py").write_text(
        "def test_foreign(): assert True\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Foreign source"):
        _run(bundle)


def test_failed_real_pytest_is_quarantined_without_replay(tmp_path):
    bundle = job_factory(
        tmp_path, content=b"def test_added():\n    assert False\n")
    with pytest.raises(ValueError, match="regression failed"):
        _run(bundle)
    saved = json.loads((bundle[3] / "code_handoff_state.json").read_text())
    assert saved["status"] == "TEST_FAILED_QUARANTINED"
    with pytest.raises(ValueError, match="quarantined"):
        _run(bundle)


def test_candidate_mutated_after_claim_cannot_rewrite(tmp_path):
    bundle = job_factory(tmp_path)
    with pytest.raises(RuntimeError, match="INJECTED"):
        _run(bundle, fault_after_write=True)
    path = bundle[0] / "tests/test_written.py"
    path.write_text("def test_foreign(): assert False\n")
    with pytest.raises(ValueError, match="differs from original"):
        _run(bundle)


def test_protected_codex_policy_cannot_be_edited_by_alternate_worker(tmp_path):
    bundle = job_factory(tmp_path)
    job = json.loads(bundle[1].read_text())
    job["files"][0]["path"] = (
        "selenium_pipeline/development_coding_provider_health_v71.py")
    bundle[1].write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(ValueError, match="Unapproved candidate source path"):
        _run(bundle)
    assert not (bundle[0] / "selenium_pipeline").exists()


def test_missing_local_write_authorization_is_refused(tmp_path):
    bundle = job_factory(tmp_path)
    job = json.loads(bundle[1].read_text())
    job["source"] = "unverified_model_output"
    bundle[1].write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(ValueError, match="authorization"):
        _run(bundle)
