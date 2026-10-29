"""Reject fabricated textbook quotations spliced from distant PDF regions."""
import hashlib
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.pdf_text_source_span_witness import prove_source_quote_occurrence
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired


def make_pdf(path:Path,placements):
    with pymupdf.open() as doc:
        page=doc.new_page(width=600,height=760)
        for x,y,txt in placements:
            page.insert_text((x,y),txt,fontsize=11)
        doc.save(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SpatialSourceWitness(unittest.TestCase):
    def test_two_columns_on_same_baseline_were_false_original_quote(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"source.pdf"
            sha=make_pdf(p,[
                (40,90,"The derivative is"),
                (300,90,"equal to cosine"),
            ])
            with pymupdf.open(p) as doc:
                extracted=" ".join(doc[0].get_text(sort=True).split())
            self.assertIn("The derivative is equal to cosine",extracted)
            with self.assertRaisesRegex(FigureIdentityReviewRequired,"column"):
                prove_source_quote_occurrence(
                    source_pdf=p,expected_sha256=sha,page_number=1,
                    verbatim_quote="The derivative is equal to cosine")
            self.assertFalse(prove_source_quote_occurrence(
                source_pdf=p,expected_sha256=sha,page_number=1,
                verbatim_quote="The derivative is")["math_semantics_author_verified"])

    def test_true_contiguous_quote_remains_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"source.pdf"
            sha=make_pdf(p,[(40,90,"The integral follows the Pythagorean identity.")])
            result=prove_source_quote_occurrence(
                source_pdf=p,expected_sha256=sha,page_number=1,
                verbatim_quote="The integral follows the Pythagorean identity.")
            self.assertEqual(result["status"],"EXACT_ORIGINAL_PDF_PAGE_QUOTE_PRESENT")
            self.assertFalse(result["publication_authorized"])

    def test_true_wrapped_paragraph_can_still_be_witnessed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"source.pdf"
            sentence="An exact original paragraph continues into the next line."
            with pymupdf.open() as doc:
                page=doc.new_page(width=500,height=700)
                page.insert_textbox(pymupdf.Rect(40,45,180,180),
                                    sentence,fontsize=11)
                doc.save(p)
            sha=hashlib.sha256(p.read_bytes()).hexdigest()
            with pymupdf.open(p) as doc:
                extracted=" ".join(doc[0].get_text(sort=True).split())
            self.assertIn(sentence,extracted)
            result=prove_source_quote_occurrence(
                source_pdf=p,expected_sha256=sha,page_number=1,
                verbatim_quote=sentence)
            self.assertFalse(result["math_semantics_author_verified"])

    def test_multiple_identical_quotations_require_correct_occurrence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"source.pdf"
            sha=make_pdf(p,[
                (40,90,"This formula is cited twice."),
                (40,200,"This formula is cited twice."),
            ])
            with self.assertRaises(FigureIdentityReviewRequired):
                prove_source_quote_occurrence(source_pdf=p,expected_sha256=sha,
                    page_number=1,verbatim_quote="This formula is cited twice.")
            got=prove_source_quote_occurrence(source_pdf=p,expected_sha256=sha,
                page_number=1,verbatim_quote="This formula is cited twice.",
                occurrence_index=1)
            self.assertEqual(got["chosen_occurrence"],1)

    def test_unrelated_text_blocks_cannot_claim_same_source_sentence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"source.pdf"
            sha=make_pdf(p,[
                (40,90,"A mathematical identity"),
                (40,140,"is not proved by typography."),
            ])
            # This distant two-line phrase is visually separate material.
            try:
                found=prove_source_quote_occurrence(source_pdf=p,expected_sha256=sha,
                    page_number=1,
                    verbatim_quote="A mathematical identity is not proved by typography.")
            except FigureIdentityReviewRequired:
                pass
            else:
                self.fail("Distant separated blocks were incorrectly accepted")
