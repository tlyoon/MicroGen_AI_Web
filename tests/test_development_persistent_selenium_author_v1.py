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
    assert result["model_sends"] == 1
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


def _pinned_caption_reply_fixture():
    fixture = (Path(__file__).parent / "fixtures" /
               "g3_pdf_caption_png_inventory_original_reply_v1.txt")
    assert author.sha(fixture) == author.PINNED_ONE_FUNCTION_REPLY_SHA
    return fixture


def _make_quarantined_original_caption_job(env):
    root, repo, old_job = env
    test = repo/"tests"/"test_g3_pdf_caption_png_inventory_v1.py"
    shutil.copyfile(
        Path(__file__).parent.parent/"development_specs"/"specs"/
        "g3_pdf_caption_png_inventory_v1.py", test)
    _git(repo, "add", "tests/test_g3_pdf_caption_png_inventory_v1.py")
    _git(repo, "commit", "-m", "Immutable independently reviewed G3 PNG tests")
    job=json.loads(old_job.read_text())
    job["job_id"]="g3_pdf_caption_png_inventory_v1"
    job["base_sha"]=_git(repo,"rev-parse","HEAD")
    job["target"]="selenium_pipeline/g3_pdf_caption_png_inventory_v1.py"
    job["target_original_sha256"]=None
    job["test"]="tests/test_g3_pdf_caption_png_inventory_v1.py"
    job["test_sha256"]=author.sha(test)
    job["context_path"]=job["test"]
    job["context_sha256"]=author.sha(test)
    job["instruction"]=("Implement pure source-caption versus cropped-PNG technical "
                        "identifier inventory comparison with distinct missing "
                        "and orphan identifiers; never grant science acceptance.")
    old_job.unlink()
    job_path=root/"inbox"/"g3_pdf_caption_png_inventory_v1.json"
    job_path.write_text(json.dumps(job))
    state_dir=root/"state"/job["job_id"]
    state_dir.mkdir()
    reply=state_dir/"original_model_reply.txt"
    reply.write_bytes(_pinned_caption_reply_fixture().read_bytes())
    state={
        "schema_version":1,"status":"UNSAFE_MODEL_REPLY_QUARANTINED",
        "job_sha256":author.sha(job_path),"base_sha":job["base_sha"],
        "job_id":job["job_id"],"model_claims":1,"model_sends":1,
        "model_reply_sha256":author.sha(reply),"paid_api_requests":0,
        "student_publication_authorized":False,"candidate_merged":False,
    }
    (state_dir/"coding_state.json").write_text(json.dumps(state))
    return root,repo,job_path,reply


def test_original_saved_one_function_indent_recovery_never_changes_tokens():
    fixture=_pinned_caption_reply_fixture()
    original=fixture.read_text("utf8")
    assert author.lookup_mechanism(
        "persistent_selenium_code_author",
        author.PINNED_ONE_FUNCTION_SIGNATURE
    ) == author.PINNED_ONE_FUNCTION_MECHANISM
    clean=author.parse_reply(original)
    assert clean.startswith("import re\n\ndef ")
    assert "def compare_g3_pdf_caption_png_inventory(" in clean
    assert [line.strip() for line in clean.splitlines() if line.strip()] == [
        line.strip() for line in original.removeprefix("Gemini said\n\n").splitlines()
        if line.strip()]
    assert author.parse_reply(original) == clean


def test_pinned_quarantined_response_auto_reconciles_without_new_send(env):
    root,repo,job,reply=_make_quarantined_original_caption_job(env)
    original_hash=author.sha(reply)
    def forbidden(_):
        raise AssertionError("Second Selenium Send forbidden")
    result=author.scan(root=root,sender=forbidden)
    assert result["jobs"][0]["status"]=="SOURCE_CANDIDATE_TESTED_NO_PUBLICATION", result
    saved=json.loads((root/"state"/job.stem/"coding_state.json").read_text())
    assert saved["pytest_exit_code"]==0
    assert saved["model_claims"]==saved["model_sends"]==1
    assert saved["paid_api_requests"]==0
    assert saved["student_publication_authorized"] is False
    assert author.sha(reply)==original_hash==author.PINNED_ONE_FUNCTION_REPLY_SHA
    assert author.sha(repo/"selenium_pipeline"/
                      "g3_pdf_caption_png_inventory_v1.py")==saved["candidate_sha256"]
    again=author.scan(root=root,sender=forbidden)
    assert again["jobs"][0]["status"]=="SOURCE_CANDIDATE_TESTED_NO_PUBLICATION"
    assert author.sha(reply)==original_hash


def test_mutated_quarantined_original_stays_blocked_without_replay(env):
    root,repo,job,reply=_make_quarantined_original_caption_job(env)
    saved=reply.read_bytes()
    reply.write_bytes(saved.replace(b"import re",b"import os",1))
    def forbidden(_):
        raise AssertionError("Second Selenium Send forbidden")
    r=author.scan(root=root,sender=forbidden)
    assert r["jobs"][0]["status"]=="UNSAFE_MODEL_REPLY_QUARANTINED"
    assert not (repo/"selenium_pipeline"/
                "g3_pdf_caption_png_inventory_v1.py").exists()


def test_unknown_saved_response_cannot_use_pinned_indent_recovery():
    original=_pinned_caption_reply_fixture().read_text("utf8")
    with pytest.raises(ValueError):
        author._recover_pinned_original_one_function(
            original.replace("import re", "import os", 1))


def _real_g3_latex_reply():
    path = (Path(__file__).parent / "fixtures" /
            "g3_caption_latex_original_ui_python_heading_v1.txt")
    assert author.sha(path) == (
        "c81b5e2651ae6036831da328ad9f03e2f5cf2832d679a3a3e7d2e6fbb951bf9a")
    return path


def _make_saved_g3_latex_job(env):
    from selenium_pipeline.development_g2g3_requirement_task_factory_v1 import (
        compile_independent_test)
    root, repo, old = env
    reviewed = json.loads((
        Path(__file__).parent.parent / "development_specs" /
        "g2g3_technical_requirement_rules_v1.json").read_text())
    rule = next(r for r in reviewed["requirements"]
                if r["id"] == "g3_caption_latex_inventory_v1")
    source = compile_independent_test(rule)
    test = repo / "tests" / "test_g3_caption_latex_inventory_v1.py"
    test.write_bytes(source)
    _git(repo, "add", "tests/test_g3_caption_latex_inventory_v1.py")
    _git(repo, "commit", "-m", "Preapproved independent G3 latex technical test")
    j = json.loads(old.read_text())
    j["job_id"] = rule["id"]
    j["base_sha"] = _git(repo, "rev-parse", "HEAD")
    j["target"] = "selenium_pipeline/g3_caption_latex_inventory_v1.py"
    j["target_original_sha256"] = None
    j["test"] = "tests/test_g3_caption_latex_inventory_v1.py"
    j["test_sha256"] = author.sha(test)
    j["context_path"] = j["test"]
    j["context_sha256"] = j["test_sha256"]
    j["instruction"] = rule["instruction"]
    old.unlink()
    job = root / "inbox" / (rule["id"] + ".json")
    job.write_text(json.dumps(j))
    evidence = root / "state" / rule["id"]
    evidence.mkdir()
    raw = evidence / "original_model_reply.txt"
    raw.write_bytes(_real_g3_latex_reply().read_bytes())
    state = {
        "schema_version":1,"status":"UNSAFE_MODEL_REPLY_QUARANTINED",
        "job_sha256":author.sha(job),"base_sha":j["base_sha"],
        "job_id":rule["id"],"model_claims":1,"model_sends":1,
        "model_reply_sha256":author.sha(raw),"paid_api_requests":0,
        "student_publication_authorized":False,"candidate_merged":False
    }
    (evidence / "coding_state.json").write_text(json.dumps(state))
    return root,repo,job,raw


def test_owned_python_language_label_removed_only_after_original_sha_check():
    original = _real_g3_latex_reply().read_text("utf8")
    assert original.startswith("Gemini said\nPython\n")
    clean = author.parse_reply(original)
    assert clean.startswith("import re\n")
    assert "re.compile" in clean
    assert clean.rstrip() == original.removeprefix(
        "Gemini said\nPython\n").rstrip()
    assert author.lookup_mechanism(
        "persistent_selenium_code_author",
        "GEMINI_UI_PYTHON_LANGUAGE_HEADER_SINGLE_SAFE_FUNCTION"
    ) == "STRIP_ONLY_UI_HEADING_THEN_AST_PYTEST_WITHOUT_RESEND"
    assert author.lookup_mechanism(
        "persistent_selenium_code_author",
        "SOURCE_PURE_REGEX_COMPILE_FOR_LITERAL_CAPTION_IDS"
    ) == "ALLOW_FIXED_ASCII_CAPTION_REGEX_ONLY_WITH_INDEPENDENT_TEST"


def test_existing_language_header_original_reconciles_without_selenium_resend(env):
    root,repo,job,raw = _make_saved_g3_latex_job(env)
    digest=author.sha(raw)
    def forbidden(_):
        raise AssertionError("Never repeat original Gemini Selenium Send")
    outcome=author.scan(root=root,sender=forbidden)
    assert outcome["jobs"][0]["status"] == (
        "SOURCE_CANDIDATE_TESTED_NO_PUBLICATION"), outcome
    state=json.loads((
        root/"state"/job.stem/"coding_state.json").read_text())
    assert state["pytest_exit_code"] == 0, state
    assert state["model_claims"] == state["model_sends"] == 1
    assert state["paid_api_requests"] == 0
    assert state["student_publication_authorized"] is False
    assert author.sha(raw) == digest
    assert author.sha(repo/"selenium_pipeline"/
                      "g3_caption_latex_inventory_v1.py") == state["candidate_sha256"]
    again=author.scan(root=root,sender=forbidden)
    assert again["jobs"][0]["status"] == "SOURCE_CANDIDATE_TESTED_NO_PUBLICATION"
    assert author.sha(raw)==digest


def test_changed_saved_ui_language_reply_is_quarantined_not_replayed(env):
    root,repo,job,raw = _make_saved_g3_latex_job(env)
    raw.write_bytes(raw.read_bytes().replace(b"import re",b"import os",1))
    outcome=author.scan(root=root,sender=lambda _: (_ for _ in ()).throw(
        AssertionError("Second Send forbidden")))
    assert outcome["jobs"][0]["status"] == "UNSAFE_MODEL_REPLY_QUARANTINED"
    assert not (repo/"selenium_pipeline"/
                "g3_caption_latex_inventory_v1.py").exists()


def test_untrusted_python_compilation_and_code_prose_stay_rejected():
    valid=author.parse_reply(_real_g3_latex_reply().read_text("utf8"))
    for source in (
        valid.replace('re.compile(r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$", re.ASCII)',
                      're.compile(r".*", re.ASCII)'),
        valid.replace('re.compile(r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$", re.ASCII)',
                      're.compile(source_caption_ids[0], re.ASCII)'),
        valid.replace('re.compile(r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$", re.ASCII)',
                      'latex_figure_ids.compile(r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$", re.ASCII)'),
        valid.replace('    pattern = re.compile(',
                      '    re = latex_figure_ids[0]\n    pattern = re.compile('),
    ):
        with pytest.raises(ValueError):
            author.validate_source(source)
    with pytest.raises(ValueError):
        author.parse_reply("Gemini said\nJavascript\n"+valid)
    with pytest.raises(ValueError):
        author.parse_reply("Gemini said\nPython\n"+valid+"print('extra')\n")


@pytest.mark.parametrize("name,sha_expected", [
    ("g3_wav_slide_alignment_v1",
     "6f061994beced5279acd40d1c1c941529b3a9519864e363911d67d33e1fae1f6"),
    ("g3_mp4_page_alignment_v1",
     "c280e99a971c63a764e9db515de6c596d120d80e413d5c322b7d4a5afb84d1ee"),
])
def test_original_local_empty_set_reply_recovers_without_model_resend(
        env,name,sha_expected):
    from selenium_pipeline.development_g2g3_requirement_task_factory_v1 import (
        compile_independent_test)
    root,repo,old=env
    rules=json.loads((Path(__file__).parent.parent /
       "development_specs"/"g2g3_technical_requirement_rules_v1.json").read_text())
    rule=next(row for row in rules["requirements"] if row["id"]==name)
    independent=compile_independent_test(rule)
    test=repo/"tests"/("test_"+name+".py")
    test.write_bytes(independent)
    _git(repo,"add","--","tests/"+test.name)
    _git(repo,"commit","-m","Immutable independently reviewed G3 ordering tests")
    claim=json.loads(old.read_text())
    claim["job_id"]=name
    claim["base_sha"]=_git(repo,"rev-parse","HEAD")
    claim["target"]="selenium_pipeline/"+name+".py"
    claim["target_original_sha256"]=None
    claim["test"]="tests/"+test.name
    claim["test_sha256"]=author.sha(test)
    claim["context_path"]=claim["test"]
    claim["context_sha256"]=claim["test_sha256"]
    claim["instruction"]=rule["instruction"]
    old.unlink()
    job=root/"inbox"/(name+".json")
    job.write_text(json.dumps(claim))
    state_dir=root/"state"/name
    state_dir.mkdir()
    raw=state_dir/"original_model_reply.txt"
    fixture=Path(__file__).parent/"fixtures"/(name+"_original_ui_python_v1.txt")
    assert author.sha(fixture)==sha_expected
    raw.write_bytes(fixture.read_bytes())
    prior=dict(schema_version=1,status="UNSAFE_MODEL_REPLY_QUARANTINED",
         job_sha256=author.sha(job),base_sha=claim["base_sha"],
         job_id=name,model_claims=1,model_sends=1,
         model_reply_sha256=author.sha(raw),
         paid_api_requests=0,student_publication_authorized=False,
         candidate_merged=False)
    (state_dir/"coding_state.json").write_text(json.dumps(prior))
    def no_send(_):
        raise AssertionError("Uncertain model request must never be replayed")
    first=author.scan(root=root,sender=no_send)
    assert first["jobs"][0]["status"]=="SOURCE_CANDIDATE_TESTED_NO_PUBLICATION",first
    saved=json.loads((state_dir/"coding_state.json").read_text())
    assert saved["pytest_exit_code"]==0,saved
    assert saved["model_claims"]==saved["model_sends"]==1
    assert saved["paid_api_requests"]==0
    assert saved["student_publication_authorized"] is False
    assert author.sha(raw)==sha_expected
    assert author.sha(repo/claim["target"])==saved["candidate_sha256"]
    second=author.scan(root=root,sender=no_send)
    assert second["jobs"][0]["status"]=="SOURCE_CANDIDATE_TESTED_NO_PUBLICATION"
    assert author.sha(raw)==sha_expected


def test_add_requires_nonshadowed_single_local_empty_set():
    source=('def pure(value):\n'
            '    seen = set()\n'
            '    for x in value:\n'
            '        seen.add(x)\n'
            '    return len(seen)\n')
    assert author.validate_source(source).rstrip()==source.rstrip()
    assert author.lookup_mechanism(
        "persistent_selenium_code_author",
        "SOURCE_BOUNDED_LOCAL_EMPTY_SET_ADDITION") == (
        "ALLOW_ONLY_ONE_NONSHADOWED_LOCAL_SET_ADD_THEN_AST_PYTEST")
    unsafe=(
        source.replace('    seen = set()','    seen = []'),
        source.replace('    seen = set()','    seen = set()\n    seen = value'),
        source.replace('    seen.add(x)','    value.add(x)'),
        source.replace('def pure(value):','def pure(value, seen):'),
        source.replace('    seen = set()',
                       '    set = value\n    seen = set()'),
        source.replace('    seen.add(x)',
                       '    seen.add(x)\n    seen.add(x, x)'),
        source.replace('    seen = set()','    seen.add(value)\n    seen = set()'),
    )
    for candidate in unsafe:
        with pytest.raises(ValueError):
            author.validate_source(candidate)


def test_original_unknown_set_add_source_is_never_silently_reinterpreted():
    files=list((Path(__file__).parent/"fixtures").glob(
        "g3_*alignment_v1_original_ui_python_v1.txt"))
    assert len(files)==2
    for path in files:
        raw=path.read_text("utf8")
        clean=author.parse_reply(raw)
        assert clean.rstrip()==raw.removeprefix("Gemini said\nPython\n").rstrip()
        altered=raw.replace("seen.add(item)", "value.add(item)")
        if altered==raw:
            altered=raw.replace("seen_pages.add(page_index)",
                                "value.add(page_index)")
        assert altered!=raw
        with pytest.raises(ValueError):
            author.parse_reply(altered)


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


REAL_FLATTENED = (
    'Gemini said\n\n'
    '"""Windows pytest process result classifier."""\n\n'
    'def classify_pytest_result(return_code, stdout, stderr):\n'
    '"""Classify a pytest process outcome strictly from its integer return code."""\n'
    'passed = type(return_code) is int and return_code == 0\n'
    'return {\n'
    '"passed": passed,\n'
    '"return_code": return_code,\n'
    '"stdout": stdout,\n'
    '"stderr": stderr,\n'
    '}\n'
)


def test_real_owned_selenium_plain_text_indent_recovered_and_tests_pass(env):
    root, repo, job = env
    result=author.step(root=root, job_path=job,
                       sender=lambda prompt: REAL_FLATTENED)
    assert result["status"] == "SOURCE_CANDIDATE_TESTED_NO_PUBLICATION"
    assert result["pytest_exit_code"] == 0
    assert result["model_claims"] == 1
    assert result["model_sends"] == 1
    saved=(root / "state" / "windows_pytest_result_v1" /
           "original_model_reply.txt")
    assert saved.read_text() == REAL_FLATTENED


def test_saved_quarantined_original_reply_reconciles_without_new_send(env):
    root, repo, job = env
    state=root / "state" / "windows_pytest_result_v1"
    state.mkdir()
    raw=state / "original_model_reply.txt"
    raw.write_text(REAL_FLATTENED)
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (state / "coding_state.json").write_text(json.dumps({
        "schema_version":1,"status":"UNSAFE_MODEL_REPLY_QUARANTINED",
        "job_sha256":digest(job),"base_sha":_git(repo,"rev-parse","HEAD"),
        "job_id":"windows_pytest_result_v1",
        "model_claims":1,"model_sends":1,"paid_api_requests":0,
        "model_reply_sha256":digest(raw),
        "student_publication_authorized":False,"candidate_merged":False,
    }))
    def forbidden_model(prompt):
        raise AssertionError("Original browser Send was consumed")
    result=author.step(root=root,job_path=job,
                       sender=forbidden_model,reconcile_only=True)
    assert result["status"]=="SOURCE_CANDIDATE_TESTED_NO_PUBLICATION"
    assert result["pytest_exit_code"]==0
    assert result["model_claims"]==1
    assert author.step(root=root,job_path=job,sender=forbidden_model)[
        "status"]=="SOURCE_CANDIDATE_TESTED_NO_PUBLICATION"


def test_offline_reconcile_cannot_create_new_model_claim(env):
    root,repo,job=env
    with pytest.raises(ValueError,match="cannot create a new browser"):
        author.step(root=root,job_path=job,reconcile_only=True)
    assert not (root / "state" / "windows_pytest_result_v1" /
                "coding_state.json").exists()


def test_non_owned_flattened_text_cannot_be_auto_repaired():
    raw=('Unverified text\n\n'
         'def classify_pytest_result(return_code, stdout, stderr):\n'
         'return {"passed":True, "return_code":0, "stdout":stdout, "stderr":stderr}')
    with pytest.raises(ValueError):
        author.parse_reply(raw)


@pytest.mark.parametrize("raw", [
    "def bad():\n    import os\n    return 4\n",
    "def bad():\n    from subprocess import run\n    return 4\n",
    "def bad():\n    return print('secret')\n",
    "def bad():\n    return object().mro()\n",
])
def test_nested_imports_and_nonpure_code_are_quarantined(raw):
    with pytest.raises(ValueError):
        author.validate_source(raw)


def test_completed_code_candidate_survives_original_git_commit(env):
    root, repo, job = env
    first = author.step(root=root, job_path=job, sender=lambda p: GOOD)
    assert first["status"] == "SOURCE_CANDIDATE_TESTED_NO_PUBLICATION"
    _git(repo, "add", "selenium_pipeline/windows_pytest_result_v1.py")
    _git(repo, "commit", "-m", "source-verified-model-candidate")
    def forbidden(prompt):
        raise AssertionError("Committed original job must never resend")
    after = author.step(root=root, job_path=job, sender=forbidden)
    assert after["status"] == first["status"]
    assert after["candidate_sha256"] == first["candidate_sha256"]


G3_FLATTENED_MULTI_LINE = (
    'Gemini said\n\n'
    '"""Technical original response."""\n'
    'import math\n\n'
    'def compare_g3_audio_video_page_durations(\n'
    'wav_durations_ms, frame_durations_ms, tolerance_ms\n'
    '):\n'
    '"""Only technical page timing; never academic acceptance."""\n'
    'page_count = max(len(wav_durations_ms), len(frame_durations_ms))\n'
    'mismatched_pages = [\n'
    'idx + 1\n'
    'for idx in range(page_count)\n'
    'if not (\n'
    'idx < len(wav_durations_ms)\n'
    'and idx < len(frame_durations_ms)\n'
    'and math.isfinite(wav_durations_ms[idx])\n'
    'and abs(wav_durations_ms[idx] - frame_durations_ms[idx]) <= tolerance_ms\n'
    ')\n'
    ']\n'
    'return {\n'
    '"technical_timing_match": bool(page_count > 0 and not mismatched_pages),\n'
    '"mismatched_pages": mismatched_pages,\n'
    '"independent_scientific_acceptance": False,\n'
    '"independent_acoustic_acceptance": False,\n'
    '"student_publication_authorized": False,\n'
    '}\n'
)


def test_original_g3_multiline_signature_and_comprehension_recovered():
    import ast
    recovered = author.parse_reply(G3_FLATTENED_MULTI_LINE)
    ast.parse(recovered)
    assert "def compare_g3_audio_video_page_durations(\n" in recovered
    assert "\n    page_count = max(" in recovered
    assert "\n    return {\n" in recovered
    assert "\n    for idx in range(page_count)\n" in recovered


def test_unclosed_multiline_signature_not_normalized():
    bad = (
        'Gemini said\n\n'
        'def compare_g3_audio_video_page_durations(\n'
        'argument, another\n'
        'return argument\n'
    )
    with pytest.raises(ValueError):
        author.parse_reply(bad)


def test_second_flattened_function_cannot_masquerade_as_body():
    bad = (
        'Gemini said\n\n'
        'def first_valid_function():\n'
        'return 5\n\n'
        'def unapproved_second_function():\n'
        'return 6\n'
    )
    with pytest.raises(ValueError, match="multiple flattened"):
        author.parse_reply(bad)


def _original_g3_highlight_timing_reply():
    path = (Path(__file__).parent / "fixtures" /
            "g3_highlight_speech_timing_original_ui_python_v1.txt")
    assert author.sha(path) == (
        "85b95c9367576609b35a9ac1c0f795331b7dd7be0606bc0adc90ddf8bb5657be")
    return path


def _make_saved_g3_highlight_timing_job(env):
    from selenium_pipeline.development_g2g3_requirement_task_factory_v1 import (
        compile_independent_test)
    root, repo, old = env
    rules = json.loads((Path(__file__).parent.parent /
                        "development_specs" /
                        "g2g3_technical_requirement_rules_v1.json").read_text())
    rule = next(x for x in rules["requirements"]
                if x["id"] == "g3_highlight_speech_timing_v1")
    content = compile_independent_test(rule)
    test = repo / "tests" / "test_g3_highlight_speech_timing_v1.py"
    test.write_bytes(content)
    _git(repo, "add", "tests/" + test.name)
    _git(repo, "commit", "-m",
         "Immutable original independent G3 speech-highlight timing tests")
    item = json.loads(old.read_text())
    item["job_id"] = rule["id"]
    item["base_sha"] = _git(repo, "rev-parse", "HEAD")
    item["target"] = "selenium_pipeline/" + rule["id"] + ".py"
    item["target_original_sha256"] = None
    item["test"] = "tests/" + test.name
    item["test_sha256"] = author.sha(test)
    item["context_path"] = item["test"]
    item["context_sha256"] = item["test_sha256"]
    item["instruction"] = rule["instruction"]
    old.unlink()
    job = root / "inbox" / (rule["id"] + ".json")
    job.write_text(json.dumps(item))
    original = root / "state" / rule["id"]
    original.mkdir()
    reply = original / "original_model_reply.txt"
    reply.write_bytes(_original_g3_highlight_timing_reply().read_bytes())
    original_state = {
        "schema_version": 1, "status": "UNSAFE_MODEL_REPLY_QUARANTINED",
        "job_sha256": author.sha(job), "base_sha": item["base_sha"],
        "job_id": item["job_id"], "model_claims": 1, "model_sends": 1,
        "model_reply_sha256": author.sha(reply), "paid_api_requests": 0,
        "student_publication_authorized": False,
        "candidate_merged": False,
    }
    (original / "coding_state.json").write_text(json.dumps(original_state))
    return root, repo, job, reply


def test_exact_original_highlight_regex_is_no_send_source_recovery():
    raw = _original_g3_highlight_timing_reply().read_text("utf8")
    assert raw.startswith("Gemini said\nPython\n")
    assert author.lookup_mechanism(
        "persistent_selenium_code_author",
        "SOURCE_FIXED_ASCII_HIGHLIGHT_NARRATION_ID_REGEX",
    ) == "ALLOW_ONLY_STATIC_ASCII_ID_REGEX_WITH_ORIGINAL_REPLY_AND_PYTEST"
    parsed = author.parse_reply(raw)
    assert parsed.strip() == raw.removeprefix("Gemini said\nPython\n").strip()
    assert parsed.count("def compare_g3_highlight_speech_timing(") == 1
    assert "seen_narration_ids.add(narration_id)" in parsed


def test_quarantined_original_g3_timing_source_passes_real_pinned_tests(
        env):
    root, repo, job, reply = _make_saved_g3_highlight_timing_job(env)
    raw_digest = author.sha(reply)
    def forbidden(_):
        raise AssertionError("Second Gemini browser Send is not permitted")
    result = author.scan(root=root, sender=forbidden)
    assert result["jobs"][0]["status"] == (
        "SOURCE_CANDIDATE_TESTED_NO_PUBLICATION"), result
    saved = json.loads((root/"state"/job.stem/"coding_state.json").read_text())
    assert saved["pytest_exit_code"] == 0, saved
    assert saved["model_claims"] == saved["model_sends"] == 1
    assert saved["paid_api_requests"] == 0
    assert saved["student_publication_authorized"] is False
    assert author.sha(reply) == raw_digest
    assert author.sha(repo/"selenium_pipeline"/
                      "g3_highlight_speech_timing_v1.py") == (
                          saved["candidate_sha256"])
    assert author.scan(root=root,sender=forbidden)["jobs"][0]["status"] == (
        "SOURCE_CANDIDATE_TESTED_NO_PUBLICATION")
    assert author.sha(reply) == raw_digest


def test_only_exact_static_ascii_highlight_id_regex_is_admitted():
    original = _original_g3_highlight_timing_reply().read_text("utf8")
    valid = author.parse_reply(original)
    exact = r're.compile(r"[A-Za-z0-9](?:[A-Za-z0-9_-]*[A-Za-z0-9])?")'
    assert exact in valid
    for unsafe in (
        valid.replace(exact, 're.compile(r".*")'),
        valid.replace(exact, "re.compile(segments[0]['element_id'])"),
        valid.replace(exact, "id_pattern.compile(r'.*')"),
        valid.replace(exact, exact.replace(")", ", re.IGNORECASE)")),
        valid.replace("    expected_keys =", "    re = segments\n    expected_keys ="),
    ):
        with pytest.raises(ValueError):
            author.validate_source(unsafe)


def test_mutated_saved_g3_timing_reply_never_replayed_or_applied(env):
    root, repo, job, reply = _make_saved_g3_highlight_timing_job(env)
    reply.write_bytes(reply.read_bytes().replace(
        b'[A-Za-z0-9_-]', b'.*', 1))
    def forbidden(_):
        raise AssertionError("Unauthorized duplicate Selenium Send")
    result = author.scan(root=root, sender=forbidden)
    assert result["jobs"][0]["status"] == "UNSAFE_MODEL_REPLY_QUARANTINED"
    assert not (repo / "selenium_pipeline" /
                "g3_highlight_speech_timing_v1.py").exists()
