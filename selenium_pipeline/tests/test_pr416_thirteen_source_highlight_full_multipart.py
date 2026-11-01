"""Thirteen source-matched elements do not certify entire original lecture."""
import unittest
from selenium_pipeline.original_thomas84_multipart_qa_preview import (
    HIGHLIGHTS,PROVENANCE,BLOCKERS,split_slides)
from selenium_pipeline.original_thomas84_five_worked_math_sync_batch import (
    BATCH_STATUS,WORKED)

class ThirteenVerifiedMathSlidePreview(unittest.TestCase):
    def test_all_thirteen_original_highlighted_scenes_are_real(self):
        self.assertEqual(sorted(HIGHLIGHTS),
            [3,4,5,6,7,8,9,10,11,12,13,14,15,16,17])
        self.assertEqual(
            sorted(set(range(1,18))-set(HIGHLIGHTS)),[1,2])

    def test_physical_original_worked_example_receipt_enforced(self):
        self.assertEqual(sorted(WORKED),[10,11,13,14,15])
        self.assertTrue(all(PROVENANCE[n]==(BATCH_STATUS,None)
                            for n in WORKED))
        self.assertTrue(all(HIGHLIGHTS[n][2] ==
            "FIVE_ORIGINAL_WORKED_MATH_CLIPS_INDEPENDENT_SOURCE_QA.json"
            for n in WORKED))

    def test_no_false_milestone_or_student_release(self):
        self.assertIn(
            "TWO_SLIDES_STILL_LACK_CERTIFIED_ELEMENT_LEVEL_TIMED_HIGHLIGHTS",
            BLOCKERS)
        self.assertIn("NOT_AN_AUTOMATED_STUDENT_PRODUCTION_RELEASE",BLOCKERS)
        self.assertIn(
            "ORIGINAL_ALL_SEVENTEEN_SLIDE_MATH_AND_FIGURE_SOURCE_SEMANTICS_NOT_APPROVED",
            BLOCKERS)

    def test_strict_auto_split_does_not_change_with_highlight_count(self):
        audio=[3.52,26.16,39.68,47.96,53.56,40.48,54.96,
               44.08,47.24,55.88,48.72,54.60,48.20,63.40,
               50.52,45.88,36.64]
        groups=split_slides(audio)
        self.assertEqual([n for group in groups for n in group],
                         list(range(1,18)))
        self.assertTrue(all(sum(audio[n-1] for n in group)<600
                            for group in groups))

if __name__=="__main__":
    unittest.main()
