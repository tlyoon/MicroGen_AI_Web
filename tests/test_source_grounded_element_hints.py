import tempfile,unittest
from pathlib import Path
from selenium_pipeline.source_grounded_element_hints import source_evidence_worklist
from selenium_pipeline.incremental_element_candidate_map import candidate_map
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_incremental_lecture_sync_queue import make_subchapter

class SourceElementEvidenceTests(unittest.TestCase):
    def test_every_utterance_has_independently_reverified_pdf_target(self):
        with tempfile.TemporaryDirectory() as t:
            folder=make_subchapter(Path(t)/"original","8.4")
            result=source_evidence_worklist(folder=folder)
            self.assertEqual(len(result["entries"]),result["utterance_count"])
            self.assertEqual(result["human_reviewed_count"],0)
            self.assertFalse(result["semantic_element_approval"])
            self.assertFalse(result["tts_authorized"])
    def test_forged_visible_pdf_text_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            folder=make_subchapter(Path(t)/"original","8.4")
            hints=candidate_map(folder=folder)
            block=hints["slides"][0]["candidate_visual_targets"][0]
            block["visible_text"]="FORGED MATH TEXT"
            with self.assertRaises(FigureIdentityReviewRequired):
                source_evidence_worklist(folder=folder,candidates=hints)
