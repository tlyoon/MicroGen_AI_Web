"""Source-only semantic candidate geometry and release safety constraints."""
from __future__ import annotations
import tempfile
import unittest
import pymupdf
from pathlib import Path
from selenium_pipeline.original_thomas84_37_contextual_cues import (
    SOURCE_CUES,_actual_block,build_contextual_source_cues,
)

class OriginalPdf37Cues(unittest.TestCase):
    def test_no_duplicate_missing_source_utterances(self):
        self.assertEqual(len(SOURCE_CUES),37)
        self.assertEqual(len({(x[0],x[1]) for x in SOURCE_CUES}),37)
    def test_all_source_candidates_unapproved(self):
        self.assertTrue(all(x[-1] in ("contextual","direct") for x in SOURCE_CUES))
    def test_geometry_requires_actual_exact_original_text(self):
        with pymupdf.open() as d:
            p=d.new_page(width=500,height=350)
            p.insert_text((20,55),"Step 2 Simplify the expression")
            row=_actual_block(p,0,"Simplify the expression")
            self.assertEqual(row["original_pdf_block_index"],0)
            with self.assertRaises(ValueError):
                _actual_block(p,0,"Unseen step")
    def test_no_original_source_never_creates_receipt(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with self.assertRaises((ValueError,FileNotFoundError)):
                build_contextual_source_cues(
                    original=p/"original",existing_candidates=p/"none.json",
                    release_guard=p/"none2.json",out=p/"out.json")
            self.assertFalse((p/"out.json").exists())

if __name__=="__main__":unittest.main()
