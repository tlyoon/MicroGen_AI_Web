import unittest,tempfile
from pathlib import Path
import pymupdf
from selenium_pipeline.pdf_drawing_fallback_inventory import inventory_unmatched_pdf_visual_regions
from test_original_packet_evidence_audit import fixture
class DrawingCandidates(unittest.TestCase):
    def test_real_pdf_vector_path_suggests_region_not_math_semantics(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"f";p=fixture(root)
            with pymupdf.open(root/"slides.pdf") as d:
                page=d[0];s=page.new_shape()
                s.draw_rect(pymupdf.Rect(30,40,130,130));s.finish(color=(0,0,0));s.commit()
                d.save(root/"modified.pdf")
            (root/"slides.pdf").write_bytes((root/"modified.pdf").read_bytes())
            import hashlib
            p["original_slides_sha256"]=hashlib.sha256((root/"slides.pdf").read_bytes()).hexdigest()
            p["review_items"][0]["candidate_targets"]=[]
            r=inventory_unmatched_pdf_visual_regions(folder=root,packet=p)
            self.assertEqual(r["unmatched_utterance_count"],1)
            self.assertTrue(r["rows"][0]["actual_pdf_vector_regions"])
            self.assertFalse(r["semantic_matching_verified"])
    def test_no_unmatched_is_not_false_approval(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"f";p=fixture(root)
            r=inventory_unmatched_pdf_visual_regions(folder=root,packet=p)
            self.assertEqual(r["unmatched_utterance_count"],0)
            self.assertFalse(r["tts_authorized"])
