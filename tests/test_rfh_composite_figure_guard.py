"""RFH Figure Fidelity regression tests: no lossy multipart mapping."""
import unittest
from selenium_pipeline.figure_composites import (
    FigureCompositeReviewRequired,
    normalized_target_filename,
    validate_and_prepare_mappings,
)


class CompositeFigureMappingTests(unittest.TestCase):
    def test_three_separately_named_panels_preserved(self):
        rows = [
            ("fig_1.png", "Figure 2.10 (a)", "Figure 2.10 (a).png"),
            ("fig_2.png", "Figure 2.10 (b)", "Figure 2.10 (b).png"),
            ("fig_3.png", "Figure 2.10 (c)", "Figure 2.10 (c).png"),
        ]
        self.assertEqual(validate_and_prepare_mappings(rows), rows)

    def test_single_complete_parent_not_claimed_verified_by_this_test(self):
        result = validate_and_prepare_mappings([
            ("fig_1.png", "Figure 2.10", "Figure 2.10.png"),
        ])
        self.assertEqual(result[0][-1], "Figure 2.10.png")
        # The crop's true visual completeness needs a later source-space gate.

    def test_single_panel_mislabeled_full_figure_rejected(self):
        with self.assertRaises(FigureCompositeReviewRequired) as ctx:
            validate_and_prepare_mappings([
                ("fig_1.png", "Figure 2.10 (a)", "Figure 2.10.png"),
            ])
        self.assertIn("panel_identifier_mismatch",
                      [item["reason"] for item in ctx.exception.issues])

    def test_horizontally_merged_composite_without_layout_rejected(self):
        with self.assertRaises(FigureCompositeReviewRequired) as ctx:
            validate_and_prepare_mappings([
                ("fig_1.png", "Figure 2.10", "Figure 2.10.png"),
                ("fig_2.png", "Figure 2.10", "Figure 2.10.png"),
                ("fig_3.png", "Figure 2.10", "Figure 2.10.png"),
            ])
        self.assertIn("ambiguous_duplicate_target_no_layout_provenance",
                      [item["reason"] for item in ctx.exception.issues])

    def test_mixed_parent_and_individual_panel_rejected(self):
        with self.assertRaises(FigureCompositeReviewRequired) as ctx:
            validate_and_prepare_mappings([
                ("fig_1.png", "Figure 2.10", "Figure 2.10.png"),
                ("fig_2.png", "Figure 2.10 (a)", "Figure 2.10 (a).png"),
            ])
        self.assertIn("mixed_parent_and_subpanel_crops",
                      [item["reason"] for item in ctx.exception.issues])

    def test_hallucinated_target_figure_number_rejected(self):
        with self.assertRaises(FigureCompositeReviewRequired) as ctx:
            validate_and_prepare_mappings([
                ("fig_1.png", "Figure 2.10", "Figure 2.11.png"),
            ])
        self.assertIn("figure_number_mismatch",
                      [item["reason"] for item in ctx.exception.issues])

    def test_filename_collision_after_sanitization_rejected(self):
        with self.assertRaises(FigureCompositeReviewRequired) as ctx:
            validate_and_prepare_mappings([
                ("fig_1.png", "Unlabeled image", "figure: one.png"),
                ("fig_2.png", "Unlabeled image", "figure? one.png"),
            ])
        self.assertEqual(ctx.exception.issues[0]["reason"],
                         "ambiguous_duplicate_target_no_layout_provenance")

    def test_no_path_traversal(self):
        for unsafe in ("../figure.png", "subdir/figure.png",
                       r"C:\temp\image.png", ""):
            with self.subTest(unsafe=unsafe):
                with self.assertRaises(FigureCompositeReviewRequired):
                    normalized_target_filename(unsafe)

    def test_canonicalization_does_not_change_valid_filenames(self):
        self.assertEqual(normalized_target_filename("Figure 2.10 (a).png"),
                         "Figure 2.10 (a).png")
        self.assertEqual(normalized_target_filename("Fig_2_10.png"),
                         "Fig_2_10.png")

    def test_rejects_misnumbered_subpanel(self):
        with self.assertRaises(FigureCompositeReviewRequired):
            validate_and_prepare_mappings([
                ("fig_1.png", "Fig. 2.10 (b)", "Figure 2.10 (c).png"),
            ])

    def test_rejects_overwrite_of_previously_published_figure(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from selenium_pipeline.figure_composites import require_non_destructive_destination
        with TemporaryDirectory() as td:
            src = Path(td) / "fig_1.png"
            dst = Path(td) / "Figure 2.10.png"
            src.write_bytes(b"new, partial crop")
            dst.write_bytes(b"existing original composite")
            with self.assertRaises(FigureCompositeReviewRequired):
                require_non_destructive_destination(src, dst)
            self.assertEqual(dst.read_bytes(), b"existing original composite")

    def test_idempotent_same_bytes_can_be_reused(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from selenium_pipeline.figure_composites import require_non_destructive_destination
        with TemporaryDirectory() as td:
            src = Path(td) / "fig_1.png"
            dst = Path(td) / "Figure 2.10.png"
            src.write_bytes(b"same data")
            dst.write_bytes(b"same data")
            self.assertTrue(require_non_destructive_destination(src, dst))

    def test_new_destination_is_safe(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from selenium_pipeline.figure_composites import require_non_destructive_destination
        with TemporaryDirectory() as td:
            src = Path(td) / "fig_1.png"
            dst = Path(td) / "Figure 2.10.png"
            src.write_bytes(b"cropped image")
            self.assertFalse(require_non_destructive_destination(src, dst))
            self.assertFalse(dst.exists())


if __name__ == "__main__":
    unittest.main()
