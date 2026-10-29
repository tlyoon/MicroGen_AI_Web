"""Exact square algebra and honest sign/radical approval boundaries."""
import os
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import unittest

from selenium_pipeline.original_figure82_symbolic_branch_qa import (
    _FAMILIES,exact_squared_identities,inspect_original_figure82_exact_squares,
)


class SourceBoundExactSquares(unittest.TestCase):
    def test_exact_three_squared_radical_identities(self):
        outcome=exact_squared_identities()
        if not outcome["exact_symbolic_squared_identities_verified"]:
            self.skipTest("SymPy unavailable; exact proof explicitly unverified")
        self.assertEqual(outcome["squared_identity_count"],3)
        self.assertTrue(all(x["squared_identity_exact_sympy_pass"]
                            for x in outcome["families"]))
        self.assertFalse(outcome["principal_root_sign_conditions_academically_approved"])
        self.assertFalse(outcome["unconditional_global_radical_equalities_proven"])
        self.assertFalse(outcome["independent_academic_consensus"])

    def test_mutated_radical_sign_contract_fails(self):
        for k in range(3):
            families=deepcopy(list(_FAMILIES))
            families[k]["positive_root_condition"]="a > 0"
            with self.subTest(k=k), self.assertRaises(ValueError):
                exact_squared_identities(families)

    def test_mutated_angle_range_fails(self):
        for k in range(3):
            families=deepcopy(list(_FAMILIES))
            families[k]["angle_interval"]="-pi < u < pi"
            with self.subTest(k=k), self.assertRaises(ValueError):
                exact_squared_identities(families)

    def test_false_principal_sign_approval_is_rejected(self):
        families=deepcopy(list(_FAMILIES))
        families[2]["principal_root_sign_from_domain_fully_certified"]=True
        with self.assertRaises(ValueError):
            exact_squared_identities(families)

    def test_mutated_sine_formula_or_utterance_mapping_fails(self):
        for key,value in (
            ("kind","TANGENT_PLUS_FORM"),
            ("formula","x = a cos u"),
            ("utterance_id","s003.utterance.004"),
        ):
            families=deepcopy(list(_FAMILIES))
            families[1][key]=value
            with self.subTest(key=key), self.assertRaises(ValueError):
                exact_squared_identities(families)

    def test_missing_or_duplicate_source_family_refused(self):
        with self.assertRaises(ValueError):
            exact_squared_identities(_FAMILIES[:2])
        with self.assertRaises(ValueError):
            exact_squared_identities((*_FAMILIES,*_FAMILIES[:1]))

    def test_missing_symbolic_engine_explicitly_blocks_verification(self):
        import builtins
        original=builtins.__import__
        def intercept(name,*a,**kw):
            if name=="sympy":
                raise ImportError("uninstalled in CI")
            return original(name,*a,**kw)
        with patch("builtins.__import__",side_effect=intercept):
            report=exact_squared_identities()
        self.assertFalse(report["exact_symbolic_squared_identities_verified"])
        self.assertFalse(report["independent_academic_consensus"])

    def test_real_source_cross_binds_formulas_to_image_source(self):
        folder=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not folder:
            self.skipTest("Real original source only on authorized Dell-115")
        report=inspect_original_figure82_exact_squares(folder=Path(folder))
        self.assertEqual(report["original_narration_formula_utterances"],[
            "s003.utterance.002","s003.utterance.003","s003.utterance.004"])
        self.assertFalse(report["source_figure_radical_glyph_verified"])
        self.assertFalse(report["genuine_Kore_TTS_authorized"])
        self.assertFalse(report["student_publication_authorized"])
        self.assertEqual(report["independent_two_pass_original_math_agreements_added"],0)


if __name__=="__main__":
    unittest.main()
