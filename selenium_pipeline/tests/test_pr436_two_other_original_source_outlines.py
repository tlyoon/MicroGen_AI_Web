"""No fictional textbook provenance for the external tank exercise outline."""
import unittest
from selenium_pipeline.original_two_other_outline_true_word_timing import (
    TOPICS,PUBLISHER,STATUS,_phrase)

class OriginalPublishedOutlineAcoustics(unittest.TestCase):
    def test_only_scientifically_source_referenced_topics(self):
        self.assertEqual(sorted(TOPICS),["8.5","8.6"])
        self.assertEqual(len(TOPICS["8.5"]),5)
        self.assertEqual(len(TOPICS["8.6"]),4)
        self.assertTrue(all("tank" not in title.lower()
                            for title,*_ in TOPICS["8.6"].values()))
        self.assertEqual(len(PUBLISHER["8.5"]),4)
        self.assertEqual(len(PUBLISHER["8.6"]),4)
    def test_missing_unique_real_pcm_anchor_never_gets_fake_time(self):
        transcript=[{"word":"different","start":1.,"end":2.}]
        with self.assertRaises(Exception):
            _phrase(transcript,["begin","with","an","introduction"])
    def test_real_original_review_status_does_not_publish(self):
        self.assertIn("APPROVED_ONLY",STATUS)
if __name__=="__main__":
    unittest.main()
