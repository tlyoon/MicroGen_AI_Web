"""Finite global source-science budget and automatic next-task execution."""
from __future__ import annotations
import json
import pytest
from selenium_pipeline import g3_continuous_advance_v1 as driver


@pytest.fixture
def campaign(tmp_path,monkeypatch):
    state=tmp_path/"state"
    state.mkdir()
    manifest=tmp_path/"source_manifest.json"
    manifest.write_text('{"source_first":true}')
    spec={
        "section":"Serway_8_2",
        "identity":{"source_inputs_sha256":{"source.pdf":"a"*64}},
        "source_folder":tmp_path/"source",
        "review_root":tmp_path/"review",
    }
    monkeypatch.setattr(driver,"_verified_specs",lambda p:({},[spec]))
    monkeypatch.setattr(driver,"_after_incident",lambda **kw:0)
    monkeypatch.setattr(driver,"latest_health",lambda **kw:{
        "status":"G3_SOURCE_FREE_NEON_HIGH_HEALTH_VERIFIED",
        "fresh_neon_high_source_free_health":True})
    return state,manifest,spec


def item(spec,scope,kind):
    return {
        "section":"Serway_8_2","utterance_id":"s015.utterance.003",
        "original_slide":15,"kind":kind,"scope":scope,
        "spec":spec,"file":spec["source_folder"]/(scope+".json")}


def test_auto_advances_context_then_next_distinct_task(campaign,monkeypatch):
    state,manifest,spec=campaign
    first=item(spec,"b"*64,"NEW_CONTEXT")
    second=item(spec,"c"*64,"ORIGINAL_DISTINCT")
    done=[]
    monkeypatch.setattr(driver,"_eligible",
       lambda **kw:[x for x in (first,second) if x["scope"] not in done])
    def run(**kw):
        scope=kw["task_file"].stem
        done.append(scope)
        return {"status":"G3_SOURCE_MODEL_ONE_PASS_CANDIDATE",
                "possible_sends_reserved":2,
                "two_pass_science_evidence":{
                    "science_AI_source_agreed":False},
                "semantic_context_recovery":None}
    monkeypatch.setattr(driver,"run_one",run)
    got=driver.advance(
        manifest=manifest,state_root=state,campaign_id="auto_forward_20261124",
        max_science_sends=4,max_tasks=2,max_health_probes=0)
    assert got["stages_advanced_this_run"]==2
    assert got["science_browser_sends_reserved"]==4
    assert got["status"]=="FINITE_G3_SOURCE_CAMPAIGN_BUDGET_EXHAUSTED"
    assert [x["kind"] for x in got["stage_results"]]==[
        "NEW_CONTEXT","ORIGINAL_DISTINCT"]
    assert got["original_historical_model_claims_replayed"] is False
    assert got["student_publication_authorized"] is False
    assert done==["b"*64,"c"*64]
    repeat=driver.advance(
        manifest=manifest,state_root=state,campaign_id="auto_forward_20261124",
        max_science_sends=4,max_tasks=2,max_health_probes=0)
    assert repeat["science_browser_sends_reserved"]==4
    assert repeat["stages_advanced_this_run"]==0


def test_crash_between_global_reservation_and_model_dispatch_is_restart_safe(
        campaign,monkeypatch):
    state,manifest,spec=campaign
    next_item=item(spec,"d"*64,"NEW_CONTEXT")
    monkeypatch.setattr(driver,"_eligible",lambda **kw:[next_item])
    count=[0]
    def interrupted(**kw):
        count[0]+=1
        if count[0]==1:
            raise RuntimeError("Simulated process crash before model response")
        return {"status":"G3_TEST_SOURCE_NO_SEND_RECONCILED",
                "possible_sends_reserved":2,
                "two_pass_science_evidence":{
                    "science_AI_source_agreed":False},
                "semantic_context_recovery":None}
    monkeypatch.setattr(driver,"run_one",interrupted)
    args={
        "manifest":manifest,"state_root":state,
        "campaign_id":"crash_recovery_20261124",
        "max_science_sends":2,"max_tasks":1,
        "max_health_probes":0}
    with pytest.raises(RuntimeError):
        driver.advance(**args)
    resumed=driver.advance(**args)
    assert resumed["science_browser_sends_reserved"]==2
    assert resumed["stages_advanced_this_run"]==1
    assert count[0]==2
    with pytest.raises(ValueError):
        driver.advance(**{**args,"max_science_sends":4})


def test_source_health_gate_prevents_unauthorized_or_unproven_send(
        campaign,monkeypatch):
    state,manifest,spec=campaign
    next_item=item(spec,"e"*64,"ORIGINAL_DISTINCT")
    monkeypatch.setattr(driver,"_eligible",lambda **kw:[next_item])
    monkeypatch.setattr(driver,"latest_health",lambda **kw:None)
    monkeypatch.setattr(driver,"run_one",
        lambda **kw:pytest.fail("No browser Send without health"))
    receipt=driver.advance(
        manifest=manifest,state_root=state,
        campaign_id="no_health_20261124",max_science_sends=2,
        max_tasks=1,max_health_probes=0)
    assert receipt["stages_advanced_this_run"]==0
    assert receipt["science_browser_sends_reserved"]==0
    assert receipt["stage_results"][0]["status"]==(
        "FRESH_OWNED_NEON_HEALTH_REQUIRED_NO_SOURCE_SEND")


def test_no_implicit_unbounded_model_or_synthetic_health_requests(campaign):
    state,manifest,spec=campaign
    with pytest.raises(ValueError):
        driver.advance(manifest=manifest,state_root=state,
                       campaign_id="invalid_budget",max_science_sends=9)
    with pytest.raises(ValueError):
        driver.advance(manifest=manifest,state_root=state,
                       campaign_id="invalid_budget",max_science_sends=1)
    with pytest.raises(ValueError):
        driver.advance(manifest=manifest,state_root=state,
                       campaign_id="invalid_budget",max_science_sends=2,
                       max_tasks=99)


def test_source_health_probe_separately_capped_and_original_pdf_never_uploaded(
        campaign,monkeypatch):
    state,manifest,spec=campaign
    next_item=item(spec,"f"*64,"NEW_CONTEXT")
    monkeypatch.setattr(driver,"_eligible",lambda **kw:[next_item])
    monkeypatch.setattr(driver,"latest_health",lambda **kw:None)
    counted=[]
    monkeypatch.setattr(driver,"probe_once",
        lambda **kw:(counted.append(kw) or {
            "status":"G3_SOURCE_FREE_NEON_HIGH_HEALTH_VERIFIED",
            "fresh_neon_high_source_free_health":True}))
    monkeypatch.setattr(driver,"run_one",lambda **kw:{
        "status":"G3_SCOPED_SOURCE_ONLY_NO_APPROVAL",
        "possible_sends_reserved":2,
        "two_pass_science_evidence":{"science_AI_source_agreed":False},
        "semantic_context_recovery":None})
    result=driver.advance(
        manifest=manifest,state_root=state,
        campaign_id="health_once_20261124",max_science_sends=2,
        max_tasks=1,max_health_probes=1)
    assert result["health_probes_attempted_this_run"]==1
    assert result["science_browser_sends_reserved"]==2
    assert len(counted)==1
    assert counted[0]["source_sha"]=="a"*64
    assert result["G3_original_semantic_mappings_promoted"]==0


def test_normal_multisection_entrypoint_automatically_advances_without_campaign_prompt(
        campaign,monkeypatch,capsys):
    from selenium_pipeline import g3_multisection_autoforward_v71 as normal
    state,manifest,spec=campaign
    source=[]
    model=[]
    def source_stage(**kw):
        source.append(kw)
        return {"schema_version":1,
                "status":"G3_SOURCE_ONLY_STAGE_NO_REPLAY",
                "student_publication_authorized":False,
                "new_browser_dispatch_attempts_this_run":0}
    monkeypatch.setattr(normal,"run_campaign",source_stage)
    monkeypatch.setattr(driver,"advance",
        lambda **kw:(model.append(kw) or {
            "status":"G3_FAULT_INJECTED_AUTOFORWARD_COMPLETE",
            "student_publication_authorized":False,
            "science_browser_sends_reserved":4}))
    assert normal.main([
        "--manifest",str(manifest),
        "--state-dir",str(state),
        "--max-new-sends","0",
        "--auto-forward-science",
        "--science-max-sends","4",
        "--science-max-tasks","2"])==0
    record=json.loads(capsys.readouterr().out)
    assert record["student_publication_authorized"] is False
    assert record["continuing_science_automatically"]["science_browser_sends_reserved"]==4
    assert source[0]["auto_offline_repair"] is True
    assert source[0]["auto_semantic_source_repair"] is True
    assert model[0]["max_tasks"]==2
    assert model[0]["execute"] is True
    assert model[0]["campaign_id"].startswith("g3_source_auto_")
    with pytest.raises(ValueError):
        normal.main([
            "--manifest",str(manifest),
            "--state-dir",str(state),
            "--max-new-sends","1","--auto-forward-science"])
    assert len(source)==1
