"""Generated PDF tests for conservative textbook-caption collision detection."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.figure_caption_column_audit import audit_caption_column_collision
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired


class FigureCaptionColumnTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.pdf = Path(temp.name) / "source.pdf"

    def make(self, *, nearby_prose=True, duplicates=False):
        with pymupdf.open() as doc:
            p = doc.new_page(width=610, height=700)
            p.insert_text((30, 410), "FIGURE 8.3", fontsize=10)
            p.insert_text((30, 424), "Inverse trig functions.", fontsize=8)
            if nearby_prose:
                for y, text in [(440,"Procedure for a Trigonometric Substitution"),
                                (459,"Write down the substitution and differential here"),
                                (478,"Substitute the expression into the integrand now")]:
                    p.insert_text((214, y), text, fontsize=7)
            if duplicates:
                p.insert_text((30, 600), "FIGURE 8.3", fontsize=10)
            doc.save(self.pdf)

    def inspect(self, **kwargs):
        return audit_caption_column_collision(
            source=self.pdf, page_number=1, figure_id="8.3", **kwargs)

    def test_adjacent_prose_is_review_required_not_caption(self):
        self.make()
        before = hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        r = self.inspect()
        self.assertEqual(r["status"], "CAPTION_PARALLEL_PROSE_COLLISION_REVIEW_REQUIRED")
        self.assertGreaterEqual(r["parallel_prose_line_count"], 2)
        self.assertEqual(r["heading_text"], "FIGURE 8.3")
        for field in ("caption_region_author_verified", "author_intended_complete_crop_certified",
                      "panel_boundaries_source_verified",
                      "source_to_slide_equivalence_certified", "tts_or_video_authorized"):
            self.assertFalse(r[field])
        self.assertEqual(hashlib.sha256(self.pdf.read_bytes()).hexdigest(), before)

    def test_no_parallel_prose_still_requires_review(self):
        self.make(nearby_prose=False)
        r = self.inspect()
        self.assertEqual(r["status"], "CAPTION_LAYOUT_CANDIDATE_REVIEW_REQUIRED")
        self.assertFalse(r["tts_or_video_authorized"])

    def test_duplicates_are_blocked(self):
        self.make(duplicates=True)
        with self.assertRaises(FigureIdentityReviewRequired):
            self.inspect()

    def test_bad_source_page_identifier_and_missing_pdf_block(self):
        self.make()
        for n, id in ((0,"8.3"), (True,"8.3"), (2,"8.3"), (1,"8.4"),
                      (1,"../8.3"), (1,"8")):
            with self.subTest(n=n,id=id):
                with self.assertRaises(FigureIdentityReviewRequired):
                    audit_caption_column_collision(
                        source=self.pdf,page_number=n,figure_id=id)
        with self.assertRaises(FigureIdentityReviewRequired):
            audit_caption_column_collision(
                source=self.pdf.parent/"missing.pdf",page_number=1,figure_id="8.3")
