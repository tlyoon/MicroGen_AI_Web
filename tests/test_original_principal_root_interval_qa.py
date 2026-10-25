"""Exact sign-domain theorems, not copied academic proof certificates."""
import builtins
import os
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from selenium_pipeline.original_principal_root_interval_qa import (
    _DOMAINS,audit_exact_principal_root_domains,inspect_original_exact_root_branches,
)


class OriginalConditionalRadicalSigns(unittest.TestCase):
    def test_exact_open_and_closed_trigonometric_ranges(self):
        r=audit_exact_principal_root_domains()
        if not r["conditional_principal_root_branches_proven"]:
            self.skipTest("SymPy optional on this host; domain proof explicitly unverified")
        self.assertTrue(r["conditional_principal_root_branches_proven"])
        self.assertEqual(r["conditional_principal_root_branch_count"],3)
        self.assertEqual([x["exact_cos_range"] for x in r["families"]],
                         ["Interval.Lopen(0, 1)","Interval(0, 1)",
                          "Interval.Lopen(0, 1)"])
        self.assertEqual(r["families"][2]["exact_tan_range"],
                         "Interval(0, oo)")
        self.assertTrue(all(x["sqrt_replacement_squared_equals_abs_replacement"]
                            and x["candidate_replacement_nonnegative_under_hypotheses"]
                            for x in r["families"]))
        self.assertFalse(r["source_pdf_radical_notation_fully_verified"])
        self.assertFalse(r["independent_source_math_review_approved"])
        self.assertFalse(r["student_publication_authorized"])

    def test_no_global_negative_cosine_or_tangent_permission(self):
        r=audit_exact_principal_root_domains()
        if not r["conditional_principal_root_branches_proven"]:
            self.skipTest("No optional symbolic engine; no conditional proof claimed")
        self.assertFalse(r["all_angles_or_negative_parameter_cases_approved"])
        self.assertTrue(all(
            not x["unconditional_principal_root_equality_proved"]
            for x in r["families"]))

    def test_wrong_or_expanded_angle_intervals_are_rejected(self):
        for index in range(3):
            modified=deepcopy(list(_DOMAINS))
            modified[index]["left_closed"]=not modified[index]["left_closed"]
            with self.subTest(index=index),self.assertRaises(ValueError):
                audit_exact_principal_root_domains(modified)

    def test_changed_source_formula_binding_rejected(self):
        for index in range(3):
            modified=deepcopy(list(_DOMAINS))
            modified[index]["utterance_id"]="s003.utterance.999"
            with self.subTest(index=index),self.assertRaises(ValueError):
                audit_exact_principal_root_domains(modified)

    def test_wrong_positive_sign_lemma_refused(self):
        modified=deepcopy(list(_DOMAINS))
        modified[2]["replacement_nonnegative_reason"]="tan always nonnegative"
        with self.assertRaises(ValueError):
            audit_exact_principal_root_domains(modified)

    def test_mutated_exact_range_expectation_rejected(self):
        modified=deepcopy(list(_DOMAINS))
        modified[0]["required_cos_range"]="Interval(-1,1)"
        with self.assertRaises(ValueError):
            audit_exact_principal_root_domains(modified)

    def test_missing_or_duplicate_domain_rejected(self):
        with self.assertRaises(ValueError):
            audit_exact_principal_root_domains(_DOMAINS[:2])
        with self.assertRaises(ValueError):
            audit_exact_principal_root_domains((*_DOMAINS,_DOMAINS[0]))

    def test_missing_sympy_reports_unverified_without_fabricated_proof(self):
        original=builtins.__import__
        def refuse_sympy(name,*args,**kwargs):
            if name=="sympy":
                raise ImportError("offline symbolic engine unavailable")
            return original(name,*args,**kwargs)
        with patch("builtins.__import__",side_effect=refuse_sympy):
            result=audit_exact_principal_root_domains()
        self.assertFalse(result["conditional_principal_root_branches_proven"])
        self.assertFalse(result["student_publication_authorized"])

    def test_real_original_source_lineage_on_authorized_dell_only(self):
        root=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not root:
            self.skipTest("Original teaching assets only on Dell-115")
        r=inspect_original_exact_root_branches(folder=Path(root))
        self.assertEqual(r["original_formula_count"],3)
        self.assertTrue(r["conditional_principal_root_branches_proven"])
        self.assertFalse(r["source_pdf_radical_notation_fully_verified"])
        self.assertEqual(r["independent_source_math_agreements_added"],0)
        self.assertFalse(r["real_element_highlight_encoded_mp4_verified"])


if __name__=="__main__":
    unittest.main()
