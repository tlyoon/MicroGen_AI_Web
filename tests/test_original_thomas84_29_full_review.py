"""Real 16-WAV plan leading silence cannot lead to invalid tiny encoding."""
from __future__ import annotations
import unittest
from selenium_pipeline.original_thomas84_29_full_review import stabilized_windows
class RealReviewClipWindows(unittest.TestCase):
    def test_30ms_leading_silence_joins_first_real_word_without_loss(self):
        r=stabilized_windows([
            {"first_pcm_sample":0,"last_pcm_sample_exclusive":720,
             "provisional_pdf_target":None},
            {"first_pcm_sample":720,"last_pcm_sample_exclusive":240000,
             "provisional_pdf_target":"PDF"}])
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]["first_pcm_sample"],0)
        self.assertTrue(r[0]["includes_unmapped_leading_samples"])
    def test_acoustic_overlap_rejected(self):
        with self.assertRaises(ValueError):
            stabilized_windows([
                {"first_pcm_sample":0,"last_pcm_sample_exclusive":240000,
                 "provisional_pdf_target":None},
                {"first_pcm_sample":230000,"last_pcm_sample_exclusive":360000,
                 "provisional_pdf_target":"wrong"}])
    def test_long_static_lead_preserved(self):
        r=stabilized_windows([
            {"first_pcm_sample":0,"last_pcm_sample_exclusive":6000,
             "provisional_pdf_target":None},
            {"first_pcm_sample":6000,"last_pcm_sample_exclusive":240000,
             "provisional_pdf_target":"PDF"}])
        self.assertEqual(len(r),2)
if __name__=="__main__":unittest.main()
