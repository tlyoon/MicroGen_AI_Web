"""Recover source-corrected math words without rigid WER or false QA claims."""
import unittest

from selenium_pipeline.original_thomas84_corrected_two_audio_vosk_qa import (
    known_math_mismatch_in_audio_asr)
from selenium_pipeline.tts_flexible_pronunciation_contract import (
    evaluate_tts_soundalike)

class CorrectedSourceSpeechScreenTests(unittest.TestCase):
    def test_old_vertical_asymptote_math_stays_blocked(self):
        self.assertTrue(known_math_mismatch_in_audio_asr(
            6,"The arctangent graph has vertical asymptotes at negative pi over two."))

    def test_correct_horizontal_arctangent_not_blocked(self):
        self.assertFalse(known_math_mismatch_in_audio_asr(
            6,"The arctangent graph has horizontal asymptotes at pi over two."))

    def test_original_strict_arcsine_and_tangent_stays_blocked(self):
        self.assertTrue(known_math_mismatch_in_audio_asr(
            17,"Angle intervals are strictly for sine and tangent."))

    def test_correct_inclusive_arcsine_is_allowed(self):
        self.assertFalse(known_math_mismatch_in_audio_asr(
            17,"The principal arcsine interval includes both endpoints."))

    def test_unrelated_slides_cannot_inherit_foreign_math_rejection(self):
        self.assertFalse(known_math_mismatch_in_audio_asr(
            5,"The arctangent graph has vertical asymptotes."))

    def test_flexible_asr_accepts_soundalike_pi_over_two(self):
        result=evaluate_tts_soundalike(
            "The horizontal asymptotes are at negative pi over two.",
            "The horizontal asymptotes are at negative pie over to.")
        self.assertTrue(result["tts_qa_soundalike_pass"])

    def test_letter_c_circa_is_still_a_hard_fail(self):
        result=evaluate_tts_soundalike(
            "The final answer is plus c.",
            "The final answer is plus circa.")
        self.assertFalse(result["tts_qa_soundalike_pass"])
        self.assertIn("LETTER_C_INCORRECTLY_EXPANDED_TO_CIRCA",
                      result["critical_errors"])

if __name__=="__main__":
    unittest.main()
