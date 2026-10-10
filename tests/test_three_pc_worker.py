"""No-Gemini scheduler tests for disjoint assignments and strict stage order."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.three_pc_worker import (
    STAGES, assigned_jobs, process_job, validate_manifest,
)


class WorkerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for key in ("8.1", "8.2", "9.1"):
            folder = self.root / key.split(".")[0] / key
            folder.mkdir(parents=True)
            (folder / "source.pdf").write_bytes(b"%PDF sample")
        run = self.root / ".microgen_coordination" / "test"
        run.mkdir(parents=True)
        self.manifest = run / "assignments.json"
        self.manifest.write_text(json.dumps({
            "source_root": str(self.root),
            "assignments": {"Dell-115": [8], "HP": [9], "Yoga6": []},
        }), encoding="utf-8")

    def test_chapters_generate_separate_ordered_jobs(self):
        self.assertEqual(assigned_jobs(self.root, [8]), ["8.1", "8.2"])
        self.assertEqual(assigned_jobs(self.root, [9]), ["9.1"])

    def test_assignment_manifest_prevents_overlap(self):
        validate_manifest(self.manifest, "Dell-115", [8])
        with self.assertRaises(ValueError):
            validate_manifest(self.manifest, "HP", [8])
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["assignments"]["HP"] = [8]
        self.manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "two owners"):
            validate_manifest(self.manifest, "Dell-115", [8])

    def test_blocked_stage_never_advances_and_defers_for_later(self):
        stages = []
        data = {}
        def simulated(_root, _key, stage, *_args):
            stages.append(stage)
            return (False, "stalled") if stage == "slides" else (True, "")
        with patch("selenium_pipeline.three_pc_worker.run_stage", side_effect=simulated):
            with patch("selenium_pipeline.three_pc_worker.stage_recorded", return_value=True):
                ok = process_job(
                    self.root, "8.1", 9222, 1, self.root / "logs",
                    self.root / "lane", 10, 60, data, lambda: None
                )
        self.assertFalse(ok)
        self.assertEqual(stages, ["figures", "slides"])
        self.assertEqual(data["8.1"]["status"], "deferred")
        self.assertEqual(data["8.1"]["stage"], "slides")

    def test_second_pass_labels_unfinished(self):
        data = {}
        with patch("selenium_pipeline.three_pc_worker.run_stage", return_value=(False, "blocked")):
            process_job(self.root, "8.2", 9222, 2, self.root / "logs",
                        self.root / "lane", 10, 60, data, lambda: None)
        self.assertEqual(data["8.2"]["status"], "unfinished")
        self.assertEqual(data["8.2"]["round"], 2)

    def test_figure_stage_accepts_legitimate_no_figure_pdf(self):
        from selenium_pipeline.runner import valid
        workspace = self.root / "empty_figure_workspace"
        (workspace / "pages" / "page_1").mkdir(parents=True)
        (workspace / "crops" / "page_1").mkdir(parents=True)
        (workspace / "pages" / "page_1" / "page_1.png").write_bytes(b"page")
        # Legacy extraction also copies whole-page preview into crops/;
        # it is not an extracted Figure and must not block a text-only PDF.
        (workspace / "crops" / "page_1" / "page_1.png").write_bytes(b"page")
        self.assertTrue(valid("figures", workspace))
        (workspace / "crops" / "Figure-crop.png").write_bytes(b"unmapped")
        self.assertFalse(valid("figures", workspace))
        (workspace / "Figure 1.1.png").write_bytes(b"mapped")
        self.assertTrue(valid("figures", workspace))

    def test_runner_stage_order_covers_required_phases(self):
        self.assertEqual(STAGES, (
            "figures", "slides", "narration", "script_qa",
            "tts", "tts_qa", "video"
        ))


if __name__ == "__main__":
    unittest.main()
