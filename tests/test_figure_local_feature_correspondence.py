"""Generated vector reflow / unrelated bitmap feature QA: no semantic promotion."""
from __future__ import annotations

import hashlib
import io
import random
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_local_feature_correspondence import (
    audit_local_feature_correspondence, main,
)

try:
    import cv2
    import numpy as np
    from PIL import Image
except ImportError:
    cv2 = None


@unittest.skipIf(cv2 is None, "Optional computer-vision QA dependencies missing")
class FeatureSourceSlideTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.source = Path(tmp.name) / "source.pdf"
        self.slides = Path(tmp.name) / "slides.pdf"

    def create(self, *, unrelated=False, overlay=False, only_one=False):
        centers = (102, 211, 320)
        with pymupdf.open() as book:
            p = book.new_page(width=610, height=700)
            p.insert_text((30, 405), "FIGURE 8.3", fontsize=10)
            for j, cy in enumerate(centers):
                p.draw_rect(pymupdf.Rect(40, cy-42, 180, cy+42),
                            color=(.3, .3, .3))
                rng = random.Random(4371 + j * 83)
                for k in range(35):
                    x = 48 + rng.randrange(115)
                    y = cy-33 + rng.randrange(64)
                    width = 3 + rng.randrange(9)
                    height = 3 + rng.randrange(8)
                    p.draw_rect(pymupdf.Rect(x, y, x+width, y+height),
                                color=(0, 0, 0), fill=(0, 0, 0))
                    if k % 3 == 0:
                        p.draw_line((x-4, y+6), (x+6, y-3), width=1.3)
                    if k % 5 == 0:
                        p.insert_text((x, y+9), f'{j}-{k}', fontsize=6)
            tiles = [
                p.get_pixmap(
                    matrix=pymupdf.Matrix(3, 3),
                    clip=pymupdf.Rect(38,cy-50,182,cy+50),
                    colorspace=pymupdf.csRGB,alpha=False)
                for cy in centers
            ]
            book.save(self.source)
        canvas = Image.new("RGB", (744,173), "white")
        if unrelated:
            rng = np.random.default_rng(7811)
            img = Image.fromarray(rng.integers(
                0, 256, size=(173,744,3), dtype=np.uint8), "RGB")
            canvas.paste(img, (0,0))
        else:
            for j,pix in enumerate(tiles[:1] if only_one else tiles):
                orig = Image.frombytes("RGB",(pix.width,pix.height),
                                       bytes(pix.samples))
                canvas.paste(orig.resize((248,173), Image.Resampling.LANCZOS),
                             (j*248,0))
        out = io.BytesIO()
        canvas.save(out,format="PNG")
        with pymupdf.open() as deck:
            p = deck.new_page(width=490,height=360)
            p.insert_image(pymupdf.Rect(35,80,407,166),
                           stream=out.getvalue(),keep_proportion=False)
            if overlay:
                p.draw_rect(pymupdf.Rect(100,100,280,135),
                            fill=(1,0,0))
            deck.save(self.slides)
    def audit(self, **kwargs):
        args = dict(source=self.source,slides=self.slides,source_page=1,
                    slide_page=1,figure_id="8.3")
        args.update(kwargs)
        return audit_local_feature_correspondence(**args)

    def test_realistic_split_vector_page_yields_only_geometric_candidates(self):
        self.create()
        old=[hashlib.sha256(p.read_bytes()).hexdigest()
             for p in (self.source,self.slides)]
        report=self.audit()
        self.assertGreater(report["source_orb_feature_count"], 35)
        self.assertGreater(report["slide_orb_feature_count"], 35)
        self.assertGreater(report["tentative_descriptor_match_count"], 12)
        self.assertGreaterEqual(report["geometrically_coherent_bin_count"], 1)
        self.assertEqual(len(report["arbitrary_four_width_bins"]),4)
        for key in ("scan_bins_are_author_intended_panels",
                    "candidate_source_region_authoritatively_owned",
                    "complete_figure_and_panel_mapping_certified",
                    "mathematical_semantics_verified",
                    "narrated_highlights_verified",
                    "encoded_video_duration_verified",
                    "video_or_publication_authorized"):
            self.assertFalse(report[key])
        self.assertEqual(old,[hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (self.source,self.slides)])

    def test_unrelated_random_slide_cannot_claim_source_figure(self):
        self.create(unrelated=True)
        report=self.audit()
        self.assertFalse(report["complete_figure_and_panel_mapping_certified"])
        self.assertFalse(report["video_or_publication_authorized"])
        self.assertEqual(report["geometrically_coherent_bin_count"],0)

    def test_single_source_tile_does_not_claim_whole_figure(self):
        self.create(only_one=True)
        report=self.audit()
        self.assertFalse(report["complete_figure_and_panel_mapping_certified"])
        self.assertFalse(report["scan_bins_are_author_intended_panels"])

    def test_slide_foreground_overlay_blocks_independent_bitmap(self):
        self.create(overlay=True)
        with self.assertRaises(FigureIdentityReviewRequired):
            self.audit()

    def test_wrong_source_figure_id_fails_closed(self):
        self.create()
        with self.assertRaises(FigureIdentityReviewRequired):
            self.audit(figure_id="8.5")

    def test_cli_returns_blocked_review_code(self):
        self.create()
        self.assertEqual(main(["--source",str(self.source),
                               "--slides",str(self.slides),
                               "--source-page","1","--slide-page","1",
                               "--figure-id","8.3"]), 2)
