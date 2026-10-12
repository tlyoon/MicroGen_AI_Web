"""Offline fault injection for Phase 1B slides transport and API grounding."""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from selenium_pipeline import slides_api
from selenium_pipeline.communication_policy import CommunicationPolicy, CommunicationMode
from selenium_pipeline.runner import _needs_browser, _needs_api_python_for_stages

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "selenium_pipeline/vendor_template_v2/gen_slides_selenium_v11.py"
LATEX = r"\documentclass{beamer}\begin{document}\begin{frame}Test\end{frame}\end{document}"


def source_inputs(tmp_path):
    src = tmp_path / "source.pdf"
    p = tmp_path / "gen_slides_prompt_v23_rendered.txt"
    metadata = tmp_path / "png_dimensions.json"
    src.write_bytes(b"%PDF-1.7\nsource")
    p.write_text("Use only figures in the attached source PDF.")
    metadata.write_text('{"Figure 2.10.png":{"width":1200,"height":400}}')
    return src, p, metadata


def test_api_grounded_in_source_and_dimension_metadata(tmp_path):
    src, prompt, dims = source_inputs(tmp_path)
    seen = {}

    class Model:
        def generate_content(self, **kwargs):
            seen.update(kwargs)
            return SimpleNamespace(
                candidates=[SimpleNamespace(finish_reason="STOP")],
                text=LATEX,
            )

    with patch("gemini_keys.call_with_client_failover",
               side_effect=lambda factory, request, **kwargs:
                   request(SimpleNamespace(models=Model()))):
        assert slides_api.request_slides(src, prompt, dims, "Use exact LaTeX") == LATEX
    parts = seen["contents"]
    assert seen["model"] == "gemini-3.8-flash"
    assert len(parts) == 3
    assert parts[2].inline_data.mime_type == "application/pdf"
    assert parts[2].inline_data.data == src.read_bytes()
    assert "Figure 2.10.png" in parts[1].text
    assert "Use exact LaTeX" in parts[0].text


def test_api_rejects_bad_model_missing_pdf_and_truncated_reply(tmp_path):
    src, prompt, dims = source_inputs(tmp_path)
    with pytest.raises(ValueError, match="other than vetted Flash"):
        slides_api.request_slides(src, prompt, dims, "Beamer", model="gemini-3.1-pro")
    src.unlink()
    with pytest.raises(ValueError, match="missing"):
        slides_api.request_slides(src, prompt, dims, "Beamer")
    src.write_bytes(b"%PDF-1.7\nsource")
    truncated = SimpleNamespace(
        text=LATEX, candidates=[SimpleNamespace(finish_reason="MAX_TOKENS")]
    )
    with patch("gemini_keys.call_with_client_failover",
               side_effect=lambda factory, request, **kwargs:
                   request(SimpleNamespace(models=SimpleNamespace(
                       generate_content=lambda **kwargs: truncated)))):
        with pytest.raises(RuntimeError, match="did not finish normally"):
            slides_api.request_slides(src, prompt, dims, "Beamer")


def test_api_cli_publishes_only_raw_response_not_slides_pdf(tmp_path):
    src, prompt, dims = source_inputs(tmp_path)
    instruction = tmp_path / "instruction.txt"
    instruction.write_text("Strict LaTeX format.")
    out = tmp_path / "api_response.txt"
    args = [
        "--source", str(src), "--prompt", str(prompt),
        "--dimensions", str(dims), "--instruction-file", str(instruction),
        "--output", str(out),
    ]
    with patch.object(slides_api, "request_slides", return_value=LATEX):
        assert slides_api.main(args) == 0
    assert out.read_text().strip() == LATEX
    assert not (tmp_path / "slides.tex").exists()
    assert not (tmp_path / "slides.pdf").exists()
    out.unlink()
    with patch.object(slides_api, "request_slides", side_effect=RuntimeError("timeout")):
        with pytest.raises(RuntimeError, match="timeout"):
            slides_api.main(args)
    assert not out.exists()


def _vendor_slide_function(monkeypatch):
    tree = ast.parse(VENDOR.read_text(encoding="utf-8-sig"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "generate_slides_tex")
    compiled = compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                       str(VENDOR), "exec")
    import os
    ns = {
        "Path": Path, "os": os, "log": lambda *args, **kwargs: None,
        "find_citation_artifacts": lambda text: [],
        "sanitize_gemini_latex_response": lambda x: x,
        "normalize_unicode_to_latex": lambda x: x,
        "beamer_stack_sanity_check": lambda text, folder, **kwargs:
            (text.startswith(r"\documentclass"), ["Not a Beamer document"]),
    }
    exec(compiled, ns)
    return ns["generate_slides_tex"]


@pytest.mark.parametrize("mode,fail_selenium,expected", [
    ("selenium", 0, ["selenium"]),
    ("selenium", 2, ["selenium"] * 3),
    ("api", 0, ["api"]),
    ("fallback", 0, ["selenium"]),
    ("fallback", 3, ["selenium"] * 3 + ["api"]),
])
def test_actual_slide_qa_stops_on_valid_backend_response(
    tmp_path, monkeypatch, mode, fail_selenium, expected
):
    src, prompt, dims = source_inputs(tmp_path)
    policy = CommunicationPolicy(CommunicationMode(mode))
    calls = []
    def source(backend, instruction):
        calls.append(backend)
        if backend == "selenium" and calls.count("selenium") <= fail_selenium:
            raise RuntimeError("Gemini composer or response stalled")
        return LATEX
    create = _vendor_slide_function(monkeypatch)
    path = tmp_path / "slides.tex"
    assert create(None, src, prompt, dims, path, 30,
                  response_provider=source, communication_plan=policy.plan("slides")) == path
    assert calls == expected
    assert path.read_text().strip() == LATEX


def test_invalid_slide_response_triggers_fallback_without_false_completion(tmp_path, monkeypatch):
    src, prompt, dims = source_inputs(tmp_path)
    calls = []
    def source(backend, instruction):
        calls.append(backend)
        return "I cannot perform the requested slide generation." if backend == "selenium" else LATEX
    create = _vendor_slide_function(monkeypatch)
    path = tmp_path / "slides.tex"
    create(None, src, prompt, dims, path, 30, response_provider=source,
           communication_plan=CommunicationPolicy(CommunicationMode.FALLBACK).plan("slides"))
    assert calls == ["selenium"] * 3 + ["api"]
    assert path.read_text().strip() == LATEX


def test_all_invalid_slide_responses_leave_no_accepted_output(tmp_path, monkeypatch):
    src, prompt, dims = source_inputs(tmp_path)
    create = _vendor_slide_function(monkeypatch)
    path = tmp_path / "slides.tex"
    with pytest.raises(RuntimeError, match="Failed to produce a valid Beamer"):
        create(None, src, prompt, dims, path, 30, response_provider=lambda *a: "No",
               communication_plan=CommunicationPolicy(CommunicationMode.FALLBACK).plan("slides"))
    assert not path.exists()


def test_api_slide_stage_never_eagerly_launches_browser(monkeypatch):
    for mode, browser, sdk in [("selenium", True, False), ("api", False, True),
                               ("fallback", False, True)]:
        monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", mode)
        assert _needs_browser("slides") is browser
        assert _needs_api_python_for_stages(["slides"]) is sdk


def test_vendor_cli_does_not_unconditionally_launch_chrome():
    src = VENDOR.read_text(encoding="utf-8-sig")
    assert 'if __name__ == "__main__":' in src
    assert 'raise SystemExit(main())' in src
    assert 'policy.plan("slides")' in src
    assert "request_slides_api_once(" in src
