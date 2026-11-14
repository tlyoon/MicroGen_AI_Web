"""Source quote recovery must exclude prior-section carryover and navigation.

Synthetic and real textbook PDFs are never treated as proof of scientific
or equation correctness merely because literal text can be quoted.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import pymupdf

from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.source_verified_quote_candidates import (
    _line_catalog, _section_scope_first_page, _publisher_navigation,
)
from selenium_pipeline.pdf_text_source_span_witness import prove_source_quote_occurrence


class PhysicallyScopedSourceEvidenceTests(unittest.TestCase):
    def test_previous_section_carryover_is_removed_only_with_matching_heading(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"6.4"
            p.mkdir()
            file=p/"source.pdf"
            with pymupdf.open() as doc:
                page=doc.new_page(width=600,height=780)
                page.insert_text((45,95),
                    "Previous topic smartphone on a turning teacup.")
                page.insert_text((45,270),
                    "This is another previous topic explanation.")
                page.insert_text((160,370),
                    "6.4 Motion in a Medium Under Resistance")
                page.insert_text((45,430),
                    "The resistive force points opposite relative velocity.")
                page.insert_text((45,458),
                    "The drag grows as the object speed increases.")
                doc.save(file)
            with pymupdf.open(file) as doc:
                self.assertGreater(_section_scope_first_page(doc[0],file),300)
            candidates=_line_catalog(str(file),_sha(file))
            combined=" | ".join(x[1] for x in candidates)
            self.assertIn("resistive force",combined)
            self.assertNotIn("smartphone",combined)
            for n,quote,terms,bbox in candidates:
                self.assertGreaterEqual(bbox[1],355)
                proof=prove_source_quote_occurrence(
                    source_pdf=file,expected_sha256=_sha(file),
                    page_number=n,verbatim_quote=quote)
                self.assertTrue(proof["source_sha256"])

    def test_no_numeric_folder_match_means_no_unjustified_discard(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"source"
            p.mkdir()
            file=p/"source.pdf"
            with pymupdf.open() as doc:
                page=doc.new_page(width=600,height=780)
                page.insert_text((45,100),
                    "Older source text kept without section identity.")
                page.insert_text((160,370),
                    "6.4 Motion in a Medium Under Resistance")
                page.insert_text((45,430),
                    "Recent resistive force observations remain.")
                doc.save(file)
            with pymupdf.open(file) as doc:
                self.assertIsNone(_section_scope_first_page(doc[0],file))
            candidates=_line_catalog(str(file),_sha(file))
            self.assertTrue(any("Older source text" in x[1] for x in candidates))

    def test_three_four_line_paragraph_quote_is_physical_not_spliced(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/"source.pdf"
            paragraph=(
                "The model describes a resistance that depends on an object's speed.\n"
                "For a falling sphere the downward weight is constant at every time.\n"
                "The resistive force increases as the falling velocity grows.\n"
                "At terminal speed the upward drag balances the downward weight."
            )
            with pymupdf.open() as doc:
                page=doc.new_page(width=600,height=780)
                space=page.insert_textbox(
                    pymupdf.Rect(44,100,548,400),paragraph,fontsize=12)
                self.assertGreater(space,0)
                doc.save(source)
            candidates=_line_catalog(str(source),_sha(source))
            long=[q for page,q,*_ in candidates if len(q)>200]
            self.assertGreater(len(long),0)
            for quote in long:
                proof=prove_source_quote_occurrence(
                    source_pdf=source,expected_sha256=_sha(source),
                    page_number=1,verbatim_quote=quote)
                self.assertEqual(proof["source_sha256"],_sha(source))

    def test_bad_assessment_footer_is_rejected_without_rewriting_real_claims(self):
        self.assertTrue(_publisher_navigation(
            "For additional assessment items for this section, go to"))
        self.assertFalse(_publisher_navigation(
            "Terminal velocity follows a balance of drag and weight."))

    def test_real_original_serway_section_heading_excludes_previous_smartphone(self):
        root=Path.home()/"AppData"/"Local"/"MicroGen_AI_Web_Checkpoints"
        src=(root/"20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"
             /"source_tree"/"6"/"6.4"/"source.pdf")
        if not src.is_file():
            self.skipTest("Real source only available on authorized Dell checkpoint")
        candidates=_line_catalog(str(src),_sha(src))
        first=[text for page,text,*_ in candidates if page==1]
        self.assertGreater(len(first),0)
        self.assertFalse(any("smartphone" in text.lower() for text in first))
        self.assertTrue(any("medium" in text.lower()
                            or "resistive" in text.lower() for text in first))
        self.assertFalse(any(_publisher_navigation(row[1])
                             for row in candidates))


if __name__=="__main__":
    unittest.main()
