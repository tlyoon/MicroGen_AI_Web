"""Previously allowed Gemini API narration; regression now proves no paid fallback."""
from pathlib import Path
from unittest.mock import patch
import pytest
from selenium_pipeline import narration_api
from selenium_pipeline.paid_api_policy import PaidAPIPolicyBlocked


def files(tmp):
    a=tmp/"slides.pdf";a.write_bytes(b"%PDF-1.7\nslide")
    b=tmp/"source.pdf";b.write_bytes(b"%PDF-1.7\nsource")
    c=tmp/"prompt.txt";c.write_text("Narrate slides.")
    return a,b,c


def script(n=2):
    return "".join(
        f"**Slide {i} [40 sec]:**\n" +
        "Physics narration text with clear words and explanations. "*6+"\n"
        for i in range(1,n+1))


def test_numbered_narration_validator_still_checks_saved_responses():
    narration_api.validate_raw_script(script(2),2)
    with pytest.raises(ValueError,match="blocks invalid"):
        narration_api.validate_raw_script(script(1),2)
    with pytest.raises(ValueError,match="blocks invalid"):
        narration_api.validate_raw_script(script(2)+script(1),2)
    with pytest.raises(ValueError,match="empty or suspiciously short"):
        narration_api.validate_raw_script("OK",2)


@pytest.mark.parametrize("model",["gemini-3.8-flash","gemini-3.1-pro"])
def test_api_narration_refused_before_sdk_or_credentials(tmp_path,model):
    a,b,c=files(tmp_path)
    with patch("gemini_keys.call_with_client_failover") as send:
        with pytest.raises(PaidAPIPolicyBlocked,match="SELENIUM_ONLY"):
            narration_api.request_narration(a,b,c,"Narration",model=model)
        send.assert_not_called()


def test_api_narration_cli_refuses_and_does_not_write_output(tmp_path):
    a,b,c=files(tmp_path)
    instr=tmp_path/"in.txt";instr.write_text("Narrate")
    result=tmp_path/"script_api_response.txt"
    with pytest.raises(PaidAPIPolicyBlocked,match="SELENIUM_ONLY"):
        narration_api.main([
            "--slides",str(a),"--source",str(b),"--prompt",str(c),
            "--instruction-file",str(instr),"--output",str(result),
            "--expected-slides","2"])
    assert not result.exists()


def test_launcher_requires_selenium_for_generation_and_scientific_review():
    root=Path(__file__).resolve().parents[1]
    runner=(root/"selenium_pipeline/runner.py").read_text(encoding="utf8")
    src=(root/"selenium_pipeline/vendor_template_v2/gen_script_selenium_v15.py").read_text(encoding="utf8")
    assert '--communication-mode' in runner
    assert 'choices=("selenium",)' in runner
    assert 'policy.plan("narration")' in src
    assert 'require_paid_gemini_api("narration")' in src
    from selenium_pipeline.runner import _needs_browser
    from selenium_pipeline.communication_policy import resolve_mode
    with patch.dict("os.environ",{"MICROGEN_COMMUNICATION_MODE":"selenium"}):
        assert _needs_browser("narration") is True
    for mode in ("api","fallback"):
        with patch.dict("os.environ",{"MICROGEN_COMMUNICATION_MODE":mode}):
            with pytest.raises(ValueError,match="SELENIUM_ONLY"):
                resolve_mode()
