"""29 tested mathematically source-bound focused scenes; still no release."""
import unittest
from selenium_pipeline.original_thomas85_86_multipart_qa_preview import (
    FOCUS,STATUS as PREVIEW)
from selenium_pipeline.original_thomas_all41_independent_joined_qa import (
    STATUS as AUDIT)
from selenium_pipeline.original_thomas85_86_coverup_erf_source import (
    CASES,STATUS as PUBLISHER)

class TwentyNineAll41OriginalSourceReview(unittest.TestCase):
    def test_two_new_genuine_mathematical_or_source_focus_scenes(self):
        self.assertEqual(sorted(FOCUS["8.5"]),[3,4,5,6,7,8,9])
        self.assertEqual(sorted(FOCUS["8.6"]),[3,4,5,7,8,10])
        self.assertEqual(16+len(FOCUS["8.5"])+len(FOCUS["8.6"]),29)
    def test_source_math_clip_receipt_exists_for_covered_original_slides(self):
        self.assertEqual(FOCUS["8.5"][9][2],"coverup_erf")
        self.assertEqual(FOCUS["8.6"][10][2],"coverup_erf")
        self.assertEqual(sorted(CASES),[("8.5",9),("8.6",10)])
        self.assertIn("SOURCE_MATH_PIXEL_EVENTS_PASS",PUBLISHER)
    def test_release_and_unverified_source_maths_remain_blocked(self):
        self.assertIn("NOT_PRODUCTION",PREVIEW)
        self.assertIn("NONPRODUCTION",AUDIT)
        self.assertIn("41_SLIDE_29_VERIFIED",AUDIT)
        self.assertEqual(sorted(set(range(1,12))-set(FOCUS["8.5"])),
                         [1,2,10,11])
        self.assertEqual(sorted(set(range(1,14))-set(FOCUS["8.6"])),
                         [1,2,6,9,11,12,13])
if __name__=="__main__":
    unittest.main()
