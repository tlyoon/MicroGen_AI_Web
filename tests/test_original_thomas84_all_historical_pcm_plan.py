"""Preserve every protected original PCM sample under overlapping/missing hypotheses."""
from __future__ import annotations
import unittest
from selenium_pipeline.original_thomas84_all_historical_pcm_plan import sample_windows

class RealHistoricalWindows(unittest.TestCase):
    def test_unmapped_slide_is_entirely_static_not_falsely_approved(self):
        x=sample_windows(240000,[])
        self.assertEqual(x,[{"first_pcm_sample":0,
              "last_pcm_sample_exclusive":240000,
              "provisional_pdf_target":None,"sentence_index":None}])
    def test_two_real_acoustic_hypotheses_and_all_samples_preserved(self):
        x=sample_windows(240000,[
            {"begin_s":1.2,"end_s":3.0,"pdf_target":"a","sentence_index":2},
            {"begin_s":4.1,"end_s":6.2,"pdf_target":"b","sentence_index":3}])
        self.assertEqual(x[0]["first_pcm_sample"],0)
        self.assertEqual(x[-1]["last_pcm_sample_exclusive"],240000)
        self.assertEqual(sum(y["last_pcm_sample_exclusive"]-y["first_pcm_sample"] for y in x),240000)
        self.assertEqual([y["provisional_pdf_target"] for y in x if y["provisional_pdf_target"]],["a","b"])
    def test_word_overlap_is_not_guessed_away(self):
        with self.assertRaises(ValueError):
            sample_windows(240000,[
                {"begin_s":1.0,"end_s":2.1,"pdf_target":"a","sentence_index":1},
                {"begin_s":2.0,"end_s":3.0,"pdf_target":"b","sentence_index":2}])
    def test_no_time_window_outside_original_pcm(self):
        with self.assertRaises(ValueError):
            sample_windows(240000,[{"begin_s":5,"end_s":12,
                 "pdf_target":"bad","sentence_index":1}])
    def test_near_zero_interval_never_loses_samples(self):
        x=sample_windows(240000,[{"begin_s":0.1,"end_s":9.99,
             "pdf_target":"a","sentence_index":1}])
        self.assertEqual(sum(y["last_pcm_sample_exclusive"]-y["first_pcm_sample"] for y in x),240000)
        self.assertTrue(x[-1].get("includes_unmapped_tail_samples",False))
if __name__=="__main__":unittest.main()
