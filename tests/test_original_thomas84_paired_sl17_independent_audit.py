"""Actual pair auditor refuses incomplete sources and false release states."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_paired_sl17_independent_audit import (
    audit_paired_new_video,STATUS)
class PairAudit(unittest.TestCase):
    def test_no_release(self):
        self.assertIn("NO_STUDENT_RELEASE",STATUS)
    def test_missing_media_never_creates_audit(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with self.assertRaises((ValueError,FileNotFoundError)):
                audit_paired_new_video(original=p/"orig",
                    new_video_receipt=p/"a.json",
                    prior_video_receipt=p/"b.json",
                    paired_source=p/"pair",corrected_voice=p/"voice",
                    out=p/"out.json")
            self.assertFalse((p/"out.json").exists())
if __name__=="__main__":unittest.main()
