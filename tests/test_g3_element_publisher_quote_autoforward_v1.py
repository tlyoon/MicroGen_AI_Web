"""Grounded original-textbook quote repair: genuine PDF geometry, immutable queue."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pymupdf
import pytest

from selenium_pipeline import g3_element_publisher_quote_autoforward_v1 as stage
from selenium_pipeline import g3_source_element_review_draft_v1 as drafts
from selenium_pipeline import acceptance_completion_scheduler_v1 as controller
from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.pdf_text_source_span_witness import prove_source_quote_occurrence
from selenium_pipeline.recovery_registry import lookup_mechanism
from tests.test_completion_scheduler_historical_static_highlight_autoforward_v1 import install


@pytest.fixture()
def publisher(tmp_path):
    home=tmp_path/"original";home.mkdir()
    state=tmp_path/"state";state.mkdir()
    doc=pymupdf.open()
    page=doc.new_page(width=500,height=500)
    page.insert_text((24,45),
        "An isolated system conserves energy when no energy crosses its boundary.",
        fontsize=10)
    doc.save(home/"source.pdf");doc.close()
    slide=pymupdf.open();slide.new_page().insert_text((20,25),
        "Conservation of mechanical energy",fontsize=10)
    slide.save(home/"slides.pdf");slide.close()
    (home/"script.txt").write_text("Chapter 8.2 original narration content\n",encoding="utf8")
    hashes={name:_sha(home/name) for name in ("source.pdf","slides.pdf","script.txt")}
    root=state/"g3_original_element_review_drafts_v1"/"Serway_8_2"
    root.mkdir(parents=True)
    target={"draft_element_id":"s001.text.001",
            "kind":"text_block",
            "visible_text":"Conservation of mechanical energy",
            "panel_identity_review_required":False}
    slides=[]
    for n in range(1,4):
        slides.append({
            "slide_number":n,
            "auto_candidate_targets":[target],
            "proposed_utterances":[{
                "proposal_id":f"s{n:03d}.utterance.001",
                "verbatim_script_fragment":
                    "An isolated system conserves mechanical energy "
                    "when no energy crosses its boundary.",
                "mapping_ambiguous":True,
                "candidate_target_rankings_unverified":[{
                    "draft_element_id":target["draft_element_id"]}]}]})
    row={"schema_version":1,
         "status":"REVIEW_REQUIRED_NOT_TTS_READY",
         "source_sha256":hashes["source.pdf"],
         "slides_sha256":hashes["slides.pdf"],
         "script_sha256":hashes["script.txt"],
         "can_stage_or_synthesize_audio":False,
         "academic_approval":False,"manual_mapping_reviewed":False,
         "student_publication":False,
         "slide_count":3,"ambiguous_utterance_count":3,"slides":slides}
    binary=stage._canon(row)
    scope=hashlib.sha256(binary).hexdigest()
    packet=root/(scope+".json")
    packet.write_bytes(binary)
    with pymupdf.open(home/"source.pdf") as actual:
        quote=actual[0].get_text(sort=True).splitlines()[0]
    evidence=prove_source_quote_occurrence(
        source_pdf=home/"source.pdf",expected_sha256=hashes["source.pdf"],
        page_number=1,verbatim_quote=quote)
    def fetcher(*,folder,job,previous_quotes):
        assert folder==home
        assert job["source_sha256"]==hashes["source.pdf"]
        assert previous_quotes==set()
        return [{
            "source_page":1,"verbatim_source_quote":quote,
            "physically_witnessed_original_PDF":True,
            "source_semantic_support_verified":False,
            "source_lexical_score":4,
            "original_source_quote_sha256":
                hashlib.sha256(quote.encode("utf8")).hexdigest(),
            "witnessed_quote_sha256":evidence["quote_sha256"],
            "original_spoken_overlap":["system","energy"],
            "rendered_target_overlap":["energy"],
        }]
    return home,state,hashes,packet,fetcher


def invoke(publisher,*,fetcher=None,max_new_tasks=2):
    home,state,hashes,packet,default=publisher
    return stage.advance(
        source_folder=home,state_root=state,section="Serway_8_2",
        draft_receipt=packet,source_hashes=hashes,
        max_new_tasks=max_new_tasks,
        context_fetcher=default if fetcher is None else fetcher)


def test_existing_executable_history_repair_registered():
    assert lookup_mechanism(stage.KIND,stage.SIGNATURE)==stage.MECHANISM


def test_actual_spatially_verified_pdf_quote_is_not_scientific_approval(publisher):
    home,state,hashes,packet,fetcher=publisher
    before={x.name:_sha(x) for x in home.iterdir()}
    result=invoke(publisher,max_new_tasks=1)
    assert result["new_source_quote_tasks_staged"]==1
    assert result["new_physically_witnessed_publisher_quotes"]==1
    assert result["remaining_unprocessed_ambiguous_tasks"]==2
    assert result["source_scientific_QA_complete"] is False
    assert result["student_publication_authorized"] is False
    assert result["new_browser_sends"]==result["new_paid_gemini_API_calls"]==0
    saved=json.loads(Path(result["new_task_receipts"][0]).read_text("utf8"))
    assert saved["status"]=="G3_PHYSICAL_PUBLISHER_CONTEXT_STAGED_NO_SEMANTIC_APPROVAL"
    assert saved["physically_witnessed_source_context"][0][
        "physical_original_publisher_source_verified"] is True
    assert saved["physically_witnessed_source_context"][0][
        "source_semantics_verified"] is False
    assert {x.name:_sha(x) for x in home.iterdir()}==before


def test_finite_incremental_runs_reuse_prior_original_claim_without_fetch(publisher):
    first=invoke(publisher)
    assert first["new_source_quote_tasks_staged"]==2
    assert first["remaining_unprocessed_ambiguous_tasks"]==1
    second=invoke(publisher)
    assert second["new_source_quote_tasks_staged"]==1
    assert second["reused_source_quote_tasks"]==2
    assert second["remaining_unprocessed_ambiguous_tasks"]==0
    third=invoke(publisher,fetcher=lambda **kw:
        pytest.fail("No new possible source review or model Send on restart"))
    assert third["new_source_quote_tasks_staged"]==0
    assert third["reused_source_quote_tasks"]==3
    assert third["remaining_unprocessed_ambiguous_tasks"]==0


def test_missing_or_drifted_publisher_source_never_claims_quote(publisher):
    home,state,hashes,packet,fetcher=publisher
    (home/"source.pdf").write_bytes(b"untrusted modified PDF")
    with pytest.raises(Exception,match="original|Original"):
        invoke(publisher,fetcher=lambda **kw:
            pytest.fail("Source context should not be called"))


def test_fake_source_quote_rejected_by_real_geometric_proof(publisher):
    home,state,hashes,packet,fetcher=publisher
    def forged(**kwargs):
        r=fetcher(**kwargs)
        r[0]["verbatim_source_quote"]="This fake physics equation is unsupported by the PDF and cannot appear."
        r[0]["original_source_quote_sha256"]=hashlib.sha256(
            r[0]["verbatim_source_quote"].encode()).hexdigest()
        return r
    with pytest.raises(Exception):
        invoke(publisher,fetcher=forged,max_new_tasks=1)
    assert not list((state/stage.ROOT/"Serway_8_2").glob("*.json"))


def test_poisoned_old_quote_evidence_cannot_be_autopromoted(publisher):
    initial=invoke(publisher,max_new_tasks=1)
    path=Path(initial["new_task_receipts"][0])
    record=json.loads(path.read_text("utf8"))
    record["student_publication_authorized"]=True
    path.write_text(json.dumps(record),encoding="utf8")
    with pytest.raises(Exception,match="Prior|source"):
        invoke(publisher,max_new_tasks=1)
    assert json.loads(path.read_text("utf8"))["student_publication_authorized"] is True


def test_no_source_quote_candidate_still_durable_hold(publisher):
    no_match=invoke(publisher,fetcher=lambda **kw:[],
                    max_new_tasks=1)
    assert no_match["new_source_quote_tasks_staged"]==1
    assert no_match["new_physically_witnessed_publisher_quotes"]==0
    again=invoke(publisher,fetcher=lambda **kw:[],
                 max_new_tasks=1)
    assert again["reused_source_quote_tasks"]==1
    assert again["new_source_quote_tasks_staged"]==1
    assert again["remaining_unprocessed_ambiguous_tasks"]==1


def test_zero_new_task_budget_never_calls_provider_or_quote_search(publisher):
    x=invoke(publisher,max_new_tasks=0,
        fetcher=lambda **kw:pytest.fail("No source quote request permitted"))
    assert x["new_source_quote_tasks_staged"]==0
    assert x["remaining_unprocessed_ambiguous_tasks"]==3


def test_controller_chains_existing_source_worklist_to_quote_retrieval(
        tmp_path,monkeypatch):
    state,media,manifest,calls=install(tmp_path,monkeypatch)
    observed=[]
    def draft_stage(**kw):
        return {"status":drafts.ROOT.replace("g3_original_element_review_drafts_v1",
            "G3_ORIGINAL_SOURCE_ELEMENT_MAPPING_REVIEW_STAGED_NO_TTS"),
            "draft_receipt":str(state/"mock.json")}
    def quote_stage(**kw):
        observed.append(kw["section"])
        assert kw["max_new_tasks"]==2 if "max_new_tasks" in kw else True
        return {
            "status":"G3_SOURCE_PHYSICAL_CONTEXT_INCREMENTALLY_STAGED_NO_APPROVAL",
            "new_source_quote_tasks_staged":2,
            "new_physically_witnessed_publisher_quotes":3,
            "source_scientific_QA_complete":False,
            "new_browser_sends":0,"new_paid_gemini_API_calls":0}
    monkeypatch.setattr(drafts,"materialize",draft_stage)
    monkeypatch.setattr(stage,"advance",quote_stage)
    got=controller._g3_media_zero_send(
        manifest=manifest,state=state,media=media)
    assert observed==["Serway_8_2","Serway_8_3"]
    assert got["source_only_element_mapping_drafts_staged"]==2
    assert got["new_physically_source_witnessed_mapping_tasks_staged"]==4
    assert got["source_only_physical_quote_candidates_staged"]==6
    assert got["student_publication_authorized"] is False
    gate=next(x for x in controller._gate_matrix({"G3_MEDIA":got})
              if x["gate_id"]=="G3_WITHIN_SLIDE_VISUAL_HIGHLIGHT_QA")
    assert gate["new_publisher_quote_mapping_tasks"]==4
    assert gate["accepted"] is False


def test_one_quote_context_provider_failure_does_not_strand_other_subsection(
        tmp_path,monkeypatch):
    state,media,manifest,calls=install(tmp_path,monkeypatch)
    observed=[]
    monkeypatch.setattr(drafts,"materialize",lambda **kw:{
        "status":"G3_ORIGINAL_SOURCE_ELEMENT_MAPPING_REVIEW_STAGED_NO_TTS",
        "draft_receipt":str(state/"original_mock.json")})
    def partial(**kw):
        observed.append(kw["section"])
        if kw["section"]=="Serway_8_2":
            raise ValueError("Unresolved original publisher PDF source quote")
        return {
            "status":"G3_SOURCE_PHYSICAL_CONTEXT_INCREMENTALLY_STAGED_NO_APPROVAL",
            "new_source_quote_tasks_staged":1,
            "new_physically_witnessed_publisher_quotes":1}
    monkeypatch.setattr(stage,"advance",partial)
    got=controller._g3_media_zero_send(
        manifest=manifest,state=state,media=media)
    assert observed==["Serway_8_2","Serway_8_3"]
    a,b=got["source_bound_actual_highlight_recovery"]
    assert a["publisher_quote_mapping_recovery"]["status"]==(
        "G3_PUBLISHER_QUOTE_SOURCE_REVIEW_HELD")
    assert b["publisher_quote_mapping_recovery"]["status"]==(
        "G3_SOURCE_PHYSICAL_CONTEXT_INCREMENTALLY_STAGED_NO_APPROVAL")
    assert got["new_physically_source_witnessed_mapping_tasks_staged"]==1
    assert got["student_publication_authorized"] is False


def test_scheduler_auto_advances_multiple_bounded_source_quote_batches(tmp_path,monkeypatch):
    from selenium_pipeline import g3_source_quote_bounded_continuation_v1 as bulk
    state,media,manifest,calls=install(tmp_path,monkeypatch)
    observed=[]
    monkeypatch.setattr(drafts,"materialize",lambda **kw:{
        "status":"G3_ORIGINAL_SOURCE_ELEMENT_MAPPING_REVIEW_STAGED_NO_TTS",
        "draft_receipt":str(state/"original_mock.json")})
    def first(**kw):
        observed.append(("initial",kw["section"]))
        return {
            "status":"G3_SOURCE_PHYSICAL_CONTEXT_INCREMENTALLY_STAGED_NO_APPROVAL",
            "new_source_quote_tasks_staged":2,
            "new_physically_witnessed_publisher_quotes":3,
            "remaining_unprocessed_ambiguous_tasks":6,
            "source_scientific_QA_complete":False,
            "new_browser_sends":0,"new_paid_gemini_API_calls":0,
            "student_publication_authorized":False}
    def continued(**kw):
        observed.append(("batch",kw["section"]))
        assert kw["expected_remaining"]==6
        return {
            "status":"G3_BOUNDED_SOURCE_PHYSICAL_QUOTE_CONTINUATION_NO_APPROVAL",
            "new_source_quote_tasks_staged":4,
            "new_physically_witnessed_publisher_quotes":6,
            "remaining_unprocessed_ambiguous_tasks":2,
            "new_browser_sends":0,"new_paid_gemini_API_calls":0,
            "source_scientific_QA_complete":False,
            "student_publication_authorized":False}
    monkeypatch.setattr(stage,"advance",first)
    monkeypatch.setattr(bulk,"continue_quotes",continued)
    result=controller._g3_media_zero_send(manifest=manifest,state=state,media=media)
    assert result["new_physically_source_witnessed_mapping_tasks_staged"]==12
    assert result["source_only_physical_quote_candidates_staged"]==18
    assert observed==[
        ("initial","Serway_8_2"),("batch","Serway_8_2"),
        ("initial","Serway_8_3"),("batch","Serway_8_3")]
    assert result["student_publication_authorized"] is False

