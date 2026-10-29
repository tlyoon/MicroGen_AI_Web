"""Untimed visual candidate pixel check on source-style PDF geometry."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

import pymupdf
from PIL import Image,ImageChops

from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.highlight_frames import emphasize_source_rectangles
from selenium_pipeline.pdf_element_geometry import ElementGeometryError
from selenium_pipeline.original_slide4_untimed_highlight_preview import (
    render_five_untimed_original_slide4_previews,
)


class RealSourceStylePixelReview(unittest.TestCase):
    def setUp(self):
        self.dir=TemporaryDirectory()
        self.root=Path(self.dir.name)
        self.original=self.root/"original"
        self.original.mkdir()
        self.output=self.root/"review-only"
        self.output.mkdir()
        (self.original/"source.pdf").write_bytes(b"test-not-real-textbook")
        (self.original/"script.txt").write_text("not original",encoding="utf8")
        with pymupdf.open() as pdf:
            for i in range(4):
                p=pdf.new_page(width=360,height=270)
                p.insert_text((40,70),f"Figure 8.2 visual {i+1}")
            pdf.save(self.original/"slides.pdf")
        self.sha=[_sha(self.original/p) for p in
                  ("source.pdf","slides.pdf","script.txt")]
        bboxes=[
            [10.909,57.794,339.762,82.252],
            [48.421,91.9534,126.4618,179.099],
            [126.4618,91.9534,208.4046,179.099],
            [208.4046,91.9534,314.4101,179.099],
            [32.727,186.691,126.5,240.062],
        ]
        self.proof={
            "status":"FIVE_ORIGINAL_SLIDE4_VISUAL_CANDIDATES_NOT_TIMED_OR_APPROVED",
            "source_sha256":self.sha[0],"slides_sha256":self.sha[1],
            "script_sha256":self.sha[2],
            "utterance_candidate_count":5,
            "source_mathematical_review_approved":False,
            "narration_timing_verified":False,
            "highlighted_video_verified":False,
            "utterance_candidates":[{
                "utterance_id":f"s004.utterance.{i:03d}",
                "original_spoken_sha256":f"{i:064x}",
                "review_target_id":f"target.{i}",
                "candidate_kind":"VISIBLE_SLIDE_TEXT_REGION",
                "candidate_highlight_bbox_pdf_pt":rect,
            } for i,rect in enumerate(bboxes,1)],
        }

    def tearDown(self):
        self.dir.cleanup()

    def render(self):
        with patch(
            "selenium_pipeline.original_slide4_untimed_highlight_preview.inspect_original_slide4_five_visual_candidates",
            return_value=self.proof):
            return render_five_untimed_original_slide4_previews(
                folder=self.original,output_dir=self.output)

    def test_five_real_pdf_rendered_distinct_visible_highlights(self):
        result=self.render()
        self.assertEqual(result["source_based_png_preview_count"],5)
        self.assertEqual(len(set(
            x["preview_png_sha256"] for x in result["review_only_preview_frames"])),5)
        self.assertFalse(result["actual_speech_to_highlight_sync_verified"])
        self.assertFalse(result["approved_encoded_mp4_available"])
        self.assertFalse(result["student_publication_authorized"])
        self.assertEqual(len(list(self.output.glob("*.png"))),5)
        self.assertTrue(all(x["changed_pixel_bbox"]
                            and not x["highlighted_video_frame_verified"]
                            and x["actual_speech_timestamp"] is None
                            for x in result["review_only_preview_frames"]))

    def test_refuse_reusing_existing_output_or_overwriting(self):
        self.render()
        with self.assertRaises(ValueError):
            self.render()

    def test_wrong_source_fingerprint_rejected(self):
        self.proof["slides_sha256"]="f"*64
        with self.assertRaises(ValueError):
            self.render()

    def test_invalid_original_text_candidate_rectangle_rejected(self):
        for rect in ([20,30,400,90],[-1,40,90,100],
                     [15,70,10,80]):
            self.proof["utterance_candidates"][0]["candidate_highlight_bbox_pdf_pt"]=rect
            with self.subTest(rect=rect),self.assertRaises(ValueError):
                self.render()

    def test_false_time_or_academic_approval_refused(self):
        for key in ("source_mathematical_review_approved",
                    "narration_timing_verified","highlighted_video_verified"):
            self.proof[key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.render()
            self.proof[key]=False

    def test_normal_highlight_style_helper_pixel_locality(self):
        base=Image.new("RGB",(720,540),(255,255,255))
        box=[80,90,130,140]
        frame=emphasize_source_rectangles(base,[box],scale=2.0)
        difference=ImageChops.difference(base,frame)
        changed=difference.getbbox()
        self.assertIsNotNone(changed)
        self.assertGreaterEqual(changed[0],150)
        self.assertLessEqual(changed[2],270)
        self.assertEqual(base.getpixel((0,0)),frame.getpixel((0,0)))

    def test_normal_highlight_style_rejects_bad_bounds(self):
        base=Image.new("RGB",(720,540),"white")
        for box in ([0,0,100,100],[100,100,50,120]):
            with self.assertRaises(ElementGeometryError):
                emphasize_source_rectangles(base,[box],scale=2)
        with self.assertRaises(ElementGeometryError):
            emphasize_source_rectangles(base,[[10,10,40,40]],scale=8)


if __name__=="__main__":
    unittest.main()
