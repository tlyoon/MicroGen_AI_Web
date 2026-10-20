import unittest
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.math_aware_slide5_figure_candidates import mentions

class Figure83ReviewAnchorContractTests(unittest.TestCase):
    def test_named_tangent_sine_secant(self):
        self.assertEqual(mentions("inverse tangent branch"),["tangent"])
        self.assertEqual(mentions("arcsec function"),["secant"])
    def test_multiple_branches_are_not_single_target(self):
        self.assertEqual(mentions("sine and secant branches"),["sine","secant"])
    def test_unrelated_narration_has_no_auto_target(self):
        self.assertEqual(mentions("the principal domain is restricted"),[])
