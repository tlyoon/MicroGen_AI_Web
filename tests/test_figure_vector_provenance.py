"""Adversarial PDF-backed source-vector/slide-raster candidate tests."""
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_vector_provenance import inspect_vector_figure_region


REGION = [40, 40, 340, 140]
PANELS = [[40, 40, 140, 140], [140, 40, 240, 140],
          [240, 40, 340, 140]]
CAPTION = "Figure 8.3 Three vector panels"


class VectorFigureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.pdf"
        self.slides = self.root / "slides.pdf"

    def make_pair(self, *, labels=("a", "b", "c"), source_raster=False,
                  slide_occlusion=False, slide_wrong=False,
                  crossing=False, caption=CAPTION):
        with pymupdf.open() as doc:
            page = doc.new_page(width=400, height=260)
            for i, letter in enumerate(labels):
                page.insert_text((55 + 100 * i, 65), f"({letter})",
                                 fontsize=12)
            for i in range(3):
                x = 75 + 100 * i
                shape = page.new_shape()
                shape.draw_rect(pymupdf.Rect(x, 85, x + 30, 105))
                shape.finish(color=(0, 0, 0), fill=None)
                shape.commit()
            if crossing:
                page.draw_line((135, 120), (145, 120))
            if source_raster:
                with pymupdf.open() as bitmap:
                    bp = bitmap.new_page(width=20, height=20)
                    bp.draw_rect(pymupdf.Rect(2, 2, 18, 18))
                    pix = bp.get_pixmap()
                    page.insert_image(pymupdf.Rect(60, 110, 80, 130),
                                      pixmap=pix)
            page.insert_text((50, 158), caption, fontsize=10)
            source_pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2),
                                         clip=pymupdf.Rect(REGION),
                                         colorspace=pymupdf.csRGB, alpha=False)
            doc.save(self.source)
        with pymupdf.open() as doc:
            page = doc.new_page(width=400, height=260)
            page.insert_image(pymupdf.Rect(REGION),
                              stream=source_pix.tobytes("png"),
                              keep_proportion=False)
            page.insert_text((50, 158), caption, fontsize=10)
            if slide_occlusion:
                page.draw_rect(pymupdf.Rect(90, 95, 110, 110),
                               fill=(1, 0, 0))
            if slide_wrong:
                page.insert_text((110, 90), "X", fontsize=20)
            doc.save(self.slides)

    def check(self, **overrides):
        kw = dict(source=self.source, slides=self.slides,
                  source_page=1, slide_page=1,
                  source_bbox=REGION, slide_bbox=REGION,
                  panel_boxes=PANELS, panel_ids=["a", "b", "c"],
                  caption=CAPTION)
        kw.update(overrides)
        return inspect_vector_figure_region(**kw)

    def test_exact_source_vector_to_raster_candidate(self):
        self.make_pair()
        result = self.check()
        self.assertTrue(result["source_panel_label_geometry_verified"])
        self.assertTrue(result["source_slide_rendered_equivalence_verified"])
        self.assertEqual([p["label"] for p in result["panels"]],
                         ["a", "b", "c"])
        self.assertFalse(result["figure_panel_completeness_certified"])
        self.assertFalse(result["tts_or_video_authorized"])

    def test_missing_label_rejected(self):
        self.make_pair(labels=("a", "b"))
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check()

    def test_duplicate_label_rejected(self):
        self.make_pair(labels=("a", "a", "c"))
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check()

    def test_plausible_wrong_partition_never_certifies_semantics(self):
        # A slightly shifted boundary crosses no PDF path. Geometry alone
        # cannot prove it is the author's intended panel division.
        self.make_pair()
        candidate=self.check(panel_boxes=[[40, 40, 135, 140],
                                          [135, 40, 240, 140],
                                          [240, 40, 340, 140]])
        self.assertFalse(candidate["true_panel_boundary_semantics_certified"])
        self.assertFalse(candidate["figure_panel_completeness_certified"])
        self.assertFalse(candidate["tts_or_video_authorized"])

    def test_vector_path_crosses_declared_panel_rejected(self):
        self.make_pair(crossing=True)
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check()

    def test_source_raster_rejected(self):
        self.make_pair(source_raster=True)
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check()

    def test_slide_vector_overlay_rejected(self):
        self.make_pair(slide_occlusion=True)
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check()

    def test_slide_text_overlay_rejected(self):
        self.make_pair(slide_wrong=True)
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check()

    def test_mismatched_caption_rejected(self):
        self.make_pair()
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check(caption="Figure 8.4 Different figure")

    def test_invalid_label_order_rejected(self):
        self.make_pair()
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check(panel_ids=["b", "a", "c"])

    def test_symlink_input_rejected_when_supported(self):
        self.make_pair()
        link = self.root / "source_link.pdf"
        try:
            link.symlink_to(self.source)
        except (OSError, NotImplementedError):
            self.skipTest("OS forbids symlink creation")
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check(source=link)


if __name__ == "__main__":
    unittest.main()
