"""Real source-bound ranked V3 science: finite browser Send and no replay."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from selenium_pipeline import g2_ranked_v3_owned_selenium_handoff_v1 as handoff
from selenium_pipeline import g2_ranked_source_review_candidate_v3 as v3
from selenium_pipeline import g2_focused_source_target_preflight_v1 as pre
from selenium_pipeline import g2_distinct_focused_source_review_v1 as focused
from selenium_pipeline.autonomous_recovery_continuation_v1 import _campaign
from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.recovery_registry import lookup_mechanism
from tests.test_g2_ranked_source_review_candidate_v3 import (
    _mismatch_fixture)
from tests.test_g2_distinct_focused_source_review_v1 import real_source_fixture


@pytest.fixture()
def eligible(real_source_fixture,monkeypatch):
    folder,queue,job,claim=_mismatch_fixture(real_source_fixture,monkeypatch)
    unit=focused.plan(folder=folder,queue_root=queue,
                      slide=3,utterance_id="s003.utterance.001")
    source=pre.stage(folder=folder,queue_root=queue,item=unit)
    ranked=v3.stage(
        folder=folder,queue_root=queue,item=unit,source_preflight=source)
    assert ranked["new_review_send_authorized"] is False
    return folder,queue,Path(ranked["receipt"]),claim


def campaign(*,folder:Path,queue:Path,cap:int,name:str="test_science_v3")->Path:
    root=queue/"autonomous_recovery_continuation_v1"
    home,header,events=_campaign(root=root,campaign_id=name,
        source_sha=_sha(folder/"source.pdf"),
        queue_sha=_sha(queue/"queue.json"),max_sends=cap)
    assert events==[]
    return home


def call(eligible,**kw):
    folder,queue,candidate,claim=eligible
    return handoff.inspect(
        folder=folder,queue_root=queue,candidate_file=candidate,
        campaign_id=kw.pop("campaign_id","test_science_v3"),**kw)


def test_registry_has_new_ranked_v3_owned_science_handler():
    assert lookup_mechanism(
        handoff.KIND,handoff.SIGNATURE)==handoff.MECHANISM


def test_existing_finite_campaign_stages_new_distinct_review_without_send(eligible):
    folder,queue,candidate,claim=eligible
    original_old_claim=(claim/"dispatch_attempted.claim").read_bytes()
    campaign(folder=folder,queue=queue,cap=2)
    out=call(eligible,execute=False)
    assert out["status"]=="G2_V3_NEW_DISTINCT_MODEL_INPUT_READY_NO_SEND"
    assert out["original_campaign_cap"]==2
    assert out["original_campaign_possible_sends_reserved"]==0
    assert out["original_corrected_physical_target_id"]=="s003.text.001"
    assert out["new_browser_sends_reserved"]==0
    assert out["paid_gemini_API_calls"]==0
    assert out["independent_two_pass_science_accepted"] is False
    assert out["student_publication_authorized"] is False
    assert (claim/"dispatch_attempted.claim").read_bytes()==original_old_claim
    assert not (queue.parent/handoff.ROOT).exists()


def test_exhausted_original_campaign_blocks_even_if_execute_approved(eligible):
    folder,queue,candidate,claim=eligible
    home=campaign(folder=folder,queue=queue,cap=0)
    def no_model(**kw):
        pytest.fail("Never Send after old campaign cap exhaustion")
    out=call(eligible,execute=True,authorized=True,reviewer=no_model)
    assert out["status"]==(
        "G2_V3_INDEPENDENT_REVIEW_AWAITING_EXISTING_SEND_BUDGET_NO_SEND")
    assert out["new_browser_sends_reserved"]==0
    assert not (queue.parent/handoff.ROOT).exists()
    assert len(list(home.glob("event_*.json")))==0


def test_existing_original_campaign_mandatory_not_new_fake_identity(eligible):
    with pytest.raises(ValueError,match="Never create a new campaign"):
        call(eligible,campaign_id="new_fake_day_after_exhaustion")
    folder,queue,candidate,claim=eligible
    assert not (queue.parent/handoff.ROOT).exists()


def test_fresh_owned_neon_health_gate_is_mandatory_for_any_new_send(eligible):
    folder,queue,candidate,claim=eligible
    home=campaign(folder=folder,queue=queue,cap=1)
    out=call(eligible,execute=True,authorized=True)
    assert out["status"]=="G2_V3_FRESH_OWNED_NEON_HEALTH_REQUIRED_NO_SEND"
    assert out["new_browser_sends_reserved"]==0
    assert len(list(home.glob("event_*.json")))==0


def test_explicit_science_authorization_is_required(eligible):
    folder,queue,candidate,claim=eligible
    campaign(folder=folder,queue=queue,cap=1)
    out=call(eligible,execute=True,authorized=False)
    assert out["status"]=="G2_V3_NEW_DISTINCT_MODEL_INPUT_READY_NO_SEND"
    assert out["new_browser_sends_reserved"]==0


def test_crash_after_pre_send_reservation_stays_held_no_replay(
        eligible,monkeypatch,tmp_path):
    folder,queue,candidate,claim=eligible
    home=campaign(folder=folder,queue=queue,cap=1)
    monkeypatch.setattr(handoff,"_health_ok",lambda **kw:{"verified":True})
    count=[]
    def uncertain(**kw):
        count.append(kw["mode"])
        raise ConnectionError("Simulated Selenium Send uncertain after click")
    out=call(eligible,execute=True,authorized=True,
             health_result=tmp_path/"fake_health.json",reviewer=uncertain)
    assert out["status"]=="G2_V3_MODEL_ATTEMPT_UNCERTAIN_HOLD_NO_REPLAY"
    assert out["new_browser_sends_reserved"]==1
    assert count==["INITIAL_REVIEW"]
    events=[json.loads(p.read_text("utf8")) for p in
            sorted(home.glob("event_*.json"))]
    assert [(e["type"],e["phase"]) for e in events]==[
        ("RESERVE","INITIAL"),("HOLD","INITIAL")]
    again=call(eligible,execute=True,authorized=True,
               health_result=tmp_path/"fake_health.json",reviewer=uncertain)
    assert again["new_browser_sends_reserved"]==0
    assert count==["INITIAL_REVIEW"]
    assert len(list(home.glob("event_*.json")))==2
    assert (claim/"dispatch_attempted.claim").is_file()
    assert not (queue.parent/handoff.ROOT).exists() or not (
        (queue.parent/handoff.ROOT)/
        out["scope_sha256"]/"initial_request").exists()


def test_challenge_must_not_send_before_independent_first_pass(eligible):
    folder,queue,candidate,claim=eligible
    campaign(folder=folder,queue=queue,cap=2)
    out=call(eligible,mode="INDEPENDENT_CHALLENGE",
             execute=True,authorized=True)
    assert out["status"]==(
        "G2_V3_INITIAL_SOURCE_REVIEW_MISSING_NO_CHALLENGE_SEND")
    assert out["new_browser_sends_reserved"]==0


def test_historical_old_source_or_job_tampering_fails_before_campaign_send(
        eligible):
    folder,queue,candidate,claim=eligible
    campaign(folder=folder,queue=queue,cap=1)
    data=json.loads(candidate.read_text("utf8"))
    data["student_publication_authorized"]=True
    candidate.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        call(eligible,execute=True,authorized=True)
    assert not (queue.parent/handoff.ROOT).exists()


def test_wrong_source_pdf_drift_refuses_transport(eligible):
    folder,queue,candidate,claim=eligible
    campaign(folder=folder,queue=queue,cap=1)
    with (folder/"source.pdf").open("ab") as file:
        file.write(b"foreign source")
    with pytest.raises(ValueError):
        call(eligible,execute=True,authorized=True)


def test_genuine_selenium_stage_returns_unapproved_even_after_source_valid_reply(
        eligible,monkeypatch,tmp_path):
    folder,queue,candidate,claim=eligible
    home=campaign(folder=folder,queue=queue,cap=2)
    monkeypatch.setattr(handoff,"_health_ok",
                        lambda **kw:{"verified_model_family":"neon",
                                     "verified_thinking_level":"high"})
    monkeypatch.setattr(handoff,"_load",
                        lambda path:{"status":"SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"})
    calls=[]
    def valid_reply(**kw):
        calls.append({"model":kw["required_model_family"],
                      "mode":kw["mode"],
                      "checkpoint":str(kw["checkpoint_dir"])})
        return {"status":"SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS"}
    got=call(eligible,execute=True,authorized=True,
             health_result=tmp_path/"fake_health_for_test_only",
             reviewer=valid_reply)
    assert got["status"]=="G2_V3_MODEL_ONE_PASS_SOURCE_VALIDATED_UNAPPROVED"
    assert got["new_browser_sends_reserved"]==1
    assert got["independent_two_pass_science_accepted"] is False
    assert got["student_publication_authorized"] is False
    assert calls[0]["model"]=="neon"
    assert calls[0]["mode"]=="INITIAL_REVIEW"
    assert handoff.ROOT in calls[0]["checkpoint"]
    events=[json.loads(x.read_text("utf8")) for x in
            sorted(home.glob("event_*.json"))]
    assert [(x["type"],x["phase"]) for x in events]==[
        ("RESERVE","INITIAL"),("RESULT","INITIAL")]
    repeat=call(eligible,execute=True,authorized=True,
                health_result=tmp_path/"fake_health_for_test_only",
                reviewer=valid_reply)
    assert repeat["new_browser_sends_reserved"]==0
    assert len(calls)==1


def test_physical_v3_candidate_cannot_use_a_legacy_v1_scope(eligible):
    folder,queue,candidate,claim=eligible
    campaign(folder=folder,queue=queue,cap=2)
    fake=queue.parent/"G2_DISTINCT_FOCUSED_SOURCE_REVIEW_V1"/candidate.name
    with pytest.raises(ValueError,match="Only original immutable ranked V3"):
        handoff.inspect(folder=folder,queue_root=queue,
                        candidate_file=fake,campaign_id="test_science_v3")


def test_real_shared_g2_supervisor_lock_prevents_parallel_v3_send(eligible):
    from selenium_pipeline.three_pc_worker import LocalInstanceLock
    import hashlib
    folder,queue,candidate,claim=eligible
    home=campaign(folder=folder,queue=queue,cap=2)
    owner="g2_qa_"+hashlib.sha256(str(queue).encode("utf8")).hexdigest()[:20]
    locks=queue/".microgen_g2_supervisor_locks"
    with LocalInstanceLock(owner,locks):
        with pytest.raises(RuntimeError,match="already active"):
            call(eligible,execute=True,authorized=True)
    assert not list(home.glob("event_*.json"))
    ready=call(eligible,execute=False)
    assert ready["new_browser_sends_reserved"]==0
    assert ready["status"]=="G2_V3_NEW_DISTINCT_MODEL_INPUT_READY_NO_SEND"
