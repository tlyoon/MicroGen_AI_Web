import unittest
from selenium_pipeline.math_aware_slide5_figure_candidates import mentions

class MathPanelCandidateTests(unittest.TestCase):
    def test_unique_trig_branch(self):
        self.assertEqual(mentions('The tangent branch'), ['tangent'])
        self.assertEqual(mentions('On the sine branch'), ['sine'])
        self.assertEqual(mentions('The positive secant branch'), ['secant'])
    def test_two_branches_remain_unresolved(self):
        self.assertEqual(mentions('Tangent and secant differ'), ['tangent','secant'])
    def test_missing_named_branch_stays_unmapped(self):
        self.assertEqual(mentions('The sign of u is positive'), [])
