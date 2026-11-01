"""Publisher's Heaviside coefficients and normalized erf are source-grounded."""
import unittest
from selenium_pipeline.original_thomas85_86_coverup_erf_source import (
    CASES,STATUS,mathematical_proof)
from selenium_pipeline.original_thomas85_86_derivation_audio_pixels import CASES as PREVIOUS

class TwoGenuinePublisherMathAndApplicationScenes(unittest.TestCase):
    def test_only_new_original_source_covered(self):
        self.assertEqual(sorted(CASES),[("8.5",9),("8.6",10)])
        self.assertEqual([len(CASES[k]["events"]) for k in sorted(CASES)],[2,2])
        self.assertFalse(set(CASES)&set(PREVIOUS))
    def test_exact_source_calculus_without_fake_non_elementarity_proof(self):
        result=mathematical_proof()
        self.assertTrue(result["85_exact_heaviside_partial_fraction_coefficients"])
        self.assertTrue(result["85_log_primitive_four_pole_separated_intervals"])
        self.assertTrue(result["86_error_function_normalization_and_derivative"])
        self.assertFalse(result["86_full_nonnelementary_classification_proved"])
    def test_critical_source_signs_and_coefficients(self):
        self.assertIn(r"-\frac{2}{5}",CASES["8.5",9]["math_tex"][0])
        self.assertIn(r"+ \frac{3}{7}",CASES["8.5",9]["math_tex"][1])
        self.assertIn(r"- \frac{1}{35}",CASES["8.5",9]["math_tex"][1])
        self.assertIn(r"\frac{2}{\sqrt{\pi}}",CASES["8.6",10]["math_tex"][1])
    def test_no_false_audio_timestamp_focus(self):
        self.assertEqual([e[1] for e in CASES["8.5",9]["events"]],[3,4])
        self.assertEqual([e[1] for e in CASES["8.6",10]["events"]],[1,4])
        self.assertIn("PIXEL_EVENTS_PASS",STATUS)
if __name__=="__main__":
    unittest.main()
