"""Explicit reordered graph crops may match pixels but never certify panels."""
from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_declared_panel_reflow import audit_declared_panel_reflow, main

class DeclaredPanelReflowTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.source=Path(self.t.name)/"source.pdf"
        self.slide=Path(self.t.name)/"slides.pdf"
        self.tiles=[
            {"source_bbox":[40,120,140,200],"slide_px_bbox":[0,0,100,80]},
            {"source_bbox":[40,220,140,300],"slide_px_bbox":[100,0,200,80]},
        ]

    def make(self, *, altered=False, overlay=False, omit_second=False):
        with pymupdf.open() as book:
            s=book.new_page(width=610,height=700)
            s.draw_line((50,130),(128,190),color=(0,0,0),width=2)
            s.draw_rect(pymupdf.Rect(62,140,79,165),color=(0,0,0))
            s.draw_line((50,280),(129,236),color=(0,0,0),width=2)
            s.draw_circle((82,258),13,color=(.2,.2,.2))
            s.insert_text((30,405),"FIGURE 8.3",fontsize=11)
            segments=[s.get_pixmap(matrix=pymupdf.Matrix(1,1),
                                   clip=pymupdf.Rect(tile["source_bbox"]),
                                   alpha=False,colorspace=pymupdf.csRGB).tobytes("png")
                      for tile in self.tiles]
            book.save(self.source)
        with pymupdf.open() as composed:
            p=composed.new_page(width=200,height=80)
            p.insert_image(pymupdf.Rect(0,0,100,80),stream=segments[0],
                           keep_proportion=False)
            if not omit_second:
                p.insert_image(pymupdf.Rect(100,0,200,80),stream=segments[1],
                               keep_proportion=False)
            if altered:
                p.draw_rect(pymupdf.Rect(140,20,180,40),fill=(0,0,0))
            png=p.get_pixmap(alpha=False).tobytes("png")
        with pymupdf.open() as slides:
            page=slides.new_page(width=480,height=360)
            page.insert_image(pymupdf.Rect(50,90,250,170),stream=png,
                              keep_proportion=False)
            if overlay:
                page.draw_line((55,100),(238,158),
                               color=(1,0,0),width=5)
            slides.save(self.slide)

    def check(self,tiles=None):
        return audit_declared_panel_reflow(
            source=self.source,slides=self.slide,
            source_page=1,slide_page=1,figure_id="8.3",
            tiles=self.tiles if tiles is None else tiles)

    def test_matching_two_source_crops_are_not_original_panel_proof(self):
        self.make()
        before=[hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.source,self.slide)]
        r=self.check()
        self.assertEqual(r["declared_tile_count"],2)
        self.assertEqual(r["status"],
            "DECLARED_REFLOW_PIXELS_EQUAL_UNTRUSTED_MAPPING_REVIEW_REQUIRED")
        self.assertEqual(r["mismatched_tile_indices"],[])
        for key in ("original_source_panel_ownership_verified",
                    "original_complete_figure_panels_verified",
                    "scientific_panel_labels_semantics_verified",
                    "full_slide_image_coverage_verified",
                    "narrated_element_highlights_verified",
                    "video_or_publication_authorized"):
            self.assertFalse(r[key])
        self.assertEqual(before,[hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (self.source,self.slide)])

    def test_tampered_panel_content_fails(self):
        self.make(altered=True)
        r=self.check()
        self.assertEqual(r["status"],
                         "DECLARED_REFLOW_PIXEL_EVIDENCE_INCOMPLETE")
        self.assertIn(2,r["mismatched_tile_indices"])

    def test_missing_panel_fails(self):
        self.make(omit_second=True)
        self.assertIn(2,self.check()["mismatched_tile_indices"])

    def test_overlaid_raster_cannot_be_approved(self):
        self.make(overlay=True)
        self.assertEqual(self.check()["status"],
                         "DECLARED_REFLOW_PIXEL_EVIDENCE_INCOMPLETE")
        self.assertFalse(self.check()["video_or_publication_authorized"])

    def test_overlapping_and_invalid_rectangles_fail_closed(self):
        self.make()
        corrupt=[dict(self.tiles[0]),dict(self.tiles[1])]
        corrupt[1]["source_bbox"]=[80,150,120,195]
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check(corrupt)
        corrupt=[dict(self.tiles[0]),dict(self.tiles[1])]
        corrupt[1]["slide_px_bbox"]=[90,0,190,80]
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check(corrupt)

    def test_one_declared_crop_never_claims_all_panels(self):
        self.make()
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check(self.tiles[:1])

    def test_below_figure_caption_source_boxes_block(self):
        self.make()
        a=[dict(t) for t in self.tiles]
        a[1]["source_bbox"]=[40,430,140,510]
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check(a)

    def test_cli_json_retains_exit_two(self):
        self.make()
        path=Path(self.t.name)/"declared_untrusted_tiles.json"
        path.write_text(json.dumps(self.tiles),encoding="utf8")
        rc=main(["--source",str(self.source),"--slides",str(self.slide),
                 "--source-page","1","--slide-page","1",
                 "--figure-id","8.3","--tiles-json",str(path)])
        self.assertEqual(rc,2)
