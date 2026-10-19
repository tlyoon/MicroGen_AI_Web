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
