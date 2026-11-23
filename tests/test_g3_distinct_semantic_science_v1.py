"""G3 independent two-pass science source checks, no original claim replay."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_g3_semantic_source_repair_v1 import sample
from selenium_pipeline import g3_semantic_source_repair_v1 as semantic
from selenium_pipeline import g3_distinct_semantic_science_v1 as science
from selenium_pipeline.series_gemini import OwnedGeminiResponse
from selenium_pipeline.recovery_registry import lookup_mechanism


@pytest.fixture
def ready(sample,tmp_path,monkeypatch):
    spec,worklists,_,request,packet,quote=sample
    root=tmp_path/"state"
    root.mkdir()
    semantic.materialize(
        specs=[spec],worklist_root=worklists,
        output_root=tmp_path/"semantic")
    task=next((tmp_path/"semantic").rglob("*.json"))
    monkeypatch.setattr(science,"qualified_health",lambda **kw:{
        "fresh_neon_high_source_free_health":True,
        "status":"G3_SOURCE_FREE_NEON_HIGH_HEALTH_VERIFIED",
    })
    monkeypatch.setattr(science,"_after_incident",lambda **kw:0.0)
    return spec,worklists,task,root,quote


def transport_for(quote,requests,*,wrong=False,dispute=False,
                  both_unresolved=False,timeout=False):
    def call(prompt,files):
        requests.append((prompt,files))
        if timeout:
            raise ConnectionError("Unexpected browser connection after Send")
        start=prompt.find('"spoken_sha256":')
        assert start>=0
        data=json.loads(prompt.split("Requested job and schema:\n",1)[1])
        unit=data["job"]["slides"][0]["utterances"][0]
        independent=(
            data["schema"]["task"]=="INDEPENDENT_CHALLENGE")
        rationale=(
            "The original physical textbook line explicitly defines "
            "average velocity as displacement divided by elapsed time."
            if not independent else
            "Independently, displacement per elapsed time is the "
            "average velocity; the selected source quote supports it.")
        obj={
            "status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
            "rows":[{
                "utterance_id":unit["id"],
                "spoken_sha256":unit["spoken_sha256"],
                "target_id":"s003.text.001",
                "source_page":1,
                "verbatim_source_quote":quote,
                "verdict":("UNRESOLVED" if both_unresolved or
                           (dispute and independent) else "SUPPORTED"),
                "math_explanation":rationale,
            }]}
        return OwnedGeminiResponse(
            json.dumps(obj,sort_keys=True),
            registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
            new_turn_verified=True,
            verified_model_family="neon" if not wrong else "flash",
            verified_thinking_level="high")
    return call


def run(ready,*,name="source_math_campaign",budget=2,execute=True,
        transport=None):
    spec,worklists,task,root,quote=ready
    return science.run_one(
        spec=spec,worklist_root=worklists,task_file=task,state_root=root,
        campaign_id=name,max_possible_sends=budget,
        execute=execute,transport=transport)


def test_semantic_science_two_pass_recovery_registered():
    assert lookup_mechanism(science.KIND,science.SIGNATURE)==science.MECHANISM


def test_two_distinct_owned_model_reviews_do_not_promote_original_mapping(ready):
    _,_,_,_,quote=ready
    calls=[]
    outcome=run(ready,transport=transport_for(quote,calls))
    assert outcome["status"]==science.REPORT
    assert outcome["possible_sends_reserved"]==2
    assert len(calls)==2
    assert all(file[0].name=="source.pdf" and file[1].name=="slides.pdf"
               for _,file in calls)
    receipt=outcome["two_pass_science_evidence"]
    assert receipt["two_actual_model_scientific_reviews"] is True
    assert receipt["science_AI_source_agreed"] is True
    assert receipt["original_G3_semantic_mappings_promoted"]==0
    assert outcome["paid_gemini_API_calls"]==0
    assert outcome["student_publication_authorized"] is False
    assert outcome["independent_scientific_QA_human_attestation"] is False
    # Replay of same campaign uses exact prior saved model text; ZERO Send.
    again=run(ready,transport=lambda *args:pytest.fail("No source replay"))
    assert again["status"]==science.REPORT
    assert again["possible_sends_reserved"]==2
    assert len(calls)==2


def test_independent_disagreement_does_not_become_scientific_support(ready):
    _,_,_,_,quote=ready
    calls=[]
    outcome=run(ready,transport=transport_for(quote,calls,dispute=True))
    assert outcome["status"]=="G3_DISTINCT_SEMANTIC_SOURCE_AI_DISPUTED_NO_PROMOTION"
    assert outcome["two_pass_science_evidence"]["science_AI_source_agreed"] is False
    assert outcome["old_G3_semantic_mappings_promoted"]==0


def test_health_missing_never_creates_source_claim(ready,monkeypatch):
    monkeypatch.setattr(science,"qualified_health",lambda **kw:None)
    result=run(ready,transport=lambda *a:pytest.fail("Must not send"))
    assert result["status"]=="G3_DISTINCT_SCIENCE_FRESH_NEON_HEALTH_REQUIRED"
    assert result["possible_sends_reserved"]==0


def test_dry_run_does_not_consume_any_send(ready):
    result=run(ready,budget=0,execute=False,
               transport=lambda *a:pytest.fail("Must not send"))
    assert result["status"]=="G3_DISTINCT_SCIENCE_AWAITING_AUTHORIZED_EXECUTION"
    assert result["possible_sends_reserved"]==0


def test_one_send_budget_then_resume_without_replaying_initial(ready):
    _,_,_,_,quote=ready
    calls=[]
    first=run(ready,budget=1,name="one_send_review",
              transport=transport_for(quote,calls))
    assert first["possible_sends_reserved"]==1
    assert first["status"]=="G3_DISTINCT_SCIENCE_BUDGET_OR_CLAIM_EXHAUSTED_NO_REPLAY"
    second=run(ready,budget=1,name="one_send_review",
               transport=lambda *a:pytest.fail("No second Send"))
    assert second["possible_sends_reserved"]==1
    assert len(calls)==1
    with pytest.raises(ValueError):
        run(ready,budget=2,name="one_send_review",
            transport=lambda *a:pytest.fail("Budget cannot increase"))


def test_ambiguous_original_send_does_not_replay_on_restart(ready):
    _,_,_,_,quote=ready
    calls=[]
    fail=run(ready,name="once_uncertain_review",transport=transport_for(
        quote,calls,timeout=True))
    assert fail["status"]=="G3_DISTINCT_SCIENCE_FAILED_OR_UNCERTAIN_NO_REPLAY"
    assert fail["possible_sends_reserved"]==1
    again=run(ready,name="once_uncertain_review",
              transport=lambda *a:pytest.fail("Never replay uncertain Send"))
    assert again["status"]=="G3_DISTINCT_SCIENCE_UNCERTAIN_NO_REPLAY"
    assert again["possible_sends_reserved"]==1
    assert len(calls)==1


def test_false_model_identity_never_becomes_accepted_science(ready):
    _,_,_,_,quote=ready
    calls=[]
    result=run(ready,name="wrong_model",transport=transport_for(
        quote,calls,wrong=True))
    assert result["status"]=="G3_DISTINCT_SCIENCE_FAILED_OR_UNCERTAIN_NO_REPLAY"
    assert result["two_pass_science_evidence"] is None
    assert result["old_G3_semantic_mappings_promoted"]==0


def test_tampered_publisher_task_halts_before_browser_send(ready):
    spec,worklists,task,root,quote=ready
    task.write_text('{"scientific_approval":true}')
    with pytest.raises(Exception):
        run(ready,transport=lambda *a:pytest.fail("Source changed"))


def test_source_pdf_change_halts_before_send(ready):
    spec,worklists,task,root,quote=ready
    (spec["source_folder"]/"source.pdf").write_bytes(b"%PDF changed")
    with pytest.raises(Exception):
        run(ready,transport=lambda *a:pytest.fail("Source changed"))


def test_normal_g3_semantic_source_cli_stages_then_dispatches_one_task(
        ready,monkeypatch,capsys):
    from selenium_pipeline import g3_multisection_autoforward_v71 as outer
    spec,worklists,task,root,quote=ready
    selected=[]
    monkeypatch.setattr(outer,"run_campaign",lambda **kw:{
        "new_browser_dispatch_attempts_this_run":0,
        "student_publication_authorized":False,
        "semantic_source_recovery":{"new_browser_sends":0}})
    monkeypatch.setattr(outer,"_verified_specs",
                        lambda manifest:({},[spec]))
    fake_root=root/"g3_distinct_semantic_science_tasks_v1"/spec["section"]
    fake_root.mkdir(parents=True)
    same=fake_root/task.name
    same.write_bytes(task.read_bytes())
    monkeypatch.setattr(science,"run_one",
        lambda **kw:(selected.append(kw) or {
            "status":"G3_TEST_ONLY_SOURCE_UNAPPROVED",
            "student_publication_authorized":False,
            "old_G3_semantic_mappings_promoted":0}))
    args=["--manifest",str(root/"placeholder_manifest.json"),
          "--state-dir",str(root),"--campaign-id","g3_campaign_test",
          "--max-possible-sends","2","--execute"]
    assert science.main(args)==0
    result=json.loads(capsys.readouterr().out)
    assert result["status"]=="G3_TEST_ONLY_SOURCE_UNAPPROVED"
    assert len(selected)==1
    assert selected[0]["task_file"]==same
    assert selected[0]["execute"] is True
    assert selected[0]["max_possible_sends"]==2


def test_new_cli_does_not_repeat_complete_twopass_task(ready,monkeypatch,capsys):
    from selenium_pipeline import g3_multisection_autoforward_v71 as outer
    spec,worklists,task,root,quote=ready
    fake_root=root/"g3_distinct_semantic_science_tasks_v1"/spec["section"]
    fake_root.mkdir(parents=True)
    (fake_root/task.name).write_bytes(task.read_bytes())
    t=json.loads(task.read_text())
    done=root/"g3_distinct_semantic_science_reviews_v1"/t["scope_sha256"]
    done.mkdir(parents=True)
    (done/"two_pass_science_evidence.json").write_text('{"unapproved":true}')
    monkeypatch.setattr(outer,"run_campaign",lambda **kw:{
        "new_browser_dispatch_attempts_this_run":0,
        "student_publication_authorized":False,
        "semantic_source_recovery":{"new_browser_sends":0}})
    monkeypatch.setattr(outer,"_verified_specs",
                        lambda manifest:({},[spec]))
    monkeypatch.setattr(science,"run_one",
                        lambda **kw:pytest.fail("Completed task not to be sent"))
    assert science.main(["--manifest",str(root/"nonexistent_manifest"),
          "--state-dir",str(root),"--campaign-id","no_more_science",
          "--max-possible-sends","2","--execute"])==0
    report=json.loads(capsys.readouterr().out)
    assert report["status"]=="NO_ELIGIBLE_NEW_G3_SOURCE_SEMANTIC_REVIEW"
    assert report["new_provider_requests"]==0
