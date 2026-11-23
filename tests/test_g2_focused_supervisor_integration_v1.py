"""The NORMAL G2 supervisor accepts only independently verified focused QA.

Source TTS and student release remain blocked if original 85-unit
whole-slide audio adapter has not been independently recertified.
"""
from __future__ import annotations
from pathlib import Path
import pytest

from selenium_pipeline import windows_g2_autonomous_qa_supervisor as sup
from selenium_pipeline import ai_academic_review_consensus as original
from selenium_pipeline import ai_academic_review_queue as q
from selenium_pipeline import g2_focused_source_consensus_bridge_v1 as focus


@pytest.fixture
def scope(tmp_path,monkeypatch):
    source=tmp_path/"source"
    queue=tmp_path/"queue"
    scratch=tmp_path/"scratch"
    for path in (source,queue,scratch):path.mkdir()
    plan={"expected_utterances":3}
    hashes={"source.pdf":"a"*64,"slides.pdf":"b"*64,"script.txt":"c"*64}
    monkeypatch.setattr(sup,"_is_verified_folder",lambda *a,**kw:(plan,hashes))
    original_accepted=[{"utterance_id":"s003.utterance.002"},
                       {"utterance_id":"s003.utterance.003"}]
    state={
        "status":"INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE",
        "original_utterances":3,
        "agreed_source_witnessed_segments":2,
        "accepted_ai_evidence":original_accepted,
        "pending_or_disputed":1,
        "student_publication_authorized":False,
    }
    monkeypatch.setattr(original,"reconcile_actual_review_queue",
                        lambda **kwargs:state)
    monkeypatch.setattr(q,"select_next_safe_review",lambda **kw:{
        "status":"NO_SAFE_REVIEW_UNIT_REMAINING",
        "blocked_other_slides":[],
        "new_model_requests":False,
    })
    return source,queue,scratch

def cert(*,focused=1):
    return {
        "status":"G2_ORIGINAL_AND_FOCUSED_SOURCE_AI_EVIDENCE_RECONCILED_NO_RELEASE",
        "original_total_utterances":3,
        "original_two_pass_source_AI_agreements":2,
        "combined_source_AI_agreements":2+focused,
        "pending_or_disputed_source_AI":1-focused,
        "new_provider_requests":0,
        "original_G2_claims_modified":False,
        "student_publication_authorized":False,
    }

def test_normal_supervisor_combines_focused_without_audio_release(
        scope,monkeypatch):
    folder,queue,scratch=scope
    monkeypatch.setattr(focus,"reconcile",lambda **kw:cert())
    out=sup.step(folder=folder,queue_root=queue,work_root=scratch,
                 execute=False,max_units=0,auto_media=False)
    assert out["two_pass_ai_source_agreed_segments"]==3
    assert out["original_legacy_two_pass_ai_source_agreements"]==2
    assert out["additional_verified_distinct_focused_agreements"]==1
    assert out["pending_or_disputed_segments"]==0
    assert out["status"]==(
        "G2_FOCUSED_SOURCE_EVIDENCE_READY_TTS_ADAPTER_NOT_CERTIFIED")
    assert out["source_verified_tts_jobs"]==0
    assert out["new_paid_tts_dispatched"] is False
    assert out["student_publication_authorized"] is False

def test_normal_supervisor_reports_legacy_and_new_pending_separately(
        scope,monkeypatch):
    folder,queue,scratch=scope
    monkeypatch.setattr(focus,"reconcile",lambda **kw:cert(focused=0))
    out=sup.step(folder=folder,queue_root=queue,work_root=scratch,
                 execute=False,max_units=0,auto_media=False)
    assert out["two_pass_ai_source_agreed_segments"]==2
    assert out["pending_or_disputed_segments"]==1
    assert out["new_paid_tts_dispatched"] is False

@pytest.mark.parametrize("change",[
    "forged_release","invented_agreements","wrong_original"])
def test_supervisor_rejects_forged_focused_source_acceptance(
        scope,monkeypatch,change):
    folder,queue,scratch=scope
    report=cert()
    if change=="forged_release":
        report["student_publication_authorized"]=True
    elif change=="invented_agreements":
        report["combined_source_AI_agreements"]=4
    else:
        report["original_two_pass_source_AI_agreements"]=1
    monkeypatch.setattr(focus,"reconcile",lambda **kw:report)
    with pytest.raises(Exception):
        sup.step(folder=folder,queue_root=queue,work_root=scratch,
                 execute=False,max_units=0,auto_media=False)
