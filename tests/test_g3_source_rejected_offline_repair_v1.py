"""G3 real-source quote repair candidates are NOT model acceptance."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from selenium_pipeline import g3_source_rejected_offline_repair_v1 as repair
from selenium_pipeline import g3_multisection_autoforward_v71 as campaign
from selenium_pipeline.recovery_registry import lookup_mechanism


def fixture(tmp_path,monkeypatch):
    base=tmp_path/"source_case"
    source,checkpoint,review=(base/"source",base/"checkpoint",base/"review")
    for p in (source,checkpoint,review):
        p.mkdir(parents=True)
    (checkpoint/"mapping_checkpoint.json").write_text(
        '{"original":true}',encoding="utf8")
    (review/"audited").mkdir()
    (review/"original_model_responses").mkdir()
    accepted={
        "status":"G3_HISTORICAL_SELENIUM_RICH_MAPPING_AUTOCONTINUATION_V1",
        "original_slides":2,
    }
    (review/"g3_auto_mapping_identity.json").write_text(json.dumps(accepted))
    request={
        "slide":1,
        "request_sha256":"a"*64,
        "source_inputs_sha256":{"source.pdf":"b"*64,
                                "slides.pdf":"c"*64,
                                "script.txt":"d"*64},
        "original_utterances":[{
            "utterance_id":"s001.utterance.001",
            "verbatim_text":"Velocity equals displacement divided by elapsed time."}],
        "visible_targets":[{
            "target_id":"s001.text.002","kind":"text_block",
            "visible_text":"Displacement divided by time gives velocity."}],
        "source_page_excerpts":[{
            "source_page":1,
            "original_page_text":"The rate of change of displacement with time is velocity.\n"
                                 "The displacement divided by elapsed time "
                                 "determines average velocity.\n"}],
    }
    response={
        "slide":1,"request_sha256":"a"*64,
        "associations":[{
            "utterance_id":"s001.utterance.001",
            "target_id":"s001.text.002","source_page":None,
            "source_quote":None,
            "reason":"Model chose a target without a valid source quotation.",
        }]
    }
    files=repair.reviewer._files(review,1)
    files["claim"].write_text(json.dumps({
        "status":"CAPTURED_SOURCE_REJECTED_NO_REPLAY",
        "request_sha256":"a"*64,
        "source_inputs_sha256":request["source_inputs_sha256"],
        "source_rejection_reason":
            "Model asserted a visible match without exact physical publisher quote",
    }))
    files["capture"].write_text(json.dumps(response))
    files["response"].write_text(json.dumps(response))
    monkeypatch.setattr(repair.reviewer,"prepare",lambda **kw:accepted)
    monkeypatch.setattr(repair.reviewer,"_verified_source_rejection",
        lambda **kw:{
            "status":"SOURCE_QUOTE_REJECTED_NO_REPLAY"})
    monkeypatch.setattr(repair,"request_for_slide",
                        lambda **kw:request.copy())
    monkeypatch.setattr(repair,"parse_response",json.loads)
    def inspect(*,n,**kw):
        if n==1:return {"status":"SOURCE_QUOTE_REJECTED_NO_REPLAY"}
        return {"status":"CLAIMED_OR_UNKNOWN_SEND_NO_REPLAY"}
    monkeypatch.setattr(repair.reviewer,"_inspect_one",inspect)
    specs=[{"section":"Serway_8_2","source_folder":source,
            "checkpoint":checkpoint,"review_root":review}]
    return specs,request,response,files


def test_recovery_mechanism_registered_and_nonexecutable_registry():
    assert lookup_mechanism(repair.KIND,repair.SIGNATURE)==repair.MECHANISM


def test_physical_verbatim_span_not_semantic_certification():
    source="The displacement divided by elapsed time determines average velocity."
    spans=repair._source_spans(
        utterance="Velocity equals displacement divided by elapsed time.",
        target_text="Displacement divided by time gives velocity.",
        pages=[{"source_page":2,"original_page_text":source}])
    assert len(spans)==1
    x=spans[0]
    assert source[x["source_offset_start"]:x["source_offset_end"]]==x[
        "publisher_quote_verbatim"]
    assert x["quote_physically_present"] is True
    assert x["meaning_or_target_mapping_verified"] is False
    assert x["independent_scientific_QA_approved"] is False
    assert x["lexical_overlap_count"]>=2


def test_missing_context_never_fabricates_quote():
    spans=repair._source_spans(
        utterance="The spin parity of the unknown boson.",
        target_text="Forbidden transition rule.",
        pages=[{"source_page":3,
                "original_page_text":
                    "This paragraph concerns the thermal properties of sand."}])
    assert spans==[]


def test_rejected_model_source_quote_worklist_durable_and_no_send(
        tmp_path,monkeypatch):
    specs,req,response,files=fixture(tmp_path,monkeypatch)
    folder=tmp_path/"g3_offline"
    a=repair.materialize(specs=specs,output_root=folder)
    assert a["status"]=="G3_REJECTED_SOURCE_OFFLINE_WORKLIST_PERSISTED_NO_MODEL_SEND"
    assert a["rejected_original_slides_retained"]==1
    assert a["uncertain_original_browser_sends_retained"]==1
    assert a["untouched_original_slides"]==0
    assert a["new_browser_sends"]==0
    assert a["new_paid_gemini_API_requests"]==0
    assert a["new_original_source_review_acceptances"]==0
    assert a["independent_scientific_QA_complete"] is False
    assert a["student_publication_authorized"] is False
    record=Path(a["offline_quote_worklists"][0]["worklist_path"])
    saved=record.read_bytes()
    data=json.loads(saved)
    assert data["original_rejected_source_review_accepted"] is False
    assert data["repaired_source_to_target_mapping_accepted"] is False
    assert len(data["publisher_quote_worklist"])==1
    assert data["publisher_quote_worklist"][0][
        "status"]=="PHYSICALLY_WITNESSED_LEXICAL_CANDIDATES_NOT_SEMANTIC_REPAIR"
    assert repair.materialize(specs=specs,output_root=folder)==a
    assert record.read_bytes()==saved


def test_tampered_prior_worklist_fails_closed(tmp_path,monkeypatch):
    specs,req,response,files=fixture(tmp_path,monkeypatch)
    folder=tmp_path/"worklists"
    first=repair.materialize(specs=specs,output_root=folder)
    path=Path(first["offline_quote_worklists"][0]["worklist_path"])
    path.write_text('{"forged":"scientific acceptance"}')
    with pytest.raises(ValueError,match="changed"):
        repair.materialize(specs=specs,output_root=folder)


def test_claim_or_source_identity_drift_blocks_worklist(tmp_path,monkeypatch):
    specs,req,response,files=fixture(tmp_path,monkeypatch)
    x=json.loads(files["claim"].read_text())
    x["request_sha256"]="f"*64
    files["claim"].write_text(json.dumps(x))
    with pytest.raises(ValueError,match="identity changed"):
        repair.materialize(specs=specs,output_root=tmp_path/"output")


def test_existing_rejected_reply_cannot_launder_semantic_or_audio_approval(
        tmp_path,monkeypatch):
    specs,req,response,files=fixture(tmp_path,monkeypatch)
    original=repair.materialize(specs=specs,output_root=tmp_path/"output")
    row=json.loads(Path(original["offline_quote_worklists"][0][
        "worklist_path"]).read_text())
    assert row["new_browser_sends"]==0
    assert row["original_historical_model_request_replayed"] is False
    assert row["independent_acoustic_review_complete"] is False
    assert row["highlighted_video_accepted"] is False
    assert row["student_publication_authorized"] is False
    assert all(not s["source_excerpt_candidates"]
               or all(c["meaning_or_target_mapping_verified"] is False
                      for c in s["source_excerpt_candidates"])
               for s in row["publisher_quote_worklist"])


def test_legacy_campaign_preserves_zero_send_contract_when_flag_unset(
        tmp_path,monkeypatch):
    from tests.test_g3_multisection_autoforward_v71 import campaign as fake_campaign
    state,manifest,root=fake_campaign(tmp_path,monkeypatch)
    report=campaign.run_campaign(
        manifest=manifest,state_dir=root,max_new_sends=0)
    assert report["source_rejected_offline_recovery"] is None
    assert report["new_browser_dispatch_attempts_this_run"]==0
    assert report["student_publication_authorized"] is False


def test_worklist_stage_crash_recovery_is_exact_and_one_time(tmp_path):
    home=tmp_path/"worklists"
    home.mkdir()
    record=home/"slide_004.json"
    packet={"status":"ORIGINAL_SOURCE_ONLY_WORKLIST","approved":False}
    stage=record.with_suffix(".stage")
    stage.write_bytes(repair._canon(packet))
    repair._write_once(record,packet)
    assert record.read_bytes()==repair._canon(packet)
    assert not stage.exists()
    # A second crash after the final write can leave a duplicate .stage.
    stage.write_bytes(record.read_bytes())
    repair._write_once(record,packet)
    assert record.read_bytes()==repair._canon(packet)
    assert not stage.exists()


def test_worklist_conflicting_interrupted_stage_fails_closed(tmp_path):
    home=tmp_path/"worklists"
    home.mkdir()
    record=home/"slide_004.json"
    stage=record.with_suffix(".stage")
    stage.write_text('{"unsafe":"source invented"}')
    with pytest.raises(ValueError,match="changed"):
        repair._write_once(record,{"status":"ORIGINAL_SOURCE_ONLY_WORKLIST"})


def test_offline_source_recovery_in_campaign_runs_with_global_circuit_open(
        tmp_path,monkeypatch):
    from tests.test_g3_multisection_autoforward_v71 import campaign as fake_campaign
    state,manifest,root=fake_campaign(tmp_path,monkeypatch)
    # The existing original source-review circuit is already open; source
    # reconciliation MUST continue with zero new Selenium Sends.
    for record in state["pages"].values():
        record["uncertain"]=1
        record["rejected"]=2
        record["remaining"]=0
    calls=[]
    monkeypatch.setattr(repair,"materialize",lambda **kwargs:(
        calls.append(kwargs) or {
            "status":"G3_REJECTED_SOURCE_OFFLINE_WORKLIST_PERSISTED_NO_MODEL_SEND",
            "rejected_original_slides_retained":4,
            "new_browser_sends":0,
            "new_paid_gemini_API_requests":0,
            "new_original_source_review_acceptances":0,
            "student_publication_authorized":False,
        }))
    result=campaign.run_campaign(
        manifest=manifest,state_dir=root,max_new_sends=1,
        auto_offline_repair=True)
    assert result["stopped_reason"]=="GLOBAL_TWO_UNCERTAIN_BROWSER_REQUESTS_NO_RETRY"
    assert result["new_browser_dispatch_attempts_this_run"]==0
    assert state["calls"]==[]
    assert result["source_rejected_offline_recovery"][
        "rejected_original_slides_retained"]==4
    assert len(calls)==1
    assert result["independent_scientific_QA_complete"] is False
    assert result["student_publication_authorized"] is False


def test_single_shared_word_does_not_count_as_a_real_lexical_candidate():
    # Source and narration sharing only 'summary' is insufficient even for
    # a source quote suggestion; do not fabricate a scientific fix.
    candidates=repair._source_spans(
        utterance="We will summarize the quantum oscillator results.",
        target_text="Summary and Review Questions",
        pages=[{"source_page":1,
                "original_page_text":
                    "Summary of the main classical conservation equations.\n"}])
    assert candidates==[]
