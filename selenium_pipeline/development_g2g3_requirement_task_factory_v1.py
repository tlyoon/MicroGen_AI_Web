"""Compile source-grounded G2/G3 technical gaps into independent code tests.

Only reviewed rules from exact clean protected GitHub main are admitted.  The
test oracle is deterministic Python authored in this module, NOT a model reply.
A live G2/G3 daemon checkpoint is required; checkpoint gaps create no work.
Science/acoustic/video acceptance and publication are never inferred here.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from .development_persistent_selenium_author_v1 import validate_job
from .recovery_registry import lookup_mechanism

STATUS = "MICROGEN_G2G3_SOURCE_GROUNDED_TECHNICAL_TASK_RULES_V1"
KIND = "autonomous_g2g3_requirement_test_derivation"
SIGNATURE = "G2_G3_QA_GAPS_PERSIST_WHILE_REVIEWED_SOURCE_JOB_CATALOG_EXHAUSTED"
MECHANISM = "PIN_CHECKPOINT_AND_GENERATE_INDEPENDENT_TECHNICAL_TEST_ONCE"
MANIFEST = "development_specs/g2g3_technical_requirement_rules_v1.json"
ID = re.compile(r"[a-z][a-z0-9_]{6,50}\Z")
FUNC = re.compile(r"compare_[a-z0-9_]{6,65}\Z")
OUTPUT = re.compile(r"technical_[a-z0-9_]{5,65}\Z")
FLAG = re.compile(r"(independent_[a-z0-9_]+|student_publication_authorized)\Z")
KINDS = frozenset(("set_coverage", "ordered_alignment",
                   "review_provenance", "highlight_timing"))
GATES = frozenset(("g3_source_complete_qa_open",
                   "g2_source_review_evidence_open"))

def need(ok, message):
    if not ok:
        raise ValueError(message)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_json(path: Path, size=50_000):
    need(path.is_file() and not path.is_symlink()
         and 1 <= path.stat().st_size <= size,
         "Missing or unsafe immutable G2/G3 source evidence")
    return json.loads(path.read_text(encoding="utf8"))

def _rules(repo: Path, git) -> tuple[list, str]:
    path = repo / MANIFEST
    require_path = git(["git", "-C", str(repo), "ls-files",
                        "--error-unmatch", "--", MANIFEST])
    need(require_path.replace("\\", "/") == MANIFEST
         and not path.parent.is_symlink(),
         "G2/G3 requirement rules not reviewed and committed on main")
    data = read_json(path)
    need(type(data) is dict and set(data) == {
        "schema_version", "status", "paid_api_authorized",
        "student_publication_authorized", "requirements"
    } and data["schema_version"] == 1 and data["status"] == STATUS
         and data["paid_api_authorized"] is False
         and data["student_publication_authorized"] is False
         and type(data["requirements"]) is list
         and 1 <= len(data["requirements"]) <= 16,
         "Unsafe G2/G3 independent test rule catalog")
    seen = set()
    for rule in data["requirements"]:
        need(type(rule) is dict and set(rule) == {
            "id", "gate", "kind", "function", "output",
            "false_flags", "instruction"
        } and type(rule["id"]) is str
             and ID.fullmatch(rule["id"])
             and rule["id"] not in seen
             and rule["gate"] in GATES
             and rule["kind"] in KINDS
             and type(rule["function"]) is str
             and FUNC.fullmatch(rule["function"])
             and type(rule["output"]) is str
             and OUTPUT.fullmatch(rule["output"])
             and type(rule["instruction"]) is str
             and 90 <= len(rule["instruction"]) <= 3500
             and type(rule["false_flags"]) is list
             and 2 <= len(rule["false_flags"]) <= 4
             and "student_publication_authorized" in rule["false_flags"]
             and len(set(rule["false_flags"])) == len(rule["false_flags"])
             and all(type(f) is str and FLAG.fullmatch(f)
                     for f in rule["false_flags"]),
             "Unreviewed, unsafe or duplicate derived G2/G3 task rule")
        seen.add(rule["id"])
    return data["requirements"], sha(path.read_bytes())

def _gate_open(rule: dict, checkpoint: dict) -> bool:
    # Do not mistake an absence of evidence for scientific acceptance.
    if (checkpoint.get("running") is not True
            or checkpoint.get("student_publication_authorized") is not False
            or checkpoint.get("status") != "G2_G3_INDEPENDENT_ACCEPTANCE_EVIDENCE_REQUIRED"):
        return False
    if rule["gate"] == "g3_source_complete_qa_open":
        return checkpoint.get("last_g3_source_status") == (
            "G3_ORIGINAL_SOURCE_COMPLETE_SCIENCE_AUDIO_VIDEO_OPEN")
    return (checkpoint.get("last_controller_status")
            == "BLOCKED_OR_AWAITING_EVIDENCE"
            and checkpoint.get("last_historical_g2_disposition")
            == "G2_ORIGINAL_REQUEST_DISPOSITION_PRESERVED_NO_REPLAY")

_SET_ORACLE = '''
from selenium_pipeline.__MODULE__ import __FUNCTION__

FLAGS = __FLAGS__
MATCH = "__MATCH__"
REQUIRED = {MATCH, "missing_ids", "unexpected_ids", "invalid_input"} | set(FLAGS)

def _shape(result):
    assert type(result) is dict and set(result) == REQUIRED
    assert type(result[MATCH]) is bool
    assert type(result["invalid_input"]) is bool
    assert type(result["missing_ids"]) is list
    assert type(result["unexpected_ids"]) is list
    assert all(result[name] is False for name in FLAGS)

def test_complete_source_evidence_out_of_order():
    observed = __FUNCTION__(["Fig_8-4", "8.2", "8.3A"],
                            ["8.3A", "Fig_8-4", "8.2"])
    _shape(observed)
    assert observed[MATCH] is True and observed["invalid_input"] is False
    assert observed["missing_ids"] == []
    assert observed["unexpected_ids"] == []

def test_gaps_are_sorted_without_acceptance():
    observed = __FUNCTION__(["8.3A", "8.1", "Fig_8-4"],
                            ["Fig_8-4", "8.5", "8.7"])
    _shape(observed)
    assert observed[MATCH] is False and observed["invalid_input"] is False
    assert observed["missing_ids"] == ["8.1", "8.3A"]
    assert observed["unexpected_ids"] == ["8.5", "8.7"]

def test_extra_rendered_asset_without_source_is_detected():
    observed = __FUNCTION__(["8.1"], ["8.1", "8.2"])
    _shape(observed)
    assert observed[MATCH] is False
    assert observed["missing_ids"] == []
    assert observed["unexpected_ids"] == ["8.2"]

def test_empty_and_duplicate_evidence_is_invalid_not_success():
    cases = (([], []), (["8.1", "8.1"], ["8.1"]),
             (["8.1"], ["8.1", "8.1"]))
    for first, second in cases:
        observed = __FUNCTION__(first, second)
        _shape(observed)
        assert observed["invalid_input"] is True
        assert observed[MATCH] is False
        assert observed["missing_ids"] == []
        assert observed["unexpected_ids"] == []

def test_malformed_source_identifiers_never_count_as_acceptance():
    for bad in ("", " ", " 8.2", "8.2 ", "../8.2",
                "8/2", "8.2.png", "A\\\\B", "8..2", 23, False, None):
        observed = __FUNCTION__([bad], ["8.1"])
        _shape(observed)
        assert observed["invalid_input"] is True
        assert observed[MATCH] is False

def test_wrong_container_types_never_count_as_acceptance():
    for first, second in ((None, []), ("8.1", []), ({}, ["8.1"]),
                          ([], None), ([], ("8.1",))):
        observed = __FUNCTION__(first, second)
        _shape(observed)
        assert observed["invalid_input"] is True and observed[MATCH] is False
'''.lstrip()

_ORDER_ORACLE = '''
from selenium_pipeline.__MODULE__ import __FUNCTION__

FLAGS = __FLAGS__
MATCH = "__MATCH__"
REQUIRED = {MATCH, "mismatched_positions", "invalid_input"} | set(FLAGS)

def _shape(result):
    assert type(result) is dict and set(result) == REQUIRED
    assert type(result[MATCH]) is bool
    assert type(result["invalid_input"]) is bool
    assert type(result["mismatched_positions"]) is list
    assert all(result[name] is False for name in FLAGS)

def test_exact_order_is_technical_match_only():
    observed = __FUNCTION__([1, 2, 3], [1, 2, 3])
    _shape(observed)
    assert observed[MATCH] is True and observed["invalid_input"] is False
    assert observed["mismatched_positions"] == []

def test_reordered_valid_ids_never_accepted():
    observed = __FUNCTION__([1, 2, 3], [1, 3, 2])
    _shape(observed)
    assert observed[MATCH] is False and observed["invalid_input"] is False
    assert observed["mismatched_positions"] == [2, 3]

def test_missing_or_extra_tail_produces_one_based_positions():
    for first, second, positions in (
        ([1, 2, 3], [1, 2], [3]),
        ([1, 2], [1, 2, 3], [3]),
        ([1, 2, 3], [1, 3], [2, 3]),
    ):
        observed = __FUNCTION__(first, second)
        _shape(observed)
        assert observed[MATCH] is False and observed["invalid_input"] is False
        assert observed["mismatched_positions"] == positions

def test_duplicate_or_empty_sequences_are_invalid():
    for first, second in (([], []), ([1, 1], [1]),
                          ([1], [1, 1]), ([], [1])):
        observed = __FUNCTION__(first, second)
        _shape(observed)
        assert observed[MATCH] is False and observed["invalid_input"] is True
        assert observed["mismatched_positions"] == []

def test_invalid_numeric_types_do_not_count_as_page_ids():
    for bad in (False, True, 0, -1, 1.0, "1", None):
        observed = __FUNCTION__([bad], [1])
        _shape(observed)
        assert observed[MATCH] is False and observed["invalid_input"] is True
        assert observed["mismatched_positions"] == []

def test_wrong_container_types_are_invalid():
    for first, second in ((None, []), ("1", []),
                          ([], {1: 2}), ((1,), [1])):
        observed = __FUNCTION__(first, second)
        _shape(observed)
        assert observed[MATCH] is False and observed["invalid_input"] is True
'''.lstrip()

_REVIEW_PROVENANCE_ORACLE = '''
from selenium_pipeline.__MODULE__ import __FUNCTION__

FLAGS = __FLAGS__
MATCH = "__MATCH__"
HASH = "a" * 64
OTHER = "b" * 64
KEYS = {"reviewer_id", "request_id", "source_sha256", "evidence_sha256"}
REQUIRED = {MATCH, "conflicting_fields", "invalid_input"} | set(FLAGS)

def _pass(reviewer, request, source=HASH, evidence=HASH):
    return {"reviewer_id": reviewer, "request_id": request,
            "source_sha256": source, "evidence_sha256": evidence}

def _shape(row):
    assert type(row) is dict and set(row) == REQUIRED
    assert type(row[MATCH]) is bool and type(row["invalid_input"]) is bool
    assert type(row["conflicting_fields"]) is list
    assert row["conflicting_fields"] == sorted(set(row["conflicting_fields"]))
    assert all(row[k] is False for k in FLAGS)

def test_two_distinct_owned_responses_have_technical_provenance_not_approval():
    row = __FUNCTION__(HASH, _pass("neon", "send-one"),
                       _pass("hydrogen", "send-two", evidence=OTHER))
    _shape(row)
    assert row[MATCH] is True and row["invalid_input"] is False
    assert row["conflicting_fields"] == []

def test_original_source_hash_mismatches_are_reported_not_approved():
    for first, second, expected in (
        (_pass("neon", "send-one", source=OTHER),
         _pass("hydrogen", "send-two"), ["first_source_sha256"]),
        (_pass("neon", "send-one"),
         _pass("hydrogen", "send-two", source=OTHER), ["second_source_sha256"]),
        (_pass("neon", "send-one", source=OTHER),
         _pass("hydrogen", "send-two", source=OTHER),
         ["first_source_sha256", "second_source_sha256"]),
    ):
        row = __FUNCTION__(HASH, first, second)
        _shape(row)
        assert row[MATCH] is False and row["invalid_input"] is False
        assert row["conflicting_fields"] == expected

def test_same_reviewer_or_same_send_cannot_claim_independent_review():
    for first, second in (
        (_pass("neon", "send-one"), _pass("neon", "send-two")),
        (_pass("neon", "send-one"), _pass("hydrogen", "send-one")),
        (_pass("neon", "send-one"), _pass("neon", "send-one")),
    ):
        row = __FUNCTION__(HASH, first, second)
        _shape(row)
        assert row[MATCH] is False and row["invalid_input"] is True
        assert row["conflicting_fields"] == []

def test_invalid_hash_or_malformed_model_evidence_fails_closed():
    valid = _pass("neon", "send-one")
    another = _pass("hydrogen", "send-two")
    bad = (
        ("ABC", valid, another),
        (HASH.upper(), valid, another),
        (HASH, dict(valid, evidence_sha256="x"), another),
        (HASH, dict(valid, source_sha256="x"), another),
        (HASH, dict(valid, reviewer_id="../escape"), another),
        (HASH, dict(valid, request_id=" "), another),
        (HASH, dict(valid, extra="surprise"), another),
        (HASH, {"request_id": "send-one"}, another),
        (HASH, None, another),
        (HASH, valid, "wrong"),
    )
    for source, first, second in bad:
        row = __FUNCTION__(source, first, second)
        _shape(row)
        assert row[MATCH] is False and row["invalid_input"] is True
        assert row["conflicting_fields"] == []
'''.lstrip()

_HIGHLIGHT_TIMING_ORACLE = '''
from selenium_pipeline.__MODULE__ import __FUNCTION__

FLAGS = __FLAGS__
MATCH = "__MATCH__"
REQUIRED = {MATCH, "mismatched_segments", "invalid_input"} | set(FLAGS)

def seg(element, narration, start, end):
    return {"element_id": element, "narration_id": narration,
            "start_ms": start, "end_ms": end}

def _shape(row):
    assert type(row) is dict and set(row) == REQUIRED
    assert type(row[MATCH]) is bool and type(row["invalid_input"]) is bool
    assert type(row["mismatched_segments"]) is list
    assert row["mismatched_segments"] == sorted(set(row["mismatched_segments"]))
    assert all(type(i) is int and i > 0 for i in row["mismatched_segments"])
    assert all(row[k] is False for k in FLAGS)

def test_nonoverlapping_source_anchored_segments_are_technical_only():
    row = __FUNCTION__(10000, [seg("Fig_8-4", "spoken_1", 0, 1500),
                               seg("Equation_8-3", "spoken_2", 1600, 4900)])
    _shape(row)
    assert row[MATCH] is True and row["invalid_input"] is False
    assert row["mismatched_segments"] == []

def test_overlapping_or_outside_slide_time_is_reported():
    for segments, expected in (
        ([seg("A", "spoken_1", 0, 6000),
          seg("B", "spoken_2", 5000, 8000)], [2]),
        ([seg("A", "spoken_1", 0, 5000),
          seg("B", "spoken_2", 5000, 11000)], [2]),
        ([seg("A", "spoken_1", 0, 15000)], [1]),
    ):
        row = __FUNCTION__(10000, segments)
        _shape(row)
        assert row[MATCH] is False and row["invalid_input"] is False
        assert row["mismatched_segments"] == expected

def test_missing_provenance_or_invalid_timing_never_passes():
    valid = seg("A", "spoken_1", 0, 100)
    for duration, segments in (
        (0, [valid]), (True, [valid]), ("1000", [valid]),
        (1000, []), (1000, None), (1000, [None]),
        (1000, [dict(valid, element_id="")]),
        (1000, [dict(valid, element_id="../source")]),
        (1000, [dict(valid, narration_id="file.wav")]),
        (1000, [dict(valid, start_ms=-1)]),
        (1000, [dict(valid, start_ms=True)]),
        (1000, [dict(valid, end_ms=0)]),
        (1000, [dict(valid, end_ms=1.0)]),
        (1000, [dict(valid, extra=1)]),
        (1000, [valid, dict(valid, element_id="B")]),
    ):
        row = __FUNCTION__(duration, segments)
        _shape(row)
        assert row[MATCH] is False and row["invalid_input"] is True
        assert row["mismatched_segments"] == []
'''.lstrip()


def compile_independent_test(rule: dict) -> bytes:
    """Tests come from reviewed deterministic oracles, not Selenium output."""
    text = {
        "set_coverage": _SET_ORACLE,
        "ordered_alignment": _ORDER_ORACLE,
        "review_provenance": _REVIEW_PROVENANCE_ORACLE,
        "highlight_timing": _HIGHLIGHT_TIMING_ORACLE,
    }[rule["kind"]]
    substitutions = {
        "__MODULE__": rule["id"],
        "__FUNCTION__": rule["function"],
        "__MATCH__": rule["output"],
        "__FLAGS__": repr(tuple(rule["false_flags"])),
    }
    for old, new in substitutions.items():
        text = text.replace(old, new)
    require = set(("__MODULE__", "__FUNCTION__", "__MATCH__", "__FLAGS__"))
    need(not any(marker in text for marker in require),
         "Unresolved original independently reviewed test oracle")
    need(100 <= len(text.encode("utf8")) < 12_000,
         "Derived source test outside bounded worker limits")
    compile(text, "independent_source_grounded_test", "exec")
    return text.encode("utf8")

def derive(*, backlog_root: Path, repo_root: Path, git):
    """Stage one new technical code task based on a real unresolved QA gate."""
    need(lookup_mechanism(KIND, SIGNATURE) == MECHANISM,
         "Source-grounded test derivation not in executable recovery registry")
    backlog_root = Path(backlog_root).absolute()
    repo_root = Path(repo_root).absolute()
    rule_file = repo_root / MANIFEST
    checkpoint_file = repo_root.parent / "live_state_migrated_v1" / "daemon_heartbeat.json"
    if not rule_file.exists() and not rule_file.is_symlink():
        return {"status":"NO_NEW_APPROVED_SOURCE_TEST_JOBS",
                "new_coding_jobs":0, "model_sends":0,
                "paid_api_requests":0,"student_publication_authorized":False}
    need(backlog_root.is_dir() and repo_root.is_dir()
         and not backlog_root.is_symlink() and not repo_root.is_symlink()
         and (backlog_root / "inbox").is_dir()
         and (backlog_root / "state").is_dir()
         and not (backlog_root / "inbox").is_symlink()
         and not repo_root.is_relative_to(backlog_root),
         "Source-grounded task store inaccessible or aliased")
    current = git(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
    remote = git(["gh", "api", "repos/tlyoon/MicroGen_AI_Web/commits/main",
                  "--jq", ".sha"])
    need(re.fullmatch(r"[a-f0-9]{40}", current)
         and remote == current
         and git(["git", "-C", str(repo_root), "status", "--porcelain"]) == "",
         "Source rules not on clean exact protected GitHub main")
    rules, rule_sha = _rules(repo_root, git)
    if not checkpoint_file.is_file() or checkpoint_file.is_symlink():
        return {"status":"SOURCE_G2G3_CHECKPOINT_UNAVAILABLE_NO_NEW_JOB",
                "new_coding_jobs":0,"model_sends":0,
                "paid_api_requests":0,"student_publication_authorized":False}
    checkpoint = read_json(checkpoint_file)
    need(type(checkpoint) is dict,
         "Corrupt G2/G3 checkpoint cannot authorize new development")
    discovered = 0
    for rule in rules:
        if not _gate_open(rule, checkpoint):
            continue
        discovered += 1
        job_id = rule["id"]
        manifest = backlog_root / "inbox" / (job_id + ".json")
        need(not manifest.is_symlink(), "Derived original claim redirected")
        if manifest.exists():
            need(manifest.is_file(), "Existing original code job is not a file")
            continue
        worktrees = backlog_root.parent / "MICROGEN_AUTONOMOUS_CODE_WORKTREES_V1"
        need(worktrees.is_dir() and not worktrees.is_symlink(),
             "Isolated original code worktree root not certified")
        repo = worktrees / ("job_" + job_id)
        need(not repo.exists() and not repo.is_symlink(),
             "Unreconciled previous source-grounded Git worktree")
        test = "tests/test_" + job_id + ".py"
        target = "selenium_pipeline/" + job_id + ".py"
        source = compile_independent_test(rule)
        digest = sha(source)
        receipt_dir = backlog_root / "derived_requirements_v1"
        receipt_dir.mkdir(exist_ok=True)
        need(not receipt_dir.is_symlink(),
             "Pinned independent-test receipt redirected")
        receipt_file = receipt_dir / (job_id + ".json")
        pinned = {
            "schema_version":1, "job_id":job_id, "gate":rule["gate"],
            "requirement_rule_sha256":rule_sha,
            "independent_test_sha256":digest,
            "test":test, "target":target,
            "observed_g2g3_status":checkpoint["status"],
            "observed_g3_source_status":checkpoint.get("last_g3_source_status"),
            "observed_g2_disposition":checkpoint.get("last_historical_g2_disposition"),
            "protected_main_sha":current, "source_generation_model_sends":0,
            "paid_api_authorized":False, "student_publication_authorized":False,
            "independent_academic_acceptance":False
        }
        content = (json.dumps(pinned,sort_keys=True,indent=2)+"\n").encode("utf8")
        if receipt_file.exists():
            need(receipt_file.is_file() and receipt_file.read_bytes()==content,
                 "Existing original G2/G3 requirement evidence changed")
        else:
            with receipt_file.open("xb") as out:
                out.write(content)
                out.flush()
                os.fsync(out.fileno())
        branch = "feature/approved_" + job_id
        git(["git","-C",str(repo_root),"worktree","add","-b",branch,
             str(repo),"HEAD"],timeout=90)
        destination = repo / test
        destination.parent.mkdir(parents=True,exist_ok=True)
        need(not destination.parent.is_symlink(), "Untrusted test directory")
        with destination.open("xb") as out:
            out.write(source)
            out.flush()
            os.fsync(out.fileno())
        need(sha(destination.read_bytes())==digest,
             "Independent original test lost its immutable SHA")
        git(["git","-C",str(repo),"add","--",test])
        git(["git","-C",str(repo),"commit","-m",
             "Pin source-grounded independently constructed test "+job_id])
        base = git(["git","-C",str(repo),"rev-parse","HEAD"])
        job = {
            "schema_version":1, "project":"MicroGen_AI_Web",
            "job_id":job_id, "authorized":True,
            "repo":str(repo), "base_sha":base, "branch":branch,
            "target":target, "target_original_sha256":None,
            "test":test,"test_sha256":digest,
            "context_path":test,"context_sha256":digest,
            "instruction":rule["instruction"],
            "selenium_mode":"hydrogen","max_wait_seconds":150,
            "browser_model_claims":1,"paid_api":False,
            "student_publication":False
        }
        job_data = (json.dumps(job,sort_keys=True,indent=2)+"\n").encode("utf8")
        with manifest.open("xb") as out:
            out.write(job_data)
            out.flush()
            os.fsync(out.fileno())
        validate_job(root=backlog_root,file=manifest)
        return {
            "status":"SOURCE_GROUNDED_INDEPENDENT_TEST_JOB_STAGED",
            "job":job_id,"source_gate":rule["gate"],
            "source_main_sha":current,
            "independent_test_sha256":digest,
            "manifest_sha256":sha(job_data),"source_commit":base,
            "new_coding_jobs":1,"model_sends":0,
            "paid_api_requests":0,"student_publication_authorized":False
        }
    return {
        "status":("SOURCE_G2G3_REQUIREMENT_TEST_JOBS_EXHAUSTED"
                  if discovered else "NO_VERIFIED_OPEN_G2G3_REQUIREMENT"),
        "new_coding_jobs":0,"model_sends":0,
        "paid_api_requests":0,"student_publication_authorized":False
    }
