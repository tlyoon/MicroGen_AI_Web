"""Original Slide4 physical PDF source quote packet and false-claim controls."""
import os
from pathlib import Path
from unittest.mock import patch
import unittest
from selenium_pipeline.original_slide4_exact_source_evidence import (
    _SOURCE_PASSAGES,build_five_original_source_evidence,
)
from selenium_pipeline.pdf_text_source_span_witness import prove_source_quote_occurrence


class OriginalSlide4SourcePacketTests(unittest.TestCase):
    def root(self):
        root=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not root:
            self.skipTest("Only source-owning Dell115 may run real asset tests")
        return Path(root)

    def test_actual_10_exact_quotes_across_five_original_utterances(self):
        r=build_five_original_source_evidence(folder=self.root())
        self.assertEqual(r["verified_exact_pdf_source_excerpt_count"],10)
        self.assertEqual(r["original_utterance_count"],5)
        self.assertEqual([x["evidence_kind"] for x in r["original_utterance_evidence"]],
             ["INTRO_REFERENCE_TRIANGLES","TANGENT_SQUARED_IDENTITY",
              "SINE_SQUARED_IDENTITY","SECANT_SQUARED_IDENTITY",
              "ROOT_ABSOLUTE_VALUES_CONTEXT_ONLY"])
        self.assertTrue(all(
            x["original_utterance_id"]==f"s004.utterance.{i:03d}"
            and len(x["source_evidence"])==2
            and all(y["original_pdf_spatial_coherence_verified"] for y in x["source_evidence"])
            for i,x in enumerate(r["original_utterance_evidence"],1)))
        self.assertEqual(r["source_math_semantically_approved_utterances"],0)
        self.assertFalse(r["source_radical_operator_academically_verified"])
        self.assertFalse(r["student_publication_authorized"])
        self.assertFalse(r["gemini_provider_request_sent"])

    def test_reject_changed_fake_and_swapped_quote_packets(self):
        root=self.root()
        cases=[]
        a=list(_SOURCE_PASSAGES)
        a[0]=((1,"FIGURE 8.2 Reference triangles for the three basic substitutions identifying the sides labeled x and a for each substitution."),a[0][1])
        cases.append(a)
        a=list(_SOURCE_PASSAGES);a[3]=_SOURCE_PASSAGES[2];cases.append(a)
        a=list(_SOURCE_PASSAGES);a.pop();cases.append(a)
        for mutated in cases:
            with self.subTest(i=len(mutated)),self.assertRaises(ValueError):
                build_five_original_source_evidence(folder=root,passages=mutated)

    def test_original_mathematics_quote_does_not_certify_root(self):
        r=build_five_original_source_evidence(folder=self.root())
        root=r["original_utterance_evidence"][-1]
        self.assertEqual(root["review_disposition"],"AWAIT_INDEPENDENT_SOURCE_MATH_REVIEW")
        self.assertFalse(root["original_radical_glyph_reliably_decoded"])
        self.assertFalse(root["evidence_is_semantic_math_approval"])

    def test_reject_false_printed_join_across_pdf_blocks(self):
        root=self.root()
        with self.assertRaises(ValueError):
            prove_source_quote_occurrence(source_pdf=root/"source.pdf",
                expected_sha256="b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068",
                page_number=1,
                verbatim_quote="FIGURE 8.2 Reference triangles for the three basic substitutions identifying the sides labeled x and a for each substitution.")

    def test_reject_quote_wrong_physical_page_or_source_sha(self):
        root=self.root()
        for number,sha in ((3,"b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"),(1,"0"*64)):
            with self.subTest(number=number),self.assertRaises(ValueError):
                prove_source_quote_occurrence(source_pdf=root/"source.pdf",
                    expected_sha256=sha,page_number=number,
                    verbatim_quote=_SOURCE_PASSAGES[1][0][1])

    def test_no_original_source_without_mount(self):
        if os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER"):
            self.skipTest("Dell has original; omission simulated separately")
        with self.assertRaises((ValueError,FileNotFoundError)):
            build_five_original_source_evidence(folder=Path("Z:/not-available/8.4"))


if __name__=="__main__":
    unittest.main()
