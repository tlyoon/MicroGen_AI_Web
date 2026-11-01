"""No guessed 5-topic intervals or silently rewritten unprompted ASR."""
import unittest
from selenium_pipeline.original_thomas84_outline_real_word_focus import (
    OUTLINE,STATUS,_phrase,_proof)

class OriginalFiveSpokenTopics(unittest.TestCase):
    def test_all_five_source_topic_rectangles_are_distinct(self):
        self.assertEqual(sorted(OUTLINE),[1,2,3,4,5])
        self.assertEqual(len({x[0] for x in OUTLINE.values()}),5)
        self.assertTrue(all(0<x[1][1]<x[1][3]<273 for x in OUTLINE.values()))

    def test_actual_word_sequence_has_unique_timestamps(self):
        words=[{"word":word,"start":i*.3,"end":i*.3+.2}
               for i,word in enumerate(["review","the","necessary","reference",
                   "right","triangles","and","algebraic","forms"])]
        self.assertEqual(_phrase(words,OUTLINE[2][2]),(0,8))

    def test_ambiguous_phrase_cannot_claim_production_timing(self):
        t=["the","step","by","step","procedure"]
        words=[{"word":word,"start":i*.2,"end":i*.2+.1}
               for i,word in enumerate(t+t)]
        with self.assertRaises(Exception):
            _phrase(words,t)

    def test_missing_real_anchor_cannot_invent_equal_time_bin(self):
        words=[{"word":"review","start":.2,"end":.5},
               {"word":"forms","start":.7,"end":.9}]
        with self.assertRaises(Exception):
            _phrase(words,OUTLINE[2][2])

    def test_original_book_topic_absence_fails_closed(self):
        p=["8.4 Trigonometric Substitutions\nreference right triangles in Figure 8.2",
           "For reversibility,\nProcedure for a Trigonometric Substitution\nEXAMPLE 1",
           "",""]
        slide="\n".join(e[0] for e in OUTLINE.values())
        spoken=("transformations help simplify complex integrals, "
            "reference right triangles and algebraic forms, "
            "reversibility and inverse function domain restrictions, "
            "step by step procedure, "
            "several detailed examples and applications.")
        self.assertTrue(_proof(p,slide,spoken)[
            "five_distinct_rendered_outline_topics_verified"])
        p[1]=p[1].replace("EXAMPLE 1","unverified")
        with self.assertRaises(Exception):
            _proof(p,slide,spoken)

    def test_real_encoded_pixel_pass_only_not_semantic_release(self):
        self.assertIn("ACOUSTIC_EVENTS_ENCODED_PIXEL_QA_PASS",STATUS)

if __name__=="__main__":
    unittest.main()
