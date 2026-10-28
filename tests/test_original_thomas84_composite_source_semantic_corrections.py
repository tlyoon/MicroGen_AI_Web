"""Actual mathematical source correction must prove original PDF blocks."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.original_thomas84_composite_source_semantic_corrections import (
    CORRECTIONS,actual_source_composite,limited_domain_proofs,
    recover_actual_context,
)
class SemanticCompositeSourceProof(unittest.TestCase):
    def test_corrections_unique_and_substantive(self):
        self.assertEqual(len(CORRECTIONS),10)
        self.assertIn((16,1),CORRECTIONS)
    def test_composite_source_bbox_is_original_geometry(self):
        with pymupdf.open() as deck:
            p=deck.new_page(width=400,height=300)
            p.insert_text((20,30),"Identity Alignment: tangent sine secant")
            p.insert_text((20,60),"Restricted Domains: secant remains positive")
            result=actual_source_composite(p,
                ((0,"Identity Alignment:"),(1,"Restricted Domains:")))
            self.assertEqual(len(result["original_pdf_source_blocks"]),2)
            self.assertTrue(result["original_pdf_visual_union_rect_pt"][3]>
                            result["original_pdf_visual_union_rect_pt"][1])
            self.assertFalse(result[
                "full_spoken_element_mathematics_semantically_approved"])
    def test_bad_source_math_anchor_fails(self):
        with pymupdf.open() as deck:
            p=deck.new_page(width=400,height=300)
            p.insert_text((20,30),"Tangent identity")
            with self.assertRaises(ValueError):
                actual_source_composite(p,((0,"No such math equation"),))
    def test_symbolic_and_principal_branch_checks(self):
        x=limited_domain_proofs()
        self.assertTrue(x["tangent_derivative_monotonic_identity"][
                        "symbolic_identity_pass"])
        self.assertTrue(x["positive_secant_radicand_square_identity"][
                        "symbolic_identity_pass"])
    def test_missing_protected_source_never_creates_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with self.assertRaises((ValueError,FileNotFoundError)):
                recover_actual_context(original=p/"original",
                    full_plan=p/"plan.json",
                    independent_media_audit=p/"old.json",out=p/"out.json")
            self.assertFalse((p/"out.json").exists())
if __name__=="__main__":unittest.main()
