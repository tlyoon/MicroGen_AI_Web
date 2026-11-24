"""Real-PDF mini fixture and zero-Send source recovery fault injections."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pymupdf
import pytest

from selenium_pipeline import g3_untouched_source_witness_v1 as witness
from selenium_pipeline.g3_unreviewed_source_preflight_v1 import ROOT as PRE_ROOT
from selenium_pipeline.g3_semantic_source_repair_v1 import _canon
from selenium_pipeline.recovery_registry import lookup_mechanism


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def original(tmp_path,monkeypatch):
    state=tmp_path/"state"
    folder=tmp_path/"source"
    mapping=tmp_path/"checkpoint"
    review=tmp_path/"review"
    for p in (state,folder,mapping,review):
        p.mkdir()
    src=pymupdf.open()
    page=src.new_page(width=595,height=842)
    page.insert_text((36,90),
        "Maximum tension force acts at the bottom of the swing.")
    page.insert_text((36,115),
        "Energy conservation determines speed at the bottom of the swing.")
    src.save(folder/"source.pdf")
    src.close()
    (folder/"slides.pdf").write_bytes(b"original fake slide fixture")
    (folder/"script.txt").write_bytes(b"synthetic script fixture")
    shas={x:sha(folder/x) for x in ("source.pdf","slides.pdf","script.txt")}
    narration="The maximum tension force acts at the bottom of the swing."
    visible="Maximum tension and speed at the bottom of the swing."
    request={
        "slide":1,"request_sha256":"1"*64,
        "source_inputs_sha256":shas.copy(),
        "original_utterances":[{
            "utterance_id":"s001.utterance.001",
            "verbatim_text":narration}],
        "visible_targets":[{
            "target_id":"s001.text.001","kind":"text_block",
            "visible_text":visible}],
    }
    prepared={
        "schema_version":1,
        "status":"G3_UNTOUCHED_ORIGINAL_SLIDE_SOURCE_PREPARED_NO_SEND",
        "scope_sha256":"2"*64,
        "original_slide":1,
        "original_mapping_request_sha256":request["request_sha256"],
        "original_utterance_count":1,
        "original_visual_target_count":1,
        "original_utterances":[{
            "original_utterance_id":"s001.utterance.001",
            "original_spoken_text_sha256":
                hashlib.sha256(narration.encode()).hexdigest()}],
        "original_visible_targets":[{
            "original_target_id":"s001.text.001",
            "original_target_kind":"text_block",
            "original_visible_text_sha256":
                hashlib.sha256(visible.encode()).hexdigest()}],
        "source_inputs_sha256":shas.copy(),
        "new_browser_sends":0,
        "independent_scientific_QA_complete":False,
    }
    spec=dict(section="Serway_8_2",source_folder=folder,
              checkpoint=mapping,review_root=review)
    saved=state/PRE_ROOT/spec["section"]
    saved.mkdir(parents=True)
    (saved/"original.json").write_bytes(_canon(prepared))
    def pin(**kw):
        assert kw["task_file"].name=="original.json"
        return copy.deepcopy(prepared)
    monkeypatch.setattr(witness,"pinned",pin)
    monkeypatch.setattr(witness,"request_for_slide",
                        lambda **kw:copy.deepcopy(request))
    return spec,state,prepared,request,folder


def test_executable_registry_has_no_send_repair():
    assert lookup_mechanism(witness.KIND,witness.SIGNATURE)==witness.MECHANISM


def test_original_pdf_witness_is_never_academic_approval(original):
    spec,state,prepared,request,folder=original
    result=witness.materialize(specs=[spec],state_root=state)
    assert result["prepared_original_slides"]==1
    assert result["original_narrations"]==1
    assert result["original_rendered_targets"]==1
    assert result["new_browser_sends"]==0
    assert result["paid_gemini_API_calls"]==0
    assert result["independent_scientific_QA_accepted"]==0
    assert result["student_publication_authorized"] is False
    assert result["physically_witnessed_quote_candidates"]>=1
    file=next((state/witness.ROOT/spec["section"]).glob("*.json"))
    from selenium_pipeline.g3_semantic_source_repair_v1 import _read
    item=_read(file)
    assert item["original_preflight_scope_sha256"]==prepared["scope_sha256"]
    assert item["original_narrations"][0]["exact_original_narration"]==(
        request["original_utterances"][0]["verbatim_text"])
    for q in item["original_narrations"][0]["physical_publisher_quote_candidates"]:
        assert q["physically_witnessed_source"] is True
        assert q["scientific_semantic_support_verified"] is False
        assert q["original_publisher_pdf_page"]==1
        from selenium_pipeline.pdf_text_source_span_witness import (
            prove_source_quote_occurrence)
        proof=prove_source_quote_occurrence(
            source_pdf=folder/"source.pdf",
            expected_sha256=sha(folder/"source.pdf"),
            page_number=1,verbatim_quote=q["verbatim_textbook_quote"])
        assert proof["quote_sha256"]==q["physically_verified_quote_sha256"]
    assert item["independent_scientific_QA_complete"] is False
    assert item["independent_visual_QA_complete"] is False
    assert item["student_publication_authorized"] is False
    assert witness.materialize(specs=[spec],state_root=state)==result


def test_pdf_drift_blocks_reuse_even_if_old_source_witness_exists(original):
    spec,state,prepared,request,folder=original
    witness.materialize(specs=[spec],state_root=state)
    with (folder/"source.pdf").open("ab") as stream:
        stream.write(b"tampered content")
    with pytest.raises(ValueError,match="publisher PDF changed"):
        witness.materialize(specs=[spec],state_root=state)


def test_original_visible_target_change_blocks_source_packet(original,monkeypatch):
    spec,state,prepared,request,folder=original
    request["visible_targets"][0]["visible_text"]="Something different"
    monkeypatch.setattr(witness,"request_for_slide",
                        lambda **kw:copy.deepcopy(request))
    with pytest.raises(ValueError,match="rendered text and narration SHA changed"):
        witness.materialize(specs=[spec],state_root=state)


def test_existing_immutable_witness_cannot_be_turned_into_approval(original):
    spec,state,prepared,request,folder=original
    witness.materialize(specs=[spec],state_root=state)
    file=next((state/witness.ROOT/spec["section"]).glob("*.json"))
    from selenium_pipeline.g3_semantic_source_repair_v1 import _read
    item=_read(file)
    item["student_publication_authorized"]=True
    file.write_bytes(_canon(item))
    with pytest.raises(ValueError,match="modified"):
        witness.materialize(specs=[spec],state_root=state)


def test_old_original_send_claim_cannot_enter_new_witnesses(original,monkeypatch):
    spec,state,prepared,request,folder=original
    def forbid(**kw):
        raise ValueError("Original slide has claimed or existing model review; never replay")
    monkeypatch.setattr(witness,"pinned",forbid)
    with pytest.raises(ValueError,match="never replay"):
        witness.materialize(specs=[spec],state_root=state)
    assert not (state/witness.ROOT).exists()


def test_unrelated_source_keeps_science_unapproved_without_quote(original,monkeypatch):
    spec,state,prepared,request,folder=original
    request["original_utterances"][0]["verbatim_text"]="This strange unmatched ziggurat."
    prepared["original_utterances"][0]["original_spoken_text_sha256"]=(
        hashlib.sha256(request["original_utterances"][0]["verbatim_text"].encode()).hexdigest())
    monkeypatch.setattr(witness,"request_for_slide",
                        lambda **kw:copy.deepcopy(request))
    result=witness.materialize(specs=[spec],state_root=state)
    assert result["physically_witnessed_quote_candidates"]==0
    assert result["original_slides_without_any_textbook_quote"]==1
    assert result["independent_scientific_QA_accepted"]==0
