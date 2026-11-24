"""Completion-driven G2/G3 scheduler: real journal identities, no provider Sends."""
from __future__ import annotations
import json
from pathlib import Path

import pytest
from selenium_pipeline import acceptance_completion_scheduler_v1 as scheduler
from selenium_pipeline.recovery_registry import lookup_mechanism


@pytest.fixture()
def roots(tmp_path):
    original=tmp_path/"g2_source"
    original.mkdir()
    (original/"source.pdf").write_bytes(b"%PDF-1.4\n original")
    queue=tmp_path/"g2_queue"
    queue.mkdir()
    (queue/"queue.json").write_text(json.dumps({
        "original_source_folder":str(original),"expected_utterances":85}))
    c=queue/"autonomous_recovery_continuation_v1"/"original_g2_campaign"
    c.mkdir(parents=True)
    (c/"campaign.json").write_text(json.dumps({
        "status":"SOURCE_BOUND_AUTOFORWARD_CAMPAIGN_V1",
        "max_possible_model_sends":0}))
    state=tmp_path/"g3_state"
    state.mkdir()
    g=state/"g3_continuous_advance_v1"/"original_g3_campaign"
    g.mkdir(parents=True)
    (g/"campaign.json").write_text(json.dumps({
        "status":"SOURCE_BOUND_AUTOFORWARD_CAMPAIGN_V1",
        "max_possible_model_sends":4}))
    (g/"event_001.json").write_text(json.dumps({
        "type":"RESERVE","phase":"INITIAL"}))
    manifest=tmp_path/"g3_manifest.json"
    manifest.write_text('{"source":"original Serway 8.2/8.3"}')
    media=tmp_path/"g3_media";media.mkdir()
    report=tmp_path/"reports"
    return dict(g2_source=original,g2_queue=queue,
                g2_campaign="original_g2_campaign",
                g3_manifest=manifest,g3_state=state,
                g3_campaign="original_g3_campaign",
                g3_media=media,report_root=report)


def good_g2(**kw):
    assert kw["campaign"]=="original_g2_campaign"
    return {"status":"G2_REAL_SOURCE_AGREEMENT_RECONCILED_NO_SEND",
        "original_total":85,"total_two_pass_AI_agreements":29,
        "pending_or_disputed":56,
        "new_browser_sends":0,"new_paid_gemini_API_calls":0,
        "independent_academic_QA_complete":False,
        "student_publication_authorized":False}


def good_g3(**kw):
    assert kw["campaign"]=="original_g3_campaign"
    return {"status":"FINITE_G3_SOURCE_CAMPAIGN_BUDGET_EXHAUSTED",
        "original_immutable_campaign_send_cap":4,
        "original_possible_model_sends_reserved":4,
        "remaining_source_science_tasks":2,
        "new_browser_sends":0,"new_paid_gemini_API_calls":0,
        "independent_scientific_QA_complete":False,
        "student_publication_authorized":False}


def good_media(**kw):
    return {"status":"G3_SOURCE_PINNED_TECHNICAL_MEDIA_REVERIFIED_NO_RELEASE",
        "original_subsections_checked":2,
        "source_video_pages_pixel_witnessed":32,
        "new_browser_sends":0,"new_paid_gemini_API_calls":0,
        "independent_scientific_QA_complete":False,
        "independent_video_highlight_QA_complete":False,
        "student_publication_authorized":False}


def run(roots,**kwargs):
    return scheduler.run(**roots,
        g2_runner=kwargs.get("g2_runner",good_g2),
        g3_science_runner=kwargs.get("g3_science_runner",good_g3),
        g3_media_runner=kwargs.get("g3_media_runner",good_media))


def test_executable_registry_contains_completion_scheduler():
    assert lookup_mechanism(
        scheduler.KIND,scheduler.SIGNATURE)==scheduler.MECHANISM


def test_every_g2_g3_acceptance_gate_explicit_not_falsely_closed(roots):
    result=run(roots)
    assert result["G2_source_AI_agreed"]==29
    assert result["G2_source_AI_required"]==85
    assert result["G3_historical_sends_reserved"]==4
    assert result["G3_historical_send_cap"]==4
    assert result["G3_science_tasks_eligible"]==2
    assert result["G3_original_video_pages_technical"]==32
    assert result["academically_accepted_gates"]==0
    assert result["source_only_workstreams_completed"]==[
        "G2_SOURCE","G3_MEDIA","G3_SCIENCE"]
    assert result["new_browser_sends"]==0
    assert result["paid_gemini_API_calls"]==0
    assert result["student_publication_authorized"] is False
    saved=json.loads(Path(result["receipt"]).read_text("utf8"))
    assert len(saved["acceptance_gates"])==8
    matrix={row["gate_id"]:row for row in saved["acceptance_gates"]}
    assert matrix["G2_INDEPENDENT_SOURCE_AI"]["accepted_units"]==29
    assert matrix["G2_INDEPENDENT_SOURCE_AI"]["required_units"]==85
    assert matrix["G3_INDEPENDENT_SCIENCE"]["status"]==(
        "BLOCKED_EXHAUSTED_ORIGINAL_MODEL_SEND_CAP")
    assert matrix["G3_ORIGINAL_VIDEO_PAGE_TECHNICAL"]["status"]==(
        "TECHNICAL_PASS_NOT_VIDEO_QA")
    assert matrix["G3_WITHIN_SLIDE_VISUAL_HIGHLIGHT_QA"]["accepted"] is False
    assert matrix["END_TO_END_PRODUCTION_RELEASE"]["accepted"] is False
    assert saved["original_historical_requests_replayed"] is False


def test_identical_source_and_claims_restart_exact_same_immutable_receipt(roots):
    a=run(roots)
    packet=Path(a["receipt"])
    original=packet.read_bytes()
    b=run(roots)
    assert a==b
    assert packet.read_bytes()==original
    assert len(list(roots["report_root"].glob("*.json")))==1


def test_one_stale_g2_recovery_does_not_strand_independent_g3(roots):
    order=[]
    def broken_g2(**kw):
        order.append("G2")
        raise RuntimeError("Original source renderer unavailable")
    def done_g3(**kw):
        order.append("G3")
        return good_g3(**kw)
    def done_media(**kw):
        order.append("MEDIA")
        return good_media(**kw)
    a=run(roots,g2_runner=broken_g2,
          g3_science_runner=done_g3,g3_media_runner=done_media)
    assert order==["G2","G3","MEDIA"]
    assert a["G2_source_AI_agreed"] is None
    assert a["G3_science_tasks_eligible"]==2
    assert a["G3_original_video_pages_technical"]==32
    assert a["independent_workstreams_held"]["G2_SOURCE"][
        "status"]=="BLOCKED_SPECIFIC_WORKSTREAM"
    assert a["all_G2_G3_requirements_accepted"] is False


def test_late_g3_media_blocker_does_not_erase_completed_independent_g2(roots):
    def bad(**kw):
        raise ValueError("Source video PDF pixels changed")
    a=run(roots,g3_media_runner=bad)
    assert a["G2_source_AI_agreed"]==29
    assert a["G3_historical_sends_reserved"]==4
    assert "G3_MEDIA" in a["independent_workstreams_held"]
    assert a["G3_original_video_pages_technical"] is None
    assert a["new_browser_sends"]==0


def test_fake_successful_model_send_or_paid_api_is_not_g2_acceptance(roots):
    def fake(**kw):
        out=good_g2(**kw)
        out["new_browser_sends"]=1
        return out
    a=run(roots,g2_runner=fake)
    assert "G2_SOURCE" in a["independent_workstreams_held"]
    assert a["G2_source_AI_agreed"] is None
    assert a["G3_original_video_pages_technical"]==32


def test_fake_independent_video_QA_cannot_be_promoted(roots):
    def bad(**kw):
        out=good_media(**kw)
        out["independent_video_highlight_QA_complete"]=True
        return out
    a=run(roots,g3_media_runner=bad)
    assert "G3_MEDIA" in a["independent_workstreams_held"]
    assert a["G3_original_video_pages_technical"] is None
    assert a["student_publication_authorized"] is False


def test_original_uncertain_g3_journal_mutation_blocks_checkpoint(roots):
    def bad(**kw):
        home=(roots["g3_state"]/"g3_continuous_advance_v1"/
              "original_g3_campaign"/"event_001.json")
        home.write_text(json.dumps({"type":"FORGED_ACCEPTANCE"}))
        return good_g3(**kw)
    with pytest.raises(ValueError,match="mutate original Send journals"):
        run(roots,g3_science_runner=bad)
    assert not roots["report_root"].exists()


def test_original_g2_queue_mutation_blocks_checkpoint_even_if_media_good(roots):
    def bad(**kw):
        path=roots["g2_queue"]/"queue.json"
        path.write_text(json.dumps({
            "original_source_folder":str(roots["g2_source"]),
            "expected_utterances":85,"forged_agreement":85}))
        return good_g2(**kw)
    with pytest.raises(ValueError,match="mutate original Send journals"):
        run(roots,g2_runner=bad)
    assert not roots["report_root"].exists()


def test_no_new_campaign_name_to_evade_exhausted_original_cap(roots):
    roots["g3_campaign"]="fresh_fake_day_20261125"
    with pytest.raises(ValueError,match="EXISTING finite model-Send campaign"):
        run(roots)
    assert not roots["report_root"].exists()


def test_wrong_original_source_path_blocks_before_any_action(roots):
    roots["g2_source"]=roots["g3_media"]
    with pytest.raises(ValueError,match="publisher source"):
        run(roots)
    assert not roots["report_root"].exists()


def test_tampered_previous_completion_record_fails_closed(roots):
    a=run(roots)
    file=Path(a["receipt"])
    packet=json.loads(file.read_text("utf8"))
    packet["student_publication_authorized"]=True
    file.write_text(json.dumps(packet))
    with pytest.raises(ValueError,match="altered since last certified"):
        run(roots)


def test_no_other_actions_if_g3_science_pending_health_is_blocked(roots):
    steps=[]
    def bad(**kw):
        steps.append("G3_BLOCKED")
        raise RuntimeError("Last source-free health receipt predates uncertain Send")
    def okmedia(**kw):
        steps.append("MEDIA_GOES_AHEAD")
        return good_media(**kw)
    a=run(roots,g3_science_runner=bad,g3_media_runner=okmedia)
    assert steps==["G3_BLOCKED","MEDIA_GOES_AHEAD"]
    assert a["G2_source_AI_agreed"]==29
    assert a["G3_original_video_pages_technical"]==32
    assert a["G3_science_tasks_eligible"] is None


def test_real_source_ai_progress_can_complete_85_without_faking_acoustics(roots):
    def accepted_source(**kw):
        result=good_g2(**kw)
        result["total_two_pass_AI_agreements"]=85
        result["pending_or_disputed"]=0
        return result
    result=run(roots,g2_runner=accepted_source)
    packet=json.loads(Path(result["receipt"]).read_text("utf8"))
    matrix={r["gate_id"]:r for r in packet["acceptance_gates"]}
    assert matrix["G2_INDEPENDENT_SOURCE_AI"]["accepted"] is True
    assert matrix["G2_INDEPENDENT_SOURCE_AI"]["status"]==(
        "TWO_PASS_SOURCE_AI_EVIDENCE_COMPLETE")
    assert matrix["G2_INDEPENDENT_ACOUSTIC_QA"]["accepted"] is False
    assert result["academically_accepted_gates"]==1
    assert result["all_G2_G3_requirements_accepted"] is False
    assert result["student_publication_authorized"] is False
