"""Independently reject fake physical MP4 and false-release evidence."""
from __future__ import annotations
import tempfile
from pathlib import Path
import unittest
from selenium_pipeline.original_thomas84_slide6_independent_audit import (
    within_bundle,audit_real_slide6,
)
class IndependentRealPilotAudit(unittest.TestCase):
    def test_relative_path_never_authorized(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            movie=root/"sample.mp4";movie.write_bytes(b"NOT real media")
            with self.assertRaises(ValueError):
                within_bundle("sample.mp4",root)
    def test_external_path_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);other=root/"other";other.mkdir()
            file=other/"sample.mp4";file.write_bytes(b"NOT real media")
            with self.assertRaises(ValueError):
                within_bundle(str(file),root/"bundle")
    def test_missing_media_no_false_receipt(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);out=p/"audited.json"
            with self.assertRaises((ValueError,FileNotFoundError)):
                audit_real_slide6(original=p/"missing",review_receipt=p/"none",
                     candidate_receipt=p/"none2",output=out)
            self.assertFalse(out.exists())
if __name__=="__main__":unittest.main()
