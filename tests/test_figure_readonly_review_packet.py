"""An isolated evidence packet cannot overwrite originals or claim approval."""
from __future__ import annotations
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pymupdf
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_readonly_review_packet import make_source_slide_review_packet

class ReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.orig=self.root/"lecture"
        self.orig.mkdir()
        self.s=self.orig/"source.pdf"
        self.d=self.orig/"slides.pdf"
        with pymupdf.open() as pdf:
            page=pdf.new_page(width=500,height=400)
            page.insert_text((30,250),"FIGURE 8.3")
            page.draw_line((60,100),(130,150))
            pdf.save(self.s)
        with pymupdf.open() as pdf:
            page=pdf.new_page(width=400,height=300)
            page.insert_text((30,80),"Slide")
            pdf.save(self.d)
        self.out=self.root/"isolated_review"

    def receipt(self):
        return {
            "source_sha256":hashlib.sha256(self.s.read_bytes()).hexdigest(),
            "slides_sha256":hashlib.sha256(self.d.read_bytes()).hexdigest(),
            "status":"SOURCE_COMPONENT_REGISTRATION_INTERSECTION_REVIEW_REQUIRED",
            "observations":[{"drawing_indices":[0],
                             "union_bbox":[60,100,130,150],
                             "registration_groups_intersecting_bbox":[]}],
            "original_complete_figure_verified":False,
            "original_panel_boundaries_verified":False,
            "original_stroke_to_slide_pixel_equality_verified":False,
            "encoded_highlighted_video_authorized":False,
            "publication_authorized":False,
        }

    def make(self,out=None,report=None):
        with patch("selenium_pipeline.figure_readonly_review_packet."
                   "audit_component_registration",return_value=(
                       self.receipt() if report is None else report)):
            return make_source_slide_review_packet(
                source=self.s,slides=self.d,source_page=1,
                slide_page=1,figure_id="8.3",
                output=self.out if out is None else out)

    def test_produces_immutable_evidence_and_explicit_blockers(self):
        before=[hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [self.s,self.d]]
        data=self.make()
        self.assertEqual(data["isolated_source_vector_indices"],[[0]])
        for key in ("author_intended_complete_figure_certified",
                    "scientific_panel_label_mapping_certified",
                    "narrated_highlight_accepted",
                    "student_publication_authorized"):
            self.assertFalse(data[key])
        self.assertTrue((self.out/"original_source_review.png").is_file())
        self.assertTrue((self.out/"existing_slide_review.png").is_file())
        self.assertTrue((self.out/"review_manifest.json").is_file())
        self.assertEqual(before,[hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [self.s,self.d]])

    def test_existing_review_target_cannot_be_overwritten(self):
        self.out.mkdir()
        (self.out/"keep.txt").write_text("existing")
        with self.assertRaises(FigureIdentityReviewRequired):
            self.make()
        self.assertEqual((self.out/"keep.txt").read_text(),"existing")

    def test_output_inside_original_lecture_folder_fails(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            self.make(out=self.orig/"review")

    def test_forged_approval_rejected_before_file_output(self):
        fake=self.receipt()
        fake["publication_authorized"]=True
        with self.assertRaises(FigureIdentityReviewRequired):
            self.make(report=fake)
        self.assertFalse(self.out.exists())
