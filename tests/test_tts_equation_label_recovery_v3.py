"""Exact original-source equation-ID audio QA recovery with no paid calls."""
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import pytest
from selenium_pipeline.tts_equation_label_recovery_v3 import (
    apply,_equation_pair,_identical_outside_equation)
from selenium_pipeline.recovery_registry import lookup_mechanism
SRC=Path(r"G:\My Drive\Serway\Serway_8_14\11\11.5\.microgen_work")

def real_report():
    return json.loads((SRC/"tts_fidelity_report.json").read_text(encoding="utf8"))

def check_uncorrected(slide_mutate):
    raw=real_report()
    slide_mutate(raw["slides"][-1])
    corrected=apply(SRC,raw)
    assert corrected["summary"]["review"]==1
    assert corrected["slides"][-1]["status"]=="review"
    assert "source_verified_minor_equation_label_variation" not in corrected["slides"][-1]

def test_recovery_registered():
    assert lookup_mechanism("tts_runtime_repair","SOURCE_BOUND_EQ_LABEL_DIGIT_BY_DIGIT_QA_VARIANT")=="SOURCE_SHA_EQ_LABEL_VERIFIED_SAME_DIGITS_KEEP_WAV_NO_REBILL"

def test_verbatim_equation_label_roundtrip_only():
    assert _equation_pair("eleven point twenty-two")==(11,22)
    assert _equation_pair("eleven point two two")==(11,22)
    assert _equation_pair("eleven point twenty-three")!=(11,22)
    assert _equation_pair("eleven point two three")!=(11,22)
    assert _equation_pair("negative eleven point twenty-two") is None
    assert _identical_outside_equation("According to Equation eleven point twenty-two, torque increases",
       "According to Equation eleven point two two, torque increases",
       "eleven point twenty-two","eleven point two two")
    assert not _identical_outside_equation("According to Equation eleven point twenty-two, torque increases",
       "According to Equation eleven point two two, torque decreases",
       "eleven point twenty-two","eleven point two two")

@pytest.mark.skipif(not SRC.is_dir(),reason="Original Chapter 11 Dell drive unavailable")
def test_real_original_source_11_5_slide10_reuses_same_wav_without_model(monkeypatch):
    raw=real_report()
    before=(SRC/"slide10.wav").read_bytes()
    with patch("selenium_pipeline.tts_fidelity.inspect_audio",
               side_effect=AssertionError("No new listening bill")):
        fixed=apply(SRC,raw)
    assert fixed["summary"]["passed"]==10 and fixed["summary"]["review"]==0
    assert fixed["summary"]["minimum_fidelity_percent"]==99
    assert fixed["slides"][-1]["source_verified_minor_equation_label_variation"]["printed_source_equation_label"]=="11.22"
    assert fixed["slides"][-1]["equivalent_reference_issues_original"]==raw["slides"][-1]["critical_token_issues"]
    assert raw["slides"][-1]["status"]=="review"
    assert (SRC/"slide10.wav").read_bytes()==before

@pytest.mark.skipif(not SRC.is_dir(),reason="Original Chapter 11 Dell drive unavailable")
def test_wrong_equation_identifier_fails_closed():
    check_uncorrected(lambda r:r["critical_token_issues"][0].update(heard_as="eleven point two three"))

@pytest.mark.skipif(not SRC.is_dir(),reason="Original Chapter 11 Dell drive unavailable")
def test_wrong_spoken_math_fails_closed():
    check_uncorrected(lambda r:r.update(transcript=r["transcript"].replace("precessional frequency change",
                   "precessional frequency decrease")))

@pytest.mark.skipif(not SRC.is_dir(),reason="Original Chapter 11 Dell drive unavailable")
def test_other_acoustic_defects_fail_closed():
    check_uncorrected(lambda r:r["audio_defects"].append("truncated final syllable"))

@pytest.mark.skipif(not SRC.is_dir(),reason="Original Chapter 11 Dell drive unavailable")
def test_other_critical_number_or_sign_fails_closed():
    check_uncorrected(lambda r:r["critical_token_issues"].append({
        "script_text":"positive","heard_as":"negative","category":"sign","severity":"major"}))

@pytest.mark.skipif(not SRC.is_dir(),reason="Original Chapter 11 Dell drive unavailable")
def test_wrong_source_pdf_blocks_minor_qa_review(tmp_path):
    original=real_report()
    d=tmp_path/"lecture";d.mkdir()
    (d/"source.pdf").write_bytes(b"bad-source-do-not-approve")
    (d/"slide10.wav").write_bytes((SRC/"slide10.wav").read_bytes())
    with pytest.raises(Exception):
        apply(d,original)

def test_unrelated_qa_never_opens_pdf_or_checks_registry(tmp_path):
    raw={"slides":[{"status":"pass"}],"summary":{"slides":1,"passed":1}}
    with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
               side_effect=AssertionError("unrelated QA changed")):
        assert apply(tmp_path,raw) is raw
