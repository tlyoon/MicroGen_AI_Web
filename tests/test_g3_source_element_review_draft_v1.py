"""Safe original publisher source-element drafting without TTS or approval."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from selenium_pipeline import g3_source_element_review_draft_v1 as stage
from selenium_pipeline import g3_original_video_page_parity_v1 as parity
from selenium_pipeline import acceptance_completion_scheduler_v1 as controller
from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.recovery_registry import lookup_mechanism
from tests.test_completion_scheduler_historical_static_highlight_autoforward_v1 import install


@pytest.fixture()
def original(tmp_path):
    source=tmp_path/"publisher";source.mkdir()
    state=tmp_path/"state";state.mkdir()
    for file in ("source.pdf","slides.pdf","script.txt"):
        (source/file).write_text("original "+file)
    sha={f:_sha(source/f) for f in ("source.pdf","slides.pdf","script.txt")}
    return source,state,sha


def fake_draft(source_pdf,slides_pdf,script_txt):
    d={
        "schema_version":1,"status":"REVIEW_REQUIRED_NOT_TTS_READY",
        "source_sha256":_sha(source_pdf),
        "slides_sha256":_sha(slides_pdf),
        "script_sha256":_sha(script_txt),
        "can_stage_or_synthesize_audio":False,
        "cannot_be_used_as_authored_element_plan":True,
        "source_meaning_reviewed":False,
        "manual_mapping_reviewed":False,
        "academic_approval":False,
        "automatic_author_approval":False,
        "student_publication":False,
        "all_audio_generated":False,
        "slide_count":2,"utterance_count":3,
        "candidate_target_count":3,"ambiguous_utterance_count":1,
        "slides":[]
    }
    for n,ids in ((1,("s001.text.001",)),(2,("s002.text.001","s002.text.002"))):
        d["slides"].append({
            "slide_number":n,"source_page_approved":False,
            "source_quote_approved":False,"approved_for_stage":False,
            "auto_candidate_targets":[{"draft_element_id":v} for v in ids],
            "proposed_utterances":[{
                "proposal_id":f"s{n:03d}.utterance.{i:03d}",
                "mapping_ambiguous":(n==2 and i==1),
                "approved_for_tts":False,
                "spoken_word_fidelity_verified":False,
                "verbatim_script_fragment":v
            } for i,v in enumerate(ids,1)]
        })
    return d


def fake_worklist(row):
    return "# Original publisher element mapping REVIEW-ONLY; not authorized for TTS"


def invoke(original,**kw):
    source,state,sha=original
    return stage.materialize(
        source_folder=source,state_root=state,section="Serway_8_2",
        original_source_hashes=sha,
        draft_producer=kw.pop("draft_producer",fake_draft),
        worklist_producer=kw.pop("worklist_producer",fake_worklist),**kw)


def test_new_executable_registry_handler():
    assert lookup_mechanism(stage.KIND,stage.SIGNATURE)==stage.MECHANISM


def test_source_input_pinning_immutable_review_worklist_and_zero_model_tts(original):
    record=invoke(original)
    assert record["status"]=="G3_ORIGINAL_SOURCE_ELEMENT_MAPPING_REVIEW_STAGED_NO_TTS"
    assert record["original_slides"]==2
    assert record["verbatim_narration_units"]==3
    assert record["unapproved_visual_candidates"]==3
    assert record["ambiguous_narration_to_visual_targets"]==1
    assert record["per_element_TTS_ready"] is False
    assert record["independent_scientific_source_review_complete"] is False
    assert record["student_publication_authorized"] is False
    assert record["new_browser_sends"]==0
    assert record["new_paid_gemini_API_calls"]==0
    packet=Path(record["draft_receipt"])
    md=Path(record["mandatory_review_worklist"])
    before=[packet.read_bytes(),md.read_bytes()]
    assert json.loads(packet.read_text("utf8"))["academic_approval"] is False
    assert invoke(original)==record
    assert [packet.read_bytes(),md.read_bytes()]==before


def test_original_source_drift_rejected_before_draft_or_tts(original):
    source,state,sha=original
    (source/"source.pdf").write_text("changed publisher")
    with pytest.raises(ValueError,match="exact original G3"):
        invoke(original,draft_producer=lambda **kw:
            pytest.fail("No original source map may be drafted"))


def test_fake_academic_or_tts_claim_fails_closed(original):
    def forged(**kw):
        draft=fake_draft(**kw)
        draft["can_stage_or_synthesize_audio"]=True
        return draft
    with pytest.raises(ValueError,match="must never act as accepted"):
        invoke(original,draft_producer=forged)
    source,state,sha=original
    assert not (state/stage.ROOT).exists()


def test_unsafe_publisher_page_association_cannot_claim_approval(original):
    def forged(**kw):
        draft=fake_draft(**kw)
        draft["slides"][0]["source_quote_approved"]=True
        return draft
    with pytest.raises(ValueError,match="coverage is misleading"):
        invoke(original,draft_producer=forged)


def test_corrupt_saved_review_packet_fails_without_overwriting(original):
    first=invoke(original)
    path=Path(first["draft_receipt"])
    path.write_bytes(b'{"student_publication":true}')
    with pytest.raises(ValueError,match="Previously saved original"):
        invoke(original)
    assert path.read_bytes()==b'{"student_publication":true}'


def test_missing_mandatory_mapping_review_worklist_fails_closed(original):
    with pytest.raises(ValueError,match="Mandatory human"):
        invoke(original,worklist_producer=lambda d:"APPROVED_FOR_TTS")
    source,state,sha=original
    assert not (state/stage.ROOT).exists()


def test_completion_controller_auto_advances_to_original_source_element_review(
        tmp_path,monkeypatch):
    state,media,manifest,calls=install(tmp_path,monkeypatch)
    observed=[]
    def stage_source(**kwargs):
        observed.append(kwargs["section"])
        return {
            "status":"G3_ORIGINAL_SOURCE_ELEMENT_MAPPING_REVIEW_STAGED_NO_TTS",
            "verbatim_narration_units":77,
            "ambiguous_narration_to_visual_targets":47,
            "new_browser_sends":0,
            "new_paid_gemini_API_calls":0,
            "per_element_TTS_ready":False,
            "student_publication_authorized":False}
    monkeypatch.setattr(stage,"materialize",stage_source)
    value=controller._g3_media_zero_send(
        manifest=manifest,state=state,media=media)
    assert observed==["Serway_8_2","Serway_8_3"]
    assert value["original_static_video_rebuilds_staged"]==2
    assert value["source_only_element_mapping_drafts_staged"]==2
    gate=next(x for x in controller._gate_matrix({"G3_MEDIA":value})
              if x["gate_id"]=="G3_WITHIN_SLIDE_VISUAL_HIGHLIGHT_QA")
    assert gate["source_pinned_rebuild_worklists"]==2
    assert gate["source_only_element_review_worklists"]==2
    assert gate["accepted"] is False
    assert value["new_browser_sends"]==value["new_paid_gemini_API_calls"]==0
    assert value["independent_video_highlight_QA_complete"] is False


def test_one_element_draft_blocker_still_advances_other_section(
        tmp_path,monkeypatch):
    state,media,manifest,calls=install(tmp_path,monkeypatch)
    encountered=[]
    def stage_source(**kwargs):
        encountered.append(kwargs["section"])
        if kwargs["section"]=="Serway_8_2":
            raise ValueError("Figure panel independently unresolved")
        return {
            "status":"G3_ORIGINAL_SOURCE_ELEMENT_MAPPING_REVIEW_STAGED_NO_TTS",
            "per_element_TTS_ready":False,
            "student_publication_authorized":False}
    monkeypatch.setattr(stage,"materialize",stage_source)
    value=controller._g3_media_zero_send(
        manifest=manifest,state=state,media=media)
    assert encountered==["Serway_8_2","Serway_8_3"]
    assert value["original_static_video_rebuilds_staged"]==2
    assert value["source_only_element_mapping_drafts_staged"]==1
    first,second=value["source_bound_actual_highlight_recovery"]
    assert first["element_mapping_source_review"]["status"]==(
        "G3_SOURCE_ELEMENT_MAPPING_DRAFT_HELD")
    assert second["element_mapping_source_review"]["status"]==(
        "G3_ORIGINAL_SOURCE_ELEMENT_MAPPING_REVIEW_STAGED_NO_TTS")
    assert value["student_publication_authorized"] is False
