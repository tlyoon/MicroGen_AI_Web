"""Title stays static and no unverified element earns student release."""
import unittest
from selenium_pipeline.original_thomas84_multipart_qa_preview import (
    HIGHLIGHTS, PROVENANCE, BLOCKERS, split_slides)
from selenium_pipeline.original_thomas84_outline_real_word_focus import (
    STATUS, OUTLINE)

class SixteenSourceBoundMathAndOutlineHighlights(unittest.TestCase):
    def test_sixteen_verified_scenes_not_weakly_timed_title(self):
        self.assertEqual(sorted(HIGHLIGHTS),list(range(2,18)))
        self.assertEqual(sorted(set(range(1,18))-set(HIGHLIGHTS)),[1])

    def test_original_outline_requires_actual_word_and_pixel_evidence(self):
        self.assertEqual(len(OUTLINE),5)
        self.assertEqual(PROVENANCE[2],(STATUS,"actual_encoded_mp4_sha256"))
        self.assertEqual(HIGHLIGHTS[2][2],
            "original_slide2_real_word_source_pixel_qa.json")

    def test_low_asr_title_not_falsely_accepted(self):
        self.assertIn(
            "ONE_TITLE_SLIDE_NO_CERTIFIED_WORD_LEVEL_TIMED_HIGHLIGHTS",
            BLOCKERS)
        self.assertIn("NOT_AN_AUTOMATED_STUDENT_PRODUCTION_RELEASE",BLOCKERS)
        self.assertIn(
            "ORIGINAL_ALL_SEVENTEEN_SLIDE_MATH_AND_FIGURE_SOURCE_SEMANTICS_NOT_APPROVED",
            BLOCKERS)

    def test_nonnegotiable_mp4_duration_limit(self):
        parts=split_slides([560.,20.],limit=570.)
        self.assertEqual(parts,[[1],[2]])
        with self.assertRaises(Exception):
            split_slides([600.],limit=600.)
if __name__=="__main__":
    unittest.main()
