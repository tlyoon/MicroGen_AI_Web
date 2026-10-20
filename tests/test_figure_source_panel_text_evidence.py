"""Adversarial original-PDF panel-marker inventory tests."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_source_panel_text_evidence import (
    inventory_source_panel_text, main,
)


class PanelTextEvidenceTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.file = Path(t.name) / "original.pdf"

    def make(self, *, top=True, duplicate=False, as_prose=False):
        with pymupdf.open() as pdf:
            p = pdf.new_page(width=610, height=700)
            p.insert_text((30, 405), "FIGURE 8.3", fontsize=11)
            p.draw_line((31, 160), (176, 310))
            if top:
                p.insert_text((40, 325), "(a)", fontsize=9)
                p.insert_text((130, 325), "(b)", fontsize=9)
                if duplicate:
                    p.insert_text((50, 345), "(a)", fontsize=9)
            p.insert_text((240, 330), "(c)", fontsize=9)
            p.insert_text((38, 447), "(d)", fontsize=9)
            if as_prose:
                p.insert_text((38, 370), "Compare (c) with (a)", fontsize=9)
            pdf.save(self.file)

    def check(self, **kw):
        return inventory_source_panel_text(
            source=self.file, page_number=1, figure_id="8.3", **kw)

    def test_printed_markers_are_lexically_observed_not_panels(self):
        self.make()
        before = hashlib.sha256(self.file.read_bytes()).hexdigest()
        r = self.check()
        self.assertEqual({i["label"] for i in r["printed_panel_marker_candidates"]},
                         {"(a)", "(b)"})
        self.assertEqual({i["label"] for i in r["printed_panel_markers_outside_corridor"]},
                         {"(c)", "(d)"})
        for field in ("original_panel_count_certified",
                      "original_panel_ownership_certified",
                      "original_complete_figure_certified",
                      "source_to_slide_content_certified",
                      "student_publication_authorized"):
            self.assertFalse(r[field])
        self.assertEqual(before, hashlib.sha256(self.file.read_bytes()).hexdigest())

    def test_duplicate_marker_blocks_complete_panel_inference(self):
        self.make(duplicate=True)
        self.assertEqual(self.check()["candidate_marker_repetitions"], ["(a)"])

    def test_prose_is_not_a_panel_marker(self):
        self.make(as_prose=True)
        self.assertEqual(len(self.check()["printed_panel_marker_candidates"]), 2)

    def test_no_markers_in_corridor_not_falsely_called_verified(self):
        self.make(top=False)
        r = self.check()
        self.assertEqual(r["status"],
                         "NO_PRECAPTION_PRINTED_PANEL_MARKERS_REVIEW_REQUIRED")
        self.assertFalse(r["vector_drawn_or_nonextractable_markers_ruled_out"])

    def test_wrong_figure_fails_closed(self):
        self.make()
        with self.assertRaises(FigureIdentityReviewRequired):
            inventory_source_panel_text(
                source=self.file, page_number=1, figure_id="8.4")

    def test_cli_returns_review_code_two(self):
        self.make()
        self.assertEqual(main(["--source",str(self.file),"--page","1",
                               "--figure-id","8.3"]), 2)
