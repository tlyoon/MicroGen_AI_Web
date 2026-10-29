import os,unittest,tempfile,wave
from pathlib import Path
from selenium_pipeline.offline_replacement_replanner import measured_replacement_replan
class OfflineRepartition(unittest.TestCase):
    def test_real_original_three_topics(self):
        chapter=os.environ.get("MICROGEN_ORIGINAL_THOMAS_CHAPTER")
        if not chapter:self.skipTest("Genuine original sources only on Dell-115")
        report=measured_replacement_replan(chapter=Path(chapter))
        self.assertEqual([len(r["parts"]) for r in report["source_sections"]],[2,2,2])
        self.assertEqual(report["new_audio_candidate_slides"],0)
        self.assertFalse(report["all_new_encoded_videos_accepted"])
    def test_other_historical_slide_cannot_fake_a_corrected_utterance(self):
        chapter=os.environ.get("MICROGEN_ORIGINAL_THOMAS_CHAPTER")
        if not chapter:self.skipTest("Genuine prior-slide audio only on Dell-115")
        stolen=str(Path(chapter)/"8.4"/"slide5.wav")
        with self.assertRaises(ValueError):
            measured_replacement_replan(
                chapter=Path(chapter),replacements={"8.4/4":[stolen]*5})
    def test_wrong_chapter_fails(self):
        with self.assertRaises(ValueError):
            measured_replacement_replan(chapter=Path("Z:/missing"))
