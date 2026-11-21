"""Opening title is source-bound to both generated Beamer and rendered PDF."""
from pathlib import Path
import pytest
fitz=pytest.importorskip("fitz")
from selenium_pipeline.vendor_template_v2.gen_script_selenium_v15 import extract_exact_slide_titles

def make_pdf(path: Path, texts):
 doc=fitz.open()
 for lines in texts:
  p=doc.new_page()
  for i,line in enumerate(lines):p.insert_text((40,90+i*24),line,fontsize=12)
 doc.save(path);doc.close()

def test_source_verified_wrapped_title_keeps_second_line(tmp_path):
 pdf=tmp_path/"slides.pdf"
 make_pdf(pdf,[["1 / 1","Section 10.8: Energy Considerations in Rotational",
                "Motion"],["2 / 2","Outline"]])
 (tmp_path/"slides.tex").write_text(
  r"\title{Section 10.8: Energy Considerations in Rotational Motion}"+"\n","utf8")
 assert extract_exact_slide_titles(pdf)==[
  "Section 10.8: Energy Considerations in Rotational Motion","Outline"]

def test_source_tex_not_rendered_does_not_override_pdf(tmp_path):
 pdf=tmp_path/"slides.pdf"
 make_pdf(pdf,[["1 / 1","Actual Visible Title","Unrelated Body"]])
 (tmp_path/"slides.tex").write_text(r"\title{Invented Alternative}",encoding="utf8")
 assert extract_exact_slide_titles(pdf)==["Actual Visible Title"]

def test_no_tex_file_returns_original_pdf_only_first_candidate(tmp_path):
 pdf=tmp_path/"slides.pdf"
 make_pdf(pdf,[["1 / 1","Source Verified Title","Description"]])
 assert extract_exact_slide_titles(pdf)==["Source Verified Title"]

def test_latex_math_macro_title_does_not_override_pdf(tmp_path):
 pdf=tmp_path/"slides.pdf"
 make_pdf(pdf,[["1 / 1","Energy","Motion"]])
 (tmp_path/"slides.tex").write_text(r"\title{Energy \alpha Motion}",encoding="utf8")
 assert extract_exact_slide_titles(pdf)==["Energy"]
