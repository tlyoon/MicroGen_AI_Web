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
    from selenium_pipeline import g3_browser_post_send_health_gate_v1 as gate
    monkeypatch.setattr(gate,"latest_unresolved_incident",lambda **kw:0.0)
    monkeypatch.setattr(driver,"latest_health",lambda **kw:{
        "status":"G3_SOURCE_FREE_NEON_HIGH_HEALTH_VERIFIED",
        "fresh_neon_high_source_free_health":True,
        "observed_unix":100.0})
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



def test_conservative_existing_campaign_budget_reentry_preserves_journal(
        campaign,monkeypatch):
    from selenium_pipeline.recovery_registry import lookup_mechanism
    assert lookup_mechanism(
        driver.CAP_KIND,driver.CAP_SIGNATURE)==driver.CAP_MECHANISM
    state,manifest,spec=campaign
    first=item(spec,"a"*64,"NEW_CONTEXT")
    second=item(spec,"b"*64,"ORIGINAL_DISTINCT")
    sent=[]
    monkeypatch.setattr(driver,"_eligible",
        lambda **kw:[x for x in (first,second)
                     if x["scope"] not in sent])
    def run(**kw):
        sent.append(kw["task_file"].stem)
        return {"status":"SOURCE_SCIENCE_NOT_AUTOMATICALLY_APPROVED",
                "possible_sends_reserved":2,
                "two_pass_science_evidence":{"science_AI_source_agreed":False},
                "semantic_context_recovery":None}
    monkeypatch.setattr(driver,"run_one",run)
    args=dict(manifest=manifest,state_root=state,
              campaign_id="conservative_restart_20261124",
              max_science_sends=4,max_tasks=1,max_health_probes=0)
    first_run=driver.advance(**args)
    assert first_run["science_browser_sends_reserved"]==2
    home=state/"g3_continuous_advance_v1"/args["campaign_id"]
    before_header=(home/"campaign.json").read_bytes()
    before_events=sorted(
        (f.name,f.read_bytes()) for f in home.glob("event_*.json"))
    resumed=driver.advance(**{**args,"max_science_sends":2,
                              "max_tasks":2})
    assert sent==["a"*64]
    assert resumed["original_immutable_campaign_send_cap"]==4
    assert resumed["max_science_browser_sends"]==2
    assert resumed["science_browser_sends_reserved"]==2
    assert resumed["stages_advanced_this_run"]==0
    assert resumed["status"]=="FINITE_G3_SOURCE_CAMPAIGN_BUDGET_EXHAUSTED"
    assert (home/"campaign.json").read_bytes()==before_header
    assert sorted((f.name,f.read_bytes()) for f in home.glob("event_*.json"))==before_events
    assert resumed["original_historical_model_claims_replayed"] is False
    assert resumed["student_publication_authorized"] is False


def test_tighter_budget_never_resumes_more_previously_reserved_sends(
        campaign,monkeypatch):
    state,manifest,spec=campaign
    todo=[item(spec,"c"*64,"NEW_CONTEXT"),
          item(spec,"d"*64,"ORIGINAL_DISTINCT")]
    completed=[]
    monkeypatch.setattr(driver,"_eligible",
        lambda **kw:[x for x in todo if x["scope"] not in completed])
    def run(**kw):
        completed.append(kw["task_file"].stem)
        return {"status":"NOT_APPROVED","possible_sends_reserved":2,
                "two_pass_science_evidence":{"science_AI_source_agreed":False},
                "semantic_context_recovery":None}
    monkeypatch.setattr(driver,"run_one",run)
    args=dict(manifest=manifest,state_root=state,
              campaign_id="above_restricted_cap_20261124",
              max_science_sends=4,max_tasks=2,max_health_probes=0)
    initial=driver.advance(**args)
    assert initial["science_browser_sends_reserved"]==4
    before=(state/"g3_continuous_advance_v1"/args["campaign_id"]/
            "campaign.json").read_bytes()
    monkeypatch.setattr(driver,"run_one",lambda **kw:
        pytest.fail("Cannot replay already-budgeted model work"))
    resumed=driver.advance(**{**args,"max_science_sends":2})
    assert resumed["science_browser_sends_reserved"]==4
    assert resumed["original_immutable_campaign_send_cap"]==4
    assert resumed["stages_advanced_this_run"]==0
    assert resumed["status"]=="FINITE_G3_SOURCE_CAMPAIGN_BUDGET_EXHAUSTED"
    assert len(completed)==2
    assert (state/"g3_continuous_advance_v1"/args["campaign_id"]/
            "campaign.json").read_bytes()==before


def test_tighter_cap_does_not_mask_original_source_manifest_drift(
        campaign,monkeypatch):
    state,manifest,spec=campaign
    monkeypatch.setattr(driver,"_eligible",lambda **kw:[])
    args=dict(manifest=manifest,state_root=state,
              campaign_id="source_sha_locked_reentry_20261124",
              max_science_sends=4,max_tasks=1,max_health_probes=0)
    driver.advance(**args)
    manifest.write_text('{"source_first":false}')
    with pytest.raises(ValueError,match="Existing immutable recovery event changed"):
        driver.advance(**{**args,"max_science_sends":2})


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
            "fresh_neon_high_source_free_health":True,
            "observed_unix":100.0}))
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


def test_held_unreconciled_source_send_does_not_strand_another_task(
        campaign,monkeypatch):
    state,manifest,spec=campaign
    first=item(spec,"1"*64,"NEW_CONTEXT")
    second=item(spec,"2"*64,"ORIGINAL_DISTINCT")
    models=[]
    monkeypatch.setattr(driver,"_eligible",lambda **kw:[first,second])
    def review(**kw):
        scope=kw["task_file"].stem
        models.append(scope)
        return {
            "status":(
                "G3_DISTINCT_SCIENCE_UNCERTAIN_NO_REPLAY"
                if scope==first["scope"] else
                "G3_DISTINCT_SCIENCE_ONE_PASS_UNAPPROVED"),
            "possible_sends_reserved":2,
            "two_pass_science_evidence":(
                None if scope==first["scope"] else
                {"science_AI_source_agreed":False}),
            "semantic_context_recovery":None,
        }
    monkeypatch.setattr(driver,"run_one",review)
    args=dict(manifest=manifest,state_root=state,
        campaign_id="quarantine_then_advance_20261124",
        max_science_sends=4,max_tasks=2,max_health_probes=0)
    outcome=driver.advance(**args)
    assert models==["1"*64,"2"*64]
    assert outcome["stages_advanced_this_run"]==2
    assert outcome["science_browser_sends_reserved"]==4
    assert outcome["stage_results"][0]["status"]==(
        "G3_DISTINCT_SCIENCE_UNCERTAIN_NO_REPLAY")
    assert outcome["original_historical_model_claims_replayed"] is False
    again=driver.advance(**args)
    assert again["stages_advanced_this_run"]==0
    assert models==["1"*64,"2"*64]


def test_stale_health_after_realistic_uncertain_send_never_reserves_new_budget(
        campaign,monkeypatch):
    from selenium_pipeline import g3_browser_post_send_health_gate_v1 as gate
    state,manifest,spec=campaign
    item_one=item(spec,"7"*64,"NEW_PUBLISHER_PREPASS")
    monkeypatch.setattr(driver,"_eligible",lambda **kw:[item_one])
    monkeypatch.setattr(gate,"latest_unresolved_incident",lambda **kw:200.0)
    monkeypatch.setattr(driver,"latest_health",lambda **kw:{
        "status":"G3_SOURCE_FREE_NEON_HIGH_HEALTH_VERIFIED",
        "fresh_neon_high_source_free_health":True,
        "observed_unix":100.0})
    monkeypatch.setattr(driver,"run_one",
        lambda **kw:pytest.fail("Cannot Send under stale post-error model health"))
    receipt=driver.advance(
        manifest=manifest,state_root=state,
        campaign_id="stale_provider_receipt_20261124",
        max_science_sends=2,max_tasks=1,max_health_probes=0)
    assert receipt["stages_advanced_this_run"]==0
    assert receipt["science_browser_sends_reserved"]==0
    assert receipt["stage_results"][0]["status"]==(
        "FRESH_OWNED_NEON_HEALTH_REQUIRED_NO_SOURCE_SEND")


def test_missing_health_in_one_section_does_not_block_another(
        campaign,monkeypatch):
    """Skip stale source 8.2, advance verified independent 8.3 only."""
    from selenium_pipeline.recovery_registry import lookup_mechanism
    assert lookup_mechanism(
        driver.SKIP_KIND,driver.SKIP_SIGNATURE)==driver.SKIP_MECHANISM
    state,manifest,spec=campaign
    other={**spec,"section":"Serway_8_3",
           "identity":{"source_inputs_sha256":{"source.pdf":"b"*64}}}
    monkeypatch.setattr(driver,"_verified_specs",
                        lambda p:({},[spec,other]))
    first=item(spec,"c"*64,"NEW_CONTEXT")
    first_repeat=item(spec,"d"*64,"ORIGINAL_DISTINCT")
    second={**item(other,"e"*64,"NEW_CONTEXT"),
            "section":"Serway_8_3"}
    monkeypatch.setattr(driver,"_eligible",
                        lambda **kw:[first,first_repeat,second])
    verified={"status":"G3_SOURCE_FREE_NEON_HIGH_HEALTH_VERIFIED",
              "fresh_neon_high_source_free_health":True,
              "observed_unix":100.0}
    monkeypatch.setattr(driver,"latest_health",lambda **kw:
                        None if kw["source_sha"]=="a"*64 else verified)
    ran=[]
    def run(**kw):
        ran.append(kw["task_file"].stem)
        return {"status":"SCIENCE_SOURCE_REVIEW_STAGED_UNAPPROVED",
                "possible_sends_reserved":2,
                "two_pass_science_evidence":{"science_AI_source_agreed":False},
                "semantic_context_recovery":None}
    monkeypatch.setattr(driver,"run_one",run)
    receipt=driver.advance(
        manifest=manifest,state_root=state,
        campaign_id="safe_other_source_forward_20261124",
        max_science_sends=2,max_tasks=3,max_health_probes=0)
    assert ran==["e"*64]
    assert receipt["science_browser_sends_reserved"]==2
    assert receipt["stages_advanced_this_run"]==1
    assert [x["section"] for x in receipt["stage_results"]]==[
        "Serway_8_2","Serway_8_3"]
    assert receipt["health_blocked_sources"]==[
        {"section":"Serway_8_2","source_sha256":"a"*64}]
    assert receipt["health_blocked_source_count"]==1
    assert receipt["health_probes_attempted_this_run"]==0
    assert receipt["paid_gemini_API_requests"]==0
    assert receipt["source_scientific_approval_automatically_granted"] is False
    assert receipt["student_publication_authorized"] is False


def test_all_missing_health_finishes_finitely_without_repeat_or_send(
        campaign,monkeypatch):
    state,manifest,spec=campaign
    other={**spec,"section":"Serway_8_3",
           "identity":{"source_inputs_sha256":{"source.pdf":"b"*64}}}
    monkeypatch.setattr(driver,"_verified_specs",
                        lambda p:({},[spec,other]))
    first=item(spec,"f"*64,"NEW_CONTEXT")
    first_repeat=item(spec,"d"*64,"ORIGINAL_DISTINCT")
    second={**item(other,"e"*64,"NEW_CONTEXT"),
            "section":"Serway_8_3"}
    monkeypatch.setattr(driver,"_eligible",lambda **kw:[
        first,first_repeat,second])
    checks=[]
    monkeypatch.setattr(driver,"latest_health",lambda **kw:
                        (checks.append(kw["source_sha"]) or None))
    monkeypatch.setattr(driver,"run_one",lambda **kw:
                        pytest.fail("No Send without owned post-incident health"))
    got=driver.advance(
        manifest=manifest,state_root=state,
        campaign_id="both_health_blocked_20261124",
        max_science_sends=2,max_tasks=4,max_health_probes=0)
    assert checks==["a"*64,"b"*64]
    assert got["health_blocked_source_count"]==2
    assert got["stages_advanced_this_run"]==0
    assert got["science_browser_sends_reserved"]==0
    assert got["status"]=="G3_SOURCE_AUTOFORWARD_AWAITING_FRESH_HEALTH_NO_SEND"
    assert len(got["stage_results"])==2
    assert got["remaining_other_source_eligible_tasks"]==0
    assert got["paid_gemini_API_requests"]==0
    assert got["original_historical_model_claims_replayed"] is False
    assert got["student_publication_authorized"] is False
    # Same campaign restart does not fabricate a new eligibility or approval.
    again=driver.advance(
        manifest=manifest,state_root=state,
        campaign_id="both_health_blocked_20261124",
        max_science_sends=2,max_tasks=4,max_health_probes=0)
    assert again["science_browser_sends_reserved"]==0
    assert again["health_blocked_source_count"]==2
    assert again["stages_advanced_this_run"]==0
