"""Check spoken expression specificity and source equality-chain integrity."""
import unittest
from selenium_pipeline.original_thomas84_slide12_synchronized_math import (
    is_complete_sine_radical_explanation)
from selenium_pipeline.original_thomas84_equation_provenance import match_line

class OriginalSlide12MathSyncTests(unittest.TestCase):
    def test_original_spoken_sine_to_cosine_expression(self):
        self.assertTrue(is_complete_sine_radical_explanation(
            "The radical expression becomes nine minus nine times the sine squared of theta, "
            "which factors into nine times the cosine squared of theta."))
    def test_both_trig_functions_must_be_spoken(self):
        self.assertFalse(is_complete_sine_radical_explanation(
            "The radical becomes nine minus nine times the sine squared of theta."))
        self.assertFalse(is_complete_sine_radical_explanation(
            "It becomes nine times the cosine squared of theta."))
    def test_wrong_result_is_not_acoustically_matched(self):
        self.assertFalse(is_complete_sine_radical_explanation(
            "nine minus nine times the sine squared of theta equals "
            "nine times the tangent squared of theta."))
    def test_original_book_first_last_chain_requires_exact_sign(self):
        src="9 - x2 = 9 - 9 sin2 u = 9(1 - sin2 u) = 9 cos2 u."
        self.assertEqual(len(match_line("9 −x2 = 9 cos2 θ",[[src]],slide=12)),1)
        self.assertEqual(match_line("9 + x2 = 9 cos2 θ",[[src]],slide=12),[])
        self.assertEqual(match_line("9 −x2 = 9 sin2 θ",[[src]],slide=12),[])

if __name__=="__main__":
    unittest.main()
