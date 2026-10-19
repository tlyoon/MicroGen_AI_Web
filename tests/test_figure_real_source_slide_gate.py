"""Real generated-PDF read-only gate tests for original figure-to-slide evidence."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

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

    def test_cli_explicit_nonzero_blocked_exit(self):
        self.create()
        rc=main(["--source",str(self.source),"--slides",str(self.slide),
                 "--source-page","1","--slide-page","1","--figure-id","8.3"])
        self.assertEqual(rc,2)
