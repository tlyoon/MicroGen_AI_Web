"""Owner 27 Oct: intelligible similarity, not strict ASR text identity."""
import unittest
from selenium_pipeline.tts_flexible_pronunciation_contract import (
    QA_VERSION, canonical_phonetic_tokens, evaluate_tts_soundalike,
)


class OwnerFlexibleTTSPronunciationContract(unittest.TestCase):
    def check_pass(self,expected,heard):
        result=evaluate_tts_soundalike(expected,heard)
        self.assertTrue(result["tts_qa_soundalike_pass"],result)
        self.assertEqual(result["critical_errors"],[])
        self.assertFalse(result["student_publication_authorized_by_this_check"])
        return result

    def test_user_contract_accepts_soundalike_math_phonetics(self):
        expected=("Assume a is positive. When x equals a tangent u, "
                  "the hypotenuse is the square root of a squared plus x squared, "
                  "and secant u is positive.")
        heard=("assume a is positive when eggs equals a tangent you "
               "the high pot news is the square root of a squared plus eggs squared "
               "and see get you is positive")
        report=self.check_pass(expected,heard)
        self.assertFalse(report["exact_ASR_word_error_rate_hard_threshold"])

    def test_hypotenuse_cosine_sine_secant_pi_and_x_misrenderings_are_not_failures(self):
        expected=("For x equals a sine u with negative pi over two, the "
                  "hypotenuse has length a. Cosine u is nonnegative and "
                  "secant u is positive.")
        heard=("four eggs equals a sign you with negative pie over to "
               "the high pot news has length a coast sign you is non negative "
               "and see get you is positive")
        self.check_pass(expected,heard)

    def test_small_hesitation_plural_inflection_accents_are_accepted(self):
        expected=("The reference triangle has nonnegative side lengths even "
                  "when the substitution angle is negative.")
        heard=("the reference triangle has non negative side length even "
               "when substitution angle is negative")
        self.check_pass(expected,heard)

    def test_letter_c_sounds_like_see_is_valid(self):
        self.check_pass("Let c be the speed of light.","let see be the speed of light")
        self.check_pass("C equals the constant.","sea equals the constant")

    def test_letter_c_pronounced_as_circa_stays_hard_failure(self):
        for text in ("Let c be the speed of light.",
                     "The parameter C. is constant.",
                     "In this formula c represents a coefficient."):
            with self.subTest(text=text):
                heard=text.lower().replace("c.","circa").replace(
                    " c "," circa ")
                result=evaluate_tts_soundalike(text,heard)
                self.assertEqual(result["tts_qa_decision"],
                                 "FAIL_CONFIRMED_CRITICAL_PRONUNCIATION")
                self.assertIn("LETTER_C_INCORRECTLY_EXPANDED_TO_CIRCA",
                              result["critical_errors"])

    def test_reverse_nonnegative_to_negative_is_not_tolerated(self):
        expected=("For this interval cosine is nonnegative and "
                  "tangent u is positive.")
        heard=("for this interval cosine is negative and "
               "tangent you is positive")
        result=evaluate_tts_soundalike(expected,heard)
        self.assertFalse(result["tts_qa_soundalike_pass"])
        self.assertIn("EXPLICIT_MATHEMATICAL_SIGN_OR_DEGENERACY_REVERSAL",
                      result["critical_errors"])

    def test_inverse_at_least_at_most_stays_hard_failure(self):
        result=evaluate_tts_soundalike(
            "For x at least a, select u between zero and pi over two.",
            "for x at most a select you between zero and pie over to")
        self.assertFalse(result["tts_qa_soundalike_pass"])
        self.assertIn("EXPLICIT_MATHEMATICAL_RELATION_DIRECTION_CHANGED",
                      result["critical_errors"])

    def test_different_spoken_numbers_not_excused_as_phonetic_variants(self):
        report=evaluate_tts_soundalike(
            "The answer is two minus three.",
            "the answer is three minus two")
        self.assertFalse(report["tts_qa_soundalike_pass"])
        self.assertIn("EXPLICIT_SPOKEN_NUMBER_CHANGED",report["critical_errors"])

    def test_sine_vs_cosine_and_hypotenuse_vs_adjacent_are_not_allowed(self):
        for source,heard,code in (
            ("The sine of u is positive.",
             "the cosine of you is positive",
             "EXPLICIT_TRIGONOMETRIC_FUNCTION_CHANGED"),
            ("The hypotenuse has length a.",
             "the adjacent has length a",
             "EXPLICIT_TRIANGLE_SIDE_ROLE_CHANGED"),
        ):
            with self.subTest(code=code):
                report=evaluate_tts_soundalike(source,heard)
                self.assertFalse(report["tts_qa_soundalike_pass"])
                self.assertIn(code,report["critical_errors"])

    def test_unintelligible_audio_is_not_passed_as_soundalike(self):
        result=evaluate_tts_soundalike(
            "The hypotenuse is the square root of a squared plus x squared.",
            "blue pineapple violin garden yellow")
        self.assertEqual(result["tts_qa_decision"],"REVIEW_UNCLEAR_AUDIO")

    def test_missing_pcm_or_source_sha_is_independent_hard_failure(self):
        for kwargs in ({"source_audio_is_genuine_pcm":False},
                       {"source_text_identity_verified":False}):
            result=evaluate_tts_soundalike(
                "A sine u is nonnegative.","a sign you is non negative",**kwargs)
            self.assertEqual(result["tts_qa_decision"],
                             "FAIL_INVALID_AUDIO_OR_SOURCE")

    def test_missing_or_imperfect_asr_is_not_automatic_tts_regeneration(self):
        bad=evaluate_tts_soundalike(
            "Absolute value of x is a nonnegative quantity.","")
        self.assertEqual(bad["tts_qa_decision"],"REVIEW_UNCLEAR_AUDIO")
        self.assertTrue(bad[
            "automatic_regeneration_solely_due_to_ASR_WER_forbidden"])
        self.assertEqual(bad["contract_version"],QA_VERSION)


if __name__=="__main__":
    unittest.main()
