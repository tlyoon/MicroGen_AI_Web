"""Two academic review-question slides source/WAV/PDF visible, not release."""
import unittest
from selenium_pipeline.original_thomas85_86_math_review_questions import CASES,STATUS
from selenium_pipeline.original_thomas85_86_derivation_audio_pixels import CASES as DERIVATIONS

class OriginalTextbookReviewQuestionEvents(unittest.TestCase):
    def test_original_question_source_pages_and_sentence_times(self):
        self.assertEqual(sorted(CASES),[("8.5",11),("8.6",13)])
        self.assertEqual([v[1] for v in CASES["8.5",11]["events"]],[2,3])
        self.assertEqual([v[1] for v in CASES["8.6",13]["events"]],[2,3])
    def test_not_mistaken_for_sympy_answers(self):
        self.assertFalse(set(DERIVATIONS).intersection(CASES))
        self.assertTrue(all(len(c["math_tex"])==2 for c in CASES.values()))
    def test_review_math_source_not_fake_student_acceptance(self):
        self.assertIn("SOURCE_WAV_PIXEL_QA_PASS",STATUS)
        self.assertIn("irreducible quadratic factor",CASES["8.5",11]["math_tex"][-1])
        self.assertIn("nonelementary integral",CASES["8.6",13]["math_tex"][-1])
if __name__=="__main__":
    unittest.main()
