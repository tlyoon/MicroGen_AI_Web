"""Numeric trigonometric radical branch QA, including adversarial sign cases."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.original_trig_substitution_numeric_preflight import (
    _CASES, check_formula_family, inspect_original_trig_substitutions,
)
from selenium_pipeline.figure_source_identity import _sha


def original_units():
    samples = (
        "For a-squared plus x-squared, we set x equal to a tangent u.",
        "For a-squared minus x-squared, setting x equal to a sine u.",
        "For x-squared minus a-squared, setting x equal to a secant u.",
    )
    return [{"id":f"s003.utterance.{n:03d}",
             "spoken_text":value,"spoken_sha256":f"{n:064x}"}
            for n,value in enumerate(samples,1)]


class OriginalSubstitutionQA(unittest.TestCase):
    def test_all_three_real_formula_branches_and_negative_domains(self):
        for c in _CASES:
            with self.subTest(c["kind"]):
                result=check_formula_family(c)
                self.assertEqual(result["inside_branch_numeric_samples"],18)
                self.assertEqual(result["outside_branch_counterexamples"],3)
                self.assertTrue(result["domain_restriction_matters"])
                self.assertFalse(result["mathematical_identity_formally_proven"])

    def test_wrong_sign_or_unrestricted_domain_is_rejected(self):
        for c in _CASES:
            bad={**c,"signed_replacement":"-1*("+c["signed_replacement"]+")"}
            with self.subTest(c["kind"]):
                with self.assertRaises(ValueError):
                    check_formula_family(bad)

    def test_duplicate_outside_domain_claim_cannot_pass(self):
        for c in _CASES:
            bad={**c,"counterexample_angle":c["valid_angles"][0]}
            with self.subTest(c["kind"]):
                with self.assertRaises(ValueError):
                    check_formula_family(bad)

    def test_original_hash_lineage_and_distinct_utterance_bindings(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            for name in ("source.pdf","slides.pdf","script.txt"):
                (folder/name).write_bytes(name.encode())
            job={
                "source_sha256":_sha(folder/"source.pdf"),
                "slides_sha256":_sha(folder/"slides.pdf"),
                "script_sha256":_sha(folder/"script.txt"),
                "slides":[{"utterances":original_units()}],
            }
            with patch("selenium_pipeline.original_trig_substitution_numeric_preflight."
                       "build_review_job",return_value=job):
                result=inspect_original_trig_substitutions(folder=folder)
            self.assertEqual(result["anchored_numerical_checks"],3)
            self.assertEqual(result["original_utterances_total_on_slide"],3)
            self.assertEqual(len({r["original_utterance_id"] for r in result["checks"]}),3)
            self.assertFalse(result["source_textbook_equivalence_certified"])
            self.assertFalse(result["independent_source_math_consensus_verified"])
            self.assertFalse(result["student_publication_authorized"])

    def test_wrong_source_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            for name in ("source.pdf","slides.pdf","script.txt"):
                (folder/name).write_bytes(name.encode())
            job={
                "source_sha256":"0"*64,
                "slides_sha256":_sha(folder/"slides.pdf"),
                "script_sha256":_sha(folder/"script.txt"),
                "slides":[{"utterances":original_units()}],
            }
            with patch("selenium_pipeline.original_trig_substitution_numeric_preflight."
                       "build_review_job",return_value=job):
                with self.assertRaises(ValueError):
                    inspect_original_trig_substitutions(folder=folder)

    def test_missing_one_original_substitution_fails(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            for name in ("source.pdf","slides.pdf","script.txt"):
                (folder/name).write_bytes(name.encode())
            job={
                "source_sha256":_sha(folder/"source.pdf"),
                "slides_sha256":_sha(folder/"slides.pdf"),
                "script_sha256":_sha(folder/"script.txt"),
                "slides":[{"utterances":original_units()[:2]+[original_units()[0]]}],
            }
            with patch("selenium_pipeline.original_trig_substitution_numeric_preflight."
                       "build_review_job",return_value=job):
                with self.assertRaises(ValueError):
                    inspect_original_trig_substitutions(folder=folder)


if __name__=="__main__":
    unittest.main()
