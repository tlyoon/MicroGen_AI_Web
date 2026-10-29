"""WAV/ASR speech QA accepts sound-alikes, never asserts unsupported errors."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.tts_flexible_pronunciation_contract import (
    evaluate_tts_soundalike,)
from selenium_pipeline.original_thomas84_historic_audio_soundalike_audit import (
    audit_real_historic_audio,classify_asr_screen,)
class HistoricAudioSemanticQA(unittest.TestCase):
    def classify(self,source,heard):
        q=evaluate_tts_soundalike(source,heard)
        return classify_asr_screen(qa=q,reference=source,recognized=heard)
    def test_circa_is_always_flagged_for_independent_check(self):
        z=self.classify("The integration constant is C.",
                        "The integration constant is circa.")
        self.assertEqual(z,"TARGETED_INDEPENDENT_AUDIO_CHECK_REQUIRED_MATH_OR_CIRCA")
    def test_legitimate_c_soundalike_not_flagged(self):
        z=self.classify("Plus C.","Plus see.")
        self.assertEqual(z,"ACCEPTABLE_PHONETIC_SIMILARITY_ASR_SCREEN_ONLY")
    def test_actual_trig_opposition_not_silenced(self):
        z=self.classify("Using sine and cosine u.",
                        "Using cosine and sine u.")
        self.assertEqual(z,"TARGETED_INDEPENDENT_AUDIO_CHECK_REQUIRED_MATH_OR_CIRCA")
    def test_math_homophone_may_pass_without_wer_threshold(self):
        z=self.classify("Cosine u is positive.", "Coast sign you is positive.")
        self.assertEqual(z,"ACCEPTABLE_PHONETIC_SIMILARITY_ASR_SCREEN_ONLY")
    def test_source_missing_refuses_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with self.assertRaises((ValueError,FileNotFoundError)):
                audit_real_historic_audio(original=p/"original",
                    asr_receipt=p/"old.json",
                    final_media_audit=p/"old_video.json",out=p/"out.json")
            self.assertFalse((p/"out.json").exists())
if __name__=="__main__":unittest.main()
