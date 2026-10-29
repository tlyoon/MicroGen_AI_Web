"""Real PDF adversarial tests for independent source-panel label evidence."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_panel_label_evidence import inspect_source_panel_label_evidence


class PanelLabelEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "source.pdf"

    def make_source(self, *, labels=("(a)", "(b)"), duplicate_heading=False,
                    outside_label=False, vector=False):
        with pymupdf.open() as pdf:
            page = pdf.new_page(width=420, height=360)
            page.insert_text((25, 121), "FIGURE 8.3", fontsize=10)
            page.insert_text((25, 133), "A figure caption has separate words.", fontsize=8)
            page.draw_rect(pymupdf.Rect(110, 145, 310, 240))
            for i, label in enumerate(labels):
                page.insert_text((132 + 63 * i, 170), label, fontsize=10)
            if outside_label:
                page.insert_text((45, 170), "(c)", fontsize=10)
            if duplicate_heading:
                page.insert_text((25, 300), "FIGURE 8.3", fontsize=10)
            if vector:
                page.draw_line((165, 145), (165, 240), color=(0, 0, 0))
            pdf.save(self.path)

    def inspect(self):
        return inspect_source_panel_label_evidence(
            source=self.path, page_number=1, figure_id="8.3")

    def test_two_explicit_source_labels_remain_only_candidates(self):
        self.make_source(outside_label=True)
        sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        report = self.inspect()
        self.assertEqual(report["status"], "EXTRACTABLE_SOURCE_PANEL_LABEL_CANDIDATES_ONLY")
        self.assertEqual([label["id"] for label in report["extractable_panel_label_candidates"]],
                         ["a", "b"])
        self.assertEqual(report["caption_heading_line_count"], 1)
        for field in ("complete_figure_crop_certified", "panel_boundaries_source_verified",
                      "panel_ids_source_verified", "figure_semantics_certified",
                      "source_to_slide_equivalence_certified",
                      "tts_or_video_authorized", "human_review_claimed"):
            self.assertIs(report[field], False)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), sha)

    def test_no_source_labels_must_not_infer_panels(self):
        self.make_source(labels=())
        report = self.inspect()
        self.assertEqual(report["status"], "SOURCE_PANEL_LABELS_MISSING_OR_INCOMPLETE")
        self.assertEqual(report["panel_label_count"], 0)

    def test_one_label_is_insufficient(self):
        self.make_source(labels=("(a)",))
        self.assertEqual(self.inspect()["status"], "SOURCE_PANEL_LABELS_MISSING_OR_INCOMPLETE")

    def test_gap_in_labels_is_not_repaired_by_guess(self):
        self.make_source(labels=("(a)", "(c)"))
        self.assertEqual(self.inspect()["status"], "SOURCE_PANEL_LABELS_MISSING_OR_INCOMPLETE")

    def test_duplicate_inside_figure_is_ambiguous(self):
        self.make_source(labels=("(a)", "(a)", "(b)"))
        self.assertEqual(self.inspect()["status"], "SOURCE_PANEL_LABELS_DUPLICATED")

    def test_fig_mentions_elsewhere_do_not_override_unique_heading(self):
        self.make_source()
        self.assertEqual(self.inspect()["caption_heading_line_text"], "FIGURE 8.3")

    def test_duplicate_heading_blocks_as_in_parent_preflight(self):
        self.make_source(duplicate_heading=True)
        with self.assertRaises(FigureIdentityReviewRequired):
            self.inspect()

    def test_bad_path_and_wrong_figure_id_fail_closed(self):
        self.make_source()
        with self.assertRaises(FigureIdentityReviewRequired):
            inspect_source_panel_label_evidence(source=self.path, page_number=1, figure_id="8.4")
        with self.assertRaises(FigureIdentityReviewRequired):
            inspect_source_panel_label_evidence(source=self.path.parent / "none.pdf",
                                                page_number=1, figure_id="8.3")
