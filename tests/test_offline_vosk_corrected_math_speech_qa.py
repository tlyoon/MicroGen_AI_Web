import unittest
from selenium_pipeline.offline_vosk_corrected_math_speech_qa import (
    words,word_error_rate,lexical_math_risk_terms,polarity_sequence,
)


class OfflineMathVoiceQA(unittest.TestCase):
    def test_punctuation_and_negative_normalization(self):
        self.assertEqual(words("Non-negative at an end-point."),
                         ["nonnegative","at","an","endpoint"])
        self.assertEqual(words("non negative"),["nonnegative"])

    def test_exact_dictation_and_one_math_misrecognition(self):
        text=("The reference triangle is degenerate, and secant u "
              "is positive when a is positive.")
        self.assertEqual(word_error_rate(text,text)["word_error_rate"],0)
        mistaken=text.replace("secant","second")
        self.assertGreater(word_error_rate(text,mistaken)["word_error_rate"],0)
        self.assertIn("secant",
                      lexical_math_risk_terms(text,mistaken)[
                          "critical_terms_unrecognized"])

    def test_math_negation_cannot_hide_inside_low_word_error_rate(self):
        long=("For x equals a tangent u, the opposite leg has "
              "the absolute value of x and the hypotenuse is positive. ")*8
        expected=long+"Cosine u is nonnegative and tangent is zero."
        wrong=long+"Cosine u is negative and tangent is zero."
        self.assertLess(word_error_rate(expected,wrong)["word_error_rate"],.05)
        self.assertFalse(polarity_sequence(expected,wrong)[
            "critical_math_polarity_sequence_exact"])

    def test_unbiased_evidence_cannot_self_approve_release(self):
        expected="At the zero endpoint the triangle is degenerate."
        observed="At the endpoint triangle is degenerate."
        report=polarity_sequence(expected,observed)
        self.assertFalse(report["critical_math_polarity_sequence_exact"])
        self.assertNotIn("student_publication_authorized",report)

if __name__=="__main__":
    unittest.main()
