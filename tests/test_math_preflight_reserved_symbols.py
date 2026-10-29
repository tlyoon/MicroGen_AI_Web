"""Reproduce and block a real false-positive in math preflight binding order."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.math_identity_preflight import verify, digest, checked_constants


class MathBindingSafety(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/"source.pdf"
        self.slides=self.root/"slides.pdf"
        self.source.write_bytes(b"immutable original")
        self.slides.write_bytes(b"immutable original slides")
        self.manifest=self.root/"checks.json"
        self.item={
            "name":"negative-first-variable-shadowing",
            "integrand":"x",
            "antiderivative":"2*x",
            "points":[-1.,0.,1.,3.],
            "constants":{"x":2.},
        }

    def run_case(self):
        self.manifest.write_text(json.dumps({
            "schema_version":1,
            "status":"review_only_explicit_formula_checks",
            "source_sha256":digest(self.source),
            "slides_sha256":digest(self.slides),
            "checks":[self.item],
        }))
        return verify(self.manifest,self.source,self.slides)

    def test_false_positive_x_constant_is_rejected_before_numeric_evaluation(self):
        # Before the fix the target integrand saw x=2 at every sample,
        # while the derivative of 2*x was also 2: a WRONG integral passed.
        with self.assertRaisesRegex(ValueError,"shadowing"):
            self.run_case()

    def test_normal_named_parameter_is_supported(self):
        self.item.update({
            "integrand":"2*a*x",
            "antiderivative":"a*x*x",
            "constants":{"a":3.0},
        })
        self.assertEqual(self.run_case()["passed"],1)
        self.assertFalse(self.run_case()["human_academic_signoff"])

    def test_pi_and_named_functions_may_not_be_shadowed(self):
        for symbol in ("pi","sin","sqrt","exp","x"):
            with self.subTest(symbol=symbol):
                with self.assertRaisesRegex(ValueError,"shadowing"):
                    checked_constants({symbol:2})

    def test_malformed_constant_names_values_and_booleans_denied(self):
        bad=({"a-b":2},{"__import__":1},{"a":True},
             {"a":"3"},{"a":float("nan")},{"a":float("inf")},
             {"a":100000},{"a":[]})
        for candidate in bad:
            with self.subTest(candidate=str(candidate)):
                with self.assertRaises(ValueError):
                    checked_constants(candidate)

    def test_huge_integer_is_rejected_as_validation_error(self):
        with self.assertRaises(ValueError):
            checked_constants({"a":10**500})

    def test_bounded_unique_named_parameters(self):
        with self.assertRaises(ValueError):
            checked_constants({f"a{i}":i for i in range(17)})
        self.assertEqual(checked_constants({"a":2.0,"b":-3}),{"a":2.0,"b":-3})

    def test_repeated_samples_and_nonfinite_points_refused(self):
        self.item["constants"]={}
        for points in ([0.,0.,1.],[0.,float("nan")],[0.,float("inf")]):
            with self.subTest(points=str(points)):
                self.item["points"]=points
                with self.assertRaisesRegex(ValueError,"sample points"):
                    self.run_case()

    def test_normal_wrong_antiderivative_still_rejected_without_shadowing(self):
        self.item["constants"]={}
        self.assertEqual(self.run_case()["failed"],1)


if __name__=="__main__":
    unittest.main()
