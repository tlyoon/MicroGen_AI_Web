"""Generated-PDF adversarial tests for independent pre-caption vector inventory."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_pre_caption_vector_inventory import inventory_pre_caption_vectors


class PreCaptionVectorInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pdf = Path(self.temp.name) / "source.pdf"

    def create(self, *, omit_graph=False, only_after=False):
        with pymupdf.open() as doc:
            p = doc.new_page(width=600, height=640)
            p.insert_text((30, 405), "FIGURE 8.3", fontsize=10)
            if not omit_graph and not only_after:
                p.draw_line((30, 180), (185, 180), color=(0, 0, 0))
                p.draw_line((32, 180), (32, 330), color=(0, 0, 0))
                p.draw_line((42, 302), (179, 120), color=(0, 0, 0))
            p.draw_rect(pymupdf.Rect(220, 425, 505, 570))
            p.insert_text((230, 445), "Procedure for the Trigonometric Substitution", fontsize=8)
            p.draw_rect(pymupdf.Rect(-20, -20, 620, 660))
            if only_after:
                p.draw_rect(pymupdf.Rect(32, 445, 140, 520))
            doc.save(self.pdf)

    def inspect(self):
        return inventory_pre_caption_vectors(
            source=self.pdf, page_number=1, figure_id="8.3")

    def test_small_vector_operations_before_heading_are_inventory_only(self):
        self.create()
        before = hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        receipt = self.inspect()
        self.assertEqual(receipt["status"],
                         "PRECAPTION_VECTOR_OBJECTS_REQUIRE_INDEPENDENT_GROUPING")
        self.assertGreaterEqual(receipt["pre_caption_object_count"], 2)
        self.assertGreaterEqual(receipt["excluded_drawing_reasons"]["outside_source_page"], 1)
        for item in receipt["pre_caption_drawing_objects"]:
            self.assertLess(item["bbox"][3], 402)
            self.assertLess(item["bbox"][2], 204)
        for field in ("source_object_membership_certified", "whole_graph_bbox_certified",
                      "original_panel_labels_certified",
                      "figure_scientific_semantics_certified",
                      "source_to_slide_equivalence_certified", "tts_or_video_authorized"):
            self.assertFalse(receipt[field])
        self.assertEqual(hashlib.sha256(self.pdf.read_bytes()).hexdigest(), before)

    def test_no_original_graph_vectors_does_not_guess(self):
        self.create(omit_graph=True)
        self.assertEqual(self.inspect()["pre_caption_object_count"], 0)

    def test_lower_procedure_vectors_never_enter_precaption_inventory(self):
        self.create(only_after=True)
        receipt = self.inspect()
        self.assertEqual(receipt["pre_caption_object_count"], 0)
        self.assertGreaterEqual(receipt["excluded_drawing_reasons"]["after_heading"], 1)

    def test_bad_figure_fails_closed_inherited_validation(self):
        self.create()
        with self.assertRaises(FigureIdentityReviewRequired):
            inventory_pre_caption_vectors(
                source=self.pdf,page_number=1,figure_id="8.4")
