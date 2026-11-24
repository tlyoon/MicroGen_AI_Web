"""Source-page context continuation is a distinct, fail-closed science task."""
from __future__ import annotations

import copy
import hashlib
import json

import pymupdf
import pytest

from selenium_pipeline import g3_context_followup_task_v1 as nextstep
from selenium_pipeline.g3_source_rejected_offline_repair_v1 import _canon,_sha


@pytest.fixture
def sample(tmp_path,monkeypatch):
    source=tmp_path/"source_section"
    source.mkdir()
    with pymupdf.open() as pdf:
        page=pdf.new_page()
        page.insert_text((40,80),
            "A pendulum may lose some energy to air resistance.",fontsize=10)
        page=pdf.new_page()
        page.insert_text((40,80),
            "Cable tension is related to the force of centripetal motion.",fontsize=10)
        page=pdf.new_page()
        page.insert_text((40,80),
            "The length R of the cable cancels from the final algebraic equation.",fontsize=10)
        pdf.save(source/"source.pdf")
    with pymupdf.open() as pdf:
        page=pdf.new_page()
        page.insert_text((40,80),
            "Why is the final swing angle independent of cable length?")
        pdf.save(source/"slides.pdf")
    (source/"script.txt").write_text(
        "Cable tension and the swing radius determine the angle.")
    hashes={k:_sha(source/k) for k in (
        "source.pdf","slides.pdf","script.txt")}
    old_citation="A pendulum may lose some energy to air resistance."
    fresh=[
        "The length R of the cable cancels from the final algebraic equation.",
        "Cable tension is related to the force of centripetal motion."]
    import selenium_pipeline.pdf_text_source_span_witness as witness
    evidence=[]
    for i,quote in ((3,fresh[0]),(2,fresh[1])):
        proof=witness.prove_source_quote_occurrence(
            source_pdf=source/"source.pdf",expected_sha256=hashes["source.pdf"],
            page_number=i,verbatim_quote=quote)
        evidence.append({
            "source_page":i,
            "verbatim_source_quote":quote,
            "original_source_quote_sha256":hashlib.sha256(
                quote.encode()).hexdigest(),
            "witnessed_quote_sha256":proof["quote_sha256"],
            "source_lexical_score":4,
            "original_spoken_overlap":["cable","tension"],
            "rendered_target_overlap":["cable"],
            "physically_witnessed_original_PDF":True,
            "source_semantic_support_verified":False,
        })
    from selenium_pipeline.g3_semantic_source_repair_v1 import SCHEMA
    original={
        "status":"G3_DISTINCT_SOURCE_SEMANTIC_QA_READY_NO_SEND",
        "scope_sha256":"a"*64,
        "section":"Serway_8_2",
        "original_utterance_id":"s001.utterance.001",
        "source_worklist_sha256":"b"*64,
        "exact_original_source_quote_candidates":[{
            "source_page":1,"verbatim_source_quote":old_citation,
            "publisher_raw_quote_sha256":hashlib.sha256(
                old_citation.encode()).hexdigest()}],
        "science_review_job":{
            "status":"SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED",
            "original_folder":str(source),
            "source_sha256":hashes["source.pdf"],
            "slides_sha256":hashes["slides.pdf"],
            "script_sha256":hashes["script.txt"],
            "selected_original_slides":[1],
            "source_only_pre_tts_review":True,
            "utterance_count":1,
            "academic_approval":False,
            "student_publication_authorized":False,
            "slides":[{
                "slide":1,
                "visual_targets":[{
                    "id":"s001.text.001",
                    "kind":"text_block",
                    "visible_text":"Why is swing angle independent of cable length?",
                    "bbox_pdf_pt":[40,55,410,90]}],
                "utterances":[{
                    "id":"s001.utterance.001",
                    "spoken_sha256":hashlib.sha256(
                        b"Cable tension and the swing radius determine the angle.").hexdigest(),
                    "spoken_text":"Cable tension and the swing radius determine the angle.",
                    "ranked_candidates":["s001.text.001"]}],
            }],
            "verified_source_quote_candidates_v1":{
                "status":"PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1",
                "source_sha256":hashes["source.pdf"],
                "slides_sha256":hashes["slides.pdf"],
                "script_sha256":hashes["script.txt"],
                "utterances":[{
                    "utterance_id":"s001.utterance.001",
                    "spoken_sha256":hashlib.sha256(
                        b"Cable tension and the swing radius determine the angle.").hexdigest(),
                    "allowed_citations":[{
                        "source_page":1,
                        "verbatim_source_quote":old_citation,
                        "quote_sha256":"c"*64}],
                }],
            },
        },
    }
    receipt={
        "status":"G3_BOTH_INDEPENDENT_SCIENCE_REVIEWERS_UNRESOLVED_SOURCE_REPAIR_V3",
        "original_two_model_verdicts":["UNRESOLVED","UNRESOLVED"],
        "new_distinct_recovery_action":"NEW_DISTINCT_EXAMPLE_CONTEXT_REVIEW_TASK_REQUIRED",
        "original_source_task_scope_sha256":original["scope_sha256"],
        "original_two_pass_receipt_sha256":"d"*64,
        "new_gemini_browser_sends":0,
        "student_publication_authorized":False,
        "source_context_alternative_candidates":evidence,
    }
    monkeypatch.setattr(nextstep,"_source_context_for_original",
        lambda **kw:(copy.deepcopy(original),copy.deepcopy(receipt)))
    spec={"section":"Serway_8_2","source_folder":source}
    root=tmp_path/"state";root.mkdir()
    return spec,root,source,original,receipt


def test_new_context_review_binds_original_unresolved_and_source_sha(sample):
    spec,root,source,old,context=sample
    result=nextstep.build(
        spec=spec,state_root=root,original_task=root/"old.json")
    assert result["status"]==nextstep.READY
    assert result["new_provider_requests"]==0
    assert result["student_publication_authorized"] is False
    assert result["parent_original_task_scope_sha256"]==old["scope_sha256"]
    assert result["review_job"]["slides"]==old["science_review_job"]["slides"]
    assert result["review_job"]["verified_source_quote_candidates_v1"][
        "utterances"][0]["allowed_citations"][0]["source_page"]==3
    assert result["new_context_scientific_support_approved"] is False
    assert result["original_G3_semantic_mappings_promoted"]==0


def test_write_once_restart_and_source_tamper(sample):
    spec,root,source,old,context=sample
    path,task=nextstep.stage(
        spec=spec,state_root=root,original_task=root/"old.json")
    assert path.read_bytes()==_canon(task)
    assert nextstep.stage(
        spec=spec,state_root=root,original_task=root/"old.json")==(
            path,task)
    (source/"script.txt").write_text("Scientifically modified narration.")
    with pytest.raises(ValueError):
        nextstep.build(
            spec=spec,state_root=root,original_task=root/"old.json")


def test_corrupt_original_quote_or_model_context_refuses_new_task(sample):
    spec,root,source,old,context=sample
    other=copy.deepcopy(context)
    other["source_context_alternative_candidates"][0][
        "verbatim_source_quote"]="An invented equation is present on this page."
    from selenium_pipeline import g3_context_followup_task_v1 as step
    step._source_context_for_original=lambda **kw:(old,other)
    with pytest.raises(ValueError):
        step.build(
            spec=spec,state_root=root,original_task=root/"old.json")


def test_no_original_context_quote_reused(sample,monkeypatch):
    spec,root,source,old,context=sample
    old["exact_original_source_quote_candidates"].append({
        "source_page":3,
        "verbatim_source_quote":context["source_context_alternative_candidates"][0][
            "verbatim_source_quote"]})
    # Reusing the PRIMARY source quote does not create a genuinely
    # new model task, even when there is an adjacent second page.
    with pytest.raises(ValueError,match="new source-context evidence"):
        nextstep.build(
            spec=spec,state_root=root,original_task=root/"old.json")
