"""35 distinct original source-spoken scenes, never complete academic approval."""
import unittest
from selenium_pipeline.original_thomas85_86_multipart_qa_preview import (
    FOCUS,STATUS)
from selenium_pipeline.original_thomas_all41_independent_joined_qa import (
    STATUS as PIXELS)
from selenium_pipeline.original_two_other_outline_true_word_timing import (
    TOPICS,STATUS as WORDS)

class ThirtyFiveOriginalSourceScenes(unittest.TestCase):
    def test_original_source_video_35_slide_foci(self):
        self.assertEqual(sorted(FOCUS["8.5"]),list(range(2,12)))
        self.assertEqual(sorted(FOCUS["8.6"]),[2,3,4,5,7,8,9,10,13])
        self.assertEqual(16+sum(len(v) for v in FOCUS.values()),35)
        self.assertEqual(FOCUS["8.5"][2][2],"outline")
        self.assertEqual(FOCUS["8.6"][2][2],"outline")
    def test_unverified_tank_figure_still_unapproved(self):
        self.assertEqual(len(TOPICS["8.6"]),4)
        self.assertEqual(len(TOPICS["8.5"]),5)
        self.assertEqual(sorted(set(range(1,14))-set(FOCUS["8.6"])),
                         [1,6,11,12])
        self.assertIn("NOT_PRODUCTION",STATUS)
        self.assertIn("41_SLIDE_35_VERIFIED",PIXELS)
        self.assertIn("APPROVED_ONLY",WORDS)
if __name__=="__main__":
    unittest.main()
