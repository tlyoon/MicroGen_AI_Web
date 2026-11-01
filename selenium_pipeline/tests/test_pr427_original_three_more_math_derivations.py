"""Scientifically verify exact publisher operators before adding math scene."""
import unittest
from selenium_pipeline.original_thomas85_86_derivation_audio_pixels import (
    CASES,STATUS,sympy_source_math)

class ThreeOriginalPublisherDerivations(unittest.TestCase):
    def test_original_slide_number_and_two_separate_acoustic_events(self):
        self.assertEqual(sorted(CASES),[("8.5",7),("8.5",8),("8.6",7)])
        self.assertEqual([len(CASES[k]["events"]) for k in sorted(CASES)],
                         [2,2,2])
    def test_original_publisher_math_derivatives_all_verified(self):
        result=sympy_source_math()
        self.assertTrue(all(value is True for key,value in result.items()
                            if key!="all_remaining_slide_formulas_mathematically_approved"))
        self.assertFalse(result["all_remaining_slide_formulas_mathematically_approved"])
    def test_exact_source_sign_and_domain_formula_requires_operator(self):
        self.assertIn(r"+ \frac{5x-3}{x^2-2x-3}",CASES["8.5",7]["math_tex"][0])
        self.assertIn(r"- 2\ln|x-1|",CASES["8.5",8]["math_tex"][-1])
        self.assertIn(r"- \frac{1}{x-1}",CASES["8.5",8]["math_tex"][-1])
        self.assertIn(r"(n \neq 1)",CASES["8.6",7]["math_tex"][0])
        self.assertIn(r"(n \neq -m)",CASES["8.6",7]["math_tex"][-1])
    def test_real_original_voice_per_equation_not_guessed(self):
        self.assertEqual([e[1] for e in CASES["8.5",7]["events"]],[4,5])
        self.assertEqual([e[1] for e in CASES["8.5",8]["events"]],[3,4])
        self.assertEqual([e[1] for e in CASES["8.6",7]["events"]],[1,3])
        self.assertIn("PIXEL_EVENTS_PASS",STATUS)
if __name__=="__main__":
    unittest.main()
