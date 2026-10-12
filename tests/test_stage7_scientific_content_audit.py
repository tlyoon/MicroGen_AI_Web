"""Offline regression tests for the read-only Stage 7 scientific-content screen."""
from __future__ import annotations

from pathlib import Path
import json

import pymupdf
import pytest

from selenium_pipeline.scientific_content_audit import inspect, inspect_campaign, main


def _pdf(path: Path, pages: list[str]):
    with pymupdf.open() as doc:
        for body in pages:
            page = doc.new_page()
            if body:
                page.insert_text((72, 72), body)
        doc.save(path)


def _job(tmp_path, chapter="8", subchapter="8.2"):
    folder = tmp_path / chapter / subchapter
    folder.mkdir(parents=True)
    _pdf(folder / "source.pdf", ["The electric field and a test charge exert an electric force. "
         "Electric field lines describe the field around a source charge. "
         "A test charge is affected by electric forces in the space."])
    _pdf(folder / "slides.pdf", ["The electric field exerts a force on a charge."])
    (folder / "slides.tex").write_text(r"\documentclass{beamer}", encoding="utf-8")
    return folder


def test_complete_textual_deck_is_screened_but_never_scientifically_certified(tmp_path):
    folder = _job(tmp_path)
    report = inspect(folder)
    assert report["slide_count"] == 1
    assert report["blockers"] == 0
    assert report["classification"] == "structurally_screened"
    assert report["scientific_correctness_certified"] is False


def test_missing_latex_figure_is_blocking_without_touching_source(tmp_path):
    folder = _job(tmp_path)
    tex = folder / "slides.tex"
    tex.write_text(r"\includegraphics{Figure_8_99.png}", encoding="utf-8")
    before = (folder / "slides.pdf").read_bytes()
    result = inspect(folder)
    assert "missing_latex_graphic" in {issue["code"] for issue in result["issues"]}
    assert result["classification"] == "blocked"
    assert before == (folder / "slides.pdf").read_bytes()


def test_truly_blank_pdf_page_is_blocking(tmp_path):
    folder = _job(tmp_path)
    _pdf(folder / "slides.pdf", ["One teaching slide.", ""])
    result = inspect(folder)
    assert result["slide_count"] == 2
    assert any(x["code"] == "blank_pdf_page" and x["slide"] == 2 for x in result["issues"])
    assert result["blockers"] >= 1


def test_content_overlap_is_review_not_science_approval(tmp_path):
    folder = _job(tmp_path)
    _pdf(folder / "slides.pdf", ["Geometry quadrilateral perimeter polygon diagonals angles."])
    result = inspect(folder)
    assert result["blockers"] == 0
    assert "low_textual_source_overlap" in {x["code"] for x in result["issues"]}
    assert result["classification"] == "review_required"


def test_real_source_root_scope_and_report_is_outside_source(tmp_path):
    root = tmp_path / "sources"
    good = _job(root)
    (root / "8" / "irrelevant").mkdir()
    report = inspect_campaign(root)
    assert report["total"] == 1
    out = tmp_path / "reports" / "stage7.json"
    assert main(["--source-root", str(root), "--expected", "1", "--report", str(out)]) == 0
    assert json.loads(out.read_text())["total"] == 1
    with pytest.raises(FileExistsError):
        main(["--source-root", str(root), "--report", str(out)])
    with pytest.raises(ValueError, match="outside"):
        main(["--folder", str(good), "--report", str(good / "quality.json")])


def test_source_pdf_is_never_changed_by_screening(tmp_path):
    folder = _job(tmp_path)
    source = folder / "source.pdf"
    data = source.read_bytes()
    for _ in range(2):
        inspect(folder)
    assert source.read_bytes() == data
    assert not list(folder.glob("*.json"))
