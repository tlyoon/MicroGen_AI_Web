"""Fail-closed genuine corrected §8.4 physical media auditor tests."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_66_corrected_independent_audit import (
    existing_file,audit_corrected,STATUS
)
class CorrectedFullRealMediaAudit(unittest.TestCase):
    def test_only_explicit_review_audit_status(self):
        self.assertIn("RELEASE_BLOCKED",STATUS)
    def test_relative_source_video_forbidden(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp); (p/"fake.mp4").write_bytes(b"fake")
            with self.assertRaises(ValueError):
                existing_file("fake.mp4",p)
    def test_outside_original_bundle_forbidden(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);movie=p/"x.mp4";movie.write_bytes(b"fake")
            with self.assertRaises(ValueError):
                existing_file(str(movie),p/"other")
    def test_missing_protected_pdf_and_receipts_cannot_create_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp); out=p/"out.json"
            with self.assertRaises((ValueError,FileNotFoundError)):
                audit_corrected(original=p/"missing",
                    corrected_review=p/"a.json",prior_review=p/"b.json",
                    prior_independent_audit=p/"c.json",
                    math_corrections=p/"d.json",original_plan=p/"e.json",out=out)
            self.assertFalse(out.exists())
if __name__=="__main__":unittest.main()
