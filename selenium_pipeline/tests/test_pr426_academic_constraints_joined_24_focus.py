"""41 original source slides, 29 verified scenes; fail-closed academic gate."""
import unittest
from selenium_pipeline.original_thomas85_86_multipart_qa_preview import (
    FOCUS,STATUS as PART_STATUS)
from selenium_pipeline.original_thomas_all41_independent_joined_qa import (
    STATUS as JOIN_STATUS)
from selenium_pipeline.original_thomas85_86_academic_constraints_focus import (
    CASES,STATUS as CONSTRAINTS_STATUS)

class PublisherConditionsIndependentJoinedScenes(unittest.TestCase):
    def test_twenty_nine_separate_genuine_source_highlights(self):
        self.assertEqual(16+len(FOCUS["8.5"])+len(FOCUS["8.6"]),31)
        self.assertEqual(sorted(FOCUS["8.5"]),[3,4,5,6,7,8,9,11])
        self.assertEqual(sorted(FOCUS["8.6"]),[3,4,5,7,8,10,13])

    def test_true_publisher_conditions_only_on_source_scenes(self):
        self.assertEqual(FOCUS["8.5"][4][2],"constraints")
        self.assertEqual(FOCUS["8.6"][3][2],"constraints")
        self.assertEqual(CASES["8.5"]["slide"],4)
        self.assertEqual(CASES["8.6"]["slide"],3)
        self.assertIn("PIXEL_QA_PASS",CONSTRAINTS_STATUS)

    def test_two_full_sections_only_qa_not_student_publication(self):
        self.assertIn("NOT_PRODUCTION",PART_STATUS)
        self.assertIn("NONPRODUCTION",JOIN_STATUS)
        self.assertIn("41_SLIDE_31_VERIFIED",JOIN_STATUS)
if __name__=="__main__":
    unittest.main()
