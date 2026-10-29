import unittest,tempfile
from pathlib import Path
import pymupdf
from selenium_pipeline.figure83_visual_review_overlay import (
 validated_review_boxes,render_review_preview)
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired,_sha

def packet(sha):
    return {"status":"ORIGINAL_FIGURE83_REVIEW_ONLY",
      "slides_sha256":sha,"slide_page":5,"student_publication_authorized":False,
      "paid_tts_authorized":False,"review_utterances":[
      {"utterance_id":"u1","candidate_full_expression_pdf_bbox_pt":[15,20,45,40]},
      {"utterance_id":"u2","candidate_full_expression_pdf_bbox_pt":None}]}
class VisualReviewOnlyTests(unittest.TestCase):
    def test_malformed_geometry_and_permission_rejected(self):
        p=packet("a"*64)
        self.assertEqual(len(validated_review_boxes(p,page_width=100,page_height=100)),1)
        p["review_utterances"][0]["candidate_full_expression_pdf_bbox_pt"]=[5,5,120,30]
        with self.assertRaises(FigureIdentityReviewRequired):
            validated_review_boxes(p,page_width=100,page_height=100)
        p=packet("a"*64);p["student_publication_authorized"]=True
        with self.assertRaises(FigureIdentityReviewRequired):
            validated_review_boxes(p,page_width=100,page_height=100)
    def test_render_is_read_only_exclusive_and_not_a_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);teach=base/"teaching";teach.mkdir()
            slides=teach/"slides.pdf"
            d=pymupdf.open()
            for _ in range(5):d.new_page(width=120,height=110)
            d.save(slides);d.close()
            original_sha=_sha(slides)
            result=render_review_preview(slides=slides,packet=packet(original_sha),
                                         output=base/"review.png")
            self.assertEqual(result["review_overlay_count"],1)
            self.assertFalse(result["student_publication_authorized"])
            self.assertEqual(_sha(slides),original_sha)
            with self.assertRaises(FileExistsError):
                render_review_preview(slides=slides,packet=packet(original_sha),
                                      output=base/"review.png")
            with self.assertRaises(FigureIdentityReviewRequired):
                render_review_preview(slides=slides,packet=packet(original_sha),
                                      output=teach/"preview.png")
