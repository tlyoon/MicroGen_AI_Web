"""Real Git and pytest fault injection for the one-Send browser coding path."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from selenium_pipeline import development_browser_code_transport_v71 as browser
from selenium_pipeline.recovery_registry import lookup_mechanism

GOOD = (
    "from selenium_pipeline.development_coding_provider_health_v71 "
    "import is_host_readonly\n\n"
    "def test_downgraded_codex_host_is_detected():\n"
    "    assert is_host_readonly('Codex\\nsandbox: read-only\\nblocked by policy')\n\n"
    "def test_normal_workspace_cannot_be_falsely_blocked():\n"
    "    assert not is_host_readonly('Codex\\nsandbox: workspace-write')\n"
)


def _git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True,
        text=True, check=True,
    )
    return result.stdout.strip()


def prepare(tmp_path):
    repo = tmp_path / "isolated"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "MicroGen offline verification")
    _git(repo, "config", "user.email", "local@example.invalid")
    package = repo / "selenium_pipeline"
    package.mkdir()
    (package / "__init__.py").write_text("")
    source_package = Path(browser.__file__).parent
    for name in (
        "development_coding_provider_health_v71.py",
        "development_continuity_executor_v71.py",
    ):
        shutil.copyfile(source_package / name, package / name)
    (repo / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n.pytest_cache/\n", encoding="utf8")
    (repo / "tests").mkdir()
    _git(repo, "add", "selenium_pipeline", ".gitignore")
    _git(repo, "commit", "-m", "source-pinned-first")
    _git(repo, "switch", "-c", "feature/browser-coding-live-test")
    path = repo / browser.SOURCE_PATH
    job = {
        "schema_version": 1, "project": "MicroGen_AI_Web",
        "job_id": "browser_coding_trial",
        "base_sha": _git(repo, "rev-parse", "HEAD"),
        "branch": "feature/browser-coding-live-test",
        "authorized": True, "transport": "gemini_selenium",
        "ui_mode": "hydrogen",
        "target_path": "tests/test_host_browser_coding.py",
        "source_path": browser.SOURCE_PATH,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "task": ("Write read-only tests that distinguish the previous observed "
                 "Codex sandbox read-only denial from permitted workspace-write."),
        "max_wait_seconds": 65,
    }
    manifest = tmp_path / "browser_job.json"
    manifest.write_text(json.dumps(job))
    return repo, manifest, tmp_path / "proof"


def invoke(paths, sender):
    repo, manifest, state = paths
    return browser.run_one(job_path=manifest, repo=repo,
                           state_dir=state, sender=sender)


def test_registered_transport_is_distinct_from_codex_host_sandbox():
    assert lookup_mechanism(
        "browser_coding_transport",
        "GEMINI_SELENIUM_CODING_ONE_CLAIM_NO_REPLAY",
    ) == "CLAIM_ONCE_CAPTURE_REPLY_STATIC_TEST_AND_HANDOFF"


def test_real_browser_model_text_flows_into_own_git_worktree_and_tests(tmp_path):
    paths = prepare(tmp_path)
    calls = []
    result = invoke(paths, lambda prompt: calls.append(prompt) or GOOD)
    assert result["status"] == "CODE_CANDIDATE_VERIFIED"
    assert result["model_requests_claimed"] == 1
    assert result["host_codex_policy_cleared"] is False
    assert result["paid_api_requests"] == 0
    assert result["student_release"] is False
    assert result["candidate_pr_pushed"] is False
    assert len(calls) == 1 and "SOURCE_CONTEXT" in calls[0]
    assert "tests/test_host_browser_coding.py" in _git(
        paths[0], "ls-files", "--others", "--exclude-standard")
    assert paths[2].joinpath("browser_reply_receipt.json").is_file()
    # A restart uses original proof only, not another model request.
    other = invoke(paths, lambda _: pytest.fail("Unexpected duplicate Send"))
    assert other == result


def test_post_response_fault_recovers_original_bytes_no_resend(tmp_path):
    paths = prepare(tmp_path)
    with pytest.raises(RuntimeError, match="INJECTED_POST_REPLY_CRASH"):
        browser.run_one(job_path=paths[1], repo=paths[0],
                        state_dir=paths[2], sender=lambda _: GOOD,
                        fault_after_response=True)
    assert paths[2].joinpath("model_response_untrusted.txt").is_file()
    done = invoke(paths, lambda _: pytest.fail("Cannot replay browser Send"))
    assert done["status"] == "CODE_CANDIDATE_VERIFIED"


def test_sender_timeout_is_forever_uncertain_and_not_resubmitted(tmp_path):
    paths = prepare(tmp_path)
    def timeout(_):
        raise TimeoutError("Possibly dispatched and consumed request")
    with pytest.raises(TimeoutError):
        invoke(paths, timeout)
    state = json.loads((paths[2] / "browser_coding_state.json").read_text())
    assert state["status"] == "SEND_CLAIMED_UNCERTAIN"
    with pytest.raises(ValueError, match="NEVER RESEND"):
        invoke(paths, lambda _: pytest.fail("Model request repeated"))


def test_malicious_response_never_runs_in_pytest(tmp_path):
    paths = prepare(tmp_path)
    bad = GOOD + "\nimport os\nos.system('whoami')\n"
    with pytest.raises(ValueError, match="only define"):
        invoke(paths, lambda _: bad)
    state = json.loads((paths[2] / "browser_coding_state.json").read_text())
    assert state["status"] == "MODEL_PROPOSAL_REJECTED"
    with pytest.raises(ValueError, match="zero-Send reconciliation"):
        invoke(paths, lambda _: pytest.fail("Model request repeated"))
    assert not (paths[0] / "tests/test_host_browser_coding.py").exists()


def test_model_cannot_escape_approved_source_or_become_paid_api(tmp_path):
    paths = prepare(tmp_path)
    job = json.loads(paths[1].read_text())
    job["transport"] = "gemini_api"
    paths[1].write_text(json.dumps(job))
    with pytest.raises(ValueError, match="Unauthorized"):
        invoke(paths, lambda _: pytest.fail("Never dispatch paid API"))
    assert not paths[2].exists()


def test_source_changed_between_authorization_and_send_is_denied(tmp_path):
    paths = prepare(tmp_path)
    context = paths[0] / browser.SOURCE_PATH
    context.write_text(context.read_text() + "\n# unauthorized change\n")
    with pytest.raises(ValueError, match="Pinned coding context changed"):
        invoke(paths, lambda _: pytest.fail("Never call provider"))


def test_untrusted_code_abi_must_be_static_ast_whitelist():
    forbidden = [
        GOOD + "\ndef test_risk():\n    __import__('os').system('rm -rf /')\n",
        GOOD.replace("import is_host_readonly",
                     "import is_host_readonly, persist_host_denial"),
        GOOD + "\ndef test_file():\n    open('file', 'w').write('x')\n",
    ]
    for candidate in forbidden:
        with pytest.raises(ValueError):
            browser.safe_test_source(candidate)


def test_fenced_python_is_parsed_but_prose_is_rejected():
    assert browser.parse_response("```python\n" + GOOD.rstrip() +
                                  "\n```") == GOOD
    with pytest.raises(ValueError):
        browser.parse_response("Here is the code:\n" + GOOD)


def test_forged_model_provenance_must_not_be_accepted(tmp_path):
    paths = prepare(tmp_path)
    with pytest.raises(RuntimeError, match="INJECTED_POST_REPLY_CRASH"):
        browser.run_one(job_path=paths[1], repo=paths[0],
                        state_dir=paths[2], sender=lambda _: GOOD,
                        fault_after_response=True)
    old = paths[2] / "model_response_untrusted.txt"
    old.write_text("Forged coding reply")
    with pytest.raises(ValueError, match="modified|only define|Unbounded|NEVER RESEND"):
        invoke(paths, lambda _: pytest.fail("No repeated model Send"))


def test_code_model_stage_hydrogen_or_neon_keeps_verified_thinking():
    from selenium_pipeline.gemini_stage_policy import (
        browser_stage_needs_thinking, GeminiStagePolicyError,
    )
    assert browser_stage_needs_thinking(
        stage="code_authoring", mode="hydrogen")
    assert browser_stage_needs_thinking(
        stage="code_authoring", mode="neon")
    with pytest.raises(GeminiStagePolicyError, match="Hydrogen/Neon"):
        browser_stage_needs_thinking(stage="code_authoring", mode="flash")
    with pytest.raises(GeminiStagePolicyError, match="Hydrogen/Neon"):
        browser_stage_needs_thinking(stage="code_authoring", mode="carbon")


def test_coding_family_cannot_downgrade_to_unpinned_menu_alias(tmp_path):
    paths = prepare(tmp_path)
    job = json.loads(paths[1].read_text())
    job["ui_mode"] = "carbon"
    paths[1].write_text(json.dumps(job), encoding="utf8")
    with pytest.raises(ValueError, match="Unauthorized"):
        invoke(paths, lambda _: pytest.fail("no request"))
    assert not paths[2].exists()


def test_post_send_windows_cp1252_logger_cannot_abort_model_capture(monkeypatch):
    """Reproduce exact Dell-115 UnicodeEncodeError without a browser Send."""
    import io
    import sys
    from selenium_pipeline.windows_safe_logging import safe_log
    from selenium_pipeline.recovery_registry import lookup_mechanism
    assert lookup_mechanism(
        "browser_stdout_encoding",
        "WINDOWS_CP1252_NONASCII_PROVIDER_WAIT_LOG_AFTER_SEND",
    ) == "ESCAPE_NONENCODABLE_LOG_CHARS_NEVER_ABORT_CAPTURE"
    buffer = io.BytesIO()
    stdout = io.TextIOWrapper(buffer, encoding="cp1252", errors="strict",
                              write_through=True)
    original = sys.stdout
    try:
        sys.stdout = stdout
        safe_log("Waiting for model response to stabilize \ufffd", "INFO")
        stdout.flush()
    finally:
        sys.stdout = original
    content = buffer.getvalue().decode("cp1252")
    assert "Waiting for model response to stabilize" in content
    assert "\\ufffd" in content  # escaped unsupported replacement glyph, no crash


def test_stdout_utf8_still_preserves_original_unicode():
    import io
    import sys
    from selenium_pipeline.windows_safe_logging import safe_log
    buf = io.BytesIO()
    stdout = io.TextIOWrapper(buf, encoding="utf-8", write_through=True)
    prior = sys.stdout
    try:
        sys.stdout = stdout
        safe_log("Processing model reply …", "INFO")
        stdout.flush()
    finally:
        sys.stdout = prior
    assert "reply …" in buf.getvalue().decode("utf8")


def test_full_registry_growth_preserves_finite_schema_and_size_bounds(tmp_path):
    from selenium_pipeline.recovery_registry import load_registry, REGISTRY_PATH
    registry = load_registry()
    assert len(registry["entries"]) >= 2
    assert REGISTRY_PATH.stat().st_size > 65536
    excessive = tmp_path / "too_large_registry.json"
    from selenium_pipeline.recovery_registry import MAX_REGISTRY_BYTES
    assert 131072 <= MAX_REGISTRY_BYTES <= 262144
    padding = MAX_REGISTRY_BYTES + 1 - REGISTRY_PATH.stat().st_size
    assert padding > 0
    excessive.write_bytes(REGISTRY_PATH.read_bytes() + b" " * padding)
    assert excessive.stat().st_size == MAX_REGISTRY_BYTES + 1
    with pytest.raises(ValueError, match="Invalid size"):
        load_registry(excessive)


def test_gemini_said_ui_flattened_asserts_recovered_only_via_registered_rule():
    from selenium_pipeline.recovery_registry import lookup_mechanism
    assert lookup_mechanism(
        "browser_coding_response_shape",
        "GEMINI_OWNED_COPY_FLATTENED_SAFE_TEST_MODULE",
    ) == "RESTORE_ASSERT_INDENT_ONLY_AFTER_TEST_DEF_VERIFY_STATIC_AST"
    flattened = "Gemini said\n\n" + GOOD.replace("    assert", "assert")
    assert browser.parse_response(flattened) == GOOD
    with pytest.raises(ValueError):
        browser.parse_response(
            flattened + "\nimport os\nos.system('del C:')\n")


def test_original_rejected_gemini_reply_reconciles_no_new_send(tmp_path):
    paths = prepare(tmp_path)
    flattened = "Gemini said\n\n" + GOOD.replace("    assert", "assert")
    with pytest.raises(RuntimeError, match="INJECTED_POST_REPLY_CRASH"):
        browser.run_one(
            job_path=paths[1], repo=paths[0], state_dir=paths[2],
            sender=lambda _: flattened, fault_after_response=True,
        )
    receipt_path = paths[2] / "browser_coding_state.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["status"] = "MODEL_PROPOSAL_REJECTED"
    receipt["failure_class"] = "SyntaxError"
    receipt_path.write_text(json.dumps(receipt), encoding="utf8")
    with pytest.raises(ValueError, match="explicit zero-Send"):
        invoke(paths, lambda _: pytest.fail("No model replay"))
    result = browser.run_one(
        job_path=paths[1], repo=paths[0], state_dir=paths[2],
        sender=lambda _: pytest.fail("No model replay"),
        reconcile_only=True,
    )
    assert result["status"] == "CODE_CANDIDATE_VERIFIED"
    assert result["model_requests_claimed"] == 1
    assert result["paid_api_requests"] == 0
    assert "tests/test_host_browser_coding.py" in result["tests_passed"]


def test_no_reconciliation_without_original_reply_or_claim(tmp_path):
    paths = prepare(tmp_path)
    with pytest.raises(ValueError, match="saved original"):
        browser.run_one(
            job_path=paths[1], repo=paths[0], state_dir=paths[2],
            reconcile_only=True,
            sender=lambda _: pytest.fail("No model send"),
        )
    assert not paths[2].joinpath("model_response_untrusted.txt").exists()
