"""Real generated-PDF read-only gate tests for original figure-to-slide evidence."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_real_source_slide_gate import (
    assess_real_source_slide_figure, main,
)


class RealSourceSlideGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source.pdf"
        self.slide = Path(self.temp.name) / "slides.pdf"

    def create(self, *, slide_mentions_figure=True):
        with pymupdf.open() as doc:
            p = doc.new_page(width=610, height=700)
            p.draw_line((29, 100), (182, 280))
            p.insert_text((30, 405), "FIGURE 8.3", fontsize=11)
            p.insert_text((30, 425), "Graph of inverse trigonometric functions.", fontsize=8)
            p.draw_rect(pymupdf.Rect(210, 435, 520, 560))
            for y in (452, 472, 492):
                p.insert_text((220,y),"Procedure for the trigonometric substitution",fontsize=7)
            doc.save(self.source)
        with pymupdf.open() as doc:
            p = doc.new_page(width=640, height=360)
            p.insert_text((40,40),"Lecture diagram of inverse trig functions",fontsize=12)
            if slide_mentions_figure:
                p.insert_text((40,55),"FIGURE 8.3",fontsize=10)
            p.draw_rect(pymupdf.Rect(45,80,280,240))
            doc.save(self.slide)

    def inspect(self, **kwargs):
        a=dict(source=self.source,slides=self.slide,source_page=1,
               slide_page=1,figure_id="8.3")
        a.update(kwargs)
        return assess_real_source_slide_figure(**a)

    def test_even_matching_slide_figure_label_does_not_authorize_media(self):
        self.create()
        pre=(hashlib.sha256(self.source.read_bytes()).hexdigest(),
             hashlib.sha256(self.slide.read_bytes()).hexdigest())
        r=self.inspect()
        self.assertEqual(r["status"],"REAL_SOURCE_SLIDE_FIGURE_EVIDENCE_BLOCKED")
        self.assertEqual(r["slide_exact_figure_caption_text_matches"],1)
        self.assertGreaterEqual(r["source_parallel_prose_line_count"],2)
        for key in ("source_graph_objects_scientifically_assigned",
                    "original_complete_panel_boundaries_verified",
                    "source_to_slide_figure_identity_verified",
                    "narrated_element_highlight_verified",
                    "video_part_duration_verified",
                    "figure_video_authorized", "student_publication_authorized",
                    "human_academic_review_claimed"):
            self.assertIs(r[key],False)
        self.assertEqual((hashlib.sha256(self.source.read_bytes()).hexdigest(),
                          hashlib.sha256(self.slide.read_bytes()).hexdigest()),pre)

    def test_no_slide_caption_still_blocks(self):
        self.create(slide_mentions_figure=False)
        r=self.inspect()
        self.assertEqual(r["slide_exact_figure_caption_text_matches"],0)
        self.assertFalse(r["source_to_slide_figure_identity_verified"])

    def test_missing_slide_and_page_bounds_rejected(self):
        self.create()
        for kwargs in (dict(slide_page=0),dict(slide_page=True),
                       dict(slide_page=2),dict(slides=self.slide.parent/"missing.pdf")):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(FigureIdentityReviewRequired):
                    self.inspect(**kwargs)

    def test_material_bitmap_triggers_optional_safe_reflow_diagnostic(self):
        self.create()
        with pymupdf.open() as image:
            page = image.new_page(width=150, height=100)
            page.draw_line((10, 20), (140, 80))
            bitmap = page.get_pixmap(alpha=False).tobytes("png")
        with pymupdf.open(self.slide) as deck:
            deck[0].insert_image(pymupdf.Rect(50, 90, 280, 230),
                                 stream=bitmap, keep_proportion=False)
            deck.saveIncr()
        before = (hashlib.sha256(self.source.read_bytes()).hexdigest(),
                  hashlib.sha256(self.slide.read_bytes()).hexdigest())
        def observe(**kwargs):
            return {
                "status":"THREE_GRAPH_REFLOW_DETECTED_SEMANTIC_REVIEW_PENDING",
                "layout_reflow_detected":True,
                "previous_whole_source_crop_aspect_mismatch_resolved_as_layout_only":True,
                "source_sha256":before[0], "slides_sha256":before[1],
                "publication_authorized":False,
            }
        with patch("selenium_pipeline.figure_layout_recovery_dispatch."
                   "discover_source_slide_reflow", side_effect=observe) as mock:
            report = self.inspect()
        self.assertEqual(mock.call_count, 1)
        self.assertTrue(report["automatically_detected_layout_reflow"])
        self.assertEqual(report["status"], "REAL_SOURCE_SLIDE_FIGURE_EVIDENCE_BLOCKED")
        self.assertFalse(report["source_to_slide_figure_identity_verified"])
        self.assertFalse(report["student_publication_authorized"])
        self.assertEqual(before, (
            hashlib.sha256(self.source.read_bytes()).hexdigest(),
            hashlib.sha256(self.slide.read_bytes()).hexdigest()))

    def test_non_raster_source_slide_does_not_invoke_vision(self):
        self.create()
        with patch("selenium_pipeline.figure_layout_recovery_dispatch."
                   "discover_source_slide_reflow") as mock:
            report = self.inspect()
        mock.assert_not_called()
        self.assertFalse(report["automatically_detected_layout_reflow"])

    def test_cli_explicit_nonzero_blocked_exit(self):
        self.create()
        rc=main(["--source",str(self.source),"--slides",str(self.slide),
                 "--source-page","1","--slide-page","1","--figure-id","8.3"])
        self.assertEqual(rc,2)
