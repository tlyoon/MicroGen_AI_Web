from pathlib import Path
import pymupdf
from selenium_pipeline.narration_repair_plan import plan_repair

def make_pdf(path, text):
    d=pymupdf.open()
    d.new_page().insert_text((60,60),text)
    d.save(path)
    d.close()

def test_changed_pdf_requires_semantic_review(tmp_path):
    make_pdf(tmp_path/"before.pdf","Before")
    make_pdf(tmp_path/"slides.pdf","After")
    report=plan_repair(tmp_path,tmp_path/"before.pdf")
    assert report["semantic_review_required"]
    assert report["video_publication_allowed"] is False
    assert report["automatic_narration_regeneration_performed"] is False
    assert (tmp_path/".microgen_figure_candidates/narration_repair_plan.json").exists()

def test_unchanged_pdf_does_not_approve_video(tmp_path):
    make_pdf(tmp_path/"slides.pdf","Same")
    report=plan_repair(tmp_path,tmp_path/"slides.pdf")
    assert not report["semantic_review_required"]
    assert report["video_publication_allowed"] is False
