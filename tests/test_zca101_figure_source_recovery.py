"""Regression checks for fail-closed source-verified figure repair."""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from selenium_pipeline.figure_composites import (
    FigureCompositeReviewRequired,
    require_non_destructive_destination,
    validate_and_prepare_mappings,
)
from selenium_pipeline.figure_source_recovery import reuse_verified_prior_panels


class VerifiedFigureRecoveryTests(unittest.TestCase):
    def test_identical_pixels_different_png_encoding_reuses_without_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "fig_1.png"
            dst = Path(td) / "Figure 8.5.png"
            Image.new("RGBA", (14, 12), (25, 51, 151, 255)).save(src, compress_level=0)
            Image.new("RGBA", (14, 12), (25, 51, 151, 255)).save(dst, compress_level=9)
            self.assertNotEqual(src.read_bytes(), dst.read_bytes())
            before = dst.read_bytes()
            self.assertTrue(require_non_destructive_destination(src, dst))
            self.assertEqual(before, dst.read_bytes())

    def test_single_changed_rgb_pixel_blocks_reuse(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "fig_1.png"
            dst = Path(td) / "Figure 8.5.png"
            a = Image.new("RGBA", (14, 12), (25, 51, 151, 255))
            a.save(src)
            a.putpixel((3, 4), (26, 51, 151, 255))
            a.save(dst)
            with self.assertRaises(FigureCompositeReviewRequired):
                require_non_destructive_destination(src, dst)

    def _fixtures(self, td):
        p = Path(td)
        root = p / "published"
        crops = p / "work" / "crops" / "page_4"
        root.mkdir()
        crops.mkdir(parents=True)
        a = Image.new("RGBA", (13, 10), (10, 10, 200, 255))
        b = Image.new("RGBA", (16, 8), (10, 200, 10, 255))
        a.save(crops / "fig_1.png", compress_level=0)
        b.save(crops / "fig_2.png", compress_level=0)
        a.save(root / "Figure 8.8a.png", compress_level=9)
        b.save(root / "Figure 8.8b.png", compress_level=9)
        parent = Image.new("RGBA", (29, 10), (0, 0, 0, 0))
        parent.paste(a, (0, 0))
        parent.paste(b, (13, 0))
        parent.save(root / "Figure 8.8.png")
        rows = [("fig_1.png", "Figure 8.8", "Figure 8.8.png"),
                ("fig_2.png", "Figure 8.8", "Figure 8.8.png")]
        return root, crops, rows

    def test_duplicate_parent_recovered_from_exact_prior_panels(self):
        with tempfile.TemporaryDirectory() as td:
            root, crops, rows = self._fixtures(td)
            with self.assertRaises(FigureCompositeReviewRequired):
                validate_and_prepare_mappings(rows)
            result = reuse_verified_prior_panels(rows, crops, (root,))
            self.assertEqual([r[2] for r in result],
                             ["Figure 8.8a.png", "Figure 8.8b.png"])
            self.assertEqual(len(validate_and_prepare_mappings(result)), 2)

    def test_corrupt_prior_parent_cannot_authorize_duplicate_repair(self):
        with tempfile.TemporaryDirectory() as td:
            root, crops, rows = self._fixtures(td)
            image = Image.open(root / "Figure 8.8.png").convert("RGBA")
            image.putpixel((3, 3), (150, 10, 10, 255))
            image.save(root / "Figure 8.8.png")
            result = reuse_verified_prior_panels(rows, crops, (root,))
            self.assertEqual(result, rows)
            with self.assertRaises(FigureCompositeReviewRequired):
                validate_and_prepare_mappings(result)

    def test_changed_prior_panel_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root, crops, rows = self._fixtures(td)
            im = Image.open(root / "Figure 8.8a.png").convert("RGBA")
            im.putpixel((0, 0), (100, 10, 200, 255))
            im.save(root / "Figure 8.8a.png")
            self.assertEqual(reuse_verified_prior_panels(rows, crops, (root,)), rows)

    def test_no_prior_assets_preserves_fail_closed_guard(self):
        with tempfile.TemporaryDirectory() as td:
            root, crops, rows = self._fixtures(td)
            empty = Path(td) / "empty"
            empty.mkdir()
            self.assertEqual(reuse_verified_prior_panels(rows, crops, (empty,)), rows)


if __name__ == "__main__":
    unittest.main()
