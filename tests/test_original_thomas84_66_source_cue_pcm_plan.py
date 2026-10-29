"""Source PCM and 66-cue academic safety guard regression."""
from __future__ import annotations
import tempfile
import unittest
import pymupdf
from pathlib import Path
from selenium_pipeline.original_thomas84_66_source_cue_pcm_plan import (
    source_cue_event,combine_source_plan,
)
class Source66CuePlan(unittest.TestCase):
    def test_refuse_absent_real_source(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with self.assertRaises((ValueError,FileNotFoundError)):
                combine_source_plan(original=p/"original",
                    old_candidates=p/"prior.json",contextual_receipt=p/"new.json",
                    worked_math_receipt=p/"proof.json",out=p/"out.json")
            self.assertFalse((p/"out.json").exists())
    def test_spoken_source_trig_contradiction_blocks_mistake(self):
        with pymupdf.open() as doc:
            page=doc.new_page(width=400,height=240)
            page.insert_text((22,60),"The cosine u is positive")
            block=page.get_text("blocks")[0]
            unit={"sentence_index":1,
                  "spoken_original_fragment_sha256":"a"*64,
                  "unique_target_review_priority":False}
            new={"slide":3,"sentence_index":1,
                 "original_narration_fragment_sha256":"a"*64,
                 "spoken_element_sync_release_approved":False,
                 "original_pdf_visible_text":block[4].strip(),
                 "original_pdf_rect_pt":list(block[:4]),
                 "original_pdf_block_index":0,
                 "source_support_category":"contextual"}
            with self.assertRaises(ValueError):
                source_cue_event(page=page,slide=3,unit=unit,
                        contextual=new,narration="Use sine u")
    def test_contextual_math_still_unapproved(self):
        with pymupdf.open() as doc:
            page=doc.new_page(width=400,height=240)
            page.insert_text((22,60),"Use sine u to simplify")
            block=page.get_text("blocks")[0]
            unit={"sentence_index":1,
                  "spoken_original_fragment_sha256":"a"*64,
                  "unique_target_review_priority":False}
            new={"slide":3,"sentence_index":1,
                 "original_narration_fragment_sha256":"a"*64,
                 "spoken_element_sync_release_approved":False,
                 "original_pdf_visible_text":block[4].strip(),
                 "original_pdf_rect_pt":list(block[:4]),
                 "original_pdf_block_index":0,
                 "source_support_category":"contextual"}
            r=source_cue_event(page=page,slide=3,unit=unit,
                        contextual=new,narration="Use sine u")
            self.assertFalse(r["independent_full_source_math_semantics_approved"])
            self.assertFalse(r["student_publication_authorized"])
if __name__=="__main__":unittest.main()
