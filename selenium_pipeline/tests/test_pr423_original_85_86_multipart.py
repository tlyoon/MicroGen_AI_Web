"""Full original source audio QA is not complete scientific video acceptance."""
import unittest
from selenium_pipeline.original_thomas85_86_multipart_qa_preview import (
    FOCUS,STATUS,MAX_DURATION)
from selenium_pipeline.original_thomas84_multipart_qa_preview import split_slides

class OriginalTwoSectionMultipartVideo(unittest.TestCase):
    def test_all_source_math_highlight_scenes_explicit_only(self):
        self.assertEqual(sorted(FOCUS["8.5"]),[3,4,5,6,7,8])
        self.assertEqual(sorted(FOCUS["8.6"]),[3,4,5,7,8])
        self.assertTrue(all(x[2] in ("first","more","constraints","derivation")
                            for m in FOCUS.values() for x in m.values()))
    def test_no_unverified_math_or_figure_implicit_approval(self):
        self.assertIn("NOT_PRODUCTION",STATUS)
        self.assertTrue(set(range(1,12))-set(FOCUS["8.5"]))
        self.assertTrue(set(range(1,14))-set(FOCUS["8.6"]))
    def test_strict_original_multipart_limit(self):
        self.assertLess(MAX_DURATION,600)
        p=split_slides([300.,270.,15.],limit=MAX_DURATION)
        self.assertEqual(p,[[1,2],[3]])
        self.assertTrue(all(sum([300.,270.,15.][i-1] for i in xs)<600
                            for xs in p))
if __name__=="__main__":
    unittest.main()
