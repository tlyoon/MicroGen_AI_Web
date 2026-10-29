"""Independent audit rejects untrusted full MP4 and fake source sample claims."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_66_independent_media_audit import (
    physical_asset,audit_two_actual_real_parts,candidate_geometry,
)
class Source66PhysicalIndependentAudit(unittest.TestCase):
    def test_relative_path_cannot_masquerade_as_movie(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/"file.mp4").write_bytes(b"no real media")
            with self.assertRaises(ValueError):
                physical_asset("file.mp4",p)
    def test_duplicate_pdf_id_with_different_geometry_is_rejected(self):
        plan={"source_historical_slides":[{"slide":3,
            "physical_original_pdf_source_targets":[
              {"physical_original_pdf_element_id":"A",
               "physical_source_pdf_text":"sin u",
               "physical_original_pdf_rect_pt":[1,2,3,4]},
              {"physical_original_pdf_element_id":"A",
               "physical_source_pdf_text":"cos u",
               "physical_original_pdf_rect_pt":[1,2,3,4]},
            ]}]}
        with self.assertRaises(ValueError): candidate_geometry(plan)
    def test_missing_actual_source_refuses_fake_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);out=p/"result.json"
            with self.assertRaises((ValueError,FileNotFoundError)):
                audit_two_actual_real_parts(original=p/"original",
                    full_review_receipt=p/"missing.json",
                    source_plan_receipt=p/"missing2.json",
                    old_corrected_receipt=p/"missing3.json",out=out)
            self.assertFalse(out.exists())
if __name__=="__main__":unittest.main()
