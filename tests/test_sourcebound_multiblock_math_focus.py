"""Windows real-PDF multi-block authored mathematics focus integration.

Tests the ORIGINAL extraction/selection interfaces, not a figure-specific
semantic check or speculative model approval. Source hashes and physical PDF
text block bytes are reread before focus/element preparation.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.scene_candidate_authoring import draft
from selenium_pipeline.element_narration_stage import rectangle,ElementStageError
from selenium_pipeline.sourcebound_multiblock_text_focus import (
    discover_groups,text_group_rect,TextGroupBlocked,
)


class SourceboundMultiblockMathFocusTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.source=self.root/"source.pdf"
        self.slides=self.root/"slides.pdf"
        with pymupdf.open() as source:
            page=source.new_page(width=480,height=390)
            page.insert_text((70,110),"Substitution gives a relationship involving x and theta.")
            source.save(self.source)
        with pymupdf.open() as document:
            page=document.new_page(width=480,height=390)
            page.insert_text((70,120),"The algebraic identity begins with x = a tan theta.")
            page.insert_text((72,142),"The next expression contains sec squared theta = 1 + tan squared theta.")
            page.insert_text((70,260),"The integration result is explained later in this slide.")
            document.save(self.slides)

    def test_adjacent_actual_math_blocks_form_real_grouped_focus(self):
        with pymupdf.open(self.slides) as pdf:
            actual=draft(self.source,self.slides)
            groups=[r for r in actual["slides"][0]["targets"]
                    if r["type"]=="text_group"]
            self.assertTrue(groups)
            group=groups[0]
            self.assertTrue(group["review_required"])
            self.assertTrue(group["mathematical_equivalence_proof_required"])
            self.assertEqual(group["anchor"]["type"],"text_group")
            rect,category=rectangle(pdf[0],group["anchor"])
            self.assertEqual(category,"text")
            self.assertGreater(rect.height,20)
            self.assertLess(rect.height,pdf[0].rect.height*.40)
            self.assertGreater(len(group["visible_text"]),50)
        self.assertFalse(actual["automatic_approval"])

    def test_mathematical_text_group_requires_exact_original_block_sha(self):
        with pymupdf.open(self.slides) as pdf:
            target=next(r for r in draft(self.source,self.slides)["slides"][0]["targets"]
                        if r["type"]=="text_group")
            damaged={**target["anchor"],
                     "text_sha256":["0"*64]+target["anchor"]["text_sha256"][1:]}
            with self.assertRaisesRegex(ElementStageError,
                                        "grouped math/text anchor"):
                rectangle(pdf[0],damaged)

    def test_distant_unrelated_equation_does_not_become_one_highlight(self):
        with pymupdf.open() as pdf:
            page=pdf.new_page(width=480,height=390)
            page.insert_text((70,110),"Identity: x = a tan theta.")
            page.insert_text((70,275),"Identity: x = a sin theta.")
            groups=discover_groups(page,1,[
                {"type":"text_block","anchor":{"type":"text_block","index":0}},
                {"type":"text_block","anchor":{"type":"text_block","index":1}}])
            self.assertEqual(groups,[])

    def test_missing_overlapping_or_far_apart_block_indices_rejected(self):
        with pymupdf.open(self.slides) as pdf:
            group=next(r for r in draft(self.source,self.slides)["slides"][0]["targets"]
                       if r["type"]=="text_group")
            anchor=group["anchor"]
            self.assertRaises(TextGroupBlocked,text_group_rect,pdf[0],
                              {**anchor,"indices":[1,1]})
            self.assertRaises(TextGroupBlocked,text_group_rect,pdf[0],
                              {**anchor,"indices":[1,100]})
            self.assertRaises(TextGroupBlocked,text_group_rect,pdf[0],
                              {**anchor,"indices":[1]})

    def test_all_candidate_focus_comes_from_author_pdf_not_model_geometry(self):
        with pymupdf.open(self.slides) as pdf:
            page=pdf[0]
            groups=[x for x in draft(self.source,self.slides)["slides"][0]["targets"]
                    if x["type"]=="text_group"]
            for group in groups:
                physical,_=rectangle(page,group["anchor"])
                self.assertEqual([round(float(v),2) for v in physical],
                                 group["rect_pt"])
                self.assertTrue(page.rect.contains(physical))


if __name__=="__main__":
    unittest.main()
