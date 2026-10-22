import unittest,tempfile,hashlib
from pathlib import Path
import pymupdf
from selenium_pipeline.pdf_text_source_span_witness import prove_source_quote_occurrence
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
class ExactTextbookWitness(unittest.TestCase):
    def test_real_page_quote_and_wrong_page(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/"s.pdf"
            with pymupdf.open() as d:
                d.new_page().insert_text((30,40),"A genuine source paragraph about limits.")
                d.new_page().insert_text((30,40),"A different topic")
                d.save(f)
            sha=hashlib.sha256(f.read_bytes()).hexdigest()
            r=prove_source_quote_occurrence(source_pdf=f,expected_sha256=sha,page_number=1,
                verbatim_quote="A genuine source paragraph about limits.")
            self.assertFalse(r["math_semantics_author_verified"])
            with self.assertRaises(FigureIdentityReviewRequired):
                prove_source_quote_occurrence(source_pdf=f,expected_sha256=sha,page_number=2,
                    verbatim_quote="A genuine source paragraph about limits.")
    def test_source_pdf_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/"source.pdf"
            with pymupdf.open() as d:
                d.new_page().insert_text((30,40),"Some real physical source content")
                d.save(f)
            with self.assertRaises(FigureIdentityReviewRequired):
                prove_source_quote_occurrence(source_pdf=f,expected_sha256="0"*64,
                    page_number=1,verbatim_quote="Some real physical source content")
