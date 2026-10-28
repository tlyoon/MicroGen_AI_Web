"""Regression: reject flipped coefficients and invalid math derivatives."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import sympy as S
from selenium_pipeline.original_thomas84_worked_examples_math_proof import (
    x,evaluate_worked_rules,verify_worked_source_math,
)

class WorkedMathProof(unittest.TestCase):
    def test_four_actual_limited_mathematical_examples(self):
        a=evaluate_worked_rules()
        self.assertEqual(len(a),4)
        self.assertTrue(all(x["limited_mathematics_result_pass"]
                            for x in a.values()))
    def test_example_one_wrong_radicand_rejected(self):
        wrong={
         "example_1_log":S.log((x+S.sqrt(9+x*x))/3),
         "example_2_asinh":S.asinh(x/S.Integer(2)) -
            S.log((x+S.sqrt(4+x*x))/2),
         "example_3_sine":S.Rational(9,2)*S.asin(x/3) -
            x*S.sqrt(9-x*x)/2,
         "example_4_secant":S.Rational(1,5)*
            S.log((5*x+S.sqrt(25*x*x-4))/2),
        }
        self.assertFalse(evaluate_worked_rules(wrong)[
            "example_1_log"]["limited_mathematics_result_pass"])
    def test_example_three_wrong_sign_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_worked_rules({"example_3_sine":x})
    def test_no_fake_original_math_source(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with self.assertRaises((ValueError,FileNotFoundError)):
                verify_worked_source_math(original=p/"missing",out=p/"out.json")
            self.assertFalse((p/"out.json").exists())

if __name__=="__main__":unittest.main()
