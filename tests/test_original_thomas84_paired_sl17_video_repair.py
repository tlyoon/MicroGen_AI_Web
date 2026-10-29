"""Paired corrected slide17 video must discard old sentence tail."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_paired_sl17_video_repair import (
    encode_paired_slide17,STATUS)
class PairedRealSource17(unittest.TestCase):
    def test_repaired_video_still_review_only(self):
        self.assertIn("REVIEW_ONLY",STATUS)
    def test_missing_source_audio_never_creates_fake_video(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            with self.assertRaises((ValueError,FileNotFoundError)):
                encode_paired_slide17(original=p/"original",
                    paired=p/"pair",tts_candidate=p/"newwav",
                    prior_video_receipt=p/"p.json",
                    prior_media_audit=p/"a.json",out=p/"video")
            self.assertFalse((p/"video").exists())
if __name__=="__main__":unittest.main()
