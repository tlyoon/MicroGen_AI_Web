"""Original PDF geometry and math-risk screen regression checks."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.original_thomas84_pdf_math_risk import (
    physical_matches, triage_flags, audit_original_pdf_review,
)

class SourcePDFMathRisk(unittest.TestCase):
    def test_source_math_risks_are_not_approved(self):
        self.assertIn("POSSIBLE_SPLIT_EQUATION_OR_FRACTION",
            triage_flags("For sine, use inverse sine", "2 < u < π", .28))
        self.assertIn("LOW_MATCH_STRENGTH",
            triage_flags("sin u", "sin u", .20))
    def test_actual_text_geometry_must_exist(self):
        with pymupdf.open() as doc:
            page=doc.new_page(width=400,height=200)
            page.insert_text((20,50),"3 Integrate: Evaluate the result")
            block=page.get_text("blocks")[0]
            valid={"source_pdf_rect_pt":list(block[:4]),
                   "actual_visible_original_pdf_text":block[4]}
            self.assertTrue(physical_matches(page,valid))
            invalid={**valid,"source_pdf_rect_pt":[1,1,100,40]}
            self.assertFalse(physical_matches(page,invalid))
    def test_reject_source_absent_without_outfile(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); output=root/"report.json"
            with self.assertRaises((ValueError, FileNotFoundError)):
                audit_original_pdf_review(
                    original=root/"missing",
                    candidate_receipt=root/"missing.json",output=output)
            self.assertFalse(output.exists())

if __name__=="__main__":
    unittest.main()
