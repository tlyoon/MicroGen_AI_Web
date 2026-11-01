"""Eight separately source-grounded original slide focuses, no student release."""
import unittest
from selenium_pipeline.original_thomas84_multipart_qa_preview import (
    HIGHLIGHTS,PROVENANCE,BLOCKERS)
from selenium_pipeline.original_thomas84_slide7_inverse_domain_sync import KINDS

class EightSourceOriginalSlideAcceptance(unittest.TestCase):
    def test_eight_original_lecture_source_grounded_highlights(self):
        self.assertEqual(sorted(HIGHLIGHTS),[4,5,6,7,8,9,12,17])
        self.assertEqual(len(set(range(1,18))-set(HIGHLIGHTS)),9)

    def test_pr413_inverse_branch_requires_physical_pixel_proof(self):
        self.assertEqual(PROVENANCE[7],(
            "ORIGINAL_SLIDE7_SOURCE_INVERSE_DOMAIN_H264_PIXEL_QA_PASS",
            "encoded_mp4_sha256"))
        self.assertEqual(KINDS,(
            "inclusive_arcsine",
            "two_arcsecant_branches",
            "nonnegative_tangent_radical"))

    def test_remaining_source_and_student_gates_not_weakened(self):
        self.assertIn("NINE_SLIDES_STILL_LACK_CERTIFIED_ELEMENT_LEVEL_TIMED_HIGHLIGHTS",
                      BLOCKERS)
        self.assertIn("NOT_AN_AUTOMATED_STUDENT_PRODUCTION_RELEASE",BLOCKERS)
if __name__=="__main__":
    unittest.main()
