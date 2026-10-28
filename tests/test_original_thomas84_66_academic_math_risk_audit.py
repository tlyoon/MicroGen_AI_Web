"""Real source math evidence detects incomplete exercise, never auto-approves."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_66_academic_math_risk_audit import (
    underdetermined_integral_proof,review_real_math)
class Source66AcademicSemantic(unittest.TestCase):
    def test_two_legal_integrals_yield_distinct_trig_integrands(self):
        p=underdetermined_integral_proof()
        self.assertTrue(p["therefore_no_unique_integrand_from_a_radicand_alone"])
        self.assertTrue(p["two_distinct_valid_resulting_integrands_symbolically_proved"])
        self.assertNotEqual(p["case_a_transformed_integrand"],
                            p["case_b_transformed_integrand"])
    def test_missing_original_never_claims_academic_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with self.assertRaises((ValueError,FileNotFoundError)):
                review_real_math(original=base/"absent",
                    source_plan=base/"a.json",corrections=base/"b.json",
                    spoken_audio=base/"c.json",
                    final_real_media_audit=base/"d.json",out=base/"out.json")
            self.assertFalse((base/"out.json").exists())
if __name__=="__main__":unittest.main()
