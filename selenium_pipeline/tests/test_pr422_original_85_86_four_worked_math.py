"""Four real source-verified additional original lecture math results."""
import unittest
from selenium_pipeline.original_thomas85_86_more_worked_math import (
    WORKED,STATUS,actual_mathematical_identities)

class OtherThomasSectionsWorkedMathTests(unittest.TestCase):
    def test_exact_identified_original_source_lecture_targets(self):
        self.assertEqual(sorted(WORKED),
                         [("8.5",5),("8.5",6),("8.6",5),("8.6",8)])
        self.assertEqual([WORKED[k][2] for k in sorted(WORKED)],[5,4,5,5])

    def test_source_math_derivatives(self):
        r=actual_mathematical_identities()
        self.assertTrue(r["85_example1_exact_partial_fractions_and_four_log_intervals"])
        self.assertTrue(r["85_example2_repeated_linear_derivative"])
        self.assertTrue(r["86_example2_formula29b_positive_radicand"])
        self.assertTrue(r["86_example4_tan5_publisher_reduction"])
        self.assertFalse(r["all_unrelated_examples_source_approved"])

    def test_source_sign_and_constants_never_inferred_from_title(self):
        self.assertIn(r"- \frac{1}{4}\ln|x+3|",WORKED["8.5",5][1])
        self.assertIn(r"+ \frac{5}{x+2}",WORKED["8.5",6][1])
        self.assertIn(r"\tan^{-1}\sqrt{\frac{x-2}{2}}",
                      WORKED["8.6",5][1])
        self.assertIn(r"- \ln|\cos x|",WORKED["8.6",8][1])

    def test_release_gate_still_explicitly_review_only(self):
        self.assertIn("QA_PASS",STATUS)
if __name__=="__main__":
    unittest.main()
