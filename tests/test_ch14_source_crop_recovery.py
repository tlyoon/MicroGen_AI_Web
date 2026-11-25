"""Real Serway Chapter14 source-PDF figure recovery: strict source/panel provenance."""
from pathlib import Path
import hashlib
import pytest
from selenium_pipeline.source_caption_figure_chain_v1 import (
  printed_source_captions, verify_figure_crops,
  verify_latex_figure_chain, verify_rendered_pdf_source_figures,
  missing_required_latex_figures,
)
ROOT=Path(r"G:\My Drive\Serway\Serway_8_14\14")
COUNTS={"14.1":2,"14.2":4,"14.3":3,"14.4":6,
        "14.5":6,"14.6":3,"14.7":3,"14.8":1}

@pytest.mark.parametrize("subsection,count",list(COUNTS.items()))
def test_exact_original_source_printed_figure_coverage(subsection,count):
    f=ROOT/subsection
    if not f.is_dir():pytest.skip("Original textbook PDF not mounted in public CI")
    src=f/"source.pdf"
    src_sha=hashlib.sha256(src.read_bytes()).hexdigest()
    rows=printed_source_captions(src)
    assert len(rows)==count
    report=verify_figure_crops(f)
    assert report["status"]=="ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED"
    assert report["figure_count"]==count
    assert report["source_sha256"]==src_sha
    assert sum(len(row["expected_panels"]) for row in rows)>=0
    assert hashlib.sha256(src.read_bytes()).hexdigest()==src_sha

@pytest.mark.parametrize("subsection",["14.1","14.2","14.3","14.4","14.5","14.6","14.8"])
def test_rendered_slides_have_exact_visible_source_pixels(subsection):
    f=ROOT/subsection
    if not f.is_dir():pytest.skip("Original textbook not mounted")
    report=verify_rendered_pdf_source_figures(f)
    assert report["figures_verified"]==COUNTS[subsection]
    assert report["source_pixels_unchanged"]
    assert report["rasterized_page_visibility_verified"]
    assert not report["scientific_approval"]
    assert not report["student_publication_authorized"]

def test_hidden_source_images_cannot_pass_hard_gate():
    refs=["Figure 14.7.png","Figure 14.8.png"]
    latex=r"\\IfFileExists{Figure 14.7.png}{\\includegraphics{Figure 14.7.png}}{}" + "\n" + r"\\includegraphics{Figure 14.8.png}"
    result=missing_required_latex_figures(latex,refs)
    assert result["missing"]==[]
    assert result["guarded"]==["Figure 14.7.png"]

def test_missing_source_figure_cannot_pass_hard_gate():
    refs=["Figure 14.7.png","Figure 14.8.png","Figure 14.9.png"]
    latex=r"\\includegraphics{Figure 14.7.png}"+ "\n" + r"\\includegraphics{Figure 14.8.png}"
    result=missing_required_latex_figures(latex,refs)
    assert result["missing"]==["Figure 14.9.png"]
