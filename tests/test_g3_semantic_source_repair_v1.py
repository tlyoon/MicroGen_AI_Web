"""Physical G3 narration-to-PDF task construction and no-promotion bounds."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pymupdf
import pytest

from selenium_pipeline import g3_semantic_source_repair_v1 as semantic
from selenium_pipeline import g3_source_rejected_offline_repair_v1 as prior
from selenium_pipeline.ai_academic_web_review import run_web_review
from selenium_pipeline.series_gemini import OwnedGeminiResponse
from selenium_pipeline.recovery_registry import lookup_mechanism


@pytest.fixture
def sample(tmp_path,monkeypatch):
    source=tmp_path/"original_8_3"
    checkpoint=tmp_path/"author_checkpoint"
    review=tmp_path/"historic_g3_claims"
    for p in (source,checkpoint,review):
        p.mkdir()
    (review/"audited").mkdir()
    (review/"original_model_responses").mkdir()
    (checkpoint/"mapping_checkpoint.json").write_text('{"original":true}')
    quote="The displacement divided by elapsed time determines average velocity."
    with pymupdf.open() as pdf:
        page=pdf.new_page()
        page.insert_text((40,85),quote,fontsize=10)
        pdf.save(source/"source.pdf")
    with pymupdf.open() as pdf:
        page=pdf.new_page()
        page.insert_text((40,85),"Displacement divided by time",fontsize=10)
        pdf.save(source/"slides.pdf")
    (source/"script.txt").write_text(
        "Velocity equals displacement divided by elapsed time.\nSecond statement.")
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    hashes={name:digest(source/name) for name in (
        "source.pdf","slides.pdf","script.txt")}
    request={
        "status":"SOURCEBOUND_RICH_ELEMENT_AI_PROPOSAL_INPUT_REVIEW_ONLY",
        "slide":3,"request_sha256":"a"*64,
        "source_inputs_sha256":hashes,
        "original_utterances":[
            {"utterance_id":"s003.utterance.001",
             "verbatim_text":"Velocity equals displacement divided by elapsed time."},
            {"utterance_id":"s003.utterance.002",
             "verbatim_text":"Second statement."}],
        "visible_targets":[{
            "target_id":"s003.text.001",
            "kind":"text_block",
            "visible_text":"Displacement divided by time",
            "author_rect_pdf_pt":[40,70,240,95]}],
        "source_page_excerpts":[{"source_page":1,"original_page_text":quote}],
    }
    spec={"section":"Serway_8_3","source_folder":source,
          "checkpoint":checkpoint,"review_root":review}
    files=prior.reviewer._files(review,3)
    files["claim"].write_text('{"status":"CAPTURED_SOURCE_REJECTED_NO_REPLAY"}')
    files["capture"].write_text('{"original_gemini_response":true}')
    files["response"].write_text('{"original_gemini_response":true}')
    claim_sha=digest(files["claim"])
    cap_sha=digest(files["capture"])
    response_sha=digest(files["response"])
    packet={
        "schema_version":2,
        "status":"G3_REJECTED_CAPTURE_SOURCE_QUOTE_WORKLIST_NO_SEND_V2",
        "source_folder":str(source),
        "source_inputs_sha256":hashes,
        "original_mapping_checkpoint_sha256":digest(
            checkpoint/"mapping_checkpoint.json"),
        "original_slide_number":3,
        "original_request_sha256":request["request_sha256"],
        "original_rejected_claim_sha256":claim_sha,
        "original_rejected_raw_model_capture_sha256":cap_sha,
        "original_rejected_parsed_response_sha256":response_sha,
        "source_rejection_reason":"Missing exact source quote",
        "original_rejected_utterances_missing_source_quote":[
            "s003.utterance.001"],
        "publisher_quote_worklist":[{
            "utterance_id":"s003.utterance.001",
            "verbatim_utterance_sha256":hashlib.sha256(
                request["original_utterances"][0]["verbatim_text"].encode()).hexdigest(),
            "original_selected_target_id":"s003.text.001",
            "original_selected_target_kind":"text_block",
            "original_visible_text_sha256":hashlib.sha256(
                request["visible_targets"][0]["visible_text"].encode()).hexdigest(),
            "original_model_source_quote_was_missing":True,
            "original_model_source_selection_rejected":True,
            "source_excerpt_candidates":[{
                "source_page":1,
                "publisher_quote_verbatim":quote,
                "publisher_quote_sha256":hashlib.sha256(quote.encode()).hexdigest(),
                "publisher_page_text_sha256":hashlib.sha256(quote.encode()).hexdigest(),
                "source_offset_start":0,"source_offset_end":len(quote),
                "overlapping_terms":["displacement","divided","time","velocity"],
                "lexical_overlap_count":4,
                "quote_physically_present":True,
                "meaning_or_target_mapping_verified":False,
                "independent_scientific_QA_approved":False,
            }],
            "status":"PHYSICALLY_WITNESSED_LEXICAL_CANDIDATES_NOT_SEMANTIC_REPAIR",
            "human_or_independent_semantic_review_required":True,
        }],
        "quote_candidates_are_scientific_proof":False,
        "original_rejected_source_review_accepted":False,
        "repaired_source_to_target_mapping_accepted":False,
        "author_source_PDF_modified":False,
        "original_historical_model_request_replayed":False,
        "new_browser_sends":0,
        "new_paid_gemini_API_requests":0,
        "independent_acoustic_review_complete":False,
        "highlighted_video_accepted":False,
        "student_publication_authorized":False,
    }
    root=tmp_path/"existing_publisher_worklists"
    (root/"Serway_8_3").mkdir(parents=True)
    file=root/"Serway_8_3"/"slide_003_fixture.json"
    file.write_bytes(prior._canon(packet))
    monkeypatch.setattr(semantic,"rejected_packet",
        lambda **kw:copy.deepcopy(packet))
    monkeypatch.setattr(semantic,"request_for_slide",
        lambda **kw:copy.deepcopy(request))
    monkeypatch.setattr(semantic,"prompt_for_request",
        lambda req:"LEGACY WHOLE-SLIDE SCIENCE MAPPING REQUEST")
    return spec,root,file,request,packet,quote


def test_semantic_mechanism_is_in_executable_registry():
    assert lookup_mechanism(semantic.KIND,semantic.SIGNATURE)==semantic.MECHANISM


def test_immutable_new_one_unit_task_with_real_pdf_quote(sample,tmp_path):
    spec,root,file,request,packet,quote=sample
    out=semantic.materialize(specs=[spec],worklist_root=root,
                             output_root=tmp_path/"semantic_tasks")
    assert out["status"]=="G3_SOURCE_SEMANTIC_REVIEW_TASKS_STAGED_NO_MODEL_SEND"
    assert out["original_missing_source_quote_units"]==1
    assert out["new_distinct_science_review_tasks_ready"]==1
    assert out["unresolved_source_quote_units"]==0
    assert out["new_browser_sends"]==0
    assert out["independent_scientific_QA_accepted"]==0
    task=next((tmp_path/"semantic_tasks").rglob("*.json"))
    data=json.loads(task.read_text("utf8"))
    job=data["science_review_job"]
    assert job["utterance_count"]==1
    assert job["selected_original_slides"]==[3]
    assert job["verified_source_quote_candidates_v1"][
        "utterances"][0]["allowed_citations"][0][
            "verbatim_source_quote"]==quote
    assert job["g3_distinct_source_science_v1"][
        "original_total_slide_utterances"]==2
    assert data["old_whole_slide_request_replayed"] is False
    assert data["new_source_review_send_allowed_without_fresh_neon_health"] is False
    assert data["student_publication_authorized"] is False
    assert semantic.materialize(specs=[spec],worklist_root=root,
                               output_root=tmp_path/"semantic_tasks")==out


def test_source_grounded_single_pass_still_refuses_scientific_acceptance(
        sample,tmp_path):
    spec,root,file,request,packet,quote=sample
    semantic.materialize(specs=[spec],worklist_root=root,
                        output_root=tmp_path/"tasks")
    job=json.loads(next((tmp_path/"tasks").rglob("*.json")).read_text())[
        "science_review_job"]
    unit=job["slides"][0]["utterances"][0]
    counter=[]
    def transport(prompt,files):
        counter.append(1)
        assert "source.pdf"==files[0].name
        assert "slides.pdf"==files[1].name
        return OwnedGeminiResponse(
            json.dumps({
                "status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
                "rows":[{
                    "utterance_id":unit["id"],
                    "spoken_sha256":unit["spoken_sha256"],
                    "target_id":"s003.text.001",
                    "source_page":1,"verbatim_source_quote":quote,
                    "verdict":"UNRESOLVED",
                    "math_explanation":(
                        "The quotation contains the claim's core terms, "
                        "but physical presence alone does not prove "
                        "the meaning of the authored narration."),
                }],
            }),
            registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
            new_turn_verified=True,verified_model_family="neon",
            verified_thinking_level="high")
    result=run_web_review(
        folder=spec["source_folder"],job=job,mode="INITIAL_REVIEW",
        checkpoint_dir=tmp_path/"synthetic_one_send",
        required_model_family="neon",transport=transport)
    assert result["status"]=="SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS"
    assert result["review_count"]==1
    assert result["rows"][0]["verdict"]=="UNRESOLVED"
    assert result["rows"][0]["exact_textbook_quote_verified"] is True
    assert result["academic_mathematics_independently_verified"] is False
    assert result["student_publication_authorized"] is False
    assert len(counter)==1
    # A second Send cannot be made under the original one-Send claim.
    with pytest.raises(Exception):
        run_web_review(
            folder=spec["source_folder"],job=job,mode="INITIAL_REVIEW",
            checkpoint_dir=tmp_path/"synthetic_one_send",
            required_model_family="neon",transport=transport)
    assert len(counter)==1


def test_weak_slide_only_lexical_overlap_must_not_launch_review(sample,tmp_path,monkeypatch):
    spec,root,file,request,packet,quote=sample
    req=copy.deepcopy(request)
    req["original_utterances"][0]["verbatim_text"]=(
        "Welcome to the conceptual review questions.")
    row=packet["publisher_quote_worklist"][0]
    row["verbatim_utterance_sha256"]=hashlib.sha256(
        req["original_utterances"][0]["verbatim_text"].encode()).hexdigest()
    file.write_bytes(prior._canon(packet))
    from selenium_pipeline import g3_semantic_source_repair_v1 as local
    monkeypatch.setattr(local,"request_for_slide",lambda **kw:copy.deepcopy(req))
    result=semantic.materialize(
        specs=[spec],worklist_root=root,output_root=tmp_path/"weak_tasks")
    assert result["new_distinct_science_review_tasks_ready"]==0
    assert result["unresolved_source_quote_units"]==1
    assert result["student_publication_authorized"] is False


def test_tampered_original_source_or_rejection_does_not_advance(sample,tmp_path):
    spec,root,file,req,packet,quote=sample
    (spec["source_folder"]/"source.pdf").write_bytes(b"%PDF tampered")
    with pytest.raises(Exception):
        semantic.materialize(specs=[spec],worklist_root=root,
                             output_root=tmp_path/"bad_tasks")


def test_tampered_existing_worklist_detected(sample,tmp_path):
    spec,root,file,req,packet,quote=sample
    file.write_text('{"forged":"source support"}')
    with pytest.raises(Exception):
        semantic.materialize(specs=[spec],worklist_root=root,
                             output_root=tmp_path/"forged_tasks")


def test_mutated_immutable_semantic_task_never_overwritten(sample,tmp_path):
    spec,root,file,req,packet,quote=sample
    semantic.materialize(specs=[spec],worklist_root=root,
                        output_root=tmp_path/"persist")
    output=next((tmp_path/"persist").rglob("*.json"))
    output.write_text('{"scientific_approval":true}')
    with pytest.raises(ValueError,match="modified"):
        semantic.materialize(specs=[spec],worklist_root=root,
                            output_root=tmp_path/"persist")


def test_semantic_worklist_stage_crash_recovery(tmp_path):
    root=tmp_path/"repo"
    root.mkdir()
    target=root/"semantic.json"
    staged=target.with_suffix(".stage")
    row={"status":"REVIEW_ONLY","approved":False}
    staged.write_bytes(prior._canon(row))
    semantic._write_once(target,row)
    assert target.read_bytes()==prior._canon(row)
    staged.write_bytes(target.read_bytes())
    semantic._write_once(target,row)
    assert not staged.exists()


def test_oversized_or_redirected_task_root_refused(sample,tmp_path):
    spec,root,file,req,packet,quote=sample
    with pytest.raises(ValueError):
        semantic.materialize(specs=[spec],worklist_root=root,
                             output_root=spec["source_folder"]/"tasks")
