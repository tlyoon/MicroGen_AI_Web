"""Regression suite for two-pass Beamer page-total publication."""
from pathlib import Path
import pymupdf
from selenium_pipeline.latex_footer import incorrect_page_totals, enforce_correct_page_totals
from selenium_pipeline.runner import check_valid


def _deck(path, n, wrong=False):
    with pymupdf.open() as d:
        for i in range(1, n+1):
            page=d.new_page()
            total=1 if wrong else n
            page.insert_text((72, 72), f"{i} / {total}")
            page.insert_text((72, 100), "Physics example with angular acceleration.")
        d.save(path)


def test_rejects_single_pass_footer_but_accepts_correct_page_count(tmp_path):
    file=tmp_path/"slides.pdf"
    _deck(file, 4, wrong=True)
    wrong=incorrect_page_totals(file)
    assert {x["slide"] for x in wrong}=={1,4}
    assert "4 / 1" in str(wrong)
    try:
        enforce_correct_page_totals(file)
    except ValueError as e:
        assert "Recompile" in str(e)
    else:
        raise AssertionError("Must block PDF with incorrect total frame count")

    assert not check_valid("slides",tmp_path)
    file.unlink()
    _deck(file, 4, wrong=False)
    assert incorrect_page_totals(file)==[]
    enforce_correct_page_totals(file)
    assert check_valid("slides",tmp_path)


def test_detects_only_numbered_footers_not_bare_fractions(tmp_path):
    path=tmp_path/"physics.pdf"
    with pymupdf.open() as d:
        for i in range(4):
            page=d.new_page()
            page.insert_text((72,72),"1 / 2")
        d.save(path)
    assert incorrect_page_totals(path)==[]


def test_legacy_vendor_runs_two_compiler_passes_and_checks_total():
    root=Path(__file__).resolve().parents[1]
    script=(root/"selenium_pipeline"/"vendor_template_v2"/"gen_slides_selenium_v11.py")
    text=script.read_text(encoding="utf-8-sig")
    assert 'for pass_number in (1, 2):' in text
    assert 'incorrect Beamer page total' in text
    assert 'Final two-pass LaTeX compilation or footer verification failed' in text


def test_source_to_slide_screen_flags_wrong_footer(tmp_path):
    from selenium_pipeline.scientific_content_audit import inspect
    root=tmp_path/"8"/"8.4";root.mkdir(parents=True)
    _deck(root/"source.pdf",3,wrong=False)
    _deck(root/"slides.pdf",3,wrong=True)
    (root/"slides.tex").write_text(r"\documentclass{beamer}",encoding="utf-8")
    result=inspect(root)
    assert result["classification"]=="blocked"
    assert "incorrect_beamer_page_total" in {i["code"] for i in result["issues"]}
