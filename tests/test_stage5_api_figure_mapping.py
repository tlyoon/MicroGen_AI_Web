"""Offline regression coverage for the live-tested Gemini Flash figure API path."""
from pathlib import Path

import pytest

from selenium_pipeline.figure_mapping_api import validate_mapping
from selenium_pipeline.runner import _needs_browser


def paths(*names):
    return [Path(name) for name in names]


def test_exact_ordered_source_figure_mapping():
    lines = validate_mapping(
        'fig_3.png : "Figure 9.23" : Figure 9.23.png\n'
        'fig_1.png : "Unlabeled image" : laboratory setup.png\n',
        paths("fig_3.png", "fig_1.png"),
    )
    assert len(lines) == 2
    assert 'Figure 9.23' in lines[0]


@pytest.mark.parametrize("text", [
    "",
    'fig_1.png : "Figure 1.2" : Figure 1.2.png',
    'fig_1.png : "Figure 1.2" : Figure 1.2.png\n'
    'fig_1.png : "Figure 1.3" : Figure 1.3.png',
    'fig_3.png : "Figure 1.2" : Figure 1.2.png\n'
    'fig_1.png : "Figure 1.3" : Figure 1.3.png',
    'fig_1.png : "Unknown" : Unknown.png\n'
    'fig_3.png : "Figure 1.3" : Figure 1.3.png',
    'fig_1.png : "Figure" : Figure.png\n'
    'fig_3.png : "Figure 1.3" : Figure 1.3.png',
    'fig_1.png : "Figure 1.2" : ../escape.png\n'
    'fig_3.png : "Figure 1.3" : Figure 1.3.png',
])
def test_api_mapping_rejects_missing_hallucinated_or_unsafe(text):
    with pytest.raises(ValueError):
        validate_mapping(text, paths("fig_1.png", "fig_3.png"))


def test_api_mapping_never_claims_validity_without_crops():
    with pytest.raises(ValueError):
        validate_mapping('fig_1.png : "Figure 1.2" : Figure 1.2.png', [])


def test_api_figure_backend_bypasses_browser(monkeypatch):
    monkeypatch.delenv("MICROGEN_FIGURE_MAPPING_BACKEND", raising=False)
    assert not _needs_browser("figures")
    assert not _needs_browser("slides")
    assert _needs_browser("narration")
    monkeypatch.setenv("MICROGEN_FIGURE_MAPPING_BACKEND", "browser")
    assert _needs_browser("figures")
    monkeypatch.setenv("MICROGEN_SLIDES_BACKEND", "browser")
    assert _needs_browser("slides")
