"""Fifteen source-verified slide elements: academic release remains blocked."""
import unittest

from selenium_pipeline.original_thomas84_multipart_qa_preview import (
    HIGHLIGHTS, PROVENANCE, BLOCKERS, split_slides)
from selenium_pipeline.original_thomas84_intro_summary_source_sync import (
    CASES, STATUS)

class FifteenActualSourceBoundHighlightPreview(unittest.TestCase):
    def test_original_15_math_and_procedure_focus_clips(self):
        self.assertEqual(sorted(HIGHLIGHTS),
            [3,4,5,6,7,8,9,10,11,12,13,14,15,16,17])
        self.assertEqual(sorted(set(range(1,18))-set(HIGHLIGHTS)),[1,2])

    def test_intro_and_summary_have_actual_source_pixel_witnesses(self):
        self.assertEqual(sorted(CASES),[3,16])
        self.assertEqual(sum(len(a) for a in CASES.values()),6)
        self.assertEqual(PROVENANCE[3],(STATUS,None))
        self.assertEqual(PROVENANCE[16],(STATUS,None))
        self.assertTrue(all(HIGHLIGHTS[n][2] ==
            "INTRO_SUMMARY_SOURCE_VIDEO_AND_PIXEL_QA.json"
            for n in (3,16)))

    def test_weak_title_asr_and_unproven_summary_bullet_not_accepted(self):
        self.assertIn(
            "TWO_SLIDES_STILL_LACK_CERTIFIED_ELEMENT_LEVEL_TIMED_HIGHLIGHTS",
            BLOCKERS)
        self.assertIn(
            "ORIGINAL_ALL_SEVENTEEN_SLIDE_MATH_AND_FIGURE_SOURCE_SEMANTICS_NOT_APPROVED",
            BLOCKERS)
        self.assertIn("NOT_AN_AUTOMATED_STUDENT_PRODUCTION_RELEASE",BLOCKERS)

    def test_strict_600_duration_contract_retained(self):
        audio=[3.52,26.16,39.68,47.96,53.56,40.48,54.96,
               44.08,47.24,55.88,48.72,54.60,48.20,63.40,
               50.52,45.88,36.64]
        chunks=split_slides(audio)
        self.assertEqual([n for g in chunks for n in g],
                         list(range(1,18)))
        self.assertTrue(all(sum(audio[j-1] for j in g)<600 for g in chunks))

if __name__=="__main__":
    unittest.main()
