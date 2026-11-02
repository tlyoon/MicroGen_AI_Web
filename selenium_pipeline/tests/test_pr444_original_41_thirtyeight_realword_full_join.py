"""Three true WAV focus clips integrated without reclassifying historic QA."""
import unittest
from selenium_pipeline.original_thomas86_all41_thirtyeight_joined_qa import (
    NEW_STATUS,NEW_FOCUS,PILOT_SUBDIR,PREVIOUS_QA_SUBDIR,
)
from selenium_pipeline.original_thomas86_remaining_realword_focus import EVENTS
from selenium_pipeline.original_thomas85_86_multipart_qa_preview import FOCUS
from selenium_pipeline.original_three_section_academic_remaining_inventory import (
    is_structural_title_only,
)

class FullOriginalSourceVideoIntegration(unittest.TestCase):
    def test_original_41_and_38_source_spoken_focus_coverage(self):
        self.assertEqual(NEW_FOCUS,{6,11,12})
        self.assertEqual(sorted(FOCUS["8.6"]),[2,3,4,5,7,8,9,10,13])
        self.assertEqual(len(FOCUS["8.5"]),10)
        self.assertEqual(16+10+9+len(NEW_FOCUS),38)
        self.assertEqual(set(FOCUS["8.6"]).union(NEW_FOCUS),set(range(2,14)))

    def test_47_real_distinct_spoken_source_element_samples(self):
        self.assertEqual([len(EVENTS[n]) for n in (6,11,12)],[4,3,5])
        self.assertEqual(16+10+9+sum(map(len,EVENTS.values())),47)
        self.assertTrue("47_REAL_FOCUS_EVENT_SAMPLES" in NEW_STATUS)
        self.assertTrue(NEW_STATUS.endswith("NONPRODUCTION"))

    def test_older_35_scene_witness_not_misrepresented_as_new(self):
        self.assertIn("PR443",PILOT_SUBDIR)
        self.assertIn("PR437",PREVIOUS_QA_SUBDIR)
        self.assertNotIn(6,FOCUS["8.6"])
        self.assertNotIn(11,FOCUS["8.6"])
        self.assertNotIn(12,FOCUS["8.6"])

    def test_original_structural_only_title_exemption_unaltered(self):
        self.assertTrue(is_structural_title_only(
            r"\begin{frame}"+"\n"+r"\titlepage"+"\n"+r"\end{frame}"))
        self.assertFalse(is_structural_title_only(
            r"\begin{frame}"+"\n"+r"\titlepage"+"\n"+r"\[x^2\]"+"\n"+r"\end{frame}"))

if __name__=="__main__":
    unittest.main()
