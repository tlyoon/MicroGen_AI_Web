"""Adversarial original-source, review-only mathematical triage checks."""
from __future__ import annotations
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from selenium_pipeline.original_math_claim_inventory import (
    inventory_original_mathematics, triage_unit,
)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fixture(root):
    root=Path(root)
    pdf=pymupdf.open()
    page=pdf.new_page()
    page.insert_text((72,80),"8.4 Trigonometric Substitutions")
    pdf.save(root/"source.pdf")
    pdf.close()
    (root/"slides.pdf").write_bytes((root/"source.pdf").read_bytes())
    (root/"script.txt").write_text("Original source",encoding="utf8")
    hashes=[digest(root/n) for n in ("source.pdf","slides.pdf","script.txt")]
    first = {
        "original_text":"8.4 Trigonometric Substitutions",
        "utterance_id":"s001.utterance.001",
        "original_text_sha256":hashlib.sha256(
            "8.4 Trigonometric Substitutions".encode()).hexdigest(),
        "candidate_visual_targets":[{"target_id":"s001.text.001"}],
    }
    second_text="For a squared plus x squared we use a tangent substitution and Pythagorean identity."
    second = {
        "original_text":second_text, "utterance_id":"s002.utterance.001",
        "original_text_sha256":hashlib.sha256(second_text.encode()).hexdigest(),
        "candidate_visual_targets":[{"target_id":"s002.text.001"}],
    }
    candidate={"source_sha256":hashes[0],"slides_sha256":hashes[1],
        "script_sha256":hashes[2],"slide_count":2,"utterance_count":2,
        "slides":[{"slide":1,"candidate_visual_targets":[{"draft_element_id":"s001.text.001"}],
            "original_utterance_candidates":[first]},
            {"slide":2,"candidate_visual_targets":[{"draft_element_id":"s002.text.001"}],
            "original_utterance_candidates":[second,]}]}
    return candidate


class SourceMathTriage(unittest.TestCase):
    def test_title_never_called_math_proof(self):
        r=triage_unit("8.4 Trigonometric Substitutions",1)
        self.assertEqual(r["triage_kind"],"SECTION_TITLE_METADATA_CANDIDATE")
        self.assertFalse(r["semantic_mathematics_verified"])

    def test_substitution_is_candidate_not_approved(self):
        r=triage_unit("x equals a tangent u; one plus tangent squared equals secant squared",3)
        self.assertEqual(r["triage_kind"],"SUBSTITUTION_OR_IDENTITY_CANDIDATE")
        self.assertFalse(r["original_source_quote_verified"])

    def test_explicit_formula_priority_requires_algebraic_phrase(self):
        loose=triage_unit("Pythagorean identities guide this substitution",2)
        exact=triage_unit("For a-squared plus x-squared choose x equal to a tangent u",3)
        self.assertFalse(loose["explicit_formula_phrase_candidate"])
        self.assertTrue(exact["explicit_formula_phrase_candidate"])

    def test_geometry_and_integral_cues_do_not_certify(self):
        for sentence in ("The triangle hypotenuse is a radical.",
                         "The integrand and antiderivative agree."):
            r=triage_unit(sentence,8)
            self.assertFalse(r["semantic_mathematics_verified"])
            self.assertNotEqual(r["triage_kind"],"SECTION_TITLE_METADATA_CANDIDATE")

    def test_valid_exact_source_inventory_counts_all_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); candidate=fixture(root)
            with patch("selenium_pipeline.original_math_claim_inventory.candidate_map",
                       return_value=candidate):
                r=inventory_original_mathematics(folder=root)
            self.assertEqual(r["original_utterance_count"],2)
            self.assertEqual(r["physical_textbook_pdf_pages"],1)
            self.assertEqual(r["triage_counts"]["SECTION_TITLE_METADATA_CANDIDATE"],1)
            self.assertEqual(r["suggested_first_substantive_slide"],None)
            self.assertEqual(r["potential_substantive_review_units"],1)
            self.assertFalse(r["independent_math_consensus_verified"])
            self.assertFalse(r["new_academic_scope_authorized"])
            self.assertFalse(r["student_publication_authorized"])

    def test_fake_original_narration_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); candidate=fixture(root)
            candidate["slides"][1]["original_utterance_candidates"][0]["utterance_id"]="s999.utterance.001"
            with patch("selenium_pipeline.original_math_claim_inventory.candidate_map",
                       return_value=candidate):
                with self.assertRaises(ValueError):
                    inventory_original_mathematics(folder=root)

    def test_changed_original_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); candidate=fixture(root)
            (root/"source.pdf").write_bytes(b"tampered")
            with patch("selenium_pipeline.original_math_claim_inventory.candidate_map",
                       return_value=candidate):
                with self.assertRaises(ValueError):
                    inventory_original_mathematics(folder=root)

    def test_candidate_count_drift_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); candidate=fixture(root)
            candidate["utterance_count"]=3
            with patch("selenium_pipeline.original_math_claim_inventory.candidate_map",
                       return_value=candidate):
                with self.assertRaises(ValueError):
                    inventory_original_mathematics(folder=root)


if __name__ == "__main__":
    unittest.main()
