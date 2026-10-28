"""Do not silently equate distinct trig, sign or domain mathematics."""
from __future__ import annotations
import tempfile
from pathlib import Path
import unittest
from selenium_pipeline.original_thomas84_math_domain_crosscheck import (
    compare_math_claims, crosscheck,
)

class MathDomainCrosscheck(unittest.TestCase):
    def test_sine_cosine_contradiction_is_not_approved(self):
        r=compare_math_claims("Use sine u here","The cosine u is positive")
        self.assertIn("SINGLE_TRIG_FUNCTION_CONFLICT",
                      r["provable_local_term_conflicts"])
        self.assertFalse(r["whole_source_math_verified"])
    def test_positive_vs_nonpositive_is_explicit_conflict(self):
        r=compare_math_claims("The tangent is strictly positive",
                              "The tangent is nonpositive")
        self.assertIn("EXPLICIT_POLARITY_CONTRADICTION",
                      r["provable_local_term_conflicts"])
    def test_mixed_functions_not_auto_rejected(self):
        r=compare_math_claims("sine and cosine ratio", "sine, cosine, tangent")
        self.assertNotIn("SINGLE_TRIG_FUNCTION_CONFLICT",
                         r["provable_local_term_conflicts"])
    def test_numerical_difference_not_automatic_proof(self):
        r=compare_math_claims("Use 4", "Use 9")
        self.assertFalse(r["provable_local_term_conflicts"])
        self.assertIn("NUMERICAL_ANCHOR_NOT_SHARED",
                      r["insufficient_evidence_flags"])
    def test_missing_actual_risk_receipt_blocks_output(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            with self.assertRaises((ValueError,FileNotFoundError)):
                crosscheck(original=p/"source",risk_receipt=p/"risk.json",
                           output=p/"out.json")
            self.assertFalse((p/"out.json").exists())

if __name__=="__main__": unittest.main()
