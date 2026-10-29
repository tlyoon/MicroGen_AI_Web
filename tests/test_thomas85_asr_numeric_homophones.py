"""Sound-alike numeric ASR transcriptions must not cause paid re-TTS.

Original Thomas 8.5 Slide9 was generated in real homogeneous Flash/Kore.
The offline, genuine WAV transcript says "x plus for", which is the same
acoustic realization as mathematical "x plus four". Distinct numbers,
reversed signs, changed trig, and "c" -> "circa" remain hard failures.
"""
from __future__ import annotations
import unittest
from selenium_pipeline.tts_flexible_pronunciation_contract import (
    evaluate_tts_soundalike,canonical_phonetic_tokens,
)

class MathHomophoneQATests(unittest.TestCase):
    def score(self,reference,heard):
        return evaluate_tts_soundalike(reference,heard)

    def test_four_for_homophone_is_not_a_changed_number(self):
        a="We calculate x plus four, then subtract five."
        b="we calculate x plus for then subtract five"
        value=self.score(a,b)
        self.assertEqual(value["critical_errors"],[])
        self.assertTrue(value["tts_qa_soundalike_pass"])

    def test_into_in_two_is_not_extra_two(self):
        reference="We factor the denominator into x, x minus two and x plus five."
        heard="we factor the denominator in two x x minus two and x plus five"
        a=self.score(reference,heard)
        self.assertEqual(a["critical_errors"],[])
        self.assertTrue(a["tts_qa_soundalike_pass"])

    def test_sevenths_plural_sound_does_not_change_the_fraction(self):
        reference="Three sevenths and negative one thirty fifth."
        heard="three sevens and negative one thirty fifth"
        self.assertEqual(self.score(reference,heard)["critical_errors"],[])

    def test_actual_math_four_to_five_remains_critical(self):
        reference="We calculate x plus four, then subtract five."
        heard="we calculate x plus five then subtract five"
        self.assertIn("EXPLICIT_SPOKEN_NUMBER_CHANGED",
                      self.score(reference,heard)["critical_errors"])

    def test_actual_sign_reversal_remains_critical(self):
        expected="x plus four and y minus three"
        got="x minus four and y plus three"
        self.assertIn("EXPLICIT_MATHEMATICAL_SIGN_OR_DEGENERACY_REVERSAL",
                      self.score(expected,got)["critical_errors"])

    def test_letter_c_as_circa_remains_critical(self):
        self.assertIn("LETTER_C_INCORRECTLY_EXPANDED_TO_CIRCA",
                      self.score("The variable c equals three",
                                 "the variable circa equals three")["critical_errors"])

    def test_trigonometric_reversal_remains_critical(self):
        expect="sine u and cosine u"
        got="cosine u and sine u"
        self.assertIn("EXPLICIT_TRIGONOMETRIC_FUNCTION_CHANGED",
                      self.score(expect,got)["critical_errors"])

    def test_no_global_four_normalization_without_expected_phrase(self):
        # "for" is not universally replaced by "four"; only contextual math.
        original,heard=canonical_phonetic_tokens(
            "We solve for the constant.", "we solve four the constant")
        self.assertIn("four",heard)
        self.assertIn("for",original)
        self.assertNotEqual(original,heard)

if __name__=="__main__":
    unittest.main()
