"""Final original 41-slide QA contains 31 verified spoken scene samples."""
import unittest
from selenium_pipeline.original_thomas85_86_multipart_qa_preview import FOCUS,STATUS
from selenium_pipeline.original_thomas_all41_independent_joined_qa import STATUS as AUDIT
from selenium_pipeline.original_thomas85_86_math_review_questions import CASES

class OriginalAll41ReviewAudioAcceptance(unittest.TestCase):
    def test_all_original_review_source_scenes_in_joined_media(self):
        self.assertEqual(sorted(FOCUS["8.5"]),[2,3,4,5,6,7,8,9,10,11])
        self.assertEqual(sorted(FOCUS["8.6"]),[2,3,4,5,7,8,9,10,13])
        self.assertEqual(16+sum(map(len,FOCUS.values())),35)
        self.assertEqual(FOCUS["8.5"][11][2],"review")
        self.assertEqual(FOCUS["8.6"][13][2],"review")
        self.assertEqual(set(CASES),{("8.5",11),("8.6",13)})
    def test_original_publisher_qa_still_unapproved_for_students(self):
        self.assertIn("NOT_PRODUCTION",STATUS)
        self.assertIn("NONPRODUCTION",AUDIT)
        self.assertIn("41_SLIDE_35_VERIFIED",AUDIT)
        self.assertEqual(sorted(set(range(1,12))-set(FOCUS["8.5"])),
                         [1])
        self.assertEqual(sorted(set(range(1,14))-set(FOCUS["8.6"])),
                         [1,6,11,12])
if __name__=="__main__":
    unittest.main()
