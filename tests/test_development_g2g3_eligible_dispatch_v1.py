"""Fault-injection regression for original-source-only G2/G3 auto-dispatch."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from selenium_pipeline.development_g2g3_eligible_dispatch_v1 import (
    CONFIG_NAME, STATUS, KIND, SIGNATURE, MECHANISM, discover,
)
from selenium_pipeline.development_continuity_executor_v71 import _plan
from selenium_pipeline.recovery_registry import lookup_mechanism


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def original(tmp_path):
    source = tmp_path / "textbook_source"
    source.mkdir()
    for name in ("source.pdf", "slides.pdf", "script.txt"):
        (source / name).write_bytes(("original " + name).encode())
    identities = {name: _sha(source / name)
                  for name in ("source.pdf", "slides.pdf", "script.txt")}
    queue = tmp_path / "original_g2_queue"
    queue.mkdir()
    (queue / "slide_001_initial_review.json").write_text('{"historic":true}')
    (queue / "slide_001_independent_challenge.json").write_text('{"historic":true}')
    # Slide 2 has an old uncertain request window. Preflight may inspect
    # its original claim, but the generated worker cannot make a Send.
    (queue / "slide_002_initial_review_attempt_01.json").write_text(
        '{"historic_uncertain_send":true}')
    rows = []
    for slide, count in ((1, 1), (2, 3), (3, 2)):
        rows.append({
            "slide": slide, "utterance_count": count,
            "original_source_sha256": identities["source.pdf"],
            "original_slides_sha256": identities["slides.pdf"],
            "original_script_sha256": identities["script.txt"],
        })
    q = {"status": "ORIGINAL_SOURCE_REVIEW_QUEUE",
         "original_source_folder": str(source),
         "slide_jobs": rows, "expected_utterances": 6,
         "provider_requests_performed": 0,
         "approved_math_utterances": [],
         "student_publication_authorized": False}
    (queue / "queue.json").write_text(json.dumps(q))
    progress = tmp_path / "original_g3_source_progress.json"
    progress.write_text(json.dumps({
        "schema_version": 1, "source_only_completed": True,
        "source_scientific_QA_complete": False,
        "independent_acoustic_QA_complete": False,
        "independent_video_highlight_QA_complete": False,
        "new_browser_sends": 0, "new_paid_gemini_API_calls": 0,
        "student_publication_authorized": False,
        "source_sections": {
            section: {"status": "SOURCE_SCOPE_COMPLETE", "remaining": 0}
            for section in ("Serway_8_2", "Serway_8_3")},
    }))
    inbox = tmp_path / "offline_handoff"
    inbox.mkdir()
    state = tmp_path / "immutable_state"
    state.mkdir()
    config = {
        "schema_version": 1, "status": STATUS,
        "g2_queue": str(queue), "g2_queue_sha256": _sha(queue / "queue.json"),
        "g2_source": str(source), "g2_inputs_sha256": identities,
        "g3_progress": str(progress), "g3_progress_sha256": _sha(progress),
        "max_slides": 4, "provider_requests_authorized": 0,
        "student_publication_authorized": False,
    }
    (inbox / CONFIG_NAME).write_text(json.dumps(config))
    return {"source": source, "queue": queue, "progress": progress,
            "inbox": inbox, "state": state, "config": config}


def _put_config(original, config):
    (original["inbox"] / CONFIG_NAME).write_text(json.dumps(config))


def test_registered_only_specific_original_recovery():
    assert lookup_mechanism(KIND, SIGNATURE) == MECHANISM


def test_missing_explicit_source_contract_never_fabricates_workers(original):
    (original["inbox"] / CONFIG_NAME).unlink()
    result = discover(handoff_dir=original["inbox"], state_dir=original["state"])
    assert result["status"] == "NO_SOURCE_PINNED_AUTO_DISCOVERY_CONFIG"
    assert result["new_plans"] == 0
    assert not list(original["inbox"].glob("next_*"))


def test_first_real_source_prep_plan_is_allowlisted_and_exact(original):
    r = discover(handoff_dir=original["inbox"], state_dir=original["state"])
    assert r["status"] == "G2_SOURCE_PREFLIGHT_HANDOFF_ADMITTED"
    assert r["source_g2_slides"] == [2, 3]
    assert r["source_g2_jobs"] == 2
    assert r["new_plans"] == 1
    assert r["new_browser_sends"] == 0
    assert r["new_paid_gemini_API_calls"] == 0
    assert r["student_publication_authorized"] is False
    assert r["g3_status"] == (
        "G3_ORIGINAL_SOURCE_COMPLETE_SCIENCE_AUDIO_VIDEO_OPEN")
    p = Path(r["handoff_plan"])
    expected = _plan(p)
    assert len(expected["tasks"]) == 2
    assert all(t["action"] == "g2_review_preflight"
               and t["authorized"] is True
               and t["workstream"] == "g2"
               and t["max_attempts"] == 1
               and not t["depends_on"]
               for t in expected["tasks"])
    assert [t["params"]["slide"] for t in expected["tasks"]] == [2, 3]


def test_restart_no_second_source_plan_or_replay(original):
    first = discover(handoff_dir=original["inbox"], state_dir=original["state"])
    saved = Path(first["handoff_plan"]).read_bytes()
    second = discover(handoff_dir=original["inbox"], state_dir=original["state"])
    assert second["new_plans"] == 0
    assert second["status"] == "G2_SOURCE_PREFLIGHT_ALREADY_CLAIMED_NO_REPLAY"
    assert Path(first["handoff_plan"]).read_bytes() == saved
    assert len(list(original["inbox"].glob("next_*"))) == 1


@pytest.mark.parametrize("what", ["source.pdf", "slides.pdf", "script.txt",
                                   "queue", "g3_progress"])
def test_mutated_immutable_sources_fail_before_dispatch(original, what):
    if what in ("source.pdf", "slides.pdf", "script.txt"):
        path = original["source"] / what
    elif what == "queue":
        path = original["queue"] / "queue.json"
    else:
        path = original["progress"]
    with path.open("ab") as f:
        f.write(b" ")
    with pytest.raises(ValueError, match="changed"):
        discover(handoff_dir=original["inbox"], state_dir=original["state"])
    assert not list(original["inbox"].glob("next_*"))


@pytest.mark.parametrize("field,value", [
    ("provider_requests_authorized", 1),
    ("student_publication_authorized", True),
    ("max_slides", 100),
])
def test_unapproved_operation_cannot_create_work(original, field, value):
    c = dict(original["config"])
    c[field] = value
    _put_config(original, c)
    with pytest.raises(ValueError, match="unsafe"):
        discover(handoff_dir=original["inbox"], state_dir=original["state"])
    assert not list(original["inbox"].glob("next_*"))


def test_old_source_scope_not_scientifically_completed(original):
    progress = json.loads(original["progress"].read_text())
    progress["source_scientific_QA_complete"] = True
    original["progress"].write_text(json.dumps(progress))
    c = dict(original["config"])
    c["g3_progress_sha256"] = _sha(original["progress"])
    _put_config(original, c)
    with pytest.raises(ValueError, match="G3 original source scope"):
        discover(handoff_dir=original["inbox"], state_dir=original["state"])


def test_duplicate_g2_slide_identity_cannot_be_admitted(original):
    q = json.loads((original["queue"] / "queue.json").read_text())
    q["slide_jobs"].append(q["slide_jobs"][0])
    q["expected_utterances"] += 1
    (original["queue"] / "queue.json").write_text(json.dumps(q))
    c = dict(original["config"])
    c["g2_queue_sha256"] = _sha(original["queue"] / "queue.json")
    _put_config(original, c)
    with pytest.raises(ValueError, match="G2 jobs diverged"):
        discover(handoff_dir=original["inbox"], state_dir=original["state"])


def test_prior_same_named_plan_cannot_be_silently_replaced(original):
    r = discover(handoff_dir=original["inbox"], state_dir=original["state"])
    path = Path(r["handoff_plan"])
    path.write_bytes(b"{}")
    with pytest.raises(ValueError, match="changed after admission"):
        discover(handoff_dir=original["inbox"], state_dir=original["state"])


def test_source_only_complete_without_open_review_scopes_no_fake_work(original):
    for slide in (2, 3):
        (original["queue"] / f"slide_{slide:03d}_initial_review.json").write_text("{}")
        (original["queue"] / f"slide_{slide:03d}_independent_challenge.json").write_text("{}")
    r = discover(handoff_dir=original["inbox"], state_dir=original["state"])
    assert r["status"] == "NO_NEW_SOURCE_ONLY_WORK_AWAITING_INDEPENDENT_QA"
    assert r["new_plans"] == 0
    assert not list(original["inbox"].glob("next_*"))
