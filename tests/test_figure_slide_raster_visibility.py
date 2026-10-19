"""Do not confuse verified slide bitmap visibility with original source art."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_slide_raster_visibility import (
    audit_vector_source_slide_raster, main,
)


class SlideRasterVisibilityTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.source = Path(tmp.name) / "source.pdf"
        self.slides = Path(tmp.name) / "slides.pdf"

    def create(self, *, overlay=False, duplicate=False, no_bitmap=False,
               original_bitmap=False, distortion=False, tiny_inline=False):
        with pymupdf.open() as icon:
            page = icon.new_page(width=200, height=80)
            page.draw_line((10, 60), (190, 12), color=(.1, .5, .9), width=3)
            page.draw_rect(pymupdf.Rect(25, 30, 45, 53), color=(0, 0, 0))
            png = page.get_pixmap(alpha=False).tobytes("png")
        with pymupdf.open() as bullet_pdf:
            bullet = bullet_pdf.new_page(width=6, height=6)
            bullet.draw_rect(pymupdf.Rect(0, 0, 6, 6),
                             color=(1, .25, .25))
            small_png = bullet.get_pixmap(alpha=False).tobytes("png")
        with pymupdf.open() as pdf:
            p = pdf.new_page(width=610, height=700)
            p.draw_line((35, 170), (180, 275), color=(0, 0, 0))
            p.insert_text((30, 405), "FIGURE 8.3", fontsize=11)
            p.insert_text((30, 425), "Graphs of inverse functions", fontsize=8)
            if original_bitmap:
                p.insert_image(pymupdf.Rect(325, 80, 525, 160), stream=png)
            pdf.save(self.source)
        with pymupdf.open() as pdf:
            p = pdf.new_page(width=480, height=360)
            rect = pymupdf.Rect(85, 65, 285, 195 if distortion else 145)
            if not no_bitmap:
                p.insert_image(rect, stream=png, keep_proportion=False)
                if duplicate:
                    p.insert_image(pymupdf.Rect(85, 225, 285, 305),
                                   stream=png)
            if tiny_inline:
                p.insert_image(pymupdf.Rect(12, 12, 18, 18), stream=small_png)
            if overlay:
                p.draw_line((90, 75), (265, 140),
                            color=(1, 0, 0), width=6)
            pdf.save(self.slides)
    def inspect(self, **kwargs):
        args = dict(source=self.source, slides=self.slides,
                    source_page=1, slide_page=1, figure_id="8.3")
        args.update(kwargs)
        return audit_vector_source_slide_raster(**args)

    def test_visible_bitmap_not_authoritative_source_proof(self):
        self.create()
        before = [hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (self.source, self.slides)]
        result = self.inspect()
        self.assertEqual(result["status"],
                         "VISIBLE_SLIDE_RASTER_ONLY_SOURCE_FIGURE_UNVERIFIED")
        self.assertTrue(result["slide_reference_render_pixels_equal"])
        self.assertEqual(result["source_image_instances"], 0)
        self.assertEqual(result["slide_image_instances"], 1)
        self.assertEqual(result["slide_material_image_instances"], 1)
        self.assertEqual(result["slide_embedded_raster_dimensions"], [200, 80])
        self.assertEqual(len(result["slide_embedded_encoded_sha256"]), 64)
        for field in ("original_complete_figure_proven",
                      "original_panel_count_and_labels_proven",
                      "source_to_slide_figure_identity_proven",
                      "scientific_semantics_proven",
                      "narrated_highlight_proven",
                      "encoded_video_accepted",
                      "student_publication_authorized"):
            self.assertIs(result[field], False)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (self.source, self.slides)])

    def test_rendered_overlay_masks_embedded_raster(self):
        self.create(overlay=True)
        result = self.inspect()
        self.assertEqual(result["status"],
                         "SLIDE_RASTER_VISIBLE_PIXELS_DIFFER_REVIEW_REQUIRED")
        self.assertFalse(result["slide_reference_render_pixels_equal"])

    def test_duplicate_placement_is_ambiguous(self):
        self.create(duplicate=True)
        result = self.inspect()
        self.assertEqual(result["slide_image_instances"], 2)
        self.assertEqual(result["status"],
                         "SLIDE_MATERIAL_IMAGE_MISSING_OR_MULTIPLE_REVIEW_REQUIRED")

    def test_tiny_inline_decorations_are_not_figure_rasters(self):
        self.create(tiny_inline=True)
        result = self.inspect()
        self.assertEqual(result["slide_image_instances"], 2)
        self.assertEqual(result["slide_material_image_instances"], 1)
        self.assertEqual(result["slide_tiny_image_instances"], 1)
        self.assertTrue(result["slide_reference_render_pixels_equal"])
        self.assertFalse(result["source_to_slide_figure_identity_proven"])

    def test_no_slide_bitmap_never_certifies(self):
        self.create(no_bitmap=True)
        result = self.inspect()
        self.assertEqual(result["slide_image_instances"], 0)
        self.assertFalse(result["source_to_slide_figure_identity_proven"])
    def test_original_source_with_raster_is_not_vector_only(self):
        self.create(original_bitmap=True)
        result = self.inspect()
        self.assertEqual(result["source_image_instances"], 1)
        self.assertEqual(result["status"],
                         "SOURCE_NOT_EXCLUSIVELY_VECTOR_REVIEW_REQUIRED")

    def test_distorted_raster_placement_blocks(self):
        self.create(distortion=True)
        result = self.inspect()
        self.assertEqual(result["status"],
                         "SLIDE_RASTER_PLACEMENT_AMBIGUOUS_REVIEW_REQUIRED")

    def test_bad_page_figure_and_missing_file_block(self):
        self.create()
        for change in (dict(source_page=0), dict(slide_page=2),
                       dict(slide_page=True), dict(figure_id="8.4"),
                       dict(slides=self.slides.parent / "missing.pdf")):
            with self.subTest(change=change):
                with self.assertRaises(FigureIdentityReviewRequired):
                    self.inspect(**change)

    def test_cli_exit_two_even_if_visible(self):
        self.create()
        self.assertEqual(main([
            "--source", str(self.source), "--slides", str(self.slides),
            "--source-page", "1", "--slide-page", "1",
            "--figure-id", "8.3",
        ]), 2)
