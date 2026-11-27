"""Paid API egress: no API calls for science/content, even in fallback mode."""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from selenium_pipeline.paid_api_policy import (
    PaidAPIPolicyBlocked, require_paid_gemini_api,
    set_tts_qa_approval_for_run, tts_qa_explicitly_approved,
    TTS_QA_APPROVAL_ENV, TTS_QA_APPROVAL_LITERAL,
)
from selenium_pipeline.communication_policy import (
    CommunicationPolicy, CommunicationBackend, resolve_mode,
)


@pytest.mark.parametrize("purpose", [
    None,"","slides","figures","narration","academic_review",
    "scientific_review","pedagogy_review","script_review","lecture_generation",
    "fallback","gemini","text","tts-and-slides",
])
def test_unknown_or_content_api_purposes_fail_before_creating_any_client(purpose,monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY_1","EXAMPLE_NOT_REAL")
    with pytest.raises(PaidAPIPolicyBlocked,match="SELENIUM_ONLY"):
        require_paid_gemini_api(purpose)


def test_tts_allowed_but_qa_not_inferred_from_tts_or_api_keys(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY_1","EXAMPLE_NOT_REAL")
    monkeypatch.delenv(TTS_QA_APPROVAL_ENV,raising=False)
    require_paid_gemini_api("tts")
    with pytest.raises(PaidAPIPolicyBlocked,match="MODEL_NOT_AUTHORIZED"):
        require_paid_gemini_api("tts_qa",qa_approved=True)
    with pytest.raises(PaidAPIPolicyBlocked,match="MODEL_NOT_AUTHORIZED"):
        require_paid_gemini_api("tts_qa")


def test_tts_qa_requires_literal_explicit_this_run_approval(monkeypatch):
    monkeypatch.setenv(TTS_QA_APPROVAL_ENV,"1")
    assert not tts_qa_explicitly_approved()
    with pytest.raises(PaidAPIPolicyBlocked,match="MODEL_NOT_AUTHORIZED"):
        require_paid_gemini_api("tts_qa",qa_approved=True)
    with monkeypatch.context() as scope:
        scope.setenv(TTS_QA_APPROVAL_ENV,TTS_QA_APPROVAL_LITERAL)
        assert tts_qa_explicitly_approved()
        require_paid_gemini_api("tts_qa",qa_approved=True)
        with pytest.raises(PaidAPIPolicyBlocked,match="MODEL_NOT_AUTHORIZED"):
            require_paid_gemini_api("tts_qa",qa_approved=False)


def test_cli_approval_reset_is_not_sticky(monkeypatch):
    monkeypatch.delenv(TTS_QA_APPROVAL_ENV,raising=False)
    set_tts_qa_approval_for_run(True)
    assert tts_qa_explicitly_approved()
    set_tts_qa_approval_for_run(False)
    assert not tts_qa_explicitly_approved()
    with pytest.raises(TypeError):
        set_tts_qa_approval_for_run(1)


def test_disabled_recovery_registry_blocks_paid_tts_and_approved_qa(tmp_path,monkeypatch):
    from selenium_pipeline import recovery_registry
    reg=json.loads(recovery_registry.REGISTRY_PATH.read_text(encoding="utf8"))
    entry=next(row for row in reg["entries"]
        if row["signature"]=="SELENIUM_ONLY_CONTENT_TTS_PAID_GATE")
    entry["enabled"]=False
    disabled=tmp_path/"registry_disabled.json"
    disabled.write_text(json.dumps(reg),encoding="utf8")
    monkeypatch.setattr(recovery_registry,"REGISTRY_PATH",disabled)
    monkeypatch.setenv(TTS_QA_APPROVAL_ENV,TTS_QA_APPROVAL_LITERAL)
    for purpose,approved in [("tts",False),("tts_qa",True)]:
        with pytest.raises(PaidAPIPolicyBlocked,match="REGISTRY"):
            require_paid_gemini_api(purpose,qa_approved=approved)


def test_api_client_constructor_and_key_failover_cannot_bypass_gate(monkeypatch):
    import gemini_keys
    monkeypatch.setenv("GEMINI_API_KEY_1","NOT_REAL")
    monkeypatch.setenv("MICROGEN_GEMINI_MAX_RETRIES","0")
    with patch("gemini_keys.genai.Client") as make:
        with pytest.raises(PaidAPIPolicyBlocked,match="SELENIUM_ONLY"):
            gemini_keys.create_gemini_client("SECRET")
        with pytest.raises(PaidAPIPolicyBlocked,match="SELENIUM_ONLY"):
            gemini_keys.call_with_key_failover(lambda _key: "UNSAFE")
        with pytest.raises(PaidAPIPolicyBlocked,match="SELENIUM_ONLY"):
            gemini_keys.call_with_client_failover(lambda _key:object(),lambda x:x)
        make.assert_not_called()


def test_paid_tts_client_still_admissible_with_explicit_purpose(monkeypatch):
    import gemini_keys
    monkeypatch.setenv("MICROGEN_GEMINI_SDK_RETRY_ATTEMPTS","1")
    with patch("gemini_keys.genai.Client",return_value=object()) as make:
        assert gemini_keys.create_gemini_client("SECRET",purpose="tts") is not None
        make.assert_called_once()


def test_direct_api_text_transports_refuse_even_with_mocked_sdk(tmp_path):
    from selenium_pipeline import slides_api,narration_api,figure_mapping_api
    source=tmp_path/"source.pdf";source.write_bytes(b"%PDF-1.7\n")
    meta=tmp_path/"metadata.json";meta.write_text("{}")
    instruction=tmp_path/"instruction.txt";instruction.write_text("Test")
    image=tmp_path/"page.png";image.write_bytes(b"PNG")
    with patch("gemini_keys.call_with_client_failover") as send:
        with pytest.raises(PaidAPIPolicyBlocked):
            slides_api.request_slides(source,instruction,meta,"Convert")
        with pytest.raises(PaidAPIPolicyBlocked):
            narration_api.request_narration(source,source,instruction,"Write")
        with pytest.raises(PaidAPIPolicyBlocked):
            figure_mapping_api.request_mapping(image,[image],"gemini-3.8-flash")
        send.assert_not_called()


def test_approved_audio_qa_can_use_mocked_sdk_but_not_other_purposes(tmp_path,monkeypatch):
    from selenium_pipeline import tts_fidelity
    wav=tmp_path/"slide1.wav";wav.write_bytes(b"RIFF"+b"0"*64)
    monkeypatch.delenv(TTS_QA_APPROVAL_ENV,raising=False)
    with patch("gemini_keys.call_with_client_failover") as send:
        # Alternative QA model remains unapproved. The exact Flash 3.8
        # default is now automatically authorized by the owner.
        with pytest.raises(PaidAPIPolicyBlocked,match="MODEL_NOT_AUTHORIZED"):
            tts_fidelity._inspect_audio_direct(wav,"Hello.", model="gemini-3.1-pro")
        send.assert_not_called()
    monkeypatch.setenv(TTS_QA_APPROVAL_ENV,TTS_QA_APPROVAL_LITERAL)
    with patch("gemini_keys.call_with_client_failover",
               return_value=SimpleNamespace(text=json.dumps({
                   "transcript":"Hello.","pronunciation_issues":[],
                   "critical_token_issues":[],"audio_defects":[],
               }))) as send:
        result=tts_fidelity._inspect_audio_direct(wav,"Hello.",model="gemini-3.1-pro")
        assert result["transcript"]=="Hello."
        assert send.call_args.kwargs["purpose"]=="tts_qa"
        assert send.call_args.kwargs["model"]=="gemini-3.1-pro"


def test_new_content_policy_never_creates_api_attempts(monkeypatch):
    for stage in ("figures","slides","narration","scientific_review"):
        assert {step.backend for step in CommunicationPolicy().plan(stage)}=={
            CommunicationBackend.SELENIUM}
    for mode in ("api","fallback","auto"):
        monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE",mode)
        with pytest.raises(ValueError,match="SELENIUM_ONLY_CONTENT_POLICY"):
            resolve_mode()


def test_source_guard_for_legacy_direct_paid_paths():
    root=Path(__file__).resolve().parents[1]
    legacy=[
        "gen_script_v12.py","gen_slides_v19.py",
        "gen_json2.py","gen_mcq_test_from_xlm.py",
        "gen_problem_sets_v5.py","gen_xml_fr_source_thomas.py",
        "selenium_pipeline/pedagogy_benchmark.py",
        "selenium_pipeline/vendor_template_v2/crop_pbset_fr_source_v2.py",
        "selenium_pipeline/figure_mapping_api.py",
        "selenium_pipeline/narration_api.py",
        "selenium_pipeline/slides_api.py",
    ]
    for name in legacy:
        source=(root/name).read_text(encoding="utf-8-sig")
        assert 'require_paid_gemini_api(' in source,name
    pipeline=(root/"selenium_pipeline/runner.py").read_text(encoding="utf8")
    assert '"MICROGEN_FIGURE_MAPPING_BACKEND": "browser"' in pipeline
    assert '"MICROGEN_NARRATION_BACKEND": "ui"' in pipeline
    assert 'choices=("selenium",)' in pipeline
    assert '--confirm-paid-tts-qa' in pipeline
