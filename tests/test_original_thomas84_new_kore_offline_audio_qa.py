"""Offline real Vosk screening respects tolerant source math and strict risks."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_new_kore_offline_audio_qa import (
    screen_speech,audit_real_corrected_kore_audio)
class NewRealSourceAudioScreen(unittest.TestCase):
    def test_math_soundalike_does_not_require_verbatim_transcript(self):
        r=screen_speech("Cosine u is positive.","Coast sign you is positive.")
        self.assertTrue(r["phonetic_soundalike_screen_pass"])
        self.assertFalse(r["individual_words_mathematically_verified"])
    def test_circa_is_still_referred_not_passed(self):
        r=screen_speech("Plus C.","Plus circa.")
        self.assertTrue(r["targeted_audible_check_required"])
        self.assertFalse(r["phonetic_soundalike_screen_pass"])
    def test_trig_function_reversal_not_normalized(self):
        r=screen_speech("Sine and cosine.","Cosine and sine.")
        self.assertTrue(r["targeted_audible_check_required"])
    def test_missing_genuine_source_and_model_never_create_approval(self):
        with tempfile.TemporaryDirectory() as t:
            b=Path(t)
            with self.assertRaises((ValueError,FileNotFoundError)):
                audit_real_corrected_kore_audio(original=b/"not_present",
                    paired_source=b/"pair",tts_candidate=b/"voice",
                    independent_mp4_audit=b/"audit.json",model_dir=b/"vosk",
                    packages_dir=b/"packages",out=b/"out.json")
            self.assertFalse((b/"out.json").exists())
if __name__=="__main__":unittest.main()
