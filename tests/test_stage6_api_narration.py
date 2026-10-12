"""Stage 6: Gemini Flash API narration transport and fail-closed validation.

API client is mocked; no live Gemini calls or browser sessions in tests.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from selenium_pipeline import narration_api


def _pdf_inputs(tmp_path: Path):
    slide = tmp_path / "slides.pdf"
    source = tmp_path / "source.pdf"
    prompt = tmp_path / "gen_script_prompt_v10_rendered.txt"
    slide.write_bytes(b"%PDF-1.7\nslide example")
    source.write_bytes(b"%PDF-1.7\nsource example")
    prompt.write_text("Speak math in plain English. Every slide gets one block.")
    return slide, source, prompt


def _script(slides=2):
    return "".join(
        f"**Slide {i} [40 sec]:**\n" +
        ("Physics narration text with clear words and explanations. " * 6) + "\n"
        for i in range(1, slides + 1)
    )


def test_header_gate_rejects_missing_or_duplicate_blocks():
    narration_api.validate_raw_script(_script(2), 2)
    with pytest.raises(ValueError, match="blocks invalid"):
        narration_api.validate_raw_script(_script(2) + _script(1), 2)
    with pytest.raises(ValueError, match="blocks invalid"):
        narration_api.validate_raw_script(_script(1), 2)
    with pytest.raises(ValueError, match="empty or suspiciously short"):
        narration_api.validate_raw_script("OK", 2)


def test_api_includes_both_pdfs_and_exact_rendered_prompt(tmp_path):
    slide, source, prompt = _pdf_inputs(tmp_path)
    recorded = {}
    response = SimpleNamespace(text=_script(2),
                               candidates=[SimpleNamespace(finish_reason="STOP")])

    class FakeModel:
        def generate_content(self, **kwargs):
            recorded.update(kwargs)
            return response

    fake_client = SimpleNamespace(models=FakeModel())

    def fake_failover(factory, operation, **kwargs):
        return operation(fake_client)

    with patch("gemini_keys.call_with_client_failover", side_effect=fake_failover):
        result = narration_api.request_narration(slide, source, prompt, "Do the narration.")
    assert result == response.text
    assert recorded["model"] == "gemini-3.8-flash"
    parts = recorded["contents"]
    assert len(parts) == 4
    assert parts[2].inline_data.mime_type == "application/pdf"
    assert parts[3].inline_data.mime_type == "application/pdf"
    assert parts[2].inline_data.data == slide.read_bytes()
    assert parts[3].inline_data.data == source.read_bytes()
    assert "Speak math in plain English" in parts[1].text
    assert "Do the narration." in parts[0].text


def test_api_refuses_nonflash_model_and_missing_source(tmp_path):
    slide, source, prompt = _pdf_inputs(tmp_path)
    with pytest.raises(ValueError, match="non-Flash"):
        narration_api.request_narration(slide, source, prompt, "Do the narration.", model="gemini-3.1-pro")
    source.unlink()
    with pytest.raises(ValueError, match="Missing"):
        narration_api.request_narration(slide, source, prompt, "Do the narration.")


def test_api_refuses_truncated_answer_without_publish(tmp_path):
    slide, source, prompt = _pdf_inputs(tmp_path)
    response = SimpleNamespace(text=_script(1),
                               candidates=[SimpleNamespace(finish_reason="MAX_TOKENS")])
    fake_client = SimpleNamespace(models=SimpleNamespace(
        generate_content=lambda **kwargs: response))
    with patch("gemini_keys.call_with_client_failover",
               side_effect=lambda factory, op, **kwargs: op(fake_client)):
        with pytest.raises(RuntimeError, match="did not finish normally"):
            narration_api.request_narration(slide, source, prompt, "Do the narration.")


def test_cli_stages_only_valid_full_answer(tmp_path):
    slide, source, prompt = _pdf_inputs(tmp_path)
    instr = tmp_path / "request.txt"
    instr.write_text("Use slides first.")
    output = tmp_path / "narration_api_response.txt"
    args = ["--slides", str(slide), "--source", str(source),
            "--prompt", str(prompt), "--instruction-file", str(instr),
            "--output", str(output), "--expected-slides", "2"]
    with patch.object(narration_api, "request_narration", return_value=_script(1)):
        with pytest.raises(ValueError, match="blocks invalid"):
            narration_api.main(args)
    assert not output.exists()
    assert output.with_suffix(".rejected.txt").exists()
    with patch.object(narration_api, "request_narration", return_value=_script(2)):
        assert narration_api.main(args) == 0
    assert output.read_text().count("**Slide ") == 2


def test_production_launcher_and_runner_default_to_api():
    repo = Path(__file__).resolve().parents[1]
    ps = (repo / "operations" / "Start-MicroGen_AI_Web.ps1").read_text(encoding="utf-8-sig")
    runner = (repo / "selenium_pipeline" / "runner.py").read_text(encoding="utf-8-sig")
    vendor = (repo / "selenium_pipeline" / "vendor_template_v2" /
              "gen_script_selenium_v15.py").read_text(encoding="utf-8-sig")
    assert "$env:MICROGEN_NARRATION_BACKEND = 'api'" in ps
    assert '"MICROGEN_NARRATION_BACKEND"' in runner
    assert 'if backend == "api":' in vendor
    assert 'request_script_api_once(revised, slide_count)' in vendor
    assert 'if backend == "ui":' in vendor
