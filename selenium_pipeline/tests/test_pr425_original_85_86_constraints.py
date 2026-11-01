"""Publisher constraints never silently relax minus signs or inequalities."""
import unittest
from selenium_pipeline.original_thomas85_86_academic_constraints_focus import CASES,STATUS

class OriginalPublisherMathematicalConstraints(unittest.TestCase):
    def test_source_specific_prerequisite_slides(self):
        self.assertEqual(CASES["8.5"]["slide"],4)
        self.assertEqual(CASES["8.6"]["slide"],3)
        self.assertEqual([len(c["events"]) for c in CASES.values()],[2,2])
    def test_original_proper_fraction_and_real_factor_prerequisites(self):
        terms=" ".join(CASES["8.5"]["latex"])
        self.assertIn("must be less than the degree",terms)
        self.assertIn("irreducible quadratic",terms)
        self.assertIn("long division first",terms)
    def test_original_table_domain_signs_must_not_reverse(self):
        terms=" ".join(CASES["8.6"]["latex"])
        self.assertIn(r"$n \neq -1$ or $n \neq -2$",terms)
        self.assertIn(r"$a \neq 0$, $b > 0$",terms)
        self.assertNotIn("$b < 0$",terms)
    def test_actual_source_voice_and_pixel_timing_guard_exists(self):
        self.assertEqual(
           [e[1] for e in CASES["8.5"]["events"]],[2,4])
        self.assertEqual(
           [e[1] for e in CASES["8.6"]["events"]],[4,5])
        self.assertIn("NONPRODUCTION",STATUS)
if __name__=="__main__":
    unittest.main()
