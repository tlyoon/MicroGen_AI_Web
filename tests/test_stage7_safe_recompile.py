"""Isolated, opt-in legacy Beamer footer repair regression tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pymupdf
import pytest

from selenium_pipeline.latex_footer import incorrect_page_totals
from selenium_pipeline.recompile_legacy_slides import compare_slide_content, repair


def _pdf(path: Path, pages: int, denominator: int, body="Angular momentum and torque"):
    with pymupdf.open() as doc:
        for index in range(1, pages + 1):
            page = doc.new_page()
            page.insert_text((page.rect.width - 52, 10), f"{index} / {denominator}")
            page.insert_text((72, 88), body)
        doc.save(path)


def _job(tmp_path):
    f = tmp_path / "source_tree" / "11" / "11.1"
    f.mkdir(parents=True)
    _pdf(f / "source.pdf", 3, 3, "Angular momentum and torque describe rotation")
    _pdf(f / "slides.pdf", 3, 1)
    (f / "slides.tex").write_text(r"\documentclass{beamer}", encoding="utf-8")
    return f


def _fake_compile(staging):
    _pdf(staging / "slides.pdf", 3, 3)
    return staging / "slides.pdf"


def test_footer_only_text_comparison_rejects_science_drift(tmp_path):
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    _pdf(a, 4, 1)
    _pdf(b, 4, 4)
    assert compare_slide_content(a, b) == 4
    b.unlink()
    _pdf(b, 4, 4, "Entirely different derivation")
    with pytest.raises(ValueError, match="non-footer PDF text"):
        compare_slide_content(a, b)


def test_dry_run_is_read_only_then_apply_archives_old_pdf(tmp_path):
    f = _job(tmp_path)
    old = (f / "slides.pdf").read_bytes()
    source = (f / "source.pdf").read_bytes()
    local = tmp_path / "local_cache"
    with patch("selenium_pipeline.recompile_legacy_slides._two_pass_compile", side_effect=_fake_compile):
        dry = repair(f, cache_root=local)
        assert dry["status"] == "eligible"
        assert (f / "slides.pdf").read_bytes() == old
        assert not (f / ".history").exists()
        changed = repair(f, cache_root=local, apply=True)
    assert changed["status"] == "repaired"
    assert (f / "source.pdf").read_bytes() == source
    assert (f / "slides.pdf").read_bytes() != old
    assert incorrect_page_totals(f / "slides.pdf") == []
    assert Path(changed["backup"]).read_bytes() == old
    assert json.loads((Path(changed["backup"]).parent / "repair.json").read_text())["nonfooter_content_unchanged"]
    assert repair(f, cache_root=local)["status"] == "already_correct"


def test_refuses_any_published_downstream_artifact(tmp_path):
    f = _job(tmp_path)
    for name in ("script.txt", "slides.mp4", "slide1.wav", ".microgen_completion.json"):
        file = f / name
        file.write_bytes(b"already published")
        with pytest.raises(ValueError, match="downstream"):
            repair(f, cache_root=tmp_path / "cache", apply=True)
        file.unlink()
    assert not (f / ".history").exists()


def test_refuses_missing_required_figures_and_unsafe_cache_location(tmp_path):
    f = _job(tmp_path)
    (f / "slides.tex").write_text(r"\includegraphics{Figure_11_99.png}")
    with pytest.raises(ValueError, match="graphic"):
        repair(f, cache_root=tmp_path / "cache")
    (f / "slides.tex").write_text(r"\documentclass{beamer}")
    with pytest.raises(ValueError, match="outside"):
        repair(f, cache_root=f / "nested")
