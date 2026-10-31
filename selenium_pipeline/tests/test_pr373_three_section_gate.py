"""Unit safety checks for independent three-section acceptance."""
import unittest
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline.three_section_production_gate import inspect_three_sections

class TestAcceptance(unittest.TestCase):
    @patch("selenium_pipeline.three_section_production_gate.inspect_sync")
    @patch("selenium_pipeline.three_section_production_gate.inspect_all")
    @patch("selenium_pipeline.three_section_production_gate._sha", return_value="same")
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("pathlib.Path.is_symlink", return_value=False)
    def test_whole_slide_audio_not_element_acceptance(self, link, exists, sha, mapping, sync):
        mapping.return_value = dict(source_sha256="same", slides_sha256="same",
                                    script_sha256="same", slide_count=2,
                                    automatic_video_approved=False)
        sync.return_value = dict(source_sha256="same", slides_sha256="same",
                                 script_sha256="same", original_slide_wav_count=2,
                                 complete_verified_source_element_wav_receipts_found=False,
                                 real_spoken_element_audio_semantics_verified=False,
                                 all_visual_elements_highlighted_as_spoken_verified=False,
                                 final_true_sync_production_encoded=False,
                                 all_staged_preview_parts_strictly_under_600=False)
        result = inspect_three_sections(root=Path("fixture"))
        self.assertEqual(result["slides_checked"], 6)
        self.assertFalse(result["all_three_stages_pass"])
        self.assertEqual(len(result["sections"]), 3)
        self.assertTrue(all(len(s["blockers"]) == 3 for s in result["sections"]))
        self.assertFalse(result["student_publication_authorized"])

if __name__ == "__main__":
    unittest.main()
