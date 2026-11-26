"""Sandboxed dry-run tests for persistent source-authoring Selenium queue.

The tests make zero model requests: all provider responses are injected strings.
Real browser Send is separately admitted by a fresh SHA-pinned job.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from selenium_pipeline import development_persistent_selenium_author_v1 as author


GOOD = '''
"""Classify a completed pytest process without guessing from log text."""

def classify_pytest_result(return_code, stdout, stderr):
    return {
        "passed": type(return_code) is int and return_code == 0,
        "return_code": return_code,
        "stdout": stdout,
        "stderr": stderr,
    }
'''.strip() + "\n"


def _git(repo, *args):
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, text=True)
    return proc.stdout.strip()


@pytest.fixture
def env(tmp_path):
    repo = tmp_path / "isolated_git"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "MicroGen safe author tests")
    _git(repo, "config", "user.email", "source-only@example.invalid")
    package = repo / "selenium_pipeline"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (repo / "tests").mkdir()
    old_test = (Path(__file__).parent /
                "test_windows_pytest_result_v1.py")
    new_test = repo / "tests" / old_test.name
    shutil.copyfile(old_test, new_test)
    (repo / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n*.pyc\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "trusted independent test")
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "switch", "-c", "feature/automatic-source-repair-v1")
    root = tmp_path / "durable_worker"
    (root / "inbox").mkdir(parents=True)
    (root / "state").mkdir()
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    job = {
        "schema_version":1, "project":"MicroGen_AI_Web",
        "job_id":"windows_pytest_result_v1", "authorized":True,
        "repo":str(repo), "base_sha":base,
        "branch":"feature/automatic-source-repair-v1",
        "target":"selenium_pipeline/windows_pytest_result_v1.py",
        "target_original_sha256":None,
        "test":"tests/test_windows_pytest_result_v1.py",
        "test_sha256":digest(new_test),
        "context_path":"tests/test_windows_pytest_result_v1.py",
        "context_sha256":digest(new_test),
        "instruction":(
            "Implement the pure Python function classify_pytest_result"
            "(return_code, stdout, stderr) as a dictionary that relies"
            " only on a genuine integer process exit code, preserving"
            " both input log strings without modifying them."),
        "selenium_mode":"hydrogen", "max_wait_seconds":65,
        "browser_model_claims":1, "paid_api":False,
        "student_publication":False,
    }
    job_path = root / "inbox" / (job["job_id"] + ".json")
    job_path.write_text(json.dumps(job))
    return root, repo, job_path


def test_model_returns_safe_pure_source_and_pytest_passes(env):
    root, repo, job = env
    prompts = []
    result = author.step(root=root, job_path=job,
                         sender=lambda prompt: prompts.append(prompt) or GOOD)
    assert result["status"] == "SOURCE_CANDIDATE_TESTED_NO_PUBLICATION"
    assert result["pytest_exit_code"] == 0
    assert result["model_claims"] == 1
    assert result["model_sends"] == 0
    assert result["paid_api_requests"] == 0
    assert "Independent" not in prompts[0] or prompts
    assert "test_zero_exit_with_swig" in prompts[0]
    assert (repo / "selenium_pipeline" /
            "windows_pytest_result_v1.py").is_file()


def test_restart_never_requests_same_model_reply_twice(env):
    root, repo, job = env
    author.step(root=root, job_path=job, sender=lambda prompt: GOOD)
    def forbidden(prompt):
        raise RuntimeError("NO SECOND MODEL SEND")
    again = author.step(root=root, job_path=job, sender=forbidden)
    assert again["status"] == "SOURCE_CANDIDATE_TESTED_NO_PUBLICATION"
    assert again["model_claims"] == 1
    assert again["pytest_exit_code"] == 0


def test_suspected_provider_send_is_never_replayed(env):
    root, repo, job = env
    def ambiguous(prompt):
        raise RuntimeError("possibly already clicked Gemini Send")
    with pytest.raises(RuntimeError):
        author.step(root=root, job_path=job, sender=ambiguous)
    result = author.step(root=root, job_path=job,
                         sender=lambda prompt: (_ for _ in ()).throw(
                             AssertionError("Replay attempted")))
    assert result["status"] == "PROVIDER_SEND_UNCERTAIN_NO_REPLAY"
    assert result["model_claims"] == 1
    assert not (repo / "selenium_pipeline" /
                "windows_pytest_result_v1.py").exists()


@pytest.mark.parametrize("bad_source", [
    "import subprocess\n\ndef dangerous():\n    return subprocess.run('curl')",
    "def wrong():\n    return eval('2 + 2')\n",
    "def wrong():\n    return __import__('os')\n",
    "def wrong():\n    return (2).__class__\n",
    "from pathlib import Path\n\ndef wrong():\n    return Path('file')",
    "def wrong():\n    with open('private'): pass\n",
])
def test_generated_python_cannot_escape_pure_source_policy(bad_source):
    with pytest.raises(ValueError):
        author.validate_source(bad_source)


def test_fenced_model_output_normalized_without_reinterpreting_code():
    code = chr(96) * 3 + "python\n" + GOOD + chr(96) * 3
    assert author.parse_reply(code) == GOOD


def test_changed_independent_test_blocks_model_send(env):
    root, repo, job = env
    (repo / "tests" / "test_windows_pytest_result_v1.py").write_text(
        "forged")
    called = []
    with pytest.raises(ValueError, match="test or context changed"):
        author.step(root=root, job_path=job,
                    sender=lambda prompt: called.append(prompt) or GOOD)
    assert not called
    assert not (root / "state" / "windows_pytest_result_v1" /
                "coding_state.json").exists()


def test_foreign_source_change_blocks_model_send(env):
    root, repo, job = env
    (repo / "unauthorized.txt").write_text("forged")
    called = []
    with pytest.raises(ValueError, match="branch not clean"):
        author.step(root=root, job_path=job,
                    sender=lambda prompt: called.append(prompt) or GOOD)
    assert called == []


def test_corrupted_original_job_sha_blocks_replay(env):
    root, repo, job = env
    author.step(root=root, job_path=job, sender=lambda prompt: GOOD)
    j = json.loads(job.read_text())
    j["instruction"] += " Modified after first Send"
    job.write_text(json.dumps(j))
    with pytest.raises(ValueError, match="Original coding job changed"):
        author.step(root=root, job_path=job, sender=lambda prompt: GOOD)


def test_mutated_generated_file_blocks_restart(env):
    root, repo, job = env
    author.step(root=root, job_path=job, sender=lambda prompt: GOOD)
    (repo / "selenium_pipeline" / "windows_pytest_result_v1.py").write_text(
        "tampered")
    with pytest.raises(ValueError, match="authenticated saved reply"):
        author.step(root=root, job_path=job, sender=lambda prompt: GOOD)


def test_invalid_provider_reply_is_quarantined_and_not_replayed(env):
    root, repo, job = env
    bad = 'import subprocess\n\ndef get_security():\n    return subprocess.getoutput("whoami")'
    result = author.step(root=root, job_path=job, sender=lambda prompt: bad)
    assert result["status"] == "UNSAFE_MODEL_REPLY_QUARANTINED"
    assert author.step(root=root, job_path=job,
                       sender=lambda prompt: GOOD)["status"] == (
                           "UNSAFE_MODEL_REPLY_QUARANTINED")


def test_different_pending_jobs_are_processed_after_one_fails(env):
    root, repo, job = env
    old = json.loads(job.read_text())
    old["job_id"] = "failed_windows_pytest_job"
    old["instruction"] += " Use a separately identified task."
    other = root / "inbox" / (old["job_id"] + ".json")
    other.write_text(json.dumps(old))
    result = author.scan(root=root, sender=lambda prompt: GOOD)
    assert len(result["jobs"]) == 2
    assert result["new_paid_api_requests"] == 0
    statuses = [x["status"] for x in result["jobs"]]
    assert "SOURCE_CANDIDATE_TESTED_NO_PUBLICATION" in statuses
    assert "ELIGIBILITY_OR_SEND_HELD" in statuses


def test_worker_one_cycle_persists_heartbeat(env):
    root, repo, job = env
    r = author.serve(root=root, max_cycles=1, poll_seconds=1,
                     sender=lambda prompt: GOOD)
    assert r["status"] == author.STATUS
    heartbeat = json.loads((root / "worker_heartbeat.json").read_text())
    assert heartbeat["cycles"] == 1
    assert heartbeat["worker_pid"] > 0
    assert heartbeat["jobs"][0]["status"] == (
        "SOURCE_CANDIDATE_TESTED_NO_PUBLICATION")
