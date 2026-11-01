"""41 original source scenes and 29 genuine highlight scenes, still QA-only."""
import unittest
from selenium_pipeline.original_thomas_all41_independent_joined_qa import STATUS
from selenium_pipeline.original_thomas85_86_multipart_qa_preview import (
    SOURCE,FOCUS)

class IndependentRealJoinedAll41Contract(unittest.TestCase):
    def test_complete_original_section_count_with_prior_sixteen(self):
        self.assertEqual(17+SOURCE["8.5"]["slides"]+
                         SOURCE["8.6"]["slides"],41)
        self.assertEqual(16+sum(map(len,FOCUS.values())),35)
    def test_new_joined_source_worked_math_only(self):
        self.assertEqual(sorted(FOCUS["8.5"]),[2,3,4,5,6,7,8,9,10,11])
        self.assertEqual(sorted(FOCUS["8.6"]),[2,3,4,5,7,8,9,10,13])
        self.assertEqual(len(FOCUS["8.5"])+len(FOCUS["8.6"]),19)
    def test_qa_does_not_conflate_pixel_samples_with_academic_proof(self):
        self.assertIn("NONPRODUCTION",STATUS)
        self.assertIn("41",STATUS)
        self.assertIn("35",STATUS)
if __name__=="__main__":
    unittest.main()
