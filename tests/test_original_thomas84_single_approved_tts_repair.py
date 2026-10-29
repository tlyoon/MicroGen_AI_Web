"""One bounded paid TTS worker never dispatches without source proof."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_single_approved_tts_repair import (
    MODEL,one_approved_correction,APPROVED_VOICE)
class SingleCorrectedTTS(unittest.TestCase):
    def test_primary_source_voice_is_unchanged(self):
        self.assertEqual(MODEL,"gemini-3.8-flash-lite-tts")
        self.assertEqual(APPROVED_VOICE,"Kore")
    def test_missing_original_source_never_creates_attempt_folder(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with self.assertRaises((ValueError,FileNotFoundError)):
                one_approved_correction(original=p/"orig",bundle=p/"pair",
                    out=p/"output",dispatch_single_routine_tts=True)
            self.assertFalse((p/"output").exists())
if __name__=="__main__":unittest.main()
