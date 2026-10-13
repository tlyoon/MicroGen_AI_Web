"""Integrated, source-free figure pipeline safety regression.

Reproduces the *geometry and naming* of a complete three-panel wide figure,
not the copyrighted textbook figure itself or educational-content verification.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from selenium_pipeline.figure_composites import (
    FigureCompositeReviewRequired, validate_and_prepare_mappings,
)
from selenium_pipeline.latex_graphics_bounds import bound_beamer_graphics
from selenium_pipeline.figure_legibility import audit_wide_figure_legibility


class FigureGuardIntegrationTests(unittest.TestCase):
    def test_same_figure_preserves_panels_and_rejects_narrow_beamer_layout(self):
        self.assertEqual(
            validate_and_prepare_mappings([
                ("wide_original.png", "Figure 2.10 composite",
                 "Figure 2.10.png")
            ])[0][2], "Figure 2.10.png"
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            Image.new("RGB", (784, 234), "white").save(root/"Figure 2.10.png")
            latex = (
                r"\begin{frame}{Understanding limits}" + "\n"
                r"\begin{columns}" + "\n"
                r"\begin{column}{0.50\textwidth}" + "\n"
                r"\includegraphics[height=0.55\textheight,keepaspectratio]{Figure 2.10.png}"
                + "\n" + r"\end{column}" + "\n"
                r"\end{columns}" + "\n" + r"\end{frame}"
            )
            rewritten, n = bound_beamer_graphics(latex)
            self.assertGreaterEqual(n, 1)
            self.assertIn(r"width=\linewidth", rewritten)
            issues = audit_wide_figure_legibility(rewritten, root)
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0]["recommendation"], "dedicated_full_width_figure_frame")
            self.assertEqual(issues[0]["image"], "Figure 2.10.png")

            safe = (
                r"\begin{frame}{Complete composite}" + "\n"
                r"\includegraphics[width=0.93\textwidth,height=0.66\textheight,"
                r"keepaspectratio]{Figure 2.10.png}" + "\n" + r"\end{frame}"
            )
            self.assertEqual(audit_wide_figure_legibility(safe, root), [])

    def test_mislabelled_panel_and_parent_collision_blocked_before_copy(self):
        cases = [
            [("crop1.png", "Figure 2.10 (a)", "Figure 2.10 (b).png")],
            [
                ("parent.png", "Figure 2.10", "Figure 2.10.png"),
                ("panel.png", "Figure 2.10 (a)", "Figure 2.10 (a).png"),
            ],
            [
                ("a.png", "Figure 2.10 (a)", "Figure 2.10.png"),
                ("b.png", "Figure 2.10 (b)", "Figure 2.10.png"),
            ],
        ]
        for triples in cases:
            with self.subTest(triples=triples), self.assertRaises(
                FigureCompositeReviewRequired
            ):
                validate_and_prepare_mappings(triples)


if __name__ == "__main__":
    unittest.main()
