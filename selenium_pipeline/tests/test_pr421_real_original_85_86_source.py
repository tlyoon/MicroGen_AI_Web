"""Original Thomas §8.5/8.6 source math must not silently drift."""
import unittest
from selenium_pipeline.original_thomas85_86_first_math_highlights import (
    SOURCE,STATUS,symbolic_integrity)

class OriginalTwoAdditionalSectionMathProof(unittest.TestCase):
    def test_real_original_sections_and_page_counts(self):
        self.assertEqual(set(SOURCE),{"8.5","8.6"})
        self.assertEqual(SOURCE["8.5"]["slides"],11)
        self.assertEqual(SOURCE["8.6"]["slides"],13)
        self.assertEqual(SOURCE["8.5"]["target"],3)
        self.assertEqual(SOURCE["8.6"]["target"],4)

    def test_source_mathematical_full_formula_operators_retained(self):
        self.assertIn(r"\frac{2}{x+1}",SOURCE["8.5"]["original_tex_required"][0])
        self.assertIn(r"\frac{3}{x-3}",SOURCE["8.5"]["original_tex_required"][0])
        self.assertIn(r"2 \ln|x+1|",SOURCE["8.5"]["original_tex_required"][1])
        self.assertIn(r"3 \ln|x-3|",SOURCE["8.5"]["original_tex_required"][1])
        self.assertIn(r"- \frac{5}{4}",SOURCE["8.6"]["original_tex_required"][0])
        self.assertIn(r"\ln|2x+5|",SOURCE["8.6"]["original_tex_required"][0])

    def test_independent_sympy_proves_decomposition_and_both_log_domains(self):
        result=symbolic_integrity()
        self.assertTrue(result["source_85_exact_decomposition_identity"])
        self.assertTrue(result["source_85_log_antiderivative_three_real_intervals"])
        self.assertTrue(result["source_86_formula24_two_real_intervals"])
        self.assertFalse(result["poles_and_logarithm_domain_ignored"])

    def test_no_false_full_lecture_acceptance_in_status(self):
        self.assertIn("REVIEW_ONLY",STATUS)
        self.assertEqual(
            [event[0] for event in SOURCE["8.5"]["events"]],
            ["publisher_partial_fraction_identity",
             "publisher_logarithmic_antiderivative"])
        self.assertEqual(
            SOURCE["8.6"]["events"][0][0],
            "formula24_original_analytic_antiderivative")

if __name__=="__main__":
    unittest.main()
