"""Campaign audit must never confuse queued files with verified completion."""
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.cleanup import _final_hashes, _sha256, _write_receipt
from selenium_pipeline.reliability_audit import inspect_campaign


class CampaignAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.one = self.create("8.1")
        self.two = self.create("8.2")

    def create(self, job):
        folder = self.root / job.split(".")[0] / job
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "source.pdf").write_bytes(b"original " + job.encode())
        return folder

    def publish(self, folder, *, verified=False):
        for name in ("slides.tex", "slides.pdf", "script.txt", "slides.mp4"):
            (folder / name).write_bytes(b"mock nonempty " + name.encode())
        if verified:
            _write_receipt(folder / "source.pdf", {
                "source_sha256": _sha256(folder / "source.pdf"),
                "final_sha256": _final_hashes(folder)
            })

    def test_actual_receipt_vs_unverified_video(self):
        self.publish(self.one, verified=True)
        self.publish(self.two)
        report = inspect_campaign(self.root, expected_count=2)
        self.assertEqual(report["categories"]["verified_complete"], 1)
        self.assertEqual(report["categories"]["published_requires_reconciliation"], 1)
        self.assertFalse(report["all_verified_complete"])

    def test_partial_and_missing_stages_are_not_complete(self):
        (self.one / "slides.pdf").write_bytes(b"mock PDF")
        report = inspect_campaign(self.root, expected_count=2)
        self.assertEqual(report["categories"]["partial_slides"], 1)
        self.assertEqual(report["categories"]["no_published_slides"], 1)

    def test_invalidated_media_hash_cannot_be_counted_complete(self):
        self.publish(self.one, verified=True)
        (self.one / "slides.mp4").write_bytes(b"modified movie")
        report = inspect_campaign(self.root, expected_count=2)
        self.assertEqual(report["categories"]["verified_complete"], 0)
        self.assertEqual(report["categories"]["published_requires_reconciliation"], 1)

    def test_detects_missing_figure_reference(self):
        self.publish(self.one)
        (self.one / "slides.tex").write_text(r"\includegraphics{Figure12_1.png}")
        record = inspect_campaign(self.root, expected_count=2)["jobs"][0]
        self.assertEqual(record["latex_graphics"], "blocked")

    def test_expected_source_count_guard(self):
        with self.assertRaisesRegex(ValueError, "Expected 46"):
            inspect_campaign(self.root, expected_count=46)
