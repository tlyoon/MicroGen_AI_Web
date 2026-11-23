"""G3 source-free exact Neon/High one-Send health is distinct from science."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from selenium_pipeline import g3_semantic_neon_health_v1 as health
from selenium_pipeline.series_gemini import OwnedGeminiResponse
from selenium_pipeline.recovery_registry import lookup_mechanism

SOURCE="d"*64


def owned(prompt,files,*,family="neon",effort="high"):
    assert files==[]  # no original textbook or student PDF attachments
    nonce=prompt.rsplit('"nonce":"',1)[1].split('"',1)[0]
    return OwnedGeminiResponse(
        json.dumps({"g3_source_health":"ready","nonce":nonce},
                   separators=(",",":")),
        registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
        new_turn_verified=True,
        verified_model_family=family,
        verified_thinking_level=effort)


def test_registered_semantic_source_free_health():
    assert lookup_mechanism(health.KIND,health.SIGNATURE)==health.MECHANISM


def test_one_owned_source_free_health_and_no_restart_replay(tmp_path):
    sent=[]
    def transport(prompt,files):
        sent.append(prompt)
        return owned(prompt,files)
    result=health.probe_once(root=tmp_path,source_sha=SOURCE,
                             browser_request=transport)
    assert result["status"]==health._OK
    assert result["fresh_neon_high_source_free_health"] is True
    assert result["new_provider_requests"]==1
    assert result["no_original_PDF_attached"] is True
    assert result["student_publication_authorized"] is False
    assert health.latest(root=tmp_path,source_sha=SOURCE,
                         after_unix=time.time()-300) is not None
    again=health.probe_once(root=tmp_path,source_sha=SOURCE,
        browser_request=lambda *a:pytest.fail("must not repeat claimed Send"))
    assert again["status"]==health._OK
    assert len(sent)==1
    day=health.datetime.fromtimestamp(time.time(),health.timezone.utc).strftime("%Y%m%d")
    assert (tmp_path/health.ROOT/SOURCE/day/"claim.json").is_file()


@pytest.mark.parametrize("family,effort",[
    ("flash","high"),("neon","medium"),("pro","high")])
def test_wrong_model_health_cannot_admit_semantic_review(
        tmp_path,family,effort):
    result=health.probe_once(
        root=tmp_path,source_sha=SOURCE,
        browser_request=lambda prompt,files:owned(
            prompt,files,family=family,effort=effort))
    assert result["status"]==health._BAD
    assert result["fresh_neon_high_source_free_health"] is False
    assert health.probe_once(root=tmp_path,source_sha=SOURCE,
        browser_request=lambda *a:pytest.fail("unsafe second Send"))[
            "status"]==health._BAD


def test_timeout_consumes_once_only_health_claim(tmp_path):
    calls=[]
    def timeout(prompt,files):
        calls.append(1)
        raise TimeoutError("The UI Send outcome is uncertain")
    result=health.probe_once(root=tmp_path,source_sha=SOURCE,
                             browser_request=timeout)
    assert result["status"]==health._BAD
    assert len(calls)==1
    health.probe_once(root=tmp_path,source_sha=SOURCE,
        browser_request=lambda *a:pytest.fail("must not repeat"))
    assert len(calls)==1


def test_tampered_original_health_receipt_is_not_readable(tmp_path):
    health.probe_once(root=tmp_path,source_sha=SOURCE,
        browser_request=lambda prompt,files:owned(prompt,files))
    day=health.datetime.fromtimestamp(time.time(),health.timezone.utc).strftime("%Y%m%d")
    result=tmp_path/health.ROOT/SOURCE/day/"result.json"
    obj=json.loads(result.read_text())
    obj["verified_model_family"]="flash"
    result.write_text(json.dumps(obj))
    with pytest.raises(ValueError,match="Wrong model"):
        health.latest(root=tmp_path,source_sha=SOURCE,after_unix=0)
