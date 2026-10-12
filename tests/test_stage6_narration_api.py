"""Stage 6 opt-in Flash narration API retains deterministic downstream guards."""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from selenium_pipeline import narration_api
from selenium_pipeline.runner import _needs_browser


def make_inputs(tmp_path):
    slides = tmp_path / "slides.pdf"
    source = tmp_path / "source.pdf"
    prompt = tmp_path / "rendered.txt"
    instruction = tmp_path / "instructions.txt"
    slides.write_bytes(b"%PDF-1.7 dummy slide deck only for mocking")
    source.write_bytes(b"%PDF-1.7 dummy source only for mocking")
    prompt.write_text("Narrate each slide from exact title and visible physics context. " * 7)
    instruction.write_text("Return precisely one numbered narration block for every slide. " * 4)
    return slides, source, prompt, instruction


def test_narration_request_is_flash_only_and_failover_managed(tmp_path):
    data = make_inputs(tmp_path)
    response = "**Slide 1 [50 sec]:**\n" + "Source-grounded teaching narration. " * 14
    called = {}
    def fake_failover(create, operation, **kwargs):
        called.update(kwargs)
        return SimpleNamespace(text=response)
    with patch("gemini_keys.call_with_client_failover", side_effect=fake_failover):
        assert narration_api.request_narration(*data, "gemini-3.8-flash") == response
    assert called["max_retries"] == 1


def test_narration_api_rejects_pro_and_missing_pdf(tmp_path):
    data = make_inputs(tmp_path)
    with pytest.raises(ValueError, match="Flash"):
        narration_api.request_narration(*data, "gemini-3.1-pro")
    data[0].unlink()
    with pytest.raises(ValueError, match="Missing"):
        narration_api.request_narration(*data, "gemini-3.8-flash")


def test_api_narration_never_uses_chrome():
    with patch.dict(os.environ, {"MICROGEN_NARRATION_BACKEND": "api"}):
        assert not _needs_browser("narration")
    with patch.dict(os.environ, {"MICROGEN_NARRATION_BACKEND": "browser"}):
        assert _needs_browser("narration")


def test_api_narration_retains_exact_script_and_repair_loop():
    source = Path(__file__).resolve().parents[1] / "selenium_pipeline" / "vendor_template_v2" / "gen_script_selenium_v15.py"
    text = source.read_text(encoding="utf-8-sig")
    for requirement in (
        'response = _request_script_via_api(',
        'sanitize_and_rebuild_script(response, exact_titles)',
        'force_exact_titles_after_postprocessing(exact_titles)',
        'warnings = collect_all_warnings(OUT_SCRIPT, SLIDES_PDF, exact_titles)',
        'Preserved rejected narration as',
    ):
        assert requirement in text
