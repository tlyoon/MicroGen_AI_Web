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
    # Selenium is the new Phase 1 default; API-only must not touch Chrome.
    monkeypatch.delenv("MICROGEN_COMMUNICATION_MODE", raising=False)
    assert _needs_browser("figures")
    assert _needs_browser("slides")
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", "api")
    assert not _needs_browser("figures")
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", "fallback")
    assert not _needs_browser("figures")  # lazy browser initialization
    assert not _needs_browser("narration")  # fallback lazily opens UI
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", "selenium")
    assert _needs_browser("narration")
    monkeypatch.setenv("MICROGEN_FIGURE_MAPPING_BACKEND", "api")
    assert _needs_browser("figures")  # old per-stage backend cannot force API


def test_api_mapping_normalizes_mathematical_figure_filenames():
    result = validate_mapping(
        'fig_1.png : "Unlabeled image" : graph of y = sec^-1 x.png',
        paths("fig_1.png"),
    )
    assert result == [
        'fig_1.png : "Unlabeled image" : graph of y equals sec power -1 x.png'
    ]


def test_api_mapping_normalized_filename_still_rejects_traversal():
    with pytest.raises(ValueError):
        validate_mapping(
            'fig_1.png : "Unlabeled image" : ../graph of y = sec^-1 x.png',
            paths("fig_1.png"),
        )
