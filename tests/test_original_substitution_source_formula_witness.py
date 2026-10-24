"""Original exact textbook mathematical formula source-witness regression."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.original_substitution_source_formula_witness import (
    _SOURCE_SENTENCE,
    _FORMS,
    inspect_original_three_formula_source,
)


def fixture(root:Path, quote:str=_SOURCE_SENTENCE, duplicate:bool=False):
    with pymupdf.open() as pdf:
        page=pdf.new_page(width=612,height=792)
        page.insert_textbox(pymupdf.Rect(50,100,560,300),
                            quote,fontsize=11)
        if duplicate:
            page.insert_textbox(pymupdf.Rect(50,350,560,550),
                                quote,fontsize=11)
        pdf.save(root/"source.pdf")
    (root/"slides.pdf").write_bytes(b"unchanged original slide sha fixture")
    (root/"script.txt").write_text("original narration id-bound test",encoding="utf8")
    hashes=tuple(_sha(root/name) for name in ("source.pdf","slides.pdf","script.txt"))
    checks=[
        {
            "kind":kind,
            "original_utterance_id":unit,
            "original_spoken_sha256":f"{idx+1:064x}",
            "inside_branch_numeric_samples":18,
            "outside_branch_counterexamples":3,
            "domain_restriction_matters":True,
        }
        for idx,(kind,_,unit) in enumerate(_FORMS)
    ]
    pilot={
        "source_sha256":hashes[0],"slides_sha256":hashes[1],
        "script_sha256":hashes[2],
        "anchored_numerical_checks":3,
        "original_utterances_total_on_slide":5,
        "all_tested_numeric_samples_consistent":True,
        "checks":checks,
    }
    return pilot


class OriginalSourceFormulaWitnessTests(unittest.TestCase):
    def run_case(self,pilot,root):
        with patch("selenium_pipeline.original_substitution_source_formula_witness."
                   "inspect_original_trig_substitutions",return_value=pilot):
            return inspect_original_three_formula_source(folder=root)

    def test_three_unique_original_math_formulas_cited_but_unapproved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            report=self.run_case(fixture(root),root)
            self.assertEqual(report["textbook_formulas_matched_as_text"],3)
            self.assertEqual(report["source_physical_page"],1)
            self.assertEqual(report["in_domain_numeric_samples_total"],54)
            self.assertEqual(report["out_of_domain_counterexamples_total"],9)
            self.assertEqual([x["original_utterance_id"] for x in report["formula_witnesses"]],
                             [e[2] for e in _FORMS])
            self.assertTrue(report["spatially_coherent_unique_context_citation"])
            self.assertFalse(report["independent_original_source_AI_math_consensus"])
            self.assertFalse(report["source_equations_are_formally_proven"])
            self.assertFalse(report["genuine_Kore_TTS_authorized"])
            self.assertFalse(report["student_publication_authorized"])

    def test_source_missing_one_actual_substitution_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            pilot=fixture(root,_SOURCE_SENTENCE.replace("x = a sec u.","x = a cos u."))
            with self.assertRaises(ValueError):
                self.run_case(pilot,root)

    def test_wrong_original_utterance_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); pilot=fixture(root)
            pilot["checks"][0]["original_utterance_id"]="s003.utterance.005"
            with self.assertRaises(ValueError):
                self.run_case(pilot,root)

    def test_lost_domain_counterexample_does_not_claim_verification(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); pilot=fixture(root)
            pilot["checks"][1]["outside_branch_counterexamples"]=0
            with self.assertRaises(ValueError):
                self.run_case(pilot,root)

    def test_input_hash_mutation_is_rejected_before_audit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); pilot=fixture(root)
            (root/"source.pdf").write_bytes(b"changed without authorization")
            with self.assertRaises(ValueError):
                self.run_case(pilot,root)

    def test_duplicate_context_quote_is_not_unambiguously_cited(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); pilot=fixture(root,duplicate=True)
            with self.assertRaises(ValueError):
                self.run_case(pilot,root)

    def test_numerical_checks_with_extra_unknown_case_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); pilot=fixture(root)
            pilot["checks"].append(dict(pilot["checks"][0],kind="UNKNOWN_SUBSTITUTION"))
            with self.assertRaises(ValueError):
                self.run_case(pilot,root)


if __name__=="__main__":
    unittest.main()
