"""Fault-injection and real receipt tests for evidence-driven stall recovery."""
import hashlib
import json
from pathlib import Path

import pytest

from selenium_pipeline.development_acceptance_frontier_v1 import (
    GATES, QUARANTINED, assess, _acceptance,
)
from selenium_pipeline.recovery_registry import lookup_mechanism


def sha(b):
    return hashlib.sha256(b).hexdigest()


def receipt():
    gates = [
        {"gate_id": name, "accepted": name == "G3_ORIGINAL_VIDEO_PAGE_TECHNICAL",
         "status": "TECHNICAL_PASS_NOT_VIDEO_QA" if name ==
                   "G3_ORIGINAL_VIDEO_PAGE_TECHNICAL" else "INDEPENDENT_REVIEW_OPEN",
         "next_action": "Obtain genuinely new independent academic source evidence"}
        for name in GATES
    ]
    return {
        "schema_version": 1,
        "scope_sha256": "a" * 64,
        "student_publication_authorized": False,
        "original_historical_requests_replayed": False,
        "all_G2_G3_requirements_accepted": False,
        "new_browser_sends": 0,
        "paid_gemini_API_calls": 0,
        "academically_accepted_gates": 0,
        "technical_only_gates_passed": 1,
        "acceptance_gates": gates,
        "actions": {
            "G2_SOURCE": {"total_two_pass_AI_agreements": 29, "original_total": 85},
            "G3_SCIENCE": {
                "original_possible_model_sends_reserved": 4,
                "original_immutable_campaign_send_cap": 4,
                "remaining_source_science_tasks": 1,
            },
        },
    }


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n",
                    encoding="utf8")


@pytest.fixture
def setup(tmp_path):
    ac = tmp_path / "academic"
    backlog = tmp_path / "backlog"
    control = tmp_path / "control"
    repo = tmp_path / "repo"
    for path in (ac, backlog, control, repo):
        path.mkdir()
    write(ac / "evidence.json", receipt())
    return (ac, backlog, control, repo)


def run(parts):
    ac, backlog, control, repo = parts
    return assess(acceptance_root=ac, backlog_root=backlog,
                  control_root=control, repo_root=repo,
                  current_main_sha="b" * 40)


def original_quarantine(parts, job_id=QUARANTINED[0]):
    _, backlog, _, _ = parts
    reply = b"Gemini said\n\ndef compare_original(a, b):\npass\n"
    test = b"def test_original():\n    assert True\n"
    source = backlog.parent / (job_id + "_original")
    (source / "tests").mkdir(parents=True)
    (source / "tests/test_original.py").write_bytes(test)
    job = {
        "job_id": job_id,
        "repo": str(source),
        "target": "selenium_pipeline/verified_original.py",
        "test": "tests/test_original.py",
        "test_sha256": sha(test),
        "paid_api": False,
        "student_publication": False,
    }
    inbox = backlog / "inbox" / (job_id + ".json")
    write(inbox, job)
    state = backlog / "state" / job_id
    state.mkdir(parents=True)
    (state / "original_model_reply.txt").write_bytes(reply)
    write(state / "coding_state.json", {
        "job_id": job_id, "job_sha256": sha(inbox.read_bytes()),
        "status": "UNSAFE_MODEL_REPLY_QUARANTINED",
        "model_claims": 1, "model_sends": 1,
        "paid_api_requests": 0, "student_publication_authorized": False,
        "model_reply_sha256": sha(reply),
    })
    return state


def test_recovery_is_registered():
    assert lookup_mechanism(
        "academic_evidence_frontier_recovery",
        "G2G3_TECHNICAL_QUEUE_EXHAUSTED_WITH_OPEN_INDEPENDENT_ACCEPTANCE_GATES"
    ) == "TRACK_VERIFIED_ACCEPTANCE_DELTA_AND_STAGE_ONE_SHA_PINNED_RECOVERY"


def test_live_academic_baseline_is_not_technical_success(setup):
    row = run(setup)
    assert row["status"] == "ACADEMIC_STALL_EXTERNAL_EVIDENCE_REQUIRED"
    assert row["academic_metrics"]["g2_two_pass_agreements"] == 29
    assert row["academic_metrics"]["g2_remaining"] == 56
    assert row["academic_metrics"]["g3_original_sends_reserved"] == 4
    assert row["academic_metrics"]["independent_academic_gates_accepted"] == 0
    assert len(row["remaining_gates"]) == 7
    assert row["provider_sends"] == row["paid_api_requests"] == 0
    assert row["student_publication_authorized"] is False


def test_real_quarantined_source_becomes_pinned_work_not_model_resend(setup):
    original_quarantine(setup)
    first = run(setup)
    assert first["status"] == "ACADEMIC_STALL_REPAIRABLE_SOURCE_JOB_IDENTIFIED"
    assert first["next_work"]["job_id"] == QUARANTINED[0]
    assert first["next_work"]["new_model_send_authorized"] is False
    work_file = (setup[2] / "academic_recovery_work_items_v1" /
                 (QUARANTINED[0] + ".json"))
    witness = json.loads(work_file.read_text("utf8"))
    assert witness["original_reply_sha256"] == first["next_work"]["original_reply_sha256"]
    assert witness["provider_sends"] == 0
    for i in range(1, 4):
        next_row = run(setup)
        assert next_row["unchanged_cycles"] == i
        assert next_row["stall_escalation"] is (i >= 2)
        assert json.loads(work_file.read_text("utf8")) == witness


def test_verified_main_source_repair_does_not_replay_quarantine(setup):
    original_quarantine(setup)
    (setup[3] / "selenium_pipeline").mkdir()
    (setup[3] / "selenium_pipeline/verified_original.py").write_text(
        "# independently CI-reviewed source exists\n", encoding="utf8")
    (setup[3] / "tests").mkdir()
    original = (setup[1].parent / (QUARANTINED[0] + "_original") /
                "tests/test_original.py")
    (setup[3] / "tests/test_original.py").write_bytes(original.read_bytes())
    row = run(setup)
    assert row["status"] == "ACADEMIC_STALL_EXTERNAL_EVIDENCE_REQUIRED"
    assert row["unresolved_quarantined_source_jobs"] == 0


def test_new_genuine_g2_agreement_resets_stall_counter(setup):
    run(setup)
    run(setup)
    path = setup[0] / "evidence.json"
    newer = receipt()
    newer["actions"]["G2_SOURCE"]["total_two_pass_AI_agreements"] = 30
    write(path, newer)
    row = run(setup)
    assert row["unchanged_cycles"] == 0
    assert row["academic_metrics"]["g2_two_pass_agreements"] == 30
    assert row["stall_escalation"] is False


def test_regressed_accepted_academic_evidence_fails_closed(setup):
    path = setup[0] / "evidence.json"
    current = receipt()
    current["actions"]["G2_SOURCE"]["total_two_pass_AI_agreements"] = 30
    write(path, current)
    run(setup)
    write(path, receipt())
    with pytest.raises(ValueError, match="regressed"):
        run(setup)


def test_original_reply_sha_tampering_does_not_resume_send(setup):
    state = original_quarantine(setup)
    (state / "original_model_reply.txt").write_bytes(b"changed reply")
    with pytest.raises(ValueError, match="identity changed"):
        run(setup)


def test_false_independent_academic_claim_rejected():
    row = receipt()
    row["acceptance_gates"][0]["accepted"] = True
    with pytest.raises(ValueError, match="Technical-only pass"):
        _acceptance(row)


def test_overreserved_model_campaign_rejected():
    row = receipt()
    row["actions"]["G3_SCIENCE"]["original_possible_model_sends_reserved"] = 5
    with pytest.raises(ValueError, match="budget"):
        _acceptance(row)


def test_missing_original_receipt_never_fabricates_progress(setup):
    (setup[0] / "evidence.json").unlink()
    with pytest.raises(ValueError, match="No genuine"):
        run(setup)


def test_provider_replay_or_publication_claim_refused():
    row = receipt()
    row["original_historical_requests_replayed"] = True
    with pytest.raises(ValueError, match="provider"):
        _acceptance(row)
    row = receipt()
    row["student_publication_authorized"] = True
    with pytest.raises(ValueError, match="provider"):
        _acceptance(row)


def test_genuine_accepted_gate_does_not_fail_on_old_zero_baseline(setup):
    first = run(setup)
    assert first["academic_metrics"]["independent_academic_gates_accepted"] == 0
    updated = receipt()
    updated["acceptance_gates"][0]["accepted"] = True
    updated["academically_accepted_gates"] = 1
    write(setup[0] / "evidence.json", updated)
    second = run(setup)
    assert second["academic_metrics"]["independent_academic_gates_accepted"] == 1
    assert second["unchanged_cycles"] == 0


def test_native_controller_uses_frontier_after_exhaustion(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from selenium_pipeline import development_autonomous_code_loop_v1 as ctl
    from selenium_pipeline import development_acceptance_frontier_v1 as frontier
    repo, backlog, control, template, cutover = [
        tmp_path / name for name in ("repo", "backlog", "control", "template",
                                     "cutover")
    ]
    for folder in (repo, backlog, control, template, cutover):
        folder.mkdir()
    (backlog / "inbox").mkdir()
    (control / "promotions/worktrees").mkdir(parents=True)
    (tmp_path / "ACCEPTANCE_COMPLETION_SCHEDULER_V1").mkdir()
    monkeypatch.setattr(ctl, "_owner_repo", lambda: repo)
    monkeypatch.setattr(
        ctl.subprocess, "run",
        lambda *a, **k: SimpleNamespace(stdout="b" * 40 + "\n"))
    seen = []
    def fake_assess(**kw):
        seen.append(kw)
        return {"status": "ACADEMIC_STALL_EXTERNAL_EVIDENCE_REQUIRED",
                "provider_sends": 0, "student_publication_authorized": False}
    monkeypatch.setattr(frontier, "assess", fake_assess)
    result = ctl.cycle(
        backlog_root=backlog, control_root=control,
        template_root=template, cutover_root=cutover,
        catalog_path=tmp_path/"not_used.json",
        source_sync_fn=lambda **kw:
            {"status": "EXACT_PROTECTED_MAIN_CURRENT"},
        select_fn=lambda **kw:
            {"status": "SOURCE_G2G3_REQUIREMENT_TEST_JOBS_EXHAUSTED",
             "new_coding_jobs": 0, "model_sends": 0})
    assert result["academic_frontier"]["status"].startswith("ACADEMIC_STALL")
    assert len(seen) == 1
    assert seen[0]["current_main_sha"] == "b" * 40
    assert seen[0]["acceptance_root"].name == (
        "ACCEPTANCE_COMPLETION_SCHEDULER_V1")
    assert result["new_model_sends"] == 0
    assert result["new_paid_gemini_API_calls"] == 0
    assert result["student_publication_authorized"] is False


def test_source_sync_hold_prevents_frontier_use(tmp_path, monkeypatch):
    from selenium_pipeline import development_autonomous_code_loop_v1 as ctl
    from selenium_pipeline import development_acceptance_frontier_v1 as frontier
    repo, backlog, control, template, cutover = [
        tmp_path / name for name in ("repo", "backlog", "control", "template",
                                     "cutover")
    ]
    for folder in (repo, backlog, control, template, cutover):
        folder.mkdir()
    (backlog / "inbox").mkdir()
    (control / "promotions/worktrees").mkdir(parents=True)
    monkeypatch.setattr(ctl, "_owner_repo", lambda: repo)
    monkeypatch.setattr(
        frontier, "assess",
        lambda **kw: pytest.fail("Stale code must not inspect academic frontier"))
    result = ctl.cycle(
        backlog_root=backlog, control_root=control,
        template_root=template, cutover_root=cutover,
        catalog_path=tmp_path/"not_used.json",
        source_sync_fn=lambda **kw:
            {"status": "CERTIFIED_MAIN_SOURCE_CUTOVER_HELD"},
        select_fn=lambda **kw:
            {"status": "SOURCE_G2G3_REQUIREMENT_TEST_JOBS_EXHAUSTED"})
    assert "academic_frontier" not in result


@pytest.mark.parametrize("file,source_sha", [
    ("test_g3_figure_caption_identity_v1.py",
     "9ff88f13f80d73f06e6337d4f9c59f2a80c61a36ac4cd60959665e6f1ea03b50"),
    ("test_g3_narration_segment_page_index_v1.py",
     "c08463039a9f3b6d0e1e7f1c36eb170beef3fbf7ddf535b3a595a155a591102e"),
    ("test_g3_captioned_png_asset_coverage_v1.py",
     "6f1cbe1a1c00bfe17a3d5705073e7981563d0282134c2c17b66c396df964c6f0"),
])
def test_original_independent_tests_remain_byte_identical(file, source_sha):
    assert sha((Path(__file__).parent / file).read_bytes()) == source_sha


def test_source_file_without_original_test_is_not_treated_as_recovered(setup):
    original_quarantine(setup)
    (setup[3] / "selenium_pipeline").mkdir()
    (setup[3] / "selenium_pipeline/verified_original.py").write_text(
        "def placeholder(): return True\n", encoding="utf8")
    row = run(setup)
    assert row["status"] == "ACADEMIC_STALL_REPAIRABLE_SOURCE_JOB_IDENTIFIED"
    assert row["unresolved_quarantined_source_jobs"] == 1
