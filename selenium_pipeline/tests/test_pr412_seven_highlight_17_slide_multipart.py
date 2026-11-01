"""Seven real source-bound clips, not a blanket full-section production pass."""
import unittest
from selenium_pipeline.original_thomas84_multipart_qa_preview import (
    HIGHLIGHTS,PROVENANCE,BLOCKERS)
from selenium_pipeline.original_thomas84_slide8_procedure_sync import (
    KEYWORDS,SPOKEN_PREFIX)

class SevenVerifiedElementSlides(unittest.TestCase):
    def test_full_original_slide_coverage_has_seven_verified_focus_clips(self):
        self.assertEqual(sorted(HIGHLIGHTS),[4,5,6,8,9,12,17])
        self.assertEqual(len(set(range(1,18))-set(HIGHLIGHTS)),10)

    def test_four_source_math_procedure_steps_have_independent_pixel_receipt(self):
        self.assertEqual(PROVENANCE[8],(
            "ORIGINAL_SLIDE8_FOUR_SOURCE_PROCEDURE_HIGHLIGHTS_PIXEL_QA_PASS",
            "actual_encoded_mp4_sha256"))
        self.assertEqual(sorted(KEYWORDS),[1,2,3,4])
        self.assertEqual(len(SPOKEN_PREFIX),4)

    def test_figure_and_unmapped_original_elements_remain_unapproved(self):
        self.assertIn("TEN_SLIDES_STILL_LACK_CERTIFIED_ELEMENT_LEVEL_TIMED_HIGHLIGHTS",
                      BLOCKERS)
        self.assertIn("NOT_AN_AUTOMATED_STUDENT_PRODUCTION_RELEASE",BLOCKERS)

if __name__=="__main__":
    unittest.main()
