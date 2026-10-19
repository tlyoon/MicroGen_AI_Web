"""Adversarial whole-raster figure identity checks on real generated PDFs.

No production changes, TTS, Gemini, browser, source overwrites or uploads.
"""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import pymupdf
from PIL import Image

from selenium_pipeline.figure_source_identity import (
    FigureIdentityReviewRequired, inspect_whole_raster_candidate,
)


class WholeFigureIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.pdf"
        self.slides = self.root / "slides.pdf"
        self.caption = "Figure 2.3 The magnetic field around a solenoid."
        self.png = self.root / "original.png"
        image = Image.new("RGB", (200, 150))
        for y in range(150):
            for x in range(200):
                image.putpixel((x, y), ((x*3)%256, (y*5)%256, (x+y)%256))
        image.save(self.png)
        self._pdf(self.source, is_slide=False)
        self._pdf(self.slides, is_slide=True)
        self.original = (self.source.read_bytes(), self.slides.read_bytes())

    def _pdf(self, path, *, is_slide, caption=None, image=None,
             repeated=False, vector=False, extra_page=False,
             figure_rect=None):
        image = image or self.png
        caption = self.caption if caption is None else caption
        with pymupdf.open() as doc:
            page = doc.new_page(width=620, height=780)
            box = figure_rect or (
                pymupdf.Rect(80, 90, 360, 300) if is_slide
                else pymupdf.Rect(80, 80, 280, 230))
            page.insert_image(box, filename=str(image))
            if repeated:
                page.insert_image(pymupdf.Rect(390,90,570,225),
                                  filename=str(image))
            if vector:
                shape=page.new_shape()
                shape.draw_rect(pymupdf.Rect(390,350,540,450))
                shape.finish(color=(0,0,0))
                shape.commit()
            page.insert_text((80, box.y1+28),caption,fontsize=11)
            if extra_page:
                second=doc.new_page(width=620,height=780)
                second.insert_image(pymupdf.Rect(80,80,280,230),
                                    filename=str(image))
            doc.save(path)

    def _inspect(self, **overrides):
        opts=dict(source=self.source, slides=self.slides,
                  source_page=1, slide_page=1, caption=self.caption)
        opts.update(overrides)
        return inspect_whole_raster_candidate(**opts)

    def test_exact_pixel_and_caption_candidate_is_not_approval(self):
        result=self._inspect()
        self.assertEqual(result["status"],
                         "EXACT_WHOLE_RASTER_CANDIDATE_REVIEW_REQUIRED")
        self.assertTrue(result["image_pixel_identity_verified"])
        self.assertTrue(result["caption_text_identity_verified"])
        for key in ("image_visible_completeness_certified",
                    "figure_semantics_certified",
                    "figure_panel_completeness_certified",
                    "tts_or_video_authorized",
                    "human_review_claimed"):
            self.assertFalse(result[key])
        self.assertEqual(result["pixel_dimensions"],[200,150])
        self.assertEqual((self.source.read_bytes(),self.slides.read_bytes()),
                         self.original)

    def test_different_raster_image_rejected(self):
        altered=self.root/"altered.png"
        with Image.open(self.png) as img:
            img.putpixel((55,33),(255,255,255))
            img.save(altered)
        self._pdf(self.slides,is_slide=True,image=altered)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "identity differs"):
            self._inspect()

    def test_cropped_reencoded_bitmap_rejected(self):
        cropped=self.root/"cropped.png"
        with Image.open(self.png) as img:
            img.crop((0,0,175,150)).resize((200,150)).save(cropped)
        self._pdf(self.slides,is_slide=True,image=cropped)
        with self.assertRaises(FigureIdentityReviewRequired):
            self._inspect()

    def test_caption_mismatch_rejected(self):
        self._pdf(self.slides,is_slide=True,
                  caption="Figure 2.3 A different physical phenomenon.")
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "caption absent"):
            self._inspect()

    def test_repeated_image_placement_rejected(self):
        self._pdf(self.slides,is_slide=True,repeated=True)
        with self.assertRaises(FigureIdentityReviewRequired):
            self._inspect()

    def test_reused_source_image_across_pages_rejected(self):
        self._pdf(self.source,is_slide=False,extra_page=True)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "reused"):
            self._inspect()

    def test_vector_overlay_rejected(self):
        self._pdf(self.slides,is_slide=True,vector=True)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "vector"):
            self._inspect()

    def test_mismatched_caption_identifier_rejected(self):
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "caption absent"):
            self._inspect(caption="Figure 2.4 A different caption.")

    def test_panel_caption_not_whole_figure_approval(self):
        self._pdf(self.source,is_slide=False,
                  caption="Figure 2.3 (a) Magnetic field.")
        self._pdf(self.slides,is_slide=True,
                  caption="Figure 2.3 (a) Magnetic field.")
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "Panel-labelled"):
            self._inspect(caption="Figure 2.3 (a) Magnetic field.")

    def test_image_too_small_rejected(self):
        self._pdf(self.slides,is_slide=True,
                  figure_rect=pymupdf.Rect(80,90,145,139))
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "too small"):
            self._inspect()

    def test_wrong_page_rejected(self):
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "invalid PDF page"):
            self._inspect(source_page=3)

    def test_symlinked_pdf_rejected_before_resolve_even_without_windows_privilege(self):
        with patch.object(Path, "is_symlink", autospec=True,
                          side_effect=lambda p: p == self.source):
            with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                        "Symlinked or junction"):
                self._inspect()

    def test_symlinked_parent_rejected_before_resolve(self):
        with patch.object(Path, "is_symlink", autospec=True,
                          side_effect=lambda p: p == self.root):
            with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                        "Symlinked or junction"):
                self._inspect()

    def test_identical_pdf_paths_rejected(self):
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "must be different"):
            self._inspect(slides=self.source)

    def test_unsafe_symlink_source_rejected(self):
        alias=self.root/"source_alias.pdf"
        try:
            alias.symlink_to(self.source)
        except OSError:
            self.skipTest("Windows symlink privilege unavailable")
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "Symlinked or junction"):
            self._inspect(source=alias)

if __name__ == "__main__":
    unittest.main()
