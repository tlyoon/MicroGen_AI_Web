"""Genuine original PCM evidence is not revised-speech acceptance."""
import hashlib
import os
from pathlib import Path
import unittest
from selenium_pipeline.original_slide4_pcm_provenance_pilot import inspect_original_slide4_pcm

class OriginalSlide4PCMProvenanceTests(unittest.TestCase):
    def test_missing_or_foreign_audio_fails_closed(self):
        with self.assertRaises((FileNotFoundError,ValueError)):
            inspect_original_slide4_pcm(folder=Path("Z:/not-real-thomas-8.4"))

    def test_genuine_original_wav_is_not_corrected_tts(self):
        value=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not value:
            self.skipTest("Real original WAV permitted only on Dell-115")
        p=Path(value)
        original=hashlib.sha256((p/"slide4.wav").read_bytes()).hexdigest()
        report=inspect_original_slide4_pcm(folder=p)
        self.assertEqual(report["pcm_frame_count"],1087088)
        self.assertEqual(report["sample_rate"],24000)
        self.assertAlmostEqual(report["measured_original_slide4_audio_duration_s"],45.29533333333333)
        self.assertFalse(report["old_WAV_valid_for_corrected_narration"])
        self.assertFalse(report["highlight_to_speech_synchronization_verified"])
        self.assertFalse(report["final_under_600s_release_approved"])
        self.assertEqual(original,hashlib.sha256((p/"slide4.wav").read_bytes()).hexdigest())
if __name__=="__main__":
    unittest.main()
