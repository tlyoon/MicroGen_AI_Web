"""Crash/restart and fault-injection for central G2 recovery autoadvance.

The fake callbacks model provider uncertainty; no Selenium or paid API.
Underlying academic model/source validation has its own independent tests.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from tests.test_g2_distinct_focused_source_review_v1 import real_source_fixture
from selenium_pipeline import autonomous_recovery_continuation_v1 as auto
from selenium_pipeline import g2_distinct_focused_source_review_v1 as focused
from selenium_pipeline.recovery_registry import lookup_mechanism


@pytest.fixture
def campaign_fixture(real_source_fixture, monkeypatch):
    folder, queue, job, quote, old = real_source_fixture
    monkeypatch.setattr(
        auto, "build_review_job", lambda **kw:copy.deepcopy(job))
    monkeypatch.setattr(
        auto, "_health", lambda **kw: queue/"fake_neon_health.json")
    (queue/"fake_neon_health.json").write_text('{"verified":true}')
    calls = []
    original = {
        "status":"INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE",
        "original_utterances":3,
        "accepted_ai_evidence":[],
        "unresolved":[
            {"utterance_id":x["id"],"reason":"HISTORICAL_UNCERTAIN"}
            for x in job["slides"][0]["utterances"]],
    }
    def read(**kw):
        return copy.deepcopy(original)
    def bridge(**kw):
        root=queue.parent/focused.REVIEW_ROOT_NAME
        agreed=[]
        if root.exists():
            for scope in root.iterdir():
                if (scope/"two_pass_evidence.json").is_file():
                    data=json.loads((scope/"two_pass_evidence.json").read_text())
                    if data["status"]=="AGREED":
                        agreed.append(data["unit"])
        return {
            "status":"G2_ORIGINAL_AND_FOCUSED_SOURCE_AI_EVIDENCE_RECONCILED_NO_RELEASE",
            "original_total_utterances":3,
            "original_two_pass_source_AI_agreements":0,
            "new_provider_requests":0,
            "student_publication_authorized":False,
            "combined_source_AI_agreements":len(agreed),
            "pending_or_disputed_source_AI":3-len(agreed),
            "new_focused_utterance_ids":agreed,
        }
    def first(**kw):
        uid=kw["utterance_id"]
        calls.append(("INITIAL",uid))
        item=focused.plan(folder=folder,queue_root=queue,
                          slide=3,utterance_id=uid)
        scope=queue.parent/focused.REVIEW_ROOT_NAME/item["scope_sha256"]
        scope.mkdir(parents=True,exist_ok=True)
        (scope/"initial_request").mkdir()
        (scope/"initial_request"/"model_response_untrusted.txt").write_text(
            "synthetic saved original model response")
        return {
            "status":"FOCUSED_NEW_REVIEW_ONE_PASS_UNAPPROVED",
            "new_original_slide_consensus_count":0,
            "student_publication_authorized":False,
        }
    def second(**kw):
        uid=kw["utterance_id"]
        calls.append(("CHALLENGE",uid))
        item=focused.plan(folder=folder,queue_root=queue,
                          slide=3,utterance_id=uid)
        scope=queue.parent/focused.REVIEW_ROOT_NAME/item["scope_sha256"]
        (scope/"two_pass_evidence.json").write_text(json.dumps({
            "status":"AGREED","unit":uid}))
        return {
            "status":"FOCUSED_TWO_PASS_SOURCE_AI_AGREEMENT_UNAPPROVED",
            "original_g2_segments_promoted":0,
            "student_publication_authorized":False,
        }
    def run(campaign_id, *, max_sends=2, execute=True, **kwargs):
        return auto.run_campaign(
            folder=folder,queue_root=queue,work_root=queue,
            campaign_id=campaign_id,max_possible_sends=max_sends,
            execute=execute,initial_runner=first,challenge_runner=second,
            source_consensus=read,consensus_bridge=bridge,**kwargs)
    return folder,queue,job,calls,run


def test_registered_autoforward_is_executable_and_not_arbitrary_code():
    assert lookup_mechanism(auto.KIND,auto.SIGNATURE)==auto.MECHANISM


def test_auto_forward_two_separate_source_review_sends_and_reconcile(campaign_fixture):
    folder,queue,job,calls,run=campaign_fixture
    result=run("two_stage_campaign")
    assert calls==[
        ("INITIAL","s003.utterance.001"),
        ("CHALLENGE","s003.utterance.001"),
    ]
    assert result["possible_provider_sends_reserved"]==2
    assert result["max_possible_provider_sends"]==2
    assert result["remaining_possible_send_budget"]==0
    assert result["reconciled_source_AI_agreements"]==1
    assert result["pending_source_AI_review"]==2
    assert result["student_publication_authorized"] is False
    assert result["new_paid_gemini_api_calls"]==0
    assert result["original_historical_requests_replayed"] is False
    again=run("two_stage_campaign")
    assert again["possible_provider_sends_reserved"]==2
    assert again["reconciled_source_AI_agreements"]==1
    assert len(calls)==2
    assert (queue/"slide_003_initial_review_attempt_01_request"/
            "dispatch_attempted.claim").is_file()


def test_dry_run_can_not_spend_model_budget(campaign_fixture):
    folder,queue,job,calls,run=campaign_fixture
    report=run("read_only_health_planner",max_sends=0,execute=False)
    assert report["status"]=="NEXT_ELIGIBLE_SOURCE_REVIEW_AWAITS_EXECUTION"
    assert report["possible_provider_sends_reserved"]==0
    assert report["stages"][0]["unit"]=="s003.utterance.001"
    assert not calls
    assert not (queue.parent/focused.REVIEW_ROOT_NAME).exists()


def test_budget_cannot_be_increased_by_restarting_campaign(campaign_fixture):
    folder,queue,job,calls,run=campaign_fixture
    first=run("one_send_campaign",max_sends=1)
    assert len(calls)==1 and calls[0][0]=="INITIAL"
    assert first["status"]=="FINITE_CAMPAIGN_SEND_BUDGET_EXHAUSTED"
    repeated=run("one_send_campaign",max_sends=1)
    assert len(calls)==1 and repeated["remaining_possible_send_budget"]==0
    with pytest.raises(Exception,match="immutable|changed"):
        run("one_send_campaign",max_sends=4)


def test_crash_during_ambiguous_click_is_not_retried(campaign_fixture,monkeypatch):
    folder,queue,job,calls,run=campaign_fixture
    def uncertain(**kwargs):
        calls.append(("CLICK_MAY_HAVE_OCCURRED",kwargs["utterance_id"]))
        raise ConnectionError("Browser connection died during Send")
    def fail(campaign_id):
        return auto.run_campaign(
            folder=folder,queue_root=queue,work_root=queue,
            campaign_id=campaign_id,max_possible_sends=2,
            execute=True,initial_runner=uncertain,
            source_consensus=lambda **kw:{
                "accepted_ai_evidence":[],
                "unresolved":[{"utterance_id":u["id"]}
                              for u in job["slides"][0]["utterances"]]},
            consensus_bridge=lambda **kw:{
                "status":"G2_ORIGINAL_AND_FOCUSED_SOURCE_AI_EVIDENCE_RECONCILED_NO_RELEASE",
                "original_total_utterances":3,
                "new_provider_requests":0,
                "student_publication_authorized":False,
                "combined_source_AI_agreements":0,
                "pending_or_disputed_source_AI":3,
                "original_two_pass_source_AI_agreements":0,
                "new_focused_utterance_ids":[]},
            challenge_runner=lambda **kw:pytest.fail("No challenge after uncertainty"))
    result=fail("uncertain_click_campaign")
    assert result["status"]=="SOURCE_REVIEW_FAILED_OR_UNCERTAIN_NO_REPLAY"
    assert result["possible_provider_sends_reserved"]==1
    again=fail("uncertain_click_campaign")
    assert again["status"]=="PERSISTED_RESERVATION_NO_REPLAY"
    assert len(calls)==1


def test_new_campaign_can_resume_saved_first_pass_with_separate_challenge(
        campaign_fixture):
    folder,queue,job,calls,run=campaign_fixture
    a=run("first_phase_only",max_sends=1)
    assert a["possible_provider_sends_reserved"]==1
    b=run("distinct_phase_continuation",max_sends=1)
    assert b["possible_provider_sends_reserved"]==1
    assert b["reconciled_source_AI_agreements"]==1
    assert calls==[
        ("INITIAL","s003.utterance.001"),
        ("CHALLENGE","s003.utterance.001")]


def test_missing_neon_health_never_attempts_source_send(campaign_fixture,monkeypatch):
    folder,queue,job,calls,run=campaign_fixture
    monkeypatch.setattr(auto,"_health",lambda **kw:None)
    result=run("health_missing_campaign",auto_health=False)
    assert result["status"]=="FRESH_SOURCE_FREE_NEON_HEALTH_REQUIRED_NO_SEND"
    assert result["possible_provider_sends_reserved"]==0
    assert not calls


def test_global_queue_source_drift_stops_before_send(campaign_fixture):
    folder,queue,job,calls,run=campaign_fixture
    (folder/"source.pdf").write_bytes(b"%PDF-1.4 tampered publisher source")
    with pytest.raises(Exception):
        run("modified_source_campaign")
    assert not calls


def test_recovery_event_stage_file_promoted_after_crash(tmp_path):
    root,header,events=auto._campaign(
        root=tmp_path,campaign_id="crashed_stage_campaign",
        source_sha="a"*64,queue_sha="b"*64,max_sends=2)
    ev=auto._event_core("RESERVE",index=1,
        previous=auto._digest(auto._json(header)),
        scope="source_scope",phase="INITIAL",
        detail="s003.utterance.001")
    stage=root/"event_001.stage"
    stage.write_bytes(auto._json(ev))
    recovered=auto._load_events(root,auto._digest(auto._json(header)))
    assert len(recovered)==1
    assert (root/"event_001.json").is_file()
    assert not stage.exists()
    assert auto._possible_sends(recovered)==1


def test_tampered_event_stops_following_work(tmp_path):
    root,header,events=auto._campaign(
        root=tmp_path,campaign_id="tamper_event_campaign",
        source_sha="a"*64,queue_sha="b"*64,max_sends=2)
    events=auto._append(root,header,events,"RESERVE",
        scope="one",phase="INITIAL",detail="s003.utterance.001")
    ev=root/"event_001.json"
    obj=json.loads(ev.read_text())
    obj["phase"]="CHALLENGE"
    ev.write_text(json.dumps(obj))
    with pytest.raises(Exception,match="chain|inconsistent"):
        auto._load_events(root,auto._digest(auto._json(header)))


def test_same_queue_lock_prevents_concurrent_owners(campaign_fixture):
    folder,queue,job,calls,run=campaign_fixture
    name="g2_qa_"+hashlib.sha256(str(queue).encode()).hexdigest()[:20]
    from selenium_pipeline.three_pc_worker import LocalInstanceLock
    with LocalInstanceLock(name,queue/".microgen_g2_supervisor_locks"):
        with pytest.raises(RuntimeError,match="already active"):
            run("concurrent_owner_campaign",max_sends=0,execute=False)
    assert not calls


def test_existing_new_uncertain_send_halts_other_eligible_units(
        campaign_fixture):
    folder,queue,job,calls,run=campaign_fixture
    item=focused.plan(folder=folder,queue_root=queue,slide=3,
                      utterance_id="s003.utterance.002")
    scope=queue.parent/focused.REVIEW_ROOT_NAME/item["scope_sha256"]
    (scope/"initial_request").mkdir(parents=True)
    (scope/"initial_request"/"dispatch_attempted.claim").write_text(
        "possibly sent earlier")
    result=run("global_uncertain_new_focused_claim",max_sends=2)
    assert result["status"]=="HOLD_UNCERTAIN_NEW_REVIEW_NO_REPLAY"
    assert not calls
    assert result["possible_provider_sends_reserved"]==0


def test_health_probe_spends_one_of_one_possible_send(campaign_fixture,
                                                     monkeypatch):
    folder,queue,job,calls,run=campaign_fixture
    probe_calls=[]
    def fake_health(**kwargs):
        probe_calls.append(1)
        return {"status":"SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED"}
    # Fail before the explicit synthetic health probe, then succeed on its
    # return. The second source Send must still be forbidden.
    def health_status(**kwargs):
        if not probe_calls:
            return None
        return queue/"fake_neon_health.json"
    monkeypatch.setattr(auto,"_health",health_status)
    result=run("one_possible_send_only_for_health",max_sends=1,
               auto_health=True,health_probe=fake_health)
    assert len(probe_calls)==1
    assert not calls
    assert result["possible_provider_sends_reserved"]==1
    assert result["status"]=="FINITE_CAMPAIGN_SEND_BUDGET_EXHAUSTED_AFTER_HEALTH"
    assert result["new_paid_gemini_api_calls"]==0
    second=run("one_possible_send_only_for_health",max_sends=1,
               auto_health=True,health_probe=lambda **kw:
                   pytest.fail("health must not repeat"))
    assert second["remaining_possible_send_budget"]==0
    assert len(probe_calls)==1


def test_crash_after_reservation_preserves_finite_budget(tmp_path):
    root,header,events=auto._campaign(
        root=tmp_path,campaign_id="crash_after_reserve",
        source_sha="a"*64,queue_sha="b"*64,max_sends=1)
    auto._append(root,header,events,"RESERVE",scope="slot",
                 phase="INITIAL",detail="s003.utterance.002")
    home,h2,ev2=auto._campaign(
        root=tmp_path,campaign_id="crash_after_reserve",
        source_sha="a"*64,queue_sha="b"*64,max_sends=1)
    assert h2==header
    assert auto._possible_sends(ev2)==1
    assert auto._reservation(ev2,"slot","INITIAL") is True
    assert home==root


def test_normal_supervisor_cli_routes_to_verified_auto_continuation(
        campaign_fixture,monkeypatch,capsys):
    from selenium_pipeline import windows_g2_autonomous_qa_supervisor as supervisor
    folder,queue,job,calls,run=campaign_fixture
    observed=[]
    monkeypatch.setattr(supervisor,"step",lambda **kwargs:{
        "status":"G2_ACADEMIC_QA_INCOMPLETE_REVIEW_OR_SOURCE_REPAIR",
        "student_publication_authorized":False,
        "two_pass_ai_source_agreed_segments":0,
        "pending_or_disputed_segments":3})
    def fake_dispatch(**kwargs):
        observed.append(kwargs)
        return {
            "student_publication_authorized":False,
            "new_paid_gemini_api_calls":0,
            "original_historical_requests_replayed":False,
            "reconciled_source_AI_agreements":1,
            "pending_source_AI_review":2,
        }
    monkeypatch.setattr(auto,"run_campaign",fake_dispatch)
    args=["--folder",str(folder),"--queue-root",str(queue),
          "--work-root",str(queue),"--max-units","0",
          "--no-auto-media","--auto-focused-next",
          "--campaign-id","cli_routed_case",
          "--focused-possible-sends","2","--execute"]
    assert supervisor.main(args)==0
    data=json.loads(capsys.readouterr().out)
    assert data["two_pass_ai_source_agreed_segments"]==1
    assert data["pending_or_disputed_segments"]==2
    assert data["student_publication_authorized"] is False
    assert observed[0]["max_possible_sends"]==2
    assert observed[0]["execute"] is True
    assert observed[0]["campaign_id"]=="cli_routed_case"


def test_supervisor_cli_rejects_legacy_plus_focused_mixed_sends(
        campaign_fixture,monkeypatch,capsys):
    from selenium_pipeline import windows_g2_autonomous_qa_supervisor as supervisor
    folder,queue,job,calls,run=campaign_fixture
    monkeypatch.setattr(supervisor,"step",
                        lambda **kw:pytest.fail("must reject before step"))
    args=["--folder",str(folder),"--queue-root",str(queue),
          "--work-root",str(queue),"--max-units","2",
          "--no-auto-media","--auto-focused-next",
          "--campaign-id","invalid_mixed_sources",
          "--focused-possible-sends","2","--execute"]
    assert supervisor.main(args)==2
    data=json.loads(capsys.readouterr().out)
    assert data["status"]=="G2_AUTONOMOUS_SUPERVISOR_SOURCE_GATE_BLOCKED"
    assert data["student_publication_authorized"] is False


def test_interrupted_duplicate_stage_identical_to_final_is_recovered(tmp_path):
    root,header,events=auto._campaign(
        root=tmp_path,campaign_id="both_stage_and_final",
        source_sha="a"*64,queue_sha="b"*64,max_sends=2)
    events=auto._append(root,header,events,"RESERVE",
                        scope="unique_review",phase="INITIAL",
                        detail="s003.utterance.002")
    final=root/"event_001.json"
    stage=root/"event_001.stage"
    stage.write_bytes(final.read_bytes())
    reopened=auto._load_events(root,auto._digest(auto._json(header)))
    assert len(reopened)==1
    assert auto._possible_sends(reopened)==1
    assert final.exists() and not stage.exists()
