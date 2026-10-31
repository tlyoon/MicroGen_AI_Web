"""The original Example 1 algebra narration must unambiguously describe both terms."""
import unittest
from selenium_pipeline.original_thomas84_slide9_synchronized_math import is_complete_example1_explanation
from selenium_pipeline.original_thomas84_equation_provenance import match_line

class OriginalSlide9SyncTests(unittest.TestCase):
    def test_complete_actual_math_narration_is_identified(self):
        script=("Substituting this into the radical expression, four plus x "
                "squared becomes four plus four times the tangent squared of theta, "
                "which factors into four times the quantity one plus the tangent "
                "squared of theta, simplifying to four times the secant squared of theta.")
        self.assertTrue(is_complete_example1_explanation(script))
    def test_not_highlighting_setup_before_equation(self):
        self.assertFalse(is_complete_example1_explanation(
            "We choose substitution x equals two times the tangent of theta, "
            "so dx equals two times the secant squared of theta."))
    def test_missing_result_is_not_equation_explanation(self):
        self.assertFalse(is_complete_example1_explanation(
            "four plus four times the tangent squared of theta"))
    def test_wrong_function_final_result_not_approved(self):
        self.assertFalse(is_complete_example1_explanation(
            "four plus four times the tangent squared of theta "
            "simplifies to four times the sine squared of theta"))
    def test_source_full_chain_operator_integrity(self):
        original="4 + x2 = 4 + 4 tan2 u = 4(1 + tan2 u) = 4 sec2 u."
        good="4 + x2 = 4 + 4 tan2 θ = 4(1 + tan2 θ) = 4 sec2 θ"
        bad="4 + x2 = 4 + 4 tan2 θ = 4(1 - tan2 θ) = 4 sec2 θ"
        self.assertEqual(len(match_line(good,[[original]],slide=9)),1)
        self.assertEqual(match_line(bad,[[original]],slide=9),[])

if __name__=="__main__":
    unittest.main()
