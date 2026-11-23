"""Independent focused source/slide narration challenge and no-replay proofs."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from tests.test_g2_distinct_focused_source_review_v1 import real_source_fixture
from selenium_pipeline import g2_distinct_focused_source_review_v1 as focused
from selenium_pipeline import g2_distinct_focused_challenge_v1 as challenged
from selenium_pipeline.ai_academic_web_review import run_web_review
from selenium_pipeline.series_gemini import OwnedGeminiResponse

def reply(job,quote,reason,*,verdict="SUPPORTED"):
    unit=job["slides"][0]["utterances"][0]
    raw=json.dumps({
        "status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
        "rows":[{
            "utterance_id":unit["id"],
            "spoken_sha256":unit["spoken_sha256"],
            "target_id":"s003.text.001",
            "source_page":1,"verbatim_source_quote":quote,
            "verdict":verdict,"math_explanation":reason,
        }]},sort_keys=True)
    return OwnedGeminiResponse(
        raw,registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
        new_turn_verified=True,verified_model_family="neon",
        verified_thinking_level="high")

def seed_initial(fixture):
    folder,queue,_,quote,_=fixture
    item=focused.plan(
        folder=folder,queue_root=queue,slide=3,
        utterance_id="s003.utterance.001")
    job=item["job"]
    scope=queue.parent/focused.REVIEW_ROOT_NAME/item["scope_sha256"]
    scope.mkdir(parents=True)
    (scope/"admission.json").write_text(json.dumps({
        "status":"NEW_SUBSTANTIVE_SOURCE_QUOTE_CHECK_NOT_ORIGINAL_RETRY",
        "scope_sha256":item["scope_sha256"],
        "old_claim_sha256":item["original_claim_sha256"],
        "prompt_sha256":item["new_prompt_sha256"],
        "source_sha256":item["source_sha256"],
        "source_quote_sha256":item["physical_source_quote_sha256"],
        "health_model_family":"neon",
        "old_request_resubmitted":False,
        "student_publication_authorized":False,
    }))
    first=run_web_review(
        folder=folder,job=job,mode="INITIAL_REVIEW",
        checkpoint_dir=scope/"initial_request",
        required_model_family="neon",
        transport=lambda *_:reply(job,quote,
            "The citation states velocity has length divided by time, "
            "matching the narrated dimensional relationship."))
    assert first["rows"][0]["verdict"]=="SUPPORTED"
    assert first["rows"][0]["exact_textbook_quote_verified"] is True
    return item,scope

def test_two_independently_saved_source_replies_agree_without_original_promotion(
        real_source_fixture,monkeypatch,tmp_path):
    folder,queue,_,quote,_=real_source_fixture
    item,scope=seed_initial(real_source_fixture)
    sent=[]
    raw_review=run_web_review
    def fake_browser(**kwargs):
        sent.append(kwargs["mode"])
        return raw_review(**kwargs,transport=lambda *_:reply(
            item["job"],quote,
            "From the original publisher sentence, velocity dimensions "
            "are the quotient of length and time, supporting the slide."))
    monkeypatch.setattr(challenged,"run_web_review",fake_browser)
    monkeypatch.setattr(challenged,"_health_ok",lambda **kw: {
        "status":"SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED"})
    got=challenged.challenge_once(
        folder=folder,queue_root=queue,slide=3,
        utterance_id="s003.utterance.001",
        health_result=tmp_path/"test_health_receipt.json")
    assert got["status"]=="FOCUSED_TWO_PASS_SOURCE_AI_AGREEMENT_UNAPPROVED"
    assert got["source_math_AI_agreed"] is True
    assert got["original_g2_segments_promoted"]==0
    assert got["student_publication_authorized"] is False
    assert got["first_response_sha256"]!=got["challenge_response_sha256"]
    assert sent==["INDEPENDENT_CHALLENGE"]
    assert not (queue/"slide_003_initial_review.json").exists()
    assert not (queue/"slide_003_independent_challenge.json").exists()
    replay=challenged.challenge_once(
        folder=folder,queue_root=queue,slide=3,
        utterance_id="s003.utterance.001",
        health_result=tmp_path/"irrelevant_after_saving.json")
    assert replay==got
    assert sent==["INDEPENDENT_CHALLENGE"]

def test_second_pass_disagreement_cannot_promote(
        real_source_fixture,monkeypatch,tmp_path):
    folder,queue,_,quote,_=real_source_fixture
    item,_=seed_initial(real_source_fixture)
    monkeypatch.setattr(challenged,"_health_ok",lambda **kw: {})
    raw_review=run_web_review
    monkeypatch.setattr(challenged,"run_web_review",
        lambda **kwargs:raw_review(**kwargs,transport=lambda *_:reply(
            item["job"],quote,
            "The second reviewer cannot establish the narration from "
            "the single listed evidence line alone.",
            verdict="UNRESOLVED")))
    result=challenged.challenge_once(folder=folder,queue_root=queue,
        slide=3,utterance_id="s003.utterance.001",
        health_result=tmp_path/"unused")
    assert result["status"]=="FOCUSED_TWO_PASS_DISPUTED_NO_PROMOTION"
    assert result["source_math_AI_agreed"] is False
    assert result["original_g2_segments_promoted"]==0

def test_uncertain_challenge_is_quarantined_without_retry(
        real_source_fixture,monkeypatch,tmp_path):
    folder,queue,_,quote,_=real_source_fixture
    item,_=seed_initial(real_source_fixture)
    monkeypatch.setattr(challenged,"_health_ok",lambda **kw: {})
    count=[]
    raw_review=run_web_review
    def fail_during_send(**kwargs):
        return raw_review(**kwargs,transport=lambda *_:(
            count.append(1) or (_ for _ in ()).throw(
                ConnectionError("Ambiguous provider Send outcome"))))
    monkeypatch.setattr(challenged,"run_web_review",fail_during_send)
    with pytest.raises(ConnectionError):
        challenged.challenge_once(folder=folder,queue_root=queue,
            slide=3,utterance_id="s003.utterance.001",
            health_result=tmp_path/"unneeded")
    assert len(count)==1
    with pytest.raises(ValueError,match="NO REPLAY"):
        challenged.challenge_once(folder=folder,queue_root=queue,
            slide=3,utterance_id="s003.utterance.001",
            health_result=tmp_path/"unneeded")
    assert len(count)==1
    assert not (queue/"slide_003_initial_review.json").exists()
