"""Source-free Neon/High requalification: exact family, one claim, no replay."""
from __future__ import annotations

import json
import os
from pathlib import Path
import pytest

from selenium_pipeline import academic_provider_requalification as health
from selenium_pipeline import academic_neon_high_two_pdf_requalification as neon
from selenium_pipeline.series_gemini import OwnedGeminiResponse

SOURCE="a"*64
NOW=1795455500.0

@pytest.fixture
def scope(tmp_path,monkeypatch):
    monkeypatch.setenv("MICROGEN_GEMINI_UI_MODE","pro")
    monkeypatch.setenv("MICROGEN_GEMINI_THINKING_LEVEL","high")
    q=tmp_path/"original_queue"
    q.mkdir()
    monkeypatch.setattr(neon,"qualifying_proof",lambda **kw:{
        "status":"NEON_HIGH_TWO_PDF_SOURCE_FREE_RESPONSE_VERIFIED",
        "source_free_neon_pdf_capability_verified":True,
        "verified_model_family":"neon","verified_thinking_level":"high",
        "new_source_review_send_allowed":False})
    return tmp_path,q

def synthetic_response(*,family="neon",effort="high"):
    _,nonce=health._expected(source_sha=SOURCE,family="neon",day=health._day(NOW))
    return OwnedGeminiResponse(
        json.dumps({"microgen_health":"ok","nonce":nonce},separators=(",",":")),
        registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
        new_turn_verified=True,verified_model_family=family,
        verified_thinking_level=effort)

def test_new_neon_health_is_one_unique_source_free_claim(scope):
    root,q=scope
    calls=[]
    def fake(prompt,port):
        calls.append((port,prompt))
        return synthetic_response()
    result=health.probe_once(checkpoint_parent=root,queue_root=q,
        source_sha=SOURCE,family="neon",now=NOW,browser_request=fake)
    assert result["status"]=="SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED",result.get("safe_error_class")
    assert result["verified_model_family"]=="neon"
    assert result["verified_thinking_level"]=="high"
    assert result["G2_approved"] is False
    assert result["student_publication_authorized"] is False
    assert len(calls)==1 and calls[0][0]==9222
    assert "source.pdf" not in calls[0][1]
    assert "slides.pdf" not in calls[0][1]
    assert "The physical dimension" not in calls[0][1]
    same=health.probe_once(checkpoint_parent=root,queue_root=q,
        source_sha=SOURCE,family="neon",now=NOW,browser_request=fake)
    assert same["reused_immutable_probe"] is True
    assert same["new_provider_requests"]==0
    assert len(calls)==1

@pytest.mark.parametrize("family,effort",[("flash","high"),("neon","medium"),
                                            ("pro","high")])
def test_misidentified_neon_health_never_qualifies(scope,family,effort):
    root,q=scope
    got=health.probe_once(checkpoint_parent=root,queue_root=q,
        source_sha=SOURCE,family="neon",now=NOW,
        browser_request=lambda *_:synthetic_response(family=family,effort=effort))
    assert got["status"]=="NO_VERIFIED_SOURCE_FREE_RESPONSE"
    assert got["G2_approved"] is False
    second=health.probe_once(checkpoint_parent=root,queue_root=q,
        source_sha=SOURCE,family="neon",now=NOW,browser_request=lambda *_:pytest.fail("unsafe duplicate send"))
    assert second["new_provider_requests"]==0

def test_missing_historical_neon_pdf_qualification_prevents_claim(scope,monkeypatch):
    root,q=scope
    monkeypatch.setattr(neon,"qualifying_proof",lambda **kw:None)
    with pytest.raises(ValueError,match="qualification"):
        health.probe_once(checkpoint_parent=root,queue_root=q,source_sha=SOURCE,
            family="neon",now=NOW,browser_request=lambda *_:pytest.fail("must not call"))
    assert not (root/health.ROOT/SOURCE/"neon").exists()

def test_wrong_family_environment_prevents_source_free_claim(scope,monkeypatch):
    root,q=scope
    monkeypatch.setenv("MICROGEN_GEMINI_UI_MODE","flash")
    with pytest.raises(ValueError,match="model/thinking"):
        health.probe_once(checkpoint_parent=root,queue_root=q,
            source_sha=SOURCE,family="neon",now=NOW,
            browser_request=lambda *_:pytest.fail("must not call"))
    assert not (root/health.ROOT/SOURCE/"neon").exists()

def test_tampered_neon_receipt_is_not_reused(scope):
    root,q=scope
    health.probe_once(checkpoint_parent=root,queue_root=q,
        source_sha=SOURCE,family="neon",now=NOW,
        browser_request=lambda *_:synthetic_response())
    _,file=health._paths(checkpoint_parent=root,source_sha=SOURCE,
                         family="neon",day=health._day(NOW))
    record=json.loads(file.read_text("utf8"))
    record["verified_model_family"]="flash"
    file.write_text(json.dumps(record))
    with pytest.raises(ValueError,match="exact-family"):
        health.probe_once(checkpoint_parent=root,queue_root=q,
            source_sha=SOURCE,family="neon",now=NOW,
            browser_request=lambda *_:pytest.fail("must not call"))
