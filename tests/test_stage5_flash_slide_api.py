"""Stage 5: API slide drafts may be published only by the original Beamer gates."""
import ast
from pathlib import Path

import pytest

from selenium_pipeline.runner import _needs_browser
from selenium_pipeline.slide_generation_api import image_inputs, make_request


def test_no_browser_for_default_api_slides(monkeypatch):
    monkeypatch.delenv("MICROGEN_SLIDES_BACKEND", raising=False)
    assert not _needs_browser("slides")
    assert _needs_browser("narration")
    monkeypatch.setenv("MICROGEN_SLIDES_BACKEND", "browser")
    assert _needs_browser("slides")


def test_slide_api_rejects_missing_source_before_sdk(tmp_path):
    prompt = tmp_path / "prompt.txt"
    metadata = tmp_path / "figures.json"
    prompt.write_text("Create slide deck", encoding="utf-8")
    metadata.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        make_request(tmp_path / "missing.pdf", prompt, metadata, tmp_path, "gemini-3.8-flash")


def test_slide_api_rejects_oversized_source_before_sdk(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"p" * 20_000_001)
    prompt = tmp_path / "prompt.txt"
    metadata = tmp_path / "figures.json"
    prompt.write_text("Create", encoding="utf-8")
    metadata.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="20 MB"):
        make_request(source, prompt, metadata, tmp_path, "gemini-3.8-flash")


def test_slide_api_rejects_silent_figure_omission(tmp_path):
    (tmp_path / "Figure 1.png").write_bytes(b"abc")
    (tmp_path / "Figure 2.png").write_bytes(b"def")
    with pytest.raises(ValueError, match="silent truncation"):
        image_inputs(tmp_path, limit=1)


def test_vendor_api_slides_still_run_compiler_and_citation_gate():
    path = (Path(__file__).resolve().parents[1] / "selenium_pipeline" /
            "vendor_template_v2" / "gen_slides_selenium_v11.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fns = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    generate = ast.unparse(fns["generate_slides_tex"])
    main = ast.unparse(fns["main"])
    assert 'slide_generation_api.py' in generate
    assert "beamer_stack_sanity_check" in generate
    assert generate.index("slide_generation_api.py") < generate.index("beamer_stack_sanity_check")
    assert 'out_tex.write_text' in generate
    assert "pdflatex_compiles" in main
    assert "pdf_citation_artifacts" in main
