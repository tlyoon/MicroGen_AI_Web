"""Offline numeric mathematics regression checks, including failure injection."""
from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from selenium_pipeline.math_identity_preflight import digest,numeric,verify

class MathPreflightTests(unittest.TestCase):
 def setUp(self):
    self.temp=tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    r=Path(self.temp.name)
    self.source=r/"source.pdf";self.slides=r/"slides.pdf"
    self.source.write_bytes(b"source");self.slides.write_bytes(b"slides")
    self.manifest=r/"checks.json"
    self.obj={"schema_version":1,
              "status":"review_only_explicit_formula_checks",
              "source_sha256":digest(self.source),
              "slides_sha256":digest(self.slides),
              "checks":[{"name":"Gaussian-trig-form",
                         "integrand":"1/sqrt(x*x+4)",
                         "antiderivative":"log(x+sqrt(x*x+4))",
                         "points":[-1.0,0.3,1.0,3.0]}]}
    self.save()
 def save(self):
    self.manifest.write_text(json.dumps(self.obj),encoding="utf8")
 def run_math(self):
    return verify(self.manifest,self.source,self.slides)
 def test_valid_derivative_consistent_but_not_formally_certified(self):
    r=self.run_math()
    self.assertEqual(r["passed"],1)
    self.assertFalse(r["human_academic_signoff"])
    self.assertFalse(r["source_equivalence_certified"])
 def test_wrong_mathematical_coefficient_fails(self):
    self.obj["checks"][0]["antiderivative"]="2*log(x+sqrt(x*x+4))"
    self.save()
    self.assertEqual(self.run_math()["failed"],1)
 def test_source_sha_mismatch_rejects(self):
    self.source.write_bytes(b"changed")
    with self.assertRaisesRegex(ValueError,"Stale"):
        self.run_math()
 def test_disallow_python_code_execution(self):
    for expr in ("__import__('os').system('echo bad')",
                 "x.__class__","[a for a in (1,2)]","pow(x,10)"):
        with self.assertRaises((ValueError,SyntaxError)):
            numeric(expr,{"x":1})
 def test_domain_violation_rejects(self):
    self.obj["checks"][0]["points"]=[0.0,999.0]
    self.obj["checks"][0]["integrand"]="1/sqrt(1-x*x)"
    self.save()
    with self.assertRaisesRegex(ValueError,"Cannot verify"):
        self.run_math()

if __name__=="__main__":unittest.main()
