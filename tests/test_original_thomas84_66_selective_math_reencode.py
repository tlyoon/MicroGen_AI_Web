"""Composite corrected original source clip selection is sample precise."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.original_thomas84_66_selective_math_reencode import (
    locate_original_source_clip,physically_exact_source_composite,selectively_reencode
)
class SelectiveRealMathCorrection(unittest.TestCase):
    def test_sample_interval_disambiguates_same_source_box(self):
        rows=[
            {"source_slide":6,"candidate_target_id":"same",
             "existing_real_slide4_corrected":False,
             "source_first_pcm_sample":0,"source_last_pcm_sample_exclusive":15000},
            {"source_slide":6,"candidate_target_id":"same",
             "existing_real_slide4_corrected":False,
             "source_first_pcm_sample":15000,"source_last_pcm_sample_exclusive":30000}
        ]
        self.assertEqual(locate_original_source_clip(rows,slide=6,old_target="same",
                         first=18000,last=26000),1)
    def test_wrong_audio_interval_rejected(self):
        with self.assertRaises(ValueError):
            locate_original_source_clip([],slide=3,old_target="bad",
                first=0,last=500)
    def test_original_source_composite_geometry_requires_exact_math(self):
        with pymupdf.open() as document:
            p=document.new_page(width=400,height=200)
            p.insert_text((20,50),"Identity Alignment: x = a tan u")
            block=p.get_text("blocks")[0]
            row={"original_pdf_source_blocks":[{
                "original_pdf_block_index":0,
                "original_pdf_text":block[4].strip(),
                "original_pdf_bbox_pt":list(block[:4])}],
                "original_pdf_visual_union_rect_pt":list(block[:4])}
            self.assertEqual(len(physically_exact_source_composite(p,row)),4)
            row["original_pdf_source_blocks"][0]["original_pdf_text"]="wrong"
            with self.assertRaises(ValueError):
                physically_exact_source_composite(p,row)
    def test_missing_original_source_no_movie(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);out=p/"out"
            with self.assertRaises((ValueError,FileNotFoundError)):
                selectively_reencode(original=p/"source",
                    full_review_receipt=p/"a.json",
                    source_plan_receipt=p/"b.json",
                    independent_media_receipt=p/"c.json",
                    corrected_math_receipt=p/"d.json",out=out)
            self.assertFalse(out.exists())
if __name__=="__main__":unittest.main()
