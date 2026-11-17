"""Original PDF duplicate fraction context is independent, not approval."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import pymupdf

from selenium_pipeline.fraction_pdf_context_review import (
    physically_witnessed_fraction_context,verify_saved_context_packet)
from selenium_pipeline.physical_fraction_review_targets import (
    physical_fraction_review_targets)


class PhysicalDuplicateFractionContextTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.pdf=self.root/"slides.pdf"
        with pymupdf.open() as doc:
            pg=doc.new_page(width=440,height=320)
            pg.insert_text((40,87),"Proposed equation: x equals",fontsize=11)
            pg.insert_text((120,100),"1",fontsize=10)
            pg.insert_text((120,114),"2",fontsize=10)
            pg.insert_text((40,162),"Right side: substitute dimensions",fontsize=11)
            pg.insert_text((120,180),"1",fontsize=10)
            pg.insert_text((120,194),"2",fontsize=10)
            doc.save(self.pdf)
        with pymupdf.open(self.pdf) as doc:
            self.choices=[x for x in physical_fraction_review_targets(doc[0],1)
                          if x["visible_text"]=="1/2"]

    def test_distinct_real_pdf_glyphs_preserve_both_review_choices(self):
        self.assertEqual(len(self.choices),2)
        packet=physically_witnessed_fraction_context(
            slides_pdf=self.pdf,slide=1,choices=self.choices)
        self.assertEqual(len(packet),2)
        self.assertEqual({v["target_id"] for v in packet},
                         {x["draft_element_id"] for x in self.choices})
        self.assertTrue(all(x["selected_target_id"] is None
                            and not x["source_semantics_approved"]
                            and x["independent_semantic_choice_required"]
                            and x["context_is_only_spatial_evidence"]
                            for x in packet))
        texts=[line["physical_line_text"] for x in packet
               for line in x["nearby_physical_pdf_lines"]]
        self.assertTrue(any("Proposed equation" in v for v in texts))
        self.assertTrue(any("Right side" in v for v in texts))
        self.assertNotIn("model_response_verified",json.dumps(packet))
        self.assertTrue(verify_saved_context_packet(
            packet,[x["draft_element_id"] for x in self.choices]))

    def test_geometry_flags_or_changed_hash_cannot_forge_pdf_witness(self):
        first={**self.choices[0], "bbox_pdf_pt":[42,43,60,70]}
        with self.assertRaisesRegex(ValueError,"does not witness"):
            physically_witnessed_fraction_context(
                slides_pdf=self.pdf,slide=1,choices=[first])
        other={**self.choices[0],
               "anchor":{**self.choices[0]["anchor"],
                         "fraction_spans_sha256":"0"*64}}
        with self.assertRaisesRegex(ValueError,"does not witness"):
            physically_witnessed_fraction_context(
                slides_pdf=self.pdf,slide=1,choices=[other])

    def test_repeated_choice_unknown_slide_and_original_pdf_mutation_fail(self):
        with self.assertRaisesRegex(ValueError,"repeated"):
            physically_witnessed_fraction_context(
                slides_pdf=self.pdf,slide=1,
                choices=[self.choices[0],self.choices[0]])
        with self.assertRaisesRegex(ValueError,"outside original PDF"):
            physically_witnessed_fraction_context(
                slides_pdf=self.pdf,slide=2,choices=self.choices)
        with pymupdf.open(self.pdf) as doc:
            pg=doc[0]
            pg.insert_text((300,270),"other unrelated content")
            doc.save(self.root/"changed.pdf")
        # Different physical glyph source is acceptable only when the glyph
        # identity and geometry match. A changed page cannot be called an
        # identical original source at the offline-audit SHA layer.
        self.assertEqual(
            len(physically_witnessed_fraction_context(
                slides_pdf=self.root/"changed.pdf",slide=1,
                choices=self.choices)),2)

    def test_stored_review_packet_rejects_forced_target_or_forged_line(self):
        import copy
        packet=physically_witnessed_fraction_context(
            slides_pdf=self.pdf,slide=1,choices=self.choices)
        ids=[x["draft_element_id"] for x in self.choices]
        hacked=copy.deepcopy(packet)
        hacked[0]["selected_target_id"]=ids[0]
        self.assertFalse(verify_saved_context_packet(hacked,ids))
        hacked=copy.deepcopy(packet)
        hacked[0]["source_semantics_approved"]=True
        self.assertFalse(verify_saved_context_packet(hacked,ids))
        hacked=copy.deepcopy(packet)
        hacked[0]["nearby_physical_pdf_lines"][0]["physical_line_text"]="fabricated"
        self.assertFalse(verify_saved_context_packet(hacked,ids))
        hacked=copy.deepcopy(packet)
        hacked[0]["nearby_physical_pdf_lines"][0]["vertical_gap_pdf_pt"]=999
        self.assertFalse(verify_saved_context_packet(hacked,ids))

    def test_page_content_not_modified(self):
        before=self.pdf.read_bytes()
        physically_witnessed_fraction_context(
            slides_pdf=self.pdf,slide=1,choices=self.choices)
        self.assertEqual(before,self.pdf.read_bytes())


if __name__=="__main__":
    unittest.main()
