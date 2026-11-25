"""Original real-source G3 historical premature CHALLENGE budget repair."""
from __future__ import annotations
import json
from pathlib import Path

import pytest
from selenium_pipeline import g3_continuous_advance_v1 as driver
from selenium_pipeline import g3_distinct_semantic_science_v1 as science
from selenium_pipeline.recovery_registry import lookup_mechanism
from tests.test_g3_continuous_advance_v1 import campaign,item
from tests.test_g3_distinct_semantic_science_v1 import ready,transport_for
from tests.test_g3_semantic_source_repair_v1 import sample


def test_just_in_time_repair_is_in_executable_recovery_registry():
    assert lookup_mechanism(
        driver.LAZY_KIND,driver.LAZY_SIGNATURE)==driver.LAZY_MECHANISM


def test_actual_two_pass_source_science_reserves_challenge_only_after_initial(
        ready):
    spec,worklists,task,root,quote=ready
    phases=[]
    calls=[]
    def before(scope,phase):
        if phase=="CHALLENGE":
            # This is the actual saved model-response first pass, not an
            # assumed source quote or a pre-allocated 2nd request.
            candidate=list(root.rglob("initial_request/model_response_untrusted.txt"))
            assert len(candidate)==1 and candidate[0].stat().st_size>0
        phases.append(phase)
    report=science.run_one(spec=spec,worklist_root=worklists,task_file=task,
        state_root=root,campaign_id="g3_two_pass_real_model_stub",
        max_possible_sends=2,execute=True,
        transport=transport_for(quote,calls),before_send=before)
    assert phases==["INITIAL","CHALLENGE"]
    assert len(calls)==2
    assert report["possible_sends_reserved"]==2
    assert report["two_pass_science_evidence"]["science_AI_source_agreed"] is True
    assert report["student_publication_authorized"] is False
    assert report["paid_gemini_API_calls"]==0
    again=science.run_one(spec=spec,worklist_root=worklists,task_file=task,
        state_root=root,campaign_id="g3_two_pass_real_model_stub",
        max_possible_sends=2,execute=True,
        transport=lambda *x:pytest.fail("Do not replay genuine model replies"),
        before_send=lambda *x:pytest.fail("Do not re-reserve claimed response"))
    assert again["status"]==science.REPORT
    assert phases==["INITIAL","CHALLENGE"]


def test_actual_initial_transport_failure_never_pre_reserves_challenge(ready):
    spec,worklists,task,root,quote=ready
    phases=[]
    calls=[]
    first=science.run_one(spec=spec,worklist_root=worklists,task_file=task,
        state_root=root,campaign_id="g3_initial_uncertain_scope",
        max_possible_sends=2,execute=True,
        transport=transport_for(quote,calls,timeout=True),
        before_send=lambda scope,phase:phases.append(phase))
    assert first["possible_sends_reserved"]==1
    assert phases==["INITIAL"]
    assert first["two_pass_science_evidence"] is None
    assert first["student_publication_authorized"] is False
    assert len(calls)==1
    second=science.run_one(spec=spec,worklist_root=worklists,task_file=task,
        state_root=root,campaign_id="g3_initial_uncertain_scope",
        max_possible_sends=2,execute=True,
        transport=lambda *x:pytest.fail("Do not replay uncertain initial"),
        before_send=lambda *x:pytest.fail("Cannot reserve missing challenge"))
    assert second["status"]=="G3_DISTINCT_SCIENCE_UNCERTAIN_NO_REPLAY"
    assert second["possible_sends_reserved"]==1
    assert phases==["INITIAL"]


def test_global_model_send_journal_uses_exact_just_in_time_order(
        campaign,monkeypatch):
    state,manifest,spec=campaign
    scope="a"*64
    work=item(spec,scope,"NEW_CONTEXT")
    monkeypatch.setattr(driver,"_eligible",lambda **kw:[work])
    events=[]
    def real_phases(**kw):
        for phase in ("INITIAL","CHALLENGE"):
            kw["before_send"](scope,phase)
            events.append(phase)
        return {"status":"G3_TEST_TWO_SAVED_RESPONSES",
            "possible_sends_reserved":2,
            "two_pass_science_evidence":{"science_AI_source_agreed":False},
            "semantic_context_recovery":None}
    monkeypatch.setattr(driver,"run_one",real_phases)
    result=driver.advance(manifest=manifest,state_root=state,
        campaign_id="g3_jit_two_phases",max_science_sends=2,
        max_tasks=1,max_health_probes=0)
    assert events==["INITIAL","CHALLENGE"]
    assert result["science_browser_sends_reserved"]==2
    assert result["student_publication_authorized"] is False
    log=state/"g3_continuous_advance_v1"/"g3_jit_two_phases"
    saved=[json.loads(f.read_text("utf8")) for f in sorted(log.glob("event_*.json"))]
    assert [(e["type"],e["phase"]) for e in saved]==[
        ("RESERVE","INITIAL"),("RESERVE","CHALLENGE"),("RESULT","RECONCILE")]


def test_global_failed_initial_claim_consumes_one_not_two_and_other_source_advances(
        campaign,monkeypatch):
    state,manifest,spec=campaign
    first=item(spec,"a"*64,"NEW_CONTEXT")
    other={**spec,"section":"Serway_8_3",
           "identity":{"source_inputs_sha256":{"source.pdf":"b"*64}}}
    next_task={**item(other,"b"*64,"NEW_CONTEXT"),"section":"Serway_8_3"}
    monkeypatch.setattr(driver,"_verified_specs",lambda p:({},[spec,other]))
    visited=[]
    monkeypatch.setattr(driver,"_eligible",lambda **kw:[
        x for x in (first,next_task) if x["scope"] not in visited])
    def run(**kw):
        scope=kw["task_file"].stem
        visited.append(scope)
        kw["before_send"](scope,"INITIAL")
        if scope==next_task["scope"]:
            kw["before_send"](scope,"CHALLENGE")
            return {"status":"G3_SECOND_SOURCE_DISPUTED_NO_RELEASE",
                "possible_sends_reserved":2,
                "two_pass_science_evidence":{"science_AI_source_agreed":False},
                "semantic_context_recovery":None}
        return {"status":"G3_INITIAL_SUBMITTED_OR_UNCERTAIN_NO_REPLAY",
            "possible_sends_reserved":1,
            "two_pass_science_evidence":None,
            "semantic_context_recovery":None}
    monkeypatch.setattr(driver,"run_one",run)
    got=driver.advance(manifest=manifest,state_root=state,
        campaign_id="g3_one_uncertain_one_distinct",max_science_sends=4,
        max_tasks=2,max_health_probes=0)
    assert visited==[first["scope"],next_task["scope"]]
    assert got["science_browser_sends_reserved"]==3
    assert got["stages_advanced_this_run"]==2
    assert got["original_historical_model_claims_replayed"] is False
    assert got["student_publication_authorized"] is False
    journal=state/"g3_continuous_advance_v1"/"g3_one_uncertain_one_distinct"
    entries=[json.loads(x.read_text("utf8")) for x in sorted(journal.glob("event_*.json"))]
    assert [(x["scope"],x["phase"]) for x in entries if x["type"]=="RESERVE"]==[
        (first["scope"],"INITIAL"),(next_task["scope"],"INITIAL"),
        (next_task["scope"],"CHALLENGE")]


def test_original_reserved_global_campaign_never_replays_or_modifies_old_claims(
        campaign,monkeypatch):
    state,manifest,spec=campaign
    work=item(spec,"c"*64,"NEW_CONTEXT")
    monkeypatch.setattr(driver,"_eligible",lambda **kw:[work])
    def crash(**kw):
        kw["before_send"](work["scope"],"INITIAL")
        raise RuntimeError("Injected power loss immediately after possible Send claim")
    monkeypatch.setattr(driver,"run_one",crash)
    args=dict(manifest=manifest,state_root=state,
        campaign_id="g3_preserve_old_post_claim",max_science_sends=2,
        max_tasks=1,max_health_probes=0)
    with pytest.raises(RuntimeError):
        driver.advance(**args)
    journal=state/"g3_continuous_advance_v1"/args["campaign_id"]
    original={f.name:f.read_bytes() for f in journal.glob("event_*.json")}
    def recovered(**kw):
        assert kw["execute"] is False
        assert kw["before_send"] is None
        return {"status":"G3_UNCERTAIN_MODEL_SEND_UNRECOVERABLE_NO_REPLAY",
            "possible_sends_reserved":0,"two_pass_science_evidence":None,
            "semantic_context_recovery":None}
    monkeypatch.setattr(driver,"run_one",recovered)
    replay=driver.advance(**args)
    assert replay["science_browser_sends_reserved"]==1
    assert replay["stages_advanced_this_run"]==1
    assert replay["stage_results"][0]["status"]==(
        "G3_UNCERTAIN_MODEL_SEND_UNRECOVERABLE_NO_REPLAY")
    for name,content in original.items():
        assert (journal/name).read_bytes()==content
    again=driver.advance(**args)
    assert again["science_browser_sends_reserved"]==1
    assert again["stages_advanced_this_run"]==0
