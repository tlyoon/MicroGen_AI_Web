"""Source-only actual media auditor refuses fabricated availability and claims."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from selenium_pipeline.original_thomas84_29_independent_media_audit import (
    _within,audit_full_real_review
)
class FullActualMediaAudit(unittest.TestCase):
    def test_relative_path_not_trusted(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); (root/"one.mp4").write_bytes(b"not an mp4")
            with self.assertRaises(ValueError): _within("one.mp4",root)
    def test_missing_or_external_path_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); src=root/"src";src.mkdir()
            file=src/"one.mp4";file.write_bytes(b"x")
            with self.assertRaises(ValueError): _within(str(file),root/"other")
    def test_missing_source_and_receipts_do_not_create_approval(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t)
            with self.assertRaises((ValueError,FileNotFoundError)):
                audit_full_real_review(original=r/"original",
                    review_receipt=r/"r.json",sample_receipt=r/"p.json",
                    candidate_receipt=r/"c.json",old_review_receipt=r/"old.json",
                    out=r/"out.json")
            self.assertFalse((r/"out.json").exists())
if __name__=="__main__":unittest.main()
