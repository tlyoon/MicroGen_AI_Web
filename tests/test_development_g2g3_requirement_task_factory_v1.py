"""Independent offline tests for source-grounded G2/G3 task derivation.

All GitHub identities are replaced by local Git; no model Send, API, paid
request or student publication is performed by these tests.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from selenium_pipeline import development_g2g3_requirement_task_factory_v1 as factory
from selenium_pipeline import development_source_pinned_next_job_v1 as selector
from selenium_pipeline import development_persistent_selenium_author_v1 as author
from selenium_pipeline.recovery_registry import lookup_mechanism


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def stub_git(main):
    def run(args, timeout=60):
        if args[:2] == ["gh", "api"]:
            return git(main, "rev-parse", "HEAD")
        r = subprocess.run(args, capture_output=True, text=True,
                           timeout=timeout)
        if r.returncode:
            raise ValueError(r.stderr[-300:])
        return r.stdout.strip()
    return run


@pytest.fixture
def env(tmp_path):
    main = tmp_path / "main"
    main.mkdir()
    git(main, "init", "-b", "main")
    git(main, "config", "user.name", "MicroGen offline evidence test")
    git(main, "config", "user.email", "offline-source@example.invalid")
    source = Path(__file__).parent.parent
    (main / "development_specs").mkdir()
    shutil.copyfile(
        source / factory.MANIFEST,
        main / factory.MANIFEST)
    (main / "tests").mkdir()
    (main / "selenium_pipeline").mkdir()
    (main / "selenium_pipeline" / "__init__.py").write_text("")
    (main / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n*.pyc\n")
    git(main, "add", ".")
    git(main, "commit", "-m", "Independently reviewed technical requirements")
    state = tmp_path / "live_state_migrated_v1"
    state.mkdir()
    evidence = state / "daemon_heartbeat.json"
    hb = {
        "running": True,
        "status": "G2_G3_INDEPENDENT_ACCEPTANCE_EVIDENCE_REQUIRED",
        "last_g3_source_status": "G3_ORIGINAL_SOURCE_COMPLETE_SCIENCE_AUDIO_VIDEO_OPEN",
        "last_controller_status": "BLOCKED_OR_AWAITING_EVIDENCE",
        "last_historical_g2_disposition": "G2_ORIGINAL_REQUEST_DISPOSITION_PRESERVED_NO_REPLAY",
        "student_publication_authorized": False,
        "provider_sends": 0
    }
    evidence.write_text(json.dumps(hb))
    backlog = tmp_path / "code_author"
    (backlog / "inbox").mkdir(parents=True)
    (backlog / "state").mkdir()
    (tmp_path / "MICROGEN_AUTONOMOUS_CODE_WORKTREES_V1").mkdir()
    return {"main": main, "backlog": backlog, "hb": evidence,
            "git": stub_git(main)}


def call(env):
    return factory.derive(backlog_root=env["backlog"],
                          repo_root=env["main"], git=env["git"])


def test_future_one_send_code_prompt_requests_stable_fenced_indentation():
    prompt = author.prompt_for(
        {"instruction":"Implement independently verified source metadata.",
         "target":"selenium_pipeline/g3_technical_source_only_v1.py"},
        "original trusted source", "independent source tests")
    assert "one fenced python code block" in prompt
    assert "four-space Python" in prompt
    assert "precisely ONE top-level" in prompt
    assert "No commentary outside" in prompt
    assert "independent source tests" in prompt


def test_existing_source_selector_falls_through_to_derived_requirement_job(env):
    """Exact production entrypoint must cross exhausted catalog automatically."""
    main = env["main"]
    source = Path(__file__).parent.parent / "development_specs"
    approved = json.loads((source / "approved_source_jobs_v1.json").read_text())
    target = main / "development_specs" / "approved_source_jobs_v1.json"
    shutil.copyfile(source / "approved_source_jobs_v1.json", target)
    specs = main / "development_specs" / "specs"
    specs.mkdir()
    for entry in approved["jobs"]:
        filename = Path(entry["spec_path"]).name
        shutil.copyfile(source / entry["spec_path"], specs / filename)
        # The approved fixed catalog was already consumed in the live source queue.
        claimed = env["backlog"] / "inbox" / (entry["job_id"] + ".json")
        claimed.write_text('{"historical_claim":"preserve_do_not_reuse"}')
    git(main, "add", ".")
    git(main, "commit", "-m", "Reviewed original catalog already consumed")
    result = selector.select(
        catalog_path=target, backlog_root=env["backlog"],
        repo_root=main, git=env["git"])
    assert result["status"] == "SOURCE_GROUNDED_INDEPENDENT_TEST_JOB_STAGED"
    assert result["job"] not in [row["job_id"] for row in approved["jobs"]]
    assert result["model_sends"] == result["paid_api_requests"] == 0


def test_registry_integrated_and_templates_are_independent():
    assert lookup_mechanism(factory.KIND, factory.SIGNATURE) == factory.MECHANISM
    path = Path(__file__).parent.parent / factory.MANIFEST
    rules = json.loads(path.read_text())
    assert len(rules["requirements"]) == 4
    assert rules["paid_api_authorized"] is False
    for rule in rules["requirements"]:
        source = factory.compile_independent_test(rule)
        assert b"student_publication_authorized" in source
        assert b"Gemini" not in source
        assert b"test_" in source
        compile(source, rule["id"], "exec")


def test_original_source_backlog_stages_distinct_real_git_worktree(env):
    result = call(env)
    assert result["status"] == "SOURCE_GROUNDED_INDEPENDENT_TEST_JOB_STAGED"
    assert result["new_coding_jobs"] == 1
    assert result["model_sends"] == result["paid_api_requests"] == 0
    job_file = env["backlog"] / "inbox" / (result["job"] + ".json")
    job = json.loads(job_file.read_text())
    assert job["student_publication"] is False
    assert job["paid_api"] is False
    assert job["browser_model_claims"] == 1
    assert job["test_sha256"] == result["independent_test_sha256"]
    independent = Path(job["repo"]) / job["test"]
    assert hashlib.sha256(independent.read_bytes()).hexdigest() == job["test_sha256"]
    assert git(Path(job["repo"]), "rev-parse", "HEAD") == job["base_sha"]
    assert git(Path(job["repo"]), "status", "--porcelain") == ""
    claim = env["backlog"] / "derived_requirements_v1" / (result["job"] + ".json")
    assert json.loads(claim.read_text())["independent_academic_acceptance"] is False
    assert json.loads(claim.read_text())["protected_main_sha"] == (
        git(env["main"], "rev-parse", "HEAD"))


def test_repeated_dispatch_never_reuses_claim_or_mutates_existing_model_job(env):
    original = call(env)
    job = env["backlog"] / "inbox" / (original["job"] + ".json")
    frozen = job.read_bytes()
    first_receipt = (env["backlog"] / "derived_requirements_v1" /
                     (original["job"] + ".json"))
    receipt_bytes = first_receipt.read_bytes()
    another = call(env)
    assert another["job"] != original["job"]
    assert job.read_bytes() == frozen
    assert first_receipt.read_bytes() == receipt_bytes
    outputs = {original["job"], another["job"]}
    for _ in range(2):
        new = call(env)
        assert new["new_coding_jobs"] == 1
        assert new["job"] not in outputs
        outputs.add(new["job"])
    last = call(env)
    assert last["status"] == "SOURCE_G2G3_REQUIREMENT_TEST_JOBS_EXHAUSTED"
    assert last["new_coding_jobs"] == 0
    assert len(outputs) == 4


def test_closed_or_unknown_g2g3_status_never_invents_a_code_task(env):
    status = json.loads(env["hb"].read_text())
    status["status"] = "G2_G3_COMPLETE"
    env["hb"].write_text(json.dumps(status))
    r = call(env)
    assert r["status"] == "NO_VERIFIED_OPEN_G2G3_REQUIREMENT"
    assert not list((env["backlog"] / "inbox").glob("*.json"))


@pytest.mark.parametrize("change", [
    {"running": False},
    {"student_publication_authorized": True},
    {"last_g3_source_status": "G3_SCIENCE_COMPLETE"},
])
def test_invalid_checkpoint_never_stages_g3_work(env, change):
    hb = json.loads(env["hb"].read_text())
    hb.update(change)
    env["hb"].write_text(json.dumps(hb))
    r = call(env)
    assert r["status"] != "SOURCE_GROUNDED_INDEPENDENT_TEST_JOB_STAGED" or (
        r["source_gate"] == "g2_source_review_evidence_open")
    assert r["model_sends"] == 0
    assert r["paid_api_requests"] == 0


def test_tampered_rules_or_dirty_main_prevent_admission(env):
    rules = env["main"] / factory.MANIFEST
    body = json.loads(rules.read_text())
    body["paid_api_authorized"] = True
    rules.write_text(json.dumps(body))
    with pytest.raises(ValueError, match="clean exact protected GitHub main"):
        call(env)
    assert not list((env["backlog"] / "inbox").glob("*.json"))
    git(env["main"], "add", ".")
    git(env["main"], "commit", "-m", "Different untrusted requirements")
    with pytest.raises(ValueError, match="Unsafe G2/G3 independent test rule"):
        call(env)


def test_malformed_checkpoint_fails_closed_without_a_new_job(env):
    env["hb"].write_text('["fake_status"]')
    with pytest.raises(ValueError, match="Corrupt G2/G3 checkpoint"):
        call(env)
    assert not list((env["backlog"] / "inbox").glob("*.json"))


def test_missing_checkpoint_fails_closed_without_a_new_job(env):
    env["hb"].unlink()
    assert call(env)["status"] == "SOURCE_G2G3_CHECKPOINT_UNAVAILABLE_NO_NEW_JOB"
    assert not list((env["backlog"] / "inbox").glob("*.json"))


def test_no_unverified_approval_or_acoustic_video_claim_in_test_program(env):
    rules = json.loads((env["main"] / factory.MANIFEST).read_text())
    for rule in rules["requirements"]:
        program = factory.compile_independent_test(rule).decode()
        assert 'all(result[name] is False for name in FLAGS)' in program
        assert 'technical_' in rule["output"]
        assert "independent_scientific_acceptance" in rule["false_flags"]


def test_technical_oracle_fails_incorrect_model_implementation(env):
    # A wrong model implementation must fail the generated independent tests.
    selected = call(env)
    claim = json.loads((env["backlog"] / "inbox" /
                        (selected["job"] + ".json")).read_text())
    working = Path(claim["repo"])
    function = json.loads((env["main"] / factory.MANIFEST).read_text())[
        "requirements"][0]["function"]
    stub = working / claim["target"]
    stub.write_text("def " + function + "(*args):\n    return {}\n")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", claim["test"]],
                       cwd=working, capture_output=True, text=True, timeout=45)
    assert r.returncode != 0
    assert "failed" in r.stdout.lower() or "error" in r.stdout.lower()
