"""Mathematical branch proofs are not all 66 speech approvals."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_five_source_domain_proofs import (
    KEYS,branch_math_checks,verify_source_domains)
class SourceDomainMath(unittest.TestCase):
    def test_exact_five_original_source_scope_cases(self):
        self.assertEqual(len(KEYS),5)
        self.assertEqual(KEYS[(5,3)],"principal_sine_closed_domain")
    def test_source_trig_branch_identities_and_sample_signs(self):
        x=branch_math_checks()
        self.assertEqual(len(x),4)
        self.assertFalse(x["principal_sine_closed_domain"][
            "finite_samples_alone_prove_whole_interval"])
    def test_missing_real_source_cannot_approve_audio_or_math(self):
        with tempfile.TemporaryDirectory() as t:
            b=Path(t)
            with self.assertRaises((ValueError,FileNotFoundError)):
                verify_source_domains(original=b/"nonexistent",
                    source_plan=b/"a.json",academic_report=b/"b.json",
                    new_voice_report=b/"c.json",out=b/"out.json")
            self.assertFalse((b/"out.json").exists())
if __name__=="__main__":unittest.main()
