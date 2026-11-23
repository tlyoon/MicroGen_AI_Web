"""Genuinely single-claim G2 source QA; no old Send replay or promotion."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path

import pymupdf
import pytest

from selenium_pipeline import g2_distinct_focused_source_review_v1 as focused
from selenium_pipeline.ai_academic_web_review import run_web_review


@pytest.fixture
def real_source_fixture(tmp_path, monkeypatch):
    root=tmp_path
    original=root/"original"/"1"/"1.3"
    original.mkdir(parents=True)
    quote="The physical dimension of velocity is length divided by time."
    with pymupdf.open() as pdf:
        page=pdf.new_page()
        page.insert_text((43, 70),quote,fontsize=10)
        pdf.save(original/"source.pdf")
    with pymupdf.open() as pdf:
        page=pdf.new_page()
        page.insert_text((43, 70),quote,fontsize=10)
        pdf.save(original/"slides.pdf")
    (original/"script.txt").write_text(
        "The velocity dimension is length divided by time.",
        encoding="utf8")
    hash_file=lambda name:hashlib.sha256((original/name).read_bytes()).hexdigest()
    hashes={n:hash_file(n) for n in ("source.pdf","slides.pdf","script.txt")}
    units=[]
    packet_units=[]
    for idx,text in enumerate((
        "The velocity dimension is length divided by time.",
        "The dimension of mass is represented by M.",
        "The dimension of time is represented by T.",
    ),1):
        ident=f"s003.utterance.{idx:03d}"
        spoken=hashlib.sha256(text.encode("utf8")).hexdigest()
        units.append({"id":ident,"spoken_text":text,
                      "spoken_sha256":spoken,
                      "ranked_candidates":["s003.text.001"]})
        packet_units.append({
            "utterance_id":ident,"spoken_sha256":spoken,
            "allowed_citations":[{
                "source_page":1,
                "verbatim_source_quote":quote,
                "quote_sha256":hashlib.sha256(quote.encode()).hexdigest(),
                "source_text_bbox_pdf_pt":[43,59,315,77],
            }],
        })
    job={
        "status":"SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED",
        "original_folder":str(original),
        "source_sha256":hashes["source.pdf"],
        "slides_sha256":hashes["slides.pdf"],
        "script_sha256":hashes["script.txt"],
        "selected_original_slides":[3],
        "utterance_count":len(units),
        "source_only_pre_tts_review":True,
        "slides":[{
            "slide":3,
            "visual_targets":[{
                "id":"s003.text.001","bbox_pdf_pt":[43,59,315,77],
                "visible_text":quote,"kind":"text",
            }],
            "utterances":units}],
        "academic_approval":False,
        "student_publication_authorized":False,
        "verified_source_quote_candidates_v1":{
            "status":"PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1",
            "source_sha256":hashes["source.pdf"],
            "slides_sha256":hashes["slides.pdf"],
            "script_sha256":hashes["script.txt"],
            "citations_are_scientific_proof":False,
            "all_mathematics_verified":False,
            "student_publication_authorized":False,
            "utterances":packet_units,
        },
    }
    queue=root/"queue"
    queue.mkdir()
    (queue/"queue.json").write_text(json.dumps({
        "status":"IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
        "original_source_folder":str(original),
        "slide_jobs":[{
            "slide":3,"utterance_count":3,
            "original_source_sha256":hashes["source.pdf"],
            "original_slides_sha256":hashes["slides.pdf"],
            "original_script_sha256":hashes["script.txt"],
        }],
        "expected_utterances":3,
        "student_publication_authorized":False,
    }))
    claim=queue/"slide_003_initial_review_attempt_01_request"
    claim.mkdir()
    fingerprint="a"*64
    (claim/"request_state.json").write_text(json.dumps({
        "schema_version":1,"status":"SUBMITTED_OR_UNCERTAIN",
        "request_fingerprint":fingerprint,
        "prompt_sha256":"b"*64,
        "source_sha256":hashes["source.pdf"],
        "slides_sha256":hashes["slides.pdf"],
        "script_sha256":hashes["script.txt"],
        "review_mode":"INITIAL_REVIEW",
        "submission_may_have_occurred":True,
        "can_auto_retry":False,
    }))
    (claim/"dispatch_attempted.claim").write_text(fingerprint+"\n")
    monkeypatch.setattr(focused,"build_review_job",
                        lambda **kwargs:copy.deepcopy(job))
    return original,queue,job,quote,claim


def plan_fixture(fixture):
    original, queue, job, quote, claim=fixture
    return focused.plan(folder=original,queue_root=queue,slide=3,
                        utterance_id="s003.utterance.001")


def test_executable_source_registry_is_registered():
    from selenium_pipeline.recovery_registry import lookup_mechanism
    assert lookup_mechanism(focused.KIND, focused.SIGNATURE)==focused.MECHANISM


def test_new_task_is_real_single_utterance_not_full_slide_replay(
        real_source_fixture):
    original,queue,full,quote,claim=real_source_fixture
    before={p.name:p.read_bytes() for p in (claim/"request_state.json",
                                            claim/"dispatch_attempted.claim",
                                            queue/"queue.json")}
    item=plan_fixture(real_source_fixture)
    assert item["status"]=="DISTINCT_SINGLE_UTTERANCE_SOURCE_TASK_PREPARED_NO_SEND"
    assert item["original_utterance_count"]==3
    assert item["focused_utterance_count"]==1
    assert item["new_prompt_sha256"]!=item["original_prompt_sha256"]
    assert item["new_provider_requests"]==0
    assert item["old_send_replay_authorized"] is False
    assert item["student_publication_authorized"] is False
    part=item["job"]
    assert len(part["slides"][0]["utterances"])==1
    assert len(part["slides"][0]["visual_targets"])==1
    assert len(part["verified_source_quote_candidates_v1"]["utterances"])==1
    assert part["focused_source_review_v1"]["full_original_slide_utterances"]==3
    assert part["focused_source_review_v1"]["quote_is_not_semantic_approval"] is True
    assert plan_fixture(real_source_fixture)["scope_sha256"]==item["scope_sha256"]
    assert {p.name:p.read_bytes() for p in
            (claim/"request_state.json",claim/"dispatch_attempted.claim",
             queue/"queue.json")}==before


def test_independent_existing_one_pass_validator_still_refuses_acceptance(
        real_source_fixture, tmp_path):
    original,queue,full,quote,claim=real_source_fixture
    item=plan_fixture(real_source_fixture)
    unit=item["job"]["slides"][0]["utterances"][0]
    responses=[]
    def synthetic_transport(prompt,files):
        responses.append(prompt)
        assert len(files)==2
        assert files[0]==original/"source.pdf"
        assert files[1]==original/"slides.pdf"
        assert quote in prompt and unit["id"] in prompt
        return json.dumps({
            "status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
            "rows":[{
                "utterance_id":unit["id"],
                "spoken_sha256":unit["spoken_sha256"],
                "target_id":"s003.text.001",
                "source_page":1,
                "verbatim_source_quote":quote,
                "verdict":"UNRESOLVED",
                "math_explanation":(
                    "This single candidate citation does not by itself "
                    "establish independent scientific verification."),
            }],
        })
    result=run_web_review(
        folder=original,job=item["job"],mode="INITIAL_REVIEW",
        checkpoint_dir=tmp_path/"focused_one_send",
        transport=synthetic_transport)
    assert len(responses)==1
    assert result["status"]=="SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS"
    assert result["review_count"]==1
    assert result["academic_mathematics_independently_verified"] is False
    assert result["student_publication_authorized"] is False
    assert not (queue/"slide_003_initial_review.json").exists()
    # The raw original submission callback cannot be called twice.
    from selenium_pipeline.academic_review_checkpoint import ReviewCheckpointError
    with pytest.raises(ReviewCheckpointError,match="already attempted"):
        run_web_review(
            folder=original,job=item["job"],mode="INITIAL_REVIEW",
            checkpoint_dir=tmp_path/"focused_one_send",
            transport=synthetic_transport)
    assert len(responses)==1
    # The focused controller itself must instead reopen and revalidate the
    # exact saved response without a provider request after restart.
    scope=queue.parent/focused.REVIEW_ROOT_NAME/item["scope_sha256"]
    scope.mkdir(parents=True)
    (tmp_path/"focused_one_send").rename(scope/"initial_request")
    (scope/"admission.json").write_text(json.dumps({
        "status":"NEW_SUBSTANTIVE_SOURCE_QUOTE_CHECK_NOT_ORIGINAL_RETRY",
        "scope_sha256":item["scope_sha256"],
        "old_claim_sha256":item["original_claim_sha256"],
        "prompt_sha256":item["new_prompt_sha256"],
        "source_sha256":item["source_sha256"],
        "source_quote_sha256":item["physical_source_quote_sha256"],
        "old_request_resubmitted":False,
        "health_model_family":"flash",
        "student_publication_authorized":False,
    }))
    recovered=focused.run_one(
        folder=original,queue_root=queue,slide=3,
        utterance_id="s003.utterance.001",
        health_result=tmp_path/"NO_HEALTH_OR_BROWSER_NEEDED_FOR_SAVED_REPLY")
    assert recovered["status"]=="FOCUSED_NEW_REVIEW_ONE_PASS_UNAPPROVED"
    assert recovered["model_result"]==result
    assert recovered["new_original_slide_consensus_count"]==0
    assert len(responses)==1


@pytest.mark.parametrize("change", [
    "no_dispatch_claim","confirmed_old_response","wrong_source",
    "old_status_pretends_unsent","cross_review_prompt",
])
def test_old_uncertain_evidence_cannot_be_rewritten_as_a_new_task(
        real_source_fixture, change):
    original,queue,job,quote,claim=real_source_fixture
    state=claim/"request_state.json"
    data=json.loads(state.read_text())
    if change=="no_dispatch_claim":
        (claim/"dispatch_attempted.claim").unlink()
    elif change=="confirmed_old_response":
        (claim/"model_response_untrusted.txt").write_text("old reply")
    elif change=="wrong_source":
        (original/"source.pdf").write_bytes(b"%PDF-1.4 wrong")
    else:
        if change=="old_status_pretends_unsent":
            data["status"]="PREPARED_NOT_SENT"
        else:
            data["review_mode"]="INDEPENDENT_CHALLENGE"
        state.write_text(json.dumps(data))
    with pytest.raises((ValueError, OSError)):
        plan_fixture(real_source_fixture)


def test_missing_or_forged_source_quote_rejected(real_source_fixture, monkeypatch):
    original,queue,job,quote,claim=real_source_fixture
    altered=copy.deepcopy(job)
    altered["verified_source_quote_candidates_v1"]["utterances"][0][
        "allowed_citations"][0]["verbatim_source_quote"]="An invented scientific quote."
    monkeypatch.setattr(focused,"build_review_job",
                        lambda **kwargs:copy.deepcopy(altered))
    with pytest.raises(ValueError):
        plan_fixture(real_source_fixture)


def test_new_provider_dispatch_requires_fresh_independent_health(
        real_source_fixture, tmp_path):
    original,queue,job,quote,claim=real_source_fixture
    with pytest.raises((ValueError,OSError)):
        focused.run_one(folder=original,queue_root=queue,slide=3,
            utterance_id="s003.utterance.001",
            health_result=tmp_path/"fake_health_result.json")
    assert not (queue.parent/focused.REVIEW_ROOT_NAME).exists()
    assert not (queue/"slide_003_initial_review.json").exists()


def test_exact_neon_health_scopes_one_new_source_review_only(
        real_source_fixture,tmp_path,monkeypatch):
    import os
    original,queue,job,quote,claim=real_source_fixture
    seen=[]
    monkeypatch.setenv("MICROGEN_GEMINI_UI_MODE","flash")
    monkeypatch.setenv("MICROGEN_GEMINI_THINKING_LEVEL","medium")
    monkeypatch.setattr(focused,"_health_ok",lambda **kw:{
        "status":"SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED",
        "verified_model_family":"neon","verified_thinking_level":"high",
        "G2_approved":False,"student_publication_authorized":False,
    })
    def fake_review(**kw):
        seen.append((kw.get("required_model_family"),
                     os.environ.get("MICROGEN_GEMINI_UI_MODE"),
                     os.environ.get("MICROGEN_GEMINI_THINKING_LEVEL"),
                     kw["job"]["utterance_count"]))
        return {
            "status":"SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS",
            "review_count":1,
            "academic_mathematics_independently_verified":False,
            "student_publication_authorized":False,
        }
    monkeypatch.setattr(focused,"run_web_review",fake_review)
    (tmp_path/"mock_source_free_health.json").write_text(
        '{"status":"SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED"}',
        encoding="utf8")
    result=focused.run_one(folder=original,queue_root=queue,slide=3,
        utterance_id="s003.utterance.001",family="neon",
        health_result=tmp_path/"mock_source_free_health.json")
    assert result["status"]=="FOCUSED_NEW_REVIEW_ONE_PASS_UNAPPROVED"
    assert result["new_original_slide_consensus_count"]==0
    assert seen==[("neon","pro","high",1)]
    assert os.environ["MICROGEN_GEMINI_UI_MODE"]=="flash"
    assert os.environ["MICROGEN_GEMINI_THINKING_LEVEL"]=="medium"
    scope=queue.parent/focused.REVIEW_ROOT_NAME/result["scope_sha256"]
    assert json.loads((scope/"admission.json").read_text())[
        "old_request_resubmitted"] is False
    assert not (queue/"slide_003_initial_review.json").exists()


def test_stale_health_before_newer_global_provider_incident_fails(
        real_source_fixture,tmp_path,monkeypatch):
    import time
    original,queue,job,quote,claim=real_source_fixture
    stamp=time.time()-100
    monkeypatch.setattr(focused,"verify_health",lambda **kw:{
        "status":"SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED",
        "observed_unix":stamp,
        "verified_model_family":"neon",
        "verified_thinking_level":"high",
        "G2_approved":False,"student_publication_authorized":False,
    })
    monkeypatch.setattr(focused,"_last_original_gemini_quarantine_mtime",
                        lambda:time.time()-40)
    with pytest.raises(ValueError,match="No fresh source-free"):
        focused.run_one(folder=original,queue_root=queue,slide=3,
            utterance_id="s003.utterance.001",
            health_result=tmp_path/"untrusted.json",family="neon")
    assert not (queue.parent/focused.REVIEW_ROOT_NAME).exists()
