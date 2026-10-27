import unittest
from selenium_pipeline.flexible_tts_pronunciation_qa import (
    flexible_pronunciation_screen,asr_soundalike_tokens,
)

class PragmaticPronunciationContract(unittest.TestCase):
    def test_phonetically_equivalent_math_terms_pass(self):
        expected=("The hypotenuse is the square root, and secant u "
                  "is positive with cosine u nonnegative.")
        heard=("The high pot news is the square root and see get you "
               "is positive with coast sign you non negative")
        decision=flexible_pronunciation_screen(expected,heard)
        self.assertTrue(decision["pronunciation_qa_pass"],decision)
        self.assertTrue(decision["soundalike_normalizations_applied"])

    def test_x_sounds_like_eggs_not_a_rejection(self):
        expected="For x equals a sine u, the opposite leg is the absolute value of x."
        heard="Four eggs equals a sign you the opposite leg is the absolute value of eggs"
        decision=flexible_pronunciation_screen(expected,heard)
        self.assertTrue(decision["pronunciation_qa_pass"],decision)

    def test_c_as_circa_still_fails_when_utterance_otherwise_perfect(self):
        expected="For the expression c squared, use c as a parameter."
        heard="For the expression circa squared use circa as a parameter"
        d=flexible_pronunciation_screen(expected,heard)
        self.assertFalse(d["pronunciation_qa_pass"])
        self.assertTrue(d["severe_pronunciation_error"])
        self.assertIn("GROSS_SYMBOL_MISPRONUNCIATION_C",d["blocker_codes"])

    def test_negative_vs_nonnegative_changes_meaning_and_must_fail(self):
        expected="The cosine is nonnegative and the radical is positive."
        heard="The coast sign is negative and the radical is positive."
        d=flexible_pronunciation_screen(expected,heard)
        self.assertFalse(d["pronunciation_qa_pass"])
        self.assertIn("MATH_SIGN_OR_DOMAIN_CONTRADICTION_REVIEW",d["blocker_codes"])

    def test_secant_phonetic_ac_cant_tokenization_accepted(self):
        expected="For x equals a secant u, tangent u is nonnegative."
        heard="For eggs equals ac can't you tangent you is non negative"
        decision=flexible_pronunciation_screen(expected,heard)
        self.assertTrue(decision["pronunciation_qa_pass"],decision)

    def test_trig_function_change_must_fail(self):
        expected="Cosine u is positive."
        heard="Sine you is positive."
        d=flexible_pronunciation_screen(expected,heard)
        self.assertFalse(d["pronunciation_qa_pass"])
        self.assertIn("TRIG_FUNCTION_MISMATCH_REVIEW",d["blocker_codes"])

    def test_small_warnings_are_targeted_review_not_forced_retries(self):
        expected="For c equals a constant, the triangle is degenerate."
        heard="For circa equals a constant the triangle is degenerate."
        d=flexible_pronunciation_screen(expected,heard)
        self.assertTrue(d["review_required"])
        self.assertFalse(d["student_release_authorized"])

    def test_empty_or_non_speech_never_passes(self):
        d=flexible_pronunciation_screen("The tangent is positive.", "")
        self.assertFalse(d["pronunciation_qa_pass"])
        self.assertIn("EMPTY_EXPECTED_OR_SPEECH",d["blocker_codes"])

    def test_documented_variants_only_no_general_fuzzy_guess(self):
        self.assertEqual(asr_soundalike_tokens("high pot news"),["hypotenuse"])
        self.assertNotEqual(asr_soundalike_tokens("second"),["secant"])

if __name__=="__main__":
    unittest.main()
