"""Original source/WAV/acoustic focus pilots never enable publication."""
import unittest
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.original_thomas86_remaining_realword_focus import (
    EVENTS, PDF_TERMS, STATUS,
)
from selenium_pipeline.original_thomas84_outline_real_word_focus import _phrase

class ActualSpokenOriginalSourceFocus(unittest.TestCase):
    def test_three_missing_substantive_source_slides_now_have_events(self):
        self.assertEqual(sorted(EVENTS),[6,11,12])
        self.assertEqual([len(EVENTS[x]) for x in (6,11,12)],[4,3,5])
        self.assertEqual(sum(map(len,EVENTS.values())),12)
        self.assertIn("NONPRODUCTION",STATUS)

    def test_each_source_event_has_unique_long_acoustic_phrase(self):
        for slide,events in EVENTS.items():
            for label,rect,phrase in events:
                with self.subTest(slide=slide,label=label):
                    self.assertGreaterEqual(len(phrase.split()),7)
                    self.assertGreater(rect[2]-rect[0],10)
                    self.assertGreater(rect[3]-rect[1],8)
                    words=[{"word":w} for w in ("placeholder " +phrase+ " end").split()]
                    a,b=_phrase(words,phrase.split())
                    self.assertEqual(a,1)
                    self.assertEqual(b,len(phrase.split()))

    def test_falsely_repeated_or_missing_speech_must_fail(self):
        phrase=EVENTS[11][1][2].split()
        words=[{"word":w} for w in (phrase+["else"]+phrase)]
        with self.assertRaises(FigureIdentityReviewRequired):
            _phrase(words,phrase)
        with self.assertRaises(FigureIdentityReviewRequired):
            _phrase([{"word":"silence"}],phrase)

    def test_original_science_terms_cover_figure_and_calculus(self):
        self.assertIn("Formula 106",PDF_TERMS[6])
        self.assertIn("Volume Integral Formulation",PDF_TERMS[11])
        self.assertEqual(len(PDF_TERMS[12]),5)
        self.assertEqual(EVENTS[11][-1][0],"publisher_original_tank_measuring_figure")


if __name__=="__main__":
    unittest.main()
