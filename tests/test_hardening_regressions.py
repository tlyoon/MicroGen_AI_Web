import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline.three_pc_worker import stage_recorded
from selenium_pipeline.runner import valid

class StageProofTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name) / "8" / "8.1"
        self.folder.mkdir(parents=True)
        self.source = self.folder / "source.pdf"
        self.source.write_bytes(b"%PDF original source")
        self.work = self.folder / ".microgen_work"
        self.work.mkdir()
        (self.folder / "slides.tex").write_text("plain Beamer")
        (self.folder / "slides.pdf").write_bytes(b"%PDF slides")
        self.write_state()

    def write_state(self, completed=None):
        state = {
            "source_sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "completed": completed if completed is not None else {"slides": {"model": "flash"}},
        }
        (self.work / ".selenium_pipeline_state.json").write_text(json.dumps(state))

    def test_changed_source_invalidates_checkpoint(self):
        self.source.write_bytes(b"%PDF changed")
        with patch("selenium_pipeline.runner.check_valid", return_value=True):
            self.assertFalse(stage_recorded(self.source, "slides"))

    def test_stage_without_model_is_incomplete(self):
        self.write_state({"slides": {}})
        with patch("selenium_pipeline.runner.check_valid", return_value=True):
            self.assertFalse(stage_recorded(self.source, "slides"))

    def test_stage_artifacts_required(self):
        with patch("selenium_pipeline.runner.check_valid", return_value=False):
            self.assertFalse(stage_recorded(self.source, "slides"))

    def test_published_pdf_required(self):
        (self.folder / "slides.pdf").unlink()
        with patch("selenium_pipeline.runner.check_valid", return_value=True):
            self.assertFalse(stage_recorded(self.source, "slides"))

    def test_missing_figure_prevents_next_stage(self):
        (self.folder / "slides.tex").write_text(
            "\\includegraphics{Figure12_1.png}")
        with patch("selenium_pipeline.runner.check_valid", return_value=True):
            self.assertFalse(stage_recorded(self.source, "slides"))

    def test_recovered_figure_allows_stage(self):
        (self.folder / "slides.tex").write_text(
            "\\includegraphics{Figure12_1.png}")
        (self.folder / "Figure12_1.png").write_bytes(b"source crop")
        with patch("selenium_pipeline.runner.check_valid", return_value=True):
            self.assertTrue(stage_recorded(self.source, "slides"))

class StrictTTSTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)
        (self.folder / "tts_fidelity_report.md").write_text("Quality report")

    def check(self, summary):
        (self.folder / "tts_fidelity_report.json").write_text(
            json.dumps({"threshold_percent": 99, "summary": summary}))
        with patch("selenium_pipeline.runner.slide_pages", return_value=2):
            return valid("tts_qa", self.folder)

    def sample(self):
        return {"slides": 2, "passed": 2, "review": 0,
                "blocking_failures": 0, "minimum_fidelity_percent": 100}

    def test_unchecked_slide_not_accepted(self):
        report = self.sample()
        report["passed"] = 1
        self.assertFalse(self.check(report))

    def test_review_pending_not_accepted(self):
        report = self.sample()
        report["review"] = 1
        self.assertFalse(self.check(report))

    def test_fidelity_below_threshold_not_accepted(self):
        report = self.sample()
        report["minimum_fidelity_percent"] = 98.5
        self.assertFalse(self.check(report))

    def test_all_checked_high_fidelity(self):
        self.assertTrue(self.check(self.sample()))


if __name__ == "__main__":
    unittest.main()
