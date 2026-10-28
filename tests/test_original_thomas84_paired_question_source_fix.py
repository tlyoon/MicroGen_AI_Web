"""Only the genuine incorrect source question can be corrected in isolation."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_paired_question_source_fix import (
  CORRECTED_TEX,ORIGINAL_TEX,CORRECTED_NARRATION,
  ORIGINAL_NARRATION,make_source_pair,
)
class CorrectedMathSlideQuestion(unittest.TestCase):
    def test_full_integral_is_specified_in_real_latex(self):
        self.assertIn(r"\int \frac{dx}{\sqrt{x^2 - 16}}",CORRECTED_TEX)
        self.assertIn("x>4",CORRECTED_TEX)
        self.assertNotIn(r"\int",ORIGINAL_TEX)
    def test_narration_contains_original_integrand(self):
        self.assertIn("integral of d x over",CORRECTED_NARRATION)
        self.assertNotEqual(ORIGINAL_NARRATION,CORRECTED_NARRATION)
    def test_missing_actual_source_does_not_create_fake_slide(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with self.assertRaises((ValueError,FileNotFoundError)):
                make_source_pair(original=p/"source",
                    academic_report=p/"audit.json",out=p/"new")
            self.assertFalse((p/"new").exists())
if __name__=="__main__":unittest.main()
