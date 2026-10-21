import tempfile,unittest
from pathlib import Path
from selenium_pipeline.incremental_element_candidate_map import candidate_map
from selenium_pipeline.incremental_lecture_sync_queue import inspect_folder
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_incremental_lecture_sync_queue import make_subchapter

class VisibleCandidateTests(unittest.TestCase):
    def test_exact_original_utterances_remain_source_bound_and_nonapproved(self):
        with tempfile.TemporaryDirectory() as t:
            folder=make_subchapter(Path(t),"8.4")
            result=candidate_map(folder=folder)
            self.assertEqual(result["slide_count"],3)
            self.assertEqual(result["utterance_count"],3)
            self.assertFalse(result["ready_for_paid_element_tts"])
            self.assertTrue(all(
                not u["element_tts_authorized"]
                for s in result["slides"] for u in s["original_utterance_candidates"]))
            self.assertTrue(all(
                x["bbox_pdf_pt"][0]>=0 for s in result["slides"]
                for x in s["candidate_visual_targets"]))
    def test_stale_source_queue_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            folder=make_subchapter(Path(t),"8.5")
            old=inspect_folder(folder)
            (folder/"script.txt").write_text("changed!",encoding="utf8")
            with self.assertRaises(FigureIdentityReviewRequired):
                candidate_map(folder=folder,queue=old)
    def test_malformed_or_partial_slide_rows_fail_closed(self):
        with tempfile.TemporaryDirectory() as t:
            folder=make_subchapter(Path(t),"8.6")
            original=inspect_folder(folder)
            original["slides"]=original["slides"][:-1]
            with self.assertRaises(FigureIdentityReviewRequired):
                candidate_map(folder=folder,queue=original)
