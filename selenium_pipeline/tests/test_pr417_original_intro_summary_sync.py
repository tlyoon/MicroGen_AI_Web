"""Review only independently source-grounded intro/summary text and math."""
import unittest
from selenium_pipeline.original_thomas84_intro_summary_source_sync import (
    CASES, STATUS, _publisher_witness)

class IntroSummaryActualOriginalMathTests(unittest.TestCase):
    @staticmethod
    def valid():
        intro=("The most common substitutions are x = a tan u, x = a sin u, and\n"
               "x = a sec u.\n"
               "2a2 + x2, 2a2 - x2, and 2x2 - a2\n"
               "come from the reference right triangles in Figure 8.2")
        reverse=("any substitution we use in an integration to be reversible\n"
                 "functions in these substitutions have inverses only\n"
                 "for selected values of u (Figure 8.3)")
        subs=r"$x = a \tan \theta$ $x = a \sin \theta$ $x = a \sec \theta$"
        frames=[""]*17
        frames[2]=subs + (
            r" $\sqrt{a^{2} + x^{2}}$"
            r" $\sqrt{a^{2} - x^{2}}$"
            r" $\sqrt{x^{2} - a^{2}}$"
            " standard right-triangle geometry")
        frames[15]=subs + " reversible Reference right triangles"
        return [intro,reverse,"",""],frames

    def test_original_three_substitutions_two_source_pages_and_sympy(self):
        pages,frames=self.valid()
        evidence=_publisher_witness(pages,frames)
        self.assertTrue(evidence["original_three_substitutions_and_radicals_verified"])
        self.assertEqual(evidence["independent_three_trig_identity_residuals"],
                         ["0","0","0"])
        self.assertFalse(evidence["title_slide_word_alignment_approved"])
        self.assertFalse(evidence["algebra_preparation_summary_fourth_bullet_approved"])

    def test_wrong_radicand_operator_blocks_publisher_math(self):
        pages,frames=self.valid()
        frames[2]=frames[2].replace(
            r"\sqrt{a^{2} - x^{2}}",r"\sqrt{a^{2} + x^{2}}")
        with self.assertRaises(Exception):
            _publisher_witness(pages,frames)

    def test_missing_substitution_in_source_blocks(self):
        pages,frames=self.valid()
        pages[0]=pages[0].replace("x = a sec u","x = a cos u")
        with self.assertRaises(Exception):
            _publisher_witness(pages,frames)

    def test_publisher_requires_domain_reversibility(self):
        pages,frames=self.valid()
        pages[1]=pages[1].replace("selected values of u","unrestricted angles")
        with self.assertRaises(Exception):
            _publisher_witness(pages,frames)

    def test_only_validated_math_events_are_in_live_clips(self):
        self.assertEqual(sorted(CASES),[3,16])
        self.assertEqual([len(CASES[k]) for k in sorted(CASES)],[3,3])
        self.assertIn("PCM_PIXEL_QA_PASS",STATUS)

if __name__=="__main__":
    unittest.main()
