"""Real checkpoint, historical replay and cross-section fault injection."""
import json
from pathlib import Path

import pytest

from selenium_pipeline import g3_multisection_autoforward_v71 as c
from selenium_pipeline.recovery_registry import lookup_mechanism


def campaign(tmp_path,monkeypatch,sections=("8_2","8_3"),total=3):
    fake={"pages":{s:{"remaining":total,"reviewed":0,"anchors":0,"uncertain":0}
                   for s in sections},"calls":[]}
    def prepare(*,source_folder,checkpoint,review_root):
        assert Path(source_folder).is_dir()
        assert Path(checkpoint).is_dir()
        assert Path(review_root).is_dir()
        return {
            "source_inputs_sha256":{"source.pdf":"a"*64,
                "slides.pdf":"b"*64,"script.txt":"c"*64},
            "mapping_checkpoint_sha256":"d"*64,
            "original_slides":total}
    def run(*,source_folder,checkpoint,review_root,max_new_sends,**kw):
        section=Path(source_folder).parent.name
        row=fake["pages"][section]
        failure=[]
        if max_new_sends:
            fake["calls"].append(section)
            if row["remaining"]:
                row["remaining"]-=1
                if fake.get("mark_uncertain"):
                    row["uncertain"]+=1
                else:
                    row["reviewed"]+=1
                    row["anchors"]+=1
            if fake.get("inject_crash"):
                fake["inject_crash"]=False
                raise SystemExit("original Send registered; caller died")
            if fake.get("failure"):
                failure=[{"error_type":"TimeoutError","slide":1}]
        return {
            "new_browser_dispatch_attempts_this_run":max_new_sends,
            "paid_gemini_api_requests":0,
            "student_publication_authorized":False,
            "developer_api_fallback_permitted":False,
            "original_reviewed_slides_reused":row["reviewed"],
            "original_textbook_and_rendered_text_anchors_proven":row["anchors"],
            "source_review_gaps_within_reviewed_slides":row["reviewed"],
            "remaining_unreviewed_slides":row["remaining"],
            "quarantined_or_uncertain_slides":row["uncertain"],
            "dispatch_failures":failure,
        }
    monkeypatch.setattr(c.reviewer,"prepare",prepare)
    monkeypatch.setattr(c.reviewer,"run",run)
    parent=tmp_path/"campaign"
    parent.mkdir()
    specs=[]
    for name in sections:
        home=tmp_path/name
        for suffix in ("source","map","review"):
            (home/suffix).mkdir(parents=True)
        specs.append({"section":name,
              "source_folder":str(home/"source"),
              "checkpoint":str(home/"map"),
              "review_root":str(home/"review")})
    manifest=parent/"source_pinned_campaign.json"
    manifest.write_text(json.dumps({
        "schema_version":1,
        "status":c.STATUS,
        "sections":specs,
        "browser_port":9222,
        "paid_gemini_api_requests_authorized":0,
        "student_publication_authorized":False,
    }),encoding="utf8")
    return fake,manifest,parent/"immutable_receipts"


def test_registered():
    assert lookup_mechanism(c.KIND,c.SIGNATURE)==c.REPAIR


def test_dry_run_creates_source_pinned_identity_without_browser_calls(
        tmp_path,monkeypatch):
    fake,manifest,root=campaign(tmp_path,monkeypatch)
    result=c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=0)
    assert result["new_browser_dispatch_attempts_this_run"]==0
    assert result["untouched_original_slides"]==6
    assert result["stopped_reason"]=="NO_NEW_SENDS_REQUESTED"
    assert fake["calls"]==[]
    assert (root/"campaign_identity.json").is_file()
    assert not list(root.glob("event_*.json"))
    again=c.run_campaign(manifest=manifest,state_dir=root)
    assert result==again


def test_automatic_next_section_no_user_proceed_and_restart_fairness(
        tmp_path,monkeypatch):
    fake,manifest,root=campaign(tmp_path,monkeypatch)
    result=c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=3)
    assert result["new_browser_dispatch_attempts_this_run"]==3
    assert fake["calls"]==["8_2","8_3","8_2"]
    assert result["total_immutable_dispatch_receipts"]==3
    next_run=c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=2)
    assert next_run["total_immutable_dispatch_receipts"]==5
    assert fake["calls"]==["8_2","8_3","8_2","8_3","8_2"]
    assert next_run["untouched_original_slides"]==1


def test_global_cross_section_circuit_breaker_persists_across_restart(
        tmp_path,monkeypatch):
    fake,manifest,root=campaign(tmp_path,monkeypatch,total=5)
    fake["mark_uncertain"]=True
    initial=c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=6)
    assert initial["new_browser_dispatch_attempts_this_run"]==2
    assert initial["quarantined_or_uncertain_original_slides"]==2
    assert initial["stopped_reason"]=="GLOBAL_TWO_UNCERTAIN_BROWSER_REQUESTS_NO_RETRY"
    assert fake["calls"]==["8_2","8_3"]
    resumed=c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=6)
    assert resumed["new_browser_dispatch_attempts_this_run"]==0
    assert fake["calls"]==["8_2","8_3"]


def test_previous_claim_after_crash_does_not_repeat_same_section_and_advances(
        tmp_path,monkeypatch):
    fake,manifest,root=campaign(tmp_path,monkeypatch,total=3)
    fake["inject_crash"]=True
    fake["mark_uncertain"]=True
    with pytest.raises(SystemExit,match="caller died"):
        c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=3)
    assert fake["calls"]==["8_2"]
    assert not list(root.glob("event_*.json"))
    resumed=c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=1)
    assert resumed["new_browser_dispatch_attempts_this_run"]==1
    assert fake["calls"]==["8_2","8_3"]
    assert resumed["quarantined_or_uncertain_original_slides"]==2
    # Another restart refuses any subsequent new submission.
    c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=3)
    assert fake["calls"]==["8_2","8_3"]


def test_tampering_previous_receipt_quarantines_without_send(
        tmp_path,monkeypatch):
    fake,manifest,root=campaign(tmp_path,monkeypatch)
    c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=2)
    first=root/"event_0000.json"
    row=json.loads(first.read_text("utf8"))
    row["student_publication_authorized"]=True
    first.write_text(json.dumps(row),encoding="utf8")
    with pytest.raises(ValueError,match="Malformed or altered"):
        c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=2)
    assert len(fake["calls"])==2


def test_source_campaign_manifest_mutation_blocked_across_restart(
        tmp_path,monkeypatch):
    fake,manifest,root=campaign(tmp_path,monkeypatch)
    c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=1)
    row=json.loads(manifest.read_text("utf8"))
    row["sections"].reverse()
    manifest.write_text(json.dumps(row),encoding="utf8")
    with pytest.raises(ValueError,match="source, files or campaign plan changed"):
        c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=2)
    assert len(fake["calls"])==1


def test_second_concurrent_owner_disallowed(tmp_path,monkeypatch):
    fake,manifest,root=campaign(tmp_path,monkeypatch)
    c.run_campaign(manifest=manifest,state_dir=root)
    with c.reviewer._exclusive(root):
        with pytest.raises(Exception,match="Another G3 source-review owner"):
            c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=2)
    assert not fake["calls"]


def test_two_browser_failures_stop_even_with_unclaimed_other_sections(
        tmp_path,monkeypatch):
    fake,manifest,root=campaign(tmp_path,monkeypatch,total=5)
    fake["failure"]=True
    result=c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=6)
    assert result["new_browser_dispatch_attempts_this_run"]==2
    assert result["stopped_reason"]=="TWO_CONSECUTIVE_BROWSER_FAILURES_NO_REPEAT"


@pytest.mark.parametrize("invalid",[-1,33,True,"2"])
def test_finite_request_budget_rejects_invalid_values_without_send(
        tmp_path,monkeypatch,invalid):
    fake,manifest,root=campaign(tmp_path,monkeypatch)
    with pytest.raises(ValueError,match="unlimited"):
        c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=invalid)
    assert fake["calls"]==[]


def test_bad_manifest_does_not_call_provider(tmp_path,monkeypatch):
    fake,manifest,root=campaign(tmp_path,monkeypatch)
    item=json.loads(manifest.read_text("utf8"))
    item["paid_gemini_api_requests_authorized"]=1
    manifest.write_text(json.dumps(item),encoding="utf8")
    with pytest.raises(ValueError,match="source-only campaign"):
        c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=2)
    assert fake["calls"]==[]


def test_no_automatic_claim_of_independent_scientific_audio_video_acceptance(
        tmp_path,monkeypatch):
    fake,manifest,root=campaign(tmp_path,monkeypatch,total=1)
    result=c.run_campaign(manifest=manifest,state_dir=root,max_new_sends=6)
    assert result["status"].endswith("REVIEW_ONLY")
    assert result["independent_scientific_QA_complete"] is False
    assert result["independent_acoustic_QA_complete"] is False
    assert result["highlighted_video_accepted"] is False
    assert result["student_publication_authorized"] is False
    assert result["paid_gemini_api_requests"]==0
