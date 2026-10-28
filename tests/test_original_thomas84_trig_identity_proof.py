"""Symbolic math must fail on a changed sign, wrong derivative or domain."""
from __future__ import annotations
import tempfile
from pathlib import Path
import unittest
import sympy as S
from selenium_pipeline.original_thomas84_trig_identity_proof import (
    RULES,prove_rule,independently_verify_three,u,a
)
class TrigSourceProof(unittest.TestCase):
    def test_three_rules_pass_limited_symbolic_and_domain_proof(self):
        for key,rule in RULES.items():
            with self.subTest(key):
                self.assertTrue(prove_rule(rule)["limited_rule_proof_pass"])
    def test_wrong_dx_rejected(self):
        bad={**RULES["tangent_plus"],
             "differential":a*S.sin(u)}
        self.assertFalse(prove_rule(bad)["limited_rule_proof_pass"])
    def test_wrong_radicand_sign_rejected(self):
        bad={**RULES["tangent_plus"],
             "radicand":a*a-S.Symbol("x")**2}
        self.assertFalse(prove_rule(bad)["limited_rule_proof_pass"])
    def test_negative_factor_not_allowed_in_principal_domain(self):
        bad={**RULES["sine_minus"],
             "square_root_factor":-a*S.cos(u)}
        self.assertFalse(prove_rule(bad)["limited_rule_proof_pass"])
    def test_source_absent_fails_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with self.assertRaises((ValueError,FileNotFoundError)):
                independently_verify_three(original=p/"missing",out=p/"out.json")
            self.assertFalse((p/"out.json").exists())
if __name__=="__main__":unittest.main()
