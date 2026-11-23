"""Original-plus-focused G2 consensus is revalidated from real saved bytes."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import pytest

from tests.test_g2_distinct_focused_source_review_v1 import real_source_fixture
from tests.test_g2_distinct_focused_challenge_v1 import seed_initial,reply
from selenium_pipeline import g2_distinct_focused_challenge_v1 as challenge
from selenium_pipeline import g2_focused_source_consensus_bridge_v1 as bridge
from selenium_pipeline.ai_academic_web_review import run_web_review


def make_two_pass(real_source_fixture,monkeypatch,*,verdict="SUPPORTED"):
    folder,queue,_,quote,_=real_source_fixture
    item,scope=seed_initial(real_source_fixture)
    original=run_web_review
    monkeypatch.setattr(challenge,"_health_ok",lambda **kw:{})
    monkeypatch.setattr(challenge,"run_web_review",
        lambda **kw:original(**kw,transport=lambda *_:reply(
            item["job"],quote,
            "An independently composed textbook-based dimensional "
            "argument recognizes speed as length divided by time.",
            verdict=verdict)))
    challenge.challenge_once(
        folder=folder,queue_root=queue,slide=3,
        utterance_id="s003.utterance.001",
        health_result=queue.parent/"fake_probe_for_synthetic_test")
    return item,scope


def original_stub(*,with_first:bool=False):
    count=3
    accepted=[{"utterance_id":"s003.utterance.001"}] if with_first else []
    ids=[f"s003.utterance.{i:03d}" for i in range(1,4)]
    return {
        "status":"INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE",
        "original_utterances":count,
        "agreed_source_witnessed_segments":len(accepted),
        "accepted_ai_evidence":accepted,
        "unresolved":[{"utterance_id":x,"reason":"MISSING_INDEPENDENT_SOURCE_PASS"}
                     for x in ids if x not in {a["utterance_id"] for a in accepted}],
        "AI_consensus_is_formal_math_proof":False,
        "student_publication_authorized":False,
    }


def test_genuine_two_pass_counts_one_not_original_slide_or_publication(
        real_source_fixture,monkeypatch,tmp_path):
    folder,queue,_,_,_=real_source_fixture
    item,scope=make_two_pass(real_source_fixture,monkeypatch)
    monkeypatch.setattr(bridge,"reconcile_actual_review_queue",
                        lambda **kw:original_stub())
    original_files=[queue/"queue.json",
       queue/"slide_003_initial_review_attempt_01_request"/"request_state.json",
       queue/"slide_003_initial_review_attempt_01_request"/"dispatch_attempted.claim",
       folder/"source.pdf",folder/"slides.pdf",folder/"script.txt"]
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in original_files}
    a=bridge.reconcile(folder=folder,queue_root=queue)
    assert a["status"]=="G2_ORIGINAL_AND_FOCUSED_SOURCE_AI_EVIDENCE_RECONCILED_NO_RELEASE"
    assert a["original_two_pass_source_AI_agreements"]==0
    assert a["additional_distinct_two_pass_source_AI_agreements"]==1
    assert a["combined_source_AI_agreements"]==1
    assert a["pending_or_disputed_source_AI"]==2
    assert a["new_focused_utterance_ids"]==["s003.utterance.001"]
    assert a["student_publication_authorized"] is False
    assert a["AI_consensus_is_formal_math_proof"] is False
    assert a["independent_acoustic_QA_complete"] is False
    assert a["new_provider_requests"]==0
    assert a["original_G2_claims_modified"] is False
    assert bridge.reconcile(folder=folder,queue_root=queue)==a
    assert Path(a["receipt"]).is_file()
    assert {str(p):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in original_files}==before


def test_original_already_accepted_is_not_counted_twice(
        real_source_fixture,monkeypatch):
    folder,queue,_,_,_=real_source_fixture
    make_two_pass(real_source_fixture,monkeypatch)
    monkeypatch.setattr(bridge,"reconcile_actual_review_queue",
                        lambda **kw:original_stub(with_first=True))
    result=bridge.reconcile(folder=folder,queue_root=queue)
    assert result["original_two_pass_source_AI_agreements"]==1
    assert result["additional_distinct_two_pass_source_AI_agreements"]==0
    assert result["combined_source_AI_agreements"]==1


@pytest.mark.parametrize("tamper",[
    "two_pass_report", "neon_witness", "first_raw", "scope_name"])
def test_corrupted_focused_two_pass_never_contributes(
        real_source_fixture,monkeypatch,tamper):
    folder,queue,_,_,_=real_source_fixture
    item,scope=make_two_pass(real_source_fixture,monkeypatch)
    monkeypatch.setattr(bridge,"reconcile_actual_review_queue",
                        lambda **kw:original_stub())
    if tamper=="two_pass_report":
        report=scope/"two_pass_evidence.json"
        data=json.loads(report.read_text())
        data["first_response_sha256"]="0"*64
        report.write_text(json.dumps(data))
    elif tamper=="neon_witness":
        (scope/"challenge_request"/"neon_high_owned_model_witness.json").unlink()
    elif tamper=="first_raw":
        (scope/"initial_request"/"model_response_untrusted.txt").write_text(
            '{"fake":"text"}')
    else:
        scope.rename(scope.with_name("b"*64))
    with pytest.raises(Exception):
        bridge.reconcile(folder=folder,queue_root=queue)
    assert not (queue/"slide_003_initial_review.json").exists()


def test_disputed_focused_review_remains_pending(
        real_source_fixture,monkeypatch):
    folder,queue,_,_,_=real_source_fixture
    make_two_pass(real_source_fixture,monkeypatch,verdict="UNRESOLVED")
    monkeypatch.setattr(bridge,"reconcile_actual_review_queue",
                        lambda **kw:original_stub())
    result=bridge.reconcile(folder=folder,queue_root=queue)
    assert result["combined_source_AI_agreements"]==0
    assert result["pending_or_disputed_source_AI"]==3
    assert result["student_publication_authorized"] is False
