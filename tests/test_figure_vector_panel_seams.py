"""Real-PDF source vector gutter QA: synthetic fixtures, zero paid services."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_vector_panel_seams import inspect_vector_panel_seams

REGION=[40,40,340,140]
PANELS=[[40,40,140,140],[140,40,240,140],[240,40,340,140]]
CAPTION="Figure 8.3 Vector composite field patterns"


class VectorGutterTests(unittest.TestCase):
    def setUp(self):
        self.work=tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root=Path(self.work.name)
        self.src=self.root/"source.pdf"
        self.dst=self.root/"slides.pdf"

    def create_pdf_pair(self, *, mark_near_seam=False, hide_label=False,
                        caption=CAPTION, add_crossing_path=False):
        with pymupdf.open() as pdf:
            p=pdf.new_page(width=420,height=260)
            for i in range(3):
                if not (hide_label and i==1):
                    p.insert_text((55+i*100,65),f"({chr(97+i)})",fontsize=12)
                p.draw_rect(pymupdf.Rect(75+i*100,85,105+i*100,105),
                            color=(0,0,0),width=1)
            if mark_near_seam:
                # Entirely within panel (a) but within seam safety stripe
                p.draw_rect(pymupdf.Rect(138,112,139,125),
                            color=(1,0,0),fill=(1,0,0),width=.3)
            if add_crossing_path:
                p.draw_line((135,120),(145,120),color=(1,0,0))
            p.insert_text((50,158),caption,fontsize=10)
            pixels=p.get_pixmap(matrix=pymupdf.Matrix(2,2),
                 clip=pymupdf.Rect(REGION),colorspace=pymupdf.csRGB,
                 alpha=False)
            pdf.save(self.src)
        with pymupdf.open() as pdf:
            p=pdf.new_page(width=420,height=260)
            p.insert_image(pymupdf.Rect(REGION),
                           stream=pixels.tobytes("png"),keep_proportion=False)
            p.insert_text((50,158),caption,fontsize=10)
            pdf.save(self.dst)

    def inspect(self, **overrides):
        args=dict(source=self.src,slides=self.dst,source_page=1,
                  slide_page=1,source_bbox=REGION,slide_bbox=REGION,
                  panel_boxes=PANELS,caption=CAPTION,panel_ids=["a","b","c"])
        args.update(overrides)
        return inspect_vector_panel_seams(**args)

    def test_full_source_vector_gutters_are_positive_but_not_semantic_proof(self):
        self.create_pdf_pair()
        r=self.inspect()
        self.assertTrue(r["source_panel_label_geometry_verified"])
        self.assertTrue(r["panel_gutter_stripes_verified"])
        self.assertEqual(r["declared_seam_count"],2)
        for key in ("true_panel_boundary_semantics_certified",
                    "source_panel_semantic_boundaries_certified",
                    "figure_panel_completeness_certified",
                    "figure_semantics_certified","tts_or_video_authorized",
                    "human_review_claimed"):
            self.assertFalse(r[key])
        self.assertFalse((self.root/"element_wav").exists())

    def test_nonwhite_stroke_near_seam_rejected_even_when_parent_mapping_passes(self):
        self.create_pdf_pair(mark_near_seam=True)
        from selenium_pipeline.figure_vector_provenance import inspect_vector_figure_region
        r=inspect_vector_figure_region(
            source=self.src,slides=self.dst,source_page=1,slide_page=1,
            source_bbox=REGION,slide_bbox=REGION,panel_boxes=PANELS,
            caption=CAPTION,panel_ids=["a","b","c"])
        self.assertTrue(r["source_slide_rendered_equivalence_verified"])
        with self.assertRaisesRegex(FigureIdentityReviewRequired,"nonwhite"):
            self.inspect()

    def test_crossing_vector_seam_rejected_by_parent_proof(self):
        self.create_pdf_pair(add_crossing_path=True)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,"crosses"):
            self.inspect()

    def test_missing_original_pdf_panel_label_rejected(self):
        self.create_pdf_pair(hide_label=True)
        with self.assertRaises(FigureIdentityReviewRequired):
            self.inspect()

    def test_wrong_caption_rejected(self):
        self.create_pdf_pair()
        with self.assertRaises(FigureIdentityReviewRequired):
            self.inspect(caption="Figure 8.4 Wrong figure")

    def test_bad_stripe_parameter_rejected(self):
        self.create_pdf_pair()
        for bad in (True,2.1,0,-1,9,"3",None):
            with self.subTest(bad=bad),self.assertRaises(FigureIdentityReviewRequired):
                self.inspect(gutter_half_width_px=bad)

    def test_plausibly_shifted_seam_still_not_semantically_approved(self):
        self.create_pdf_pair()
        shifted=[[40,40,135,140],[135,40,240,140],[240,40,340,140]]
        r=self.inspect(panel_boxes=shifted)
        self.assertTrue(r["panel_gutter_stripes_verified"])
        self.assertFalse(r["source_panel_semantic_boundaries_certified"])
        self.assertFalse(r["tts_or_video_authorized"])


if __name__ == "__main__":
    unittest.main()
