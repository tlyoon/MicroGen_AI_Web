"""Twenty-seven original-source speech focus scenes, 41 full slide videos."""
import unittest
from selenium_pipeline.original_thomas85_86_multipart_qa_preview import (
    FOCUS, STATUS as MEDIA_STATUS)
from selenium_pipeline.original_thomas_all41_independent_joined_qa import (
    STATUS as INDEPENDENT_STATUS)
from selenium_pipeline.original_thomas85_86_derivation_audio_pixels import (
    CASES, STATUS as MATH_STATUS)

class TwentyNineSourceMathJoinedAcceptance(unittest.TestCase):
    def test_ten_plus_one_additional_scientific_scenes(self):
        self.assertEqual(sorted(FOCUS["8.5"]),[3,4,5,6,7,8,9])
        self.assertEqual(sorted(FOCUS["8.6"]),[3,4,5,7,8,10])
        self.assertEqual(16+len(FOCUS["8.5"])+len(FOCUS["8.6"]),29)

    def test_only_original_publisher_and_sympy_source_video_receipts(self):
        self.assertEqual([FOCUS["8.5"][n][2] for n in (7,8)],
                         ["derivation","derivation"])
        self.assertEqual(FOCUS["8.6"][7][2],"derivation")
        self.assertEqual(sorted(CASES),[("8.5",7),("8.5",8),("8.6",7)])
        self.assertIn("SIX_SOURCE_WORD_PIXEL_EVENTS_PASS",MATH_STATUS)

    def test_no_false_qa_promotion_to_student_release(self):
        self.assertIn("NOT_PRODUCTION",MEDIA_STATUS)
        self.assertIn("NONPRODUCTION",INDEPENDENT_STATUS)
        self.assertIn("41_SLIDE_29_VERIFIED",INDEPENDENT_STATUS)
        self.assertEqual(sorted(set(range(1,12))-set(FOCUS["8.5"])),
                         [1,2,10,11])
        self.assertEqual(sorted(set(range(1,14))-set(FOCUS["8.6"])),
                         [1,2,6,9,11,12,13])
if __name__=="__main__":
    unittest.main()
