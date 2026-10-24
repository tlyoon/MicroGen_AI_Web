"""Actual source-to-slide *pixel* evidence with adversarial mismatches."""
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from selenium_pipeline.original_figure82_pixel_registration import (
    inspect_original_figure82_pixel_registration, score_registered_pixels,
)


def arrays():
    rng=np.random.default_rng(20261025)
    target=rng.integers(0,256,size=(134,409),dtype=np.uint8)
    source=np.full((900,1000),255,dtype=np.uint8)
    source[400:534,300:709]=target
    return source,target


class SourceFigurePixelIdentity(unittest.TestCase):
    def score(self,source=None,target=None,roi=(240,320,780,600),
              cuts=(0,120,246,409)):
        goodsource,goodtarget=arrays()
        return score_registered_pixels(
            original_page_gray=goodsource if source is None else source,
            slide_gray=goodtarget if target is None else target,
            scan_box_px=roi,strip_boundaries_px=cuts)

    def test_exact_original_composite_and_three_strips_register(self):
        result=self.score()
        self.assertAlmostEqual(result["full_figure_normalized_pixel_correlation"],1,places=5)
        self.assertEqual(result["full_figure_grayscale_mean_absolute_difference"],0)
        self.assertEqual(result["matching_source_pixel_box_at_render_scale"],
                         [300,400,709,534])
        self.assertEqual(result["individual_strip_count"],3)
        self.assertFalse(result["triangle_meanings_or_side_labels_verified"])
        self.assertTrue(all(not p["source_triangle_semantics_verified"]
                            for p in result["strip_pixel_registration_metrics"]))

    def test_shifted_or_unrelated_source_region_fails_closed(self):
        with self.assertRaises(ValueError):
            self.score(roi=(100,80,650,270))

    def test_incorrect_or_swapped_figure_raster_is_rejected(self):
        source,target=arrays()
        with self.assertRaises(ValueError):
            self.score(source=source,target=target[:,::-1].copy())

    def test_blank_and_corrupt_composite_are_rejected(self):
        source,target=arrays()
        with self.assertRaises(ValueError):
            self.score(source=source,target=np.full_like(target,255))
        changed=target.copy()
        changed[:,120:246]=255-target[:,120:246]
        with self.assertRaises(ValueError):
            self.score(source=source,target=changed)

    def test_invalid_or_overlapping_strip_bounds_cannot_pass(self):
        for cuts in ((0,120,200,300),(0,246,120,409),
                     (0,120,120,409),(0,20,220,409),(0,120,246,409,410)):
            with self.subTest(cuts=cuts), self.assertRaises(ValueError):
                self.score(cuts=cuts)

    def test_huge_source_image_refused(self):
        # Even plausible copied target data may not bypass bounded memory.
        source,target=arrays()
        with self.assertRaises(ValueError):
            self.score(source=np.full((4000,4000),255,dtype=np.uint8),
                       target=target)

    def test_uninformative_or_undersize_source_region_refused(self):
        source,target=arrays()
        with self.assertRaises(ValueError):
            self.score(source=source,roi=(280,395,550,490))

    def test_real_source_only_when_separately_accessible_and_authorized(self):
        # GitHub Actions is NOT an authorized local textbook mount.
        root=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not root:
            self.skipTest("User-owned original textbook available only on authorized PC")
        report=inspect_original_figure82_pixel_registration(folder=Path(root))
        self.assertTrue(report["original_source_to_slide_pixel_similarity_accepted"])
        self.assertEqual(report["individual_strip_count"],3)
        self.assertFalse(report["independent_AI_mathematical_consensus_verified"])
        self.assertFalse(report["student_publication_authorized"])


if __name__=="__main__":
    unittest.main()
