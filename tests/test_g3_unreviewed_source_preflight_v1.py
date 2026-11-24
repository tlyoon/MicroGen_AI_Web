"""Old G3 source-only slides must be staged without browser / model Sends."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from selenium_pipeline import g3_unreviewed_source_preflight_v1 as pre
from selenium_pipeline.recovery_registry import lookup_mechanism


@pytest.fixture
def source(tmp_path,monkeypatch):
    from selenium_pipeline import g3_unreviewed_source_preflight_v1 as mod
    state=tmp_path/"state"
    folder=tmp_path/"source"
    checkpoint=tmp_path/"mapping"
    review=tmp_path/"saved_reviews"
    for p in (state,folder,checkpoint,review):p.mkdir()
    spec={"section":"Serway_8_2","source_folder":folder,
          "checkpoint":checkpoint,"review_root":review}
    shas={"source.pdf":"a"*64,"slides.pdf":"b"*64,
          "script.txt":"c"*64}
    identity={
        "original_slides":3,
        "source_inputs_sha256":shas.copy(),
        "mapping_checkpoint_sha256":"d"*64,
    }
    states={1:"ELIGIBLE_FRESH_SOURCE_REVIEW_NO_SEND_YET",
            2:"CLAIMED_OR_UNKNOWN_SEND_NO_REPLAY",
            3:"ELIGIBLE_FRESH_SOURCE_REVIEW_NO_SEND_YET"}
    def inspect(**kw):
        return {"slide":kw["n"],"status":states[kw["n"]]}
    def request(**kw):
        number=kw["slide_number"]
        return {
            "slide":number,"source_inputs_sha256":shas.copy(),
            "request_sha256":f"{number:064x}",
            "original_utterances":[
                {"utterance_id":f"s{number:03d}.utterance.001",
                 "verbatim_text":f"Original Serway {number} narration."}],
            "visible_targets":[
                {"target_id":f"s{number:03d}.text.001",
                 "visible_text":f"Original slide {number} text.",
                 "kind":"text_block"}],
        }
    monkeypatch.setattr(mod,"prepare_owner",lambda **kw:identity)
    monkeypatch.setattr(mod,"_inspect_one",inspect)
    monkeypatch.setattr(mod,"request_for_slide",request)
    return spec,state,states,shas,request


def test_registry_explicit_recovery():
    assert lookup_mechanism(pre.KIND,pre.SIGNATURE)==pre.MECHANISM


def test_source_preflight_stages_only_uncaptured_original_slides(source):
    spec,root,states,shas,request=source
    result=pre.materialize(specs=[spec],state_root=root)
    assert result["status"]=="G3_ORIGINAL_UNREVIEWED_SLIDES_SOURCE_PINNED_NO_SEND"
    assert [item["slide"] for item in result["tasks"]]==[1,3]
    assert result["original_untouched_slides_prepared"]==2
    assert result["new_browser_sends"]==0
    assert result["original_science_approvals"]==0
    assert result["paid_gemini_API_calls"]==0
    assert result["student_publication_authorized"] is False
    saved=list((root/pre.ROOT/spec["section"]).glob("*.json"))
    assert len(saved)==2
    for file in saved:
        task=pre.pinned(spec=spec,state_root=root,task_file=file)
        assert task["original_model_claim_observed"] is False
        assert task["independent_scientific_QA_complete"] is False
        assert task["independent_acoustic_QA_complete"] is False
        assert task["student_publication_authorized"] is False
        assert len(task["original_utterances"])==1
        assert len(task["original_visible_targets"])==1
        assert task["original_mapping_request_sha256"]==(
            f"{task['original_slide']:064x}")
    # Restart/reconcile on SAME immutable source has identical results.
    assert pre.materialize(specs=[spec],state_root=root)==result


def test_old_send_claim_appearing_after_preflight_blocks_reuse(source):
    spec,root,states,shas,request=source
    pre.materialize(specs=[spec],state_root=root)
    p=next((root/pre.ROOT/spec["section"]).glob("*.json"))
    slide=json.loads(p.read_text("utf8"))["original_slide"]
    states[slide]="CLAIMED_OR_UNKNOWN_SEND_NO_REPLAY"
    with pytest.raises(ValueError,match="never replay"):
        pre.pinned(spec=spec,state_root=root,task_file=p)


def test_original_mapping_identity_change_rejected(source):
    spec,root,states,shas,request=source
    shas["source.pdf"]="f"*64
    # original owner held the PREVIOUS original source, not the new fake hash
    with pytest.raises(ValueError,match="fingerprint changed"):
        pre.materialize(specs=[spec],state_root=root)


def test_original_visible_text_change_after_stage_rejected(source,monkeypatch):
    spec,root,states,shas,request=source
    pre.materialize(specs=[spec],state_root=root)
    p=next((root/pre.ROOT/spec["section"]).glob("*.json"))
    old=request
    def changed(**kw):
        item=old(**kw)
        item["visible_targets"][0]["visible_text"]="Different diagram"
        return item
    monkeypatch.setattr(pre,"request_for_slide",changed)
    with pytest.raises(ValueError,match="source proof changed"):
        pre.pinned(spec=spec,state_root=root,task_file=p)


def test_mutation_of_immutable_task_fails_closed(source):
    spec,root,states,shas,request=source
    pre.materialize(specs=[spec],state_root=root)
    p=next((root/pre.ROOT/spec["section"]).glob("*.json"))
    task=json.loads(p.read_text("utf8"))
    task["student_publication_authorized"]=True
    p.write_text(json.dumps(task))
    with pytest.raises(ValueError,match="modified"):
        pre.materialize(specs=[spec],state_root=root)


def test_reviewed_or_uncertain_only_creates_no_fake_work(source):
    spec,root,states,shas,request=source
    states[1]="SAVED_SOURCE_AUDITED_REVIEW_ONLY"
    states[3]="CLAIMED_OR_UNKNOWN_SEND_NO_REPLAY"
    report=pre.materialize(specs=[spec],state_root=root)
    assert report["original_untouched_slides_prepared"]==0
    assert report["new_browser_sends"]==0
    assert report["student_publication_authorized"] is False
