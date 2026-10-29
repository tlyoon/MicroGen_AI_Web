"""Adversarial explicit source-crop vs slide bitmap pixel comparisons."""
from __future__ import annotations
import hashlib
import tempfile
import unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_declared_crop_slide_comparison import (
    audit_declared_crop_match, main,
)

class DeclaredCropComparisonTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.source=Path(t.name)/"source.pdf"
        self.slides=Path(t.name)/"slides.pdf"
        self.crop=[40,120,140,180]

    def make(self, *, alteration=False, overlay=False):
        with pymupdf.open() as book:
            p=book.new_page(width=610,height=700)
            p.draw_line((43,140),(135,170),color=(0,0,0),width=2)
            p.draw_rect(pymupdf.Rect(60,130,90,160),color=(0,0,0))
            p.insert_text((30,405),"FIGURE 8.3",fontsize=11)
            b=p.get_pixmap(matrix=pymupdf.Matrix(2,2),
                            clip=pymupdf.Rect(self.crop),
                            colorspace=pymupdf.csRGB,alpha=False).tobytes("png")
            book.save(self.source)
        if alteration:
            with pymupdf.open() as other:
                q=other.new_page(width=200,height=120)
                q.draw_rect(pymupdf.Rect(20,20,180,100),fill=(0,0,0))
                b=q.get_pixmap(alpha=False).tobytes("png")
        with pymupdf.open() as pdf:
            p=pdf.new_page(width=480,height=330)
            p.insert_image(pymupdf.Rect(40,60,240,180),stream=b,
                           keep_proportion=False)
            if overlay:
                p.draw_line((50,80),(230,140),color=(1,0,0),width=8)
            pdf.save(self.slides)

    def inspect(self, crop=None):
        return audit_declared_crop_match(
            source=self.source,slides=self.slides,source_page=1,
            slide_page=1,figure_id="8.3",
            crop=self.crop if crop is None else crop)

    def test_matching_crop_only_indicates_untrusted_pixel_hypothesis(self):
        self.make()
        sha=hashlib.sha256(self.source.read_bytes()).hexdigest()
        r=self.inspect()
        self.assertEqual(r["status"],
                         "DECLARED_CROP_RGB_PIXELS_MATCH_UNTRUSTED_HYPOTHESIS")
        self.assertTrue(r["declared_crop_visible_rgb_pixels_equal"])
        self.assertFalse(r["declared_crop_authoritatively_selected"])
        self.assertFalse(r["source_slide_figure_identity_certified"])
        self.assertFalse(r["video_or_publication_authorized"])
        self.assertEqual(sha,hashlib.sha256(self.source.read_bytes()).hexdigest())

    def test_other_image_contents_do_not_match(self):
        self.make(alteration=True)
        r=self.inspect()
        self.assertEqual(r["status"],"DECLARED_CROP_RGB_PIXELS_DIFFER")

    def test_wrong_aspect_stays_unverified(self):
        self.make()
        r=self.inspect(crop=[40,120,140,230])
        self.assertEqual(r["status"],"DECLARED_SOURCE_CROP_SLIDE_ASPECT_MISMATCH")
        self.assertFalse(r["source_slide_figure_identity_certified"])

    def test_overlaid_slide_bitmap_does_not_pass_reference_gate(self):
        self.make(overlay=True)
        self.assertEqual(self.inspect()["status"],
                         "SLIDE_BITMAP_VISIBILITY_UNVERIFIED")

    def test_malicious_outside_or_below_caption_bbox_rejected(self):
        self.make()
        for crop in ([40,120,140,440], [0,0,900,80], [10,10,10,30],
                     [40,float("nan"),140,180],[40,"120",140,180]):
            with self.subTest(crop=crop):
                with self.assertRaises(FigureIdentityReviewRequired):
                    self.inspect(crop=crop)

    def test_cli_is_blocked_even_for_matching_raster(self):
        self.make()
        self.assertEqual(main(["--source",str(self.source),
                               "--slides",str(self.slides),
                               "--source-page","1","--slide-page","1",
                               "--figure-id","8.3",
                               "--crop","40","120","140","180"]),2)
