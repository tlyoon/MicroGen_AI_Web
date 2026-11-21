"""Real Git + pytest acceptance and fault injection for bounded coding inbox."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from selenium_pipeline import development_browser_code_dispatch_v71 as dispatch
from selenium_pipeline.development_continuity_executor_v71 import (
    _exclusive, _atomic_json,
)
from selenium_pipeline.recovery_registry import lookup_mechanism

GOOD = (
    "from selenium_pipeline.development_coding_provider_health_v71 "
    "import is_host_readonly\n\n"
    "def test_codex_policy_denial_true():\n"
    "    assert is_host_readonly('Codex\\nsandbox: read-only\\nblocked by policy')\n\n"
    "def test_unrelated_workspace_write_false():\n"
    "    assert not is_host_readonly('Codex\\nsandbox: workspace-write')\n"
)


def git(repo, *params):
    run = subprocess.run(["git", "-C", str(repo), *params],
                         capture_output=True, text=True, check=True)
    return run.stdout.strip()


def root_for(tmp_path):
    root = tmp_path / "coding_dispatch"
    (root / "inbox").mkdir(parents=True)
    (root / "jobs").mkdir()
    return root


def enroll(root: Path, name: str):
    jobdir = root / "jobs" / name
    jobdir.mkdir()
    repo = jobdir / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "MicroGen isolated verification")
    git(repo, "config", "user.email", "verification@example.invalid")
    pkg = repo / "selenium_pipeline"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf8")
    source_pkg = Path(dispatch.__file__).parent
    for filename in ("development_coding_provider_health_v71.py",
                     "development_continuity_executor_v71.py"):
        shutil.copyfile(source_pkg / filename, pkg / filename)
    (repo / "tests").mkdir()
    (repo / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n.pytest_cache/\n", encoding="utf8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "source context")
    branch = "feature/browser-dispatch-local-test"
    git(repo, "switch", "-c", branch)
    source_path = "selenium_pipeline/development_coding_provider_health_v71.py"
    source = repo / source_path
    job = {
        "schema_version": 1, "project": "MicroGen_AI_Web",
        "job_id": name, "base_sha": git(repo, "rev-parse", "HEAD"),
        "branch": branch, "authorized": True,
        "transport": "gemini_selenium", "ui_mode": "hydrogen",
        "target_path": f"tests/test_{name}.py",
        "source_path": source_path,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "task": ("Write pure read-only pytest tests for the Codex host "
                 "read-only policy-denial predicate; no credentials or changes."),
        "max_wait_seconds": 65,
    }
    jobfile = jobdir / "job.json"
    jobfile.write_text(json.dumps(job), encoding="utf8")
    pinned = hashlib.sha256(jobfile.read_bytes()).hexdigest()
    entry = {
        "schema_version": 1, "project": "MicroGen_AI_Web",
        "dispatch_id": name, "authorized": True,
        "job_sha256": pinned, "model_transport": "gemini_selenium",
        "max_browser_claims": 1, "paid_gemini_api": False,
        "student_release_authorized": False,
    }
    (root / "inbox" / f"dispatch_{name}.json").write_text(
        json.dumps(entry), encoding="utf8")
    return jobdir


def test_registry_gates_separate_dispatch_without_weakening_offline_daemon():
    assert lookup_mechanism(dispatch.KIN, dispatch.SIG) == dispatch.MECHANISM
    from selenium_pipeline.development_continuity_executor_v71 import SAFE_ACTIONS
    assert "browser_send" not in SAFE_ACTIONS
    from selenium_pipeline.development_continuity_daemon_v71 import daemon
    assert "handoff_dir" in daemon.__code__.co_varnames


def test_inspect_never_claims_or_calls_model(tmp_path):
    root = root_for(tmp_path)
    enroll(root, "pending_code_review")
    r = dispatch.scan(queue_root=root, inspect_only=True,
                      allow_one_browser_send=True, sender=lambda _: pytest.fail(
                          "Inspection cannot dispatch model request"))
    assert r["new_browser_claims"] == 0
    assert r["jobs"][0]["status"] == "READY_NEW_JOB"
    assert not (root / "dispatch_control" / "ledger.json").exists()
    assert not (root / "jobs" / "pending_code_review" /
                "state" / "browser_coding_state.json").exists()


def test_real_git_and_pytest_one_claim_then_restart_no_resend(tmp_path):
    root = root_for(tmp_path)
    job = enroll(root, "bounded_readonly_test")
    sent = []
    result = dispatch.scan(
        queue_root=root, allow_one_browser_send=True,
        sender=lambda prompt: sent.append(prompt) or GOOD,
    )
    assert result["new_browser_claims"] == 1
    assert result["jobs"][0]["status"] == "CODE_CANDIDATE_VERIFIED"
    assert len(sent) == 1 and "<SOURCE_CONTEXT>" in sent[0]
    assert result["paid_api_requests"] == 0
    assert result["student_publication_authorized"] is False
    candidate = job / "repo" / "tests" / "test_bounded_readonly_test.py"
    assert candidate.is_file()
    assert "tests/test_bounded_readonly_test.py" in git(
        job / "repo", "ls-files", "--others", "--exclude-standard")
    repeated = dispatch.scan(queue_root=root, allow_one_browser_send=True,
                             sender=lambda _: pytest.fail("Never resend"))
    assert repeated["new_browser_claims"] == 0
    assert repeated["jobs"][0]["status"] == "CODE_CANDIDATE_VERIFIED"
    led = json.loads((root / "dispatch_control" / "ledger.json").read_text())
    assert led["entries"]["bounded_readonly_test"]["browser_claims"] == 1


def test_fault_between_dispatch_claim_and_worker_never_resends(tmp_path):
    root = root_for(tmp_path)
    enroll(root, "crash_during_dispatch")
    with pytest.raises(RuntimeError, match="INJECTED_POST_DISPATCH_CLAIM"):
        dispatch.scan(queue_root=root, allow_one_browser_send=True,
                      sender=lambda _: pytest.fail("No provider call"),
                      fault_after_dispatch_claim=True)
    rest = dispatch.scan(queue_root=root, allow_one_browser_send=True,
                         sender=lambda _: pytest.fail("No Send after crash"))
    assert rest["new_browser_claims"] == 0
    assert rest["jobs"][0]["status"] == "WORKER_DISPATCH_UNCERTAIN_NO_REPLAY"


def test_timeout_does_not_block_other_eligible_job(tmp_path):
    root = root_for(tmp_path)
    enroll(root, "alpha_timeout_case")
    enroll(root, "beta_working_case")
    calls = []
    def model(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            raise TimeoutError("Possibly transmitted and consumed one model request")
        return GOOD
    result = dispatch.scan(queue_root=root, allow_one_browser_send=True,
                           max_jobs=2, sender=model)
    assert result["new_browser_claims"] == 2
    statuses = {a["entry"]: a["status"] for a in result["jobs"]}
    assert statuses["dispatch_alpha_timeout_case.json"] == "SEND_UNCERTAIN_NO_REPLAY"
    assert statuses["dispatch_beta_working_case.json"] == "CODE_CANDIDATE_VERIFIED"
    assert len(calls) == 2
    rest = dispatch.scan(queue_root=root, allow_one_browser_send=True,
                         max_jobs=2, sender=lambda _: pytest.fail(
                             "No duplicate Send for either job"))
    assert rest["new_browser_claims"] == 0


def test_previously_saved_original_response_is_reconciled_without_send(tmp_path):
    root = root_for(tmp_path)
    jobdir = enroll(root, "saved_reply_case")
    with pytest.raises(RuntimeError, match="INJECTED_POST_DISPATCH_CLAIM"):
        dispatch.scan(queue_root=root, allow_one_browser_send=True,
                      fault_after_dispatch_claim=True)
    # Simulate the original worker's recorded browser reply and a parser
    # rejection. Only these exact saved original bytes can be reconciled.
    state_dir = jobdir / "state"
    state_dir.mkdir()
    raw_reply = "Gemini said\n\n" + GOOD.replace("    assert", "assert")
    reply = state_dir / "model_response_untrusted.txt"
    reply.write_text(raw_reply, encoding="utf8")
    job = json.loads((jobdir / "job.json").read_text(encoding="utf8"))
    original_claim = {
        "schema_version": 1,
        "status": "MODEL_PROPOSAL_REJECTED",
        "job_sha256": hashlib.sha256(
            (jobdir / "job.json").read_bytes()).hexdigest(),
        "base_sha": job["base_sha"],
        "model_requests_claimed": 1,
        "response_sha256": hashlib.sha256(reply.read_bytes()).hexdigest(),
        "paid_api_requests": 0, "host_codex_policy_cleared": False,
        "student_release": False, "candidate_pr_pushed": False,
        "failure_class": "ValueError",
    }
    _atomic_json(state_dir / "browser_coding_state.json", original_claim)
    done = dispatch.scan(queue_root=root, allow_one_browser_send=True,
                         sender=lambda _: pytest.fail("No model replay"))
    assert done["new_browser_claims"] == 0
    assert done["jobs"][0]["status"] == "CODE_CANDIDATE_VERIFIED"
    assert (jobdir / "repo" / "tests" /
            "test_saved_reply_case.py").is_file()
    second = dispatch.scan(queue_root=root, allow_one_browser_send=True,
                           sender=lambda _: pytest.fail("No replay on restart"))
    assert second["jobs"][0]["status"] == "CODE_CANDIDATE_VERIFIED"


def test_changed_job_or_model_permissions_fail_closed(tmp_path):
    root = root_for(tmp_path)
    j = enroll(root, "tampered_dispatch_job")
    jobpath = j / "job.json"
    altered = json.loads(jobpath.read_text())
    altered["transport"] = "gemini_api"
    jobpath.write_text(json.dumps(altered), encoding="utf8")
    out = dispatch.scan(queue_root=root, allow_one_browser_send=True,
                        sender=lambda _: pytest.fail("No API or browser send"))
    assert out["new_browser_claims"] == 0
    assert out["jobs"][0]["status"] == "INVALID_PINNED_JOB_NO_SEND"


def test_concurrent_dispatchers_refuse_second_lock(tmp_path):
    root = root_for(tmp_path)
    enroll(root, "exclusive_owner_test")
    with _exclusive(root / "dispatch_control"):
        with pytest.raises((RuntimeError, PermissionError, BlockingIOError)):
            dispatch.scan(queue_root=root, inspect_only=True)


def test_unbounded_inbox_and_missing_authz_rejected(tmp_path):
    root = root_for(tmp_path)
    for i in range(9):
        enroll(root, f"overfull_job_{i:02}")
    with pytest.raises(ValueError, match="Unbounded browser coding inbox"):
        dispatch.scan(queue_root=root, inspect_only=True)
    (root / "inbox" / "dispatch_overfull_job_08.json").unlink()
    path = root / "inbox" / "dispatch_overfull_job_00.json"
    item = json.loads(path.read_text())
    item["authorized"] = False
    path.write_text(json.dumps(item))
    result = dispatch.scan(queue_root=root, allow_one_browser_send=False,
                           max_jobs=1, sender=lambda _: pytest.fail("No Send"))
    assert result["jobs"][0]["status"] == "INVALID_PINNED_JOB_NO_SEND"
    assert result["new_browser_claims"] == 0


def test_source_sha_mutation_not_accepted(tmp_path):
    root = root_for(tmp_path)
    jobdir = enroll(root, "changed_source_sha_case")
    source = jobdir / "repo" / "selenium_pipeline" / (
        "development_coding_provider_health_v71.py")
    source.write_text(source.read_text(encoding="utf8") + "\n# changed\n")
    out = dispatch.scan(queue_root=root, allow_one_browser_send=True,
                        sender=lambda _: pytest.fail("No Send after source mutation"))
    assert out["jobs"][0]["status"] == "INVALID_PINNED_JOB_NO_SEND"
    assert out["new_browser_claims"] == 0


def test_original_windows_crlf_reply_recovery_is_non_mutating():
    from selenium_pipeline.development_browser_code_transport_v71 import (
        parse_response,
    )
    original = ("Gemini said\r\n\r\n"
                + GOOD.replace("    assert", "assert").replace("\n", "\r\n"))
    before = hashlib.sha256(original.encode("utf8")).hexdigest()
    normalized = parse_response(original)
    assert normalized == GOOD
    assert hashlib.sha256(original.encode("utf8")).hexdigest() == before
    assert "\r" not in normalized


def test_terminal_first_job_does_not_starve_independent_new_job(tmp_path):
    root = root_for(tmp_path)
    enroll(root, "alpha_completed_case")
    enroll(root, "beta_fresh_eligible")
    calls = []
    first = dispatch.scan(
        queue_root=root, allow_one_browser_send=True, max_jobs=1,
        sender=lambda prompt: calls.append(prompt) or GOOD)
    assert first["new_browser_claims"] == 1
    assert first["jobs"][1]["status"] == "DEFERRED_FINITE_CYCLE_LIMIT"
    second = dispatch.scan(
        queue_root=root, allow_one_browser_send=True, max_jobs=1,
        sender=lambda prompt: calls.append(prompt) or GOOD)
    assert second["new_browser_claims"] == 1
    assert second["jobs"][0]["status"] == "CODE_CANDIDATE_VERIFIED"
    assert second["jobs"][1]["status"] == "CODE_CANDIDATE_VERIFIED"
    assert len(calls) == 2
    third = dispatch.scan(queue_root=root, allow_one_browser_send=True,
                          max_jobs=1, sender=lambda _: pytest.fail("No replay"))
    assert third["new_browser_claims"] == 0


def test_corrupt_child_receipt_is_held_without_stranding_other_job(tmp_path):
    root = root_for(tmp_path)
    jobdir = enroll(root, "alpha_corrupt_receipt")
    enroll(root, "beta_independent_job")
    with pytest.raises(RuntimeError, match="INJECTED_POST_DISPATCH_CLAIM"):
        dispatch.scan(queue_root=root, max_jobs=1,
                      allow_one_browser_send=True,
                      fault_after_dispatch_claim=True)
    state_dir = jobdir / "state"
    state_dir.mkdir()
    (state_dir / "browser_coding_state.json").write_text(
        "{invalid original checkpoint", encoding="utf8")
    good = []
    r = dispatch.scan(
        queue_root=root, max_jobs=2, allow_one_browser_send=True,
        sender=lambda prompt: good.append(prompt) or GOOD)
    assert r["new_browser_claims"] == 1
    assert r["jobs"][0]["status"] == "SEND_UNCERTAIN_NO_REPLAY"
    assert r["jobs"][1]["status"] == "CODE_CANDIDATE_VERIFIED"
    assert len(good) == 1


def test_tampered_completed_source_is_quarantined_without_model_replay(tmp_path):
    root = root_for(tmp_path)
    jobdir = enroll(root, "source_tamper_after_qa")
    out = dispatch.scan(queue_root=root, allow_one_browser_send=True,
                        sender=lambda _: GOOD)
    assert out["jobs"][0]["status"] == "CODE_CANDIDATE_VERIFIED"
    target = (jobdir / "repo" / "tests" /
              "test_source_tamper_after_qa.py")
    target.write_text(target.read_text(encoding="utf8")
                      + "\n# unexpected edit\n", encoding="utf8")
    again = dispatch.scan(
        queue_root=root, allow_one_browser_send=True,
        sender=lambda _: pytest.fail("Never resend tampered job"))
    assert again["jobs"][0]["status"] == "MODEL_REPLY_UNSAFE_QUARANTINED"
    assert again["new_browser_claims"] == 0


def test_boolean_claim_limit_cannot_masquerade_as_one(tmp_path):
    root = root_for(tmp_path)
    enroll(root, "boolean_limit_case")
    entry_file = (root / "inbox" /
                  "dispatch_boolean_limit_case.json")
    payload = json.loads(entry_file.read_text(encoding="utf8"))
    payload["max_browser_claims"] = True
    entry_file.write_text(json.dumps(payload), encoding="utf8")
    out = dispatch.scan(
        queue_root=root, allow_one_browser_send=True,
        sender=lambda _: pytest.fail("Boolean claim limit must not send"))
    assert out["new_browser_claims"] == 0
    assert out["jobs"][0]["status"] == "INVALID_PINNED_JOB_NO_SEND"
