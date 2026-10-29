"""Adversarial real-PDF tests for conservative vector figure discovery."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_vector_region_discovery import (
    discover_vector_figure_candidate,
)


class SourceVectorDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "source.pdf"

    def create(self, *, identifier="8.3", duplicate_caption=False,
               extra_candidate=False, missing_art=False,
               only_small_art=False, oversized_path=False):
        with pymupdf.open() as pdf:
            page = pdf.new_page(width=400, height=340)
            page.insert_text((30, 120), "FIGURE " + identifier, fontsize=11)
            page.insert_text((30, 130), "An original vector diagram", fontsize=8)
            if duplicate_caption:
                page.insert_text((30, 250), "FIGURE " + identifier, fontsize=11)
            if not missing_art:
                if only_small_art:
                    page.draw_rect(pymupdf.Rect(100, 140, 110, 148))
                else:
                    page.draw_rect(pymupdf.Rect(110, 145, 280, 210))
            if extra_candidate:
                page.draw_rect(pymupdf.Rect(40, 151, 91, 202))
            if oversized_path:
                page.draw_rect(pymupdf.Rect(-30, -20, 440, 360))
            pdf.save(self.path)

    def inspect(self, **kwargs):
        args = dict(source=self.path, page_number=1, figure_id="8.3")
        args.update(kwargs)
        return discover_vector_figure_candidate(**args)

    def test_unique_vector_candidate_is_not_scientific_approval(self):
        self.create(oversized_path=True)
        sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        receipt = self.inspect()
        self.assertEqual(receipt["status"],
                         "VECTOR_REGION_CANDIDATE_REVIEW_REQUIRED")
        self.assertTrue(receipt["unique_anchored_vector_candidate"])
        self.assertGreaterEqual(receipt["rejected_drawing_count"], 1)
        for key in ("author_intended_complete_crop_certified",
                    "panel_ids_source_verified",
                    "panel_boundaries_source_verified",
                    "figure_semantics_certified",
                    "tts_or_video_authorized", "human_review_claimed"):
            self.assertIs(receipt[key], False)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), sha)

    def test_two_plausible_figures_require_review(self):
        self.create(extra_candidate=True)
        with self.assertRaisesRegex(FigureIdentityReviewRequired, "ambiguous"):
            self.inspect()

    def test_missing_source_heading_blocks(self):
        self.create(identifier="8.4")
        with self.assertRaisesRegex(FigureIdentityReviewRequired, "heading"):
            self.inspect()

    def test_no_source_vector_blocks(self):
        self.create(missing_art=True)
        with self.assertRaisesRegex(FigureIdentityReviewRequired, "absent"):
            self.inspect()

    def test_math_strokes_not_mistaken_for_source_figure(self):
        self.create(only_small_art=True)
        with self.assertRaises(FigureIdentityReviewRequired):
            self.inspect()

    def test_invalid_pages_and_figures_fail_closed(self):
        self.create()
        for page_number in (0, True, 2, "1"):
            with self.subTest(page=page_number):
                with self.assertRaises(FigureIdentityReviewRequired):
                    self.inspect(page_number=page_number)
        for fid in ("", "8", "FIGURE 8.3", "../8.3"):
            with self.subTest(fid=fid):
                with self.assertRaises(FigureIdentityReviewRequired):
                    self.inspect(figure_id=fid)

    def test_symlink_rejected_when_os_supports_it(self):
        self.create()
        alias = self.path.parent / "alias.pdf"
        try:
            alias.symlink_to(self.path)
        except (OSError, NotImplementedError):
            self.skipTest("Windows does not permit symlink for this user")
        with self.assertRaises(FigureIdentityReviewRequired):
            self.inspect(source=alias)

    def test_boxed_procedure_is_not_a_figure_candidate(self):
        """Caption text blocks can merge a nearby instruction box."""
        with pymupdf.open() as pdf:
            page = pdf.new_page(width=460, height=390)
            page.insert_text((30, 120), "FIGURE 8.3", fontsize=11)
            page.insert_text((30, 132), "The graph of inverse trigonometric functions.", fontsize=8)
            page.draw_rect(pymupdf.Rect(120, 145, 410, 305))
            for y, txt in (
                (169, "Procedure for the Trigonometric Substitution"),
                (188, "1. Write the substitution, calculate the differential and specify the angle."),
                (207, "2. Substitute the expression and simplify the results carefully."),
                (226, "3. Integrate the trigonometric integral and note restrictions."),
                (245, "4. Draw an appropriate reference triangle to reverse substitution."),
            ):
                page.insert_text((130, y), txt, fontsize=7)
            pdf.save(self.path)
        original = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(FigureIdentityReviewRequired, "prose|instructions"):
            self.inspect()
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), original)

    def test_short_axis_and_panel_labels_are_not_misclassified_as_prose(self):
        with pymupdf.open() as pdf:
            page = pdf.new_page(width=400, height=340)
            page.insert_text((30, 120), "FIGURE 8.3", fontsize=11)
            page.draw_rect(pymupdf.Rect(110, 145, 280, 210))
            for pos, txt in (((140, 168), "(a)"), ((230, 168), "(b)"),
                             ((155, 194), "sine"), ((240, 194), "cosine")):
                page.insert_text(pos, txt, fontsize=8)
            pdf.save(self.path)
        receipt = self.inspect()
        self.assertEqual(receipt["candidate_embedded_long_word_count"], 2)
        self.assertEqual(receipt["candidate_dense_prose_line_count"], 0)
        self.assertFalse(receipt["tts_or_video_authorized"])

    def test_single_long_text_line_must_fail_closed(self):
        """Some PDF encoders expose a whole instruction paragraph as one line."""
        with pymupdf.open() as pdf:
            page = pdf.new_page(width=720, height=340)
            page.insert_text((30, 120), "FIGURE 8.3", fontsize=11)
            page.draw_rect(pymupdf.Rect(95, 145, 680, 215))
            page.insert_text((105, 175), " ".join(["context"] * 29), fontsize=5)
            pdf.save(self.path)
        with self.assertRaisesRegex(FigureIdentityReviewRequired, "prose|instructions"):
            self.inspect()
