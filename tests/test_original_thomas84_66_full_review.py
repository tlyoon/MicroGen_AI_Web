"""Original two-part 66-cue review must preserve 24-kHz source PCM."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_66_full_review import (
    stabilized_windows, encode_two_review_parts,
    REVIEW_STATUS,
)
class TwoPart66RealReview(unittest.TestCase):
    def test_explicit_review_only_status(self):
        self.assertIn("REVIEW_ONLY",REVIEW_STATUS)
    def test_tiny_original_prefix_never_dropped(self):
        x=stabilized_windows([
            {"first_pcm_sample":0,"last_pcm_sample_exclusive":720,
             "provisional_pdf_target":None},
            {"first_pcm_sample":720,"last_pcm_sample_exclusive":240000,
             "provisional_pdf_target":"s002.pdf_block.002"}])
        self.assertEqual(len(x),1)
        self.assertEqual(x[0]["first_pcm_sample"],0)
        self.assertEqual(x[-1]["last_pcm_sample_exclusive"],240000)
    def test_original_pcm_overlaps_rejected(self):
        with self.assertRaises(ValueError):
            stabilized_windows([
                {"first_pcm_sample":0,"last_pcm_sample_exclusive":240000,
                 "provisional_pdf_target":None},
                {"first_pcm_sample":239999,"last_pcm_sample_exclusive":250000,
                 "provisional_pdf_target":"fake"}])
    def test_missing_real_source_does_not_create_movie(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)
            out=base/"videos"
            with self.assertRaises((ValueError,FileNotFoundError)):
                encode_two_review_parts(original=base/"missing",
                    plan_receipt=base/"missing-plan.json",
                    old_review_receipt=base/"missing-old.json",out=out)
            self.assertFalse(out.exists())
if __name__=="__main__":unittest.main()
