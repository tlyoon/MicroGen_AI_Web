"""Reject fabricated or changed timings/figures in original corrected pilots."""
import unittest
from selenium_pipeline.original_thomas84_corrected_visual_audio_sync import (
    match_actual_sentences,words,MATCH_REQUIRED)

class TestCorrectedTimingIntegrity(unittest.TestCase):
    def test_real_acoustic_sentences_have_correct_monotonic_interval(self):
        sentences=["The sine function is restricted to a valid interval.",
                   "The inverse tangent is the principal arctangent."]
        text=" ".join(sentences)
        tokens=words(text)
        events=[{"word":w,"start":i*.21+.1,"end":i*.21+.26}
                for i,w in enumerate(tokens)]
        rows=match_actual_sentences(sentences,events)
        self.assertEqual(len(rows),2)
        self.assertGreaterEqual(rows[0]["actual_matched_word_fraction"],MATCH_REQUIRED)
        self.assertEqual(rows[0]["actual_matched_word_fraction"],1.)
        self.assertLess(rows[0]["real_last_matched_word_s"],
                        rows[1]["real_earliest_matched_word_s"])

    def test_missing_spoken_math_cannot_claim_match(self):
        sentences=["The arctangent graph has horizontal asymptotes.",
                   "Restrict trigonometric functions to a one to one interval."]
        actual="The graph has vertical lines at both sides. Another result."
        events=[{"word":w,"start":i*.1+.1,"end":i*.1+.2}
                for i,w in enumerate(words(actual))]
        with self.assertRaises(Exception):
            match_actual_sentences(sentences,events)

    def test_overlap_and_invalid_word_times_fail_closed(self):
        phrases=["The left side has one source equation.",
                 "The right side has one other source equation."]
        tokens=words(" ".join(phrases))
        events=[{"word":w,"start":i*.22+.1,"end":i*.22+.3}
                for i,w in enumerate(tokens)]
        events[1]["end"]=events[1]["start"]
        with self.assertRaises(Exception):
            match_actual_sentences(phrases,events)

    def test_no_asr_word_event_is_not_timed_math(self):
        with self.assertRaises(Exception):
            match_actual_sentences(["The source sine function.","One other."],[])

if __name__=="__main__":
    unittest.main()
