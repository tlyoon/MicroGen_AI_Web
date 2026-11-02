"""Publisher-original §8.6 Example3 and summary are not audio acceptance."""
import importlib.util
import unittest
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.original_thomas86_example3_summary_source_math import (
    textbook_headings_proven, exact_example_three_math, HEADING_TERMS,
)

class ExampleSummarySourceTests(unittest.TestCase):
    def setUp(self):
        self.pages=["" for _ in range(6)]
        for key,(phrase,page) in HEADING_TERMS.items():
            self.pages[page]+=phrase+" "
    def test_original_textbook_sections_present_on_exact_pages(self):
        proof=textbook_headings_proven(self.pages)
        self.assertEqual(len(proof),8)
        self.assertEqual(proof["formula_106"]["page"],1)
        self.assertEqual(proof["formula_49"]["page"],2)
        self.assertEqual(proof["tank_applications"]["page"],6)
    def test_missing_formula49_must_fail_closed(self):
        self.pages[1]=self.pages[1].replace("formula 49","")
        with self.assertRaises(FigureIdentityReviewRequired):
            textbook_headings_proven(self.pages)
    def test_wrong_section_length_must_fail_closed(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            textbook_headings_proven(self.pages[:5])
    @unittest.skipUnless(importlib.util.find_spec("sympy"),"Independent SymPy unavailable")
    def test_real_interval_both_exact_derivatives(self):
        proof=exact_example_three_math()
        self.assertTrue(proof["symbolic_antiderivative_exact"])
        self.assertTrue(proof["formula49_remaining_integral_exact"])
        self.assertEqual(proof["real_domain"],"-1 < x < 1")

if __name__=="__main__":
    unittest.main()
