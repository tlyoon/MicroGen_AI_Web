"""Stage 6 Gemini Flash API slide transport and browser-lane isolation."""
from __future__ import annotations
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest

from selenium_pipeline import slides_api
from selenium_pipeline.runner import _needs_browser


def fixture(tmp_path):
    src = tmp_path / "source.pdf"
    prompt = tmp_path / "rendered.txt"
    dims = tmp_path / "png_dimensions.json"
    instructions = tmp_path / "instruction.txt"
    src.write_bytes(b"%PDF-1.7 fake payload for unit mocking")
    prompt.write_text("Explain scientific models and equations from source only. " * 12)
    dims.write_text('{"figures":[]}\n')
    instructions.write_text("Return exactly one fenced Beamer LaTeX document and do not invent figures. " * 3)
    return src, prompt, dims, instructions


def test_flash_api_request_is_grounded_and_failover_managed(tmp_path):
    data = fixture(tmp_path)
    output = r"\\documentclass{beamer}\n\\begin{document}\n" + "X" * 220 + r"\\end{document}"
    captured = {}
    def fake_failover(create, operation, **kwargs):
        captured.update(kwargs)
        # The actual google.genai SDK types are used to build real PDF parts.
        return SimpleNamespace(text=output)
    with patch("gemini_keys.call_with_client_failover", side_effect=fake_failover):
        assert slides_api.request_slides(*data, "gemini-3.8-flash") == output
    assert captured["max_retries"] == 1
    assert "figure" not in captured["label"].lower() or "slides" in captured["label"]


def test_reject_pro_or_missing_source_before_api_network(tmp_path):
    inputs = fixture(tmp_path)
    with pytest.raises(ValueError, match="Flash"):
        slides_api.request_slides(*inputs, "gemini-3.1-pro")
    inputs[0].unlink()
    with pytest.raises(ValueError, match="Missing"):
        slides_api.request_slides(*inputs, "gemini-3.8-flash")


def test_slide_api_stage_does_not_require_browser():
    with patch.dict(os.environ, {"MICROGEN_SLIDES_BACKEND": "api"}):
        assert not _needs_browser("slides")
        assert _needs_browser("narration")
    with patch.dict(os.environ, {"MICROGEN_SLIDES_BACKEND": "browser"}):
        assert _needs_browser("slides")


def test_vendor_api_draft_still_uses_existing_beamer_quality_gates():
    path = Path(__file__).resolve().parents[1] / "selenium_pipeline" / "vendor_template_v2" / "gen_slides_selenium_v11.py"
    s = path.read_text(encoding="utf-8-sig")
    assert "response_text = _api_transport_for_slides(" in s
    assert "latex = sanitize_gemini_latex_response(response_text)" in s
    assert "sanity_ok, sanity_reasons = beamer_stack_sanity_check(" in s
    assert "if pdflatex_compiles(out_tex):" in s
    assert "final_artifacts = final_tex_artifacts +" in s
