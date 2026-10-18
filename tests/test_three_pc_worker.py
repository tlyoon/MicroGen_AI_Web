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
        self.assertEqual(stages, [])  # no expensive work before contract readiness
        self.assertEqual(data["8.1"]["status"], "deferred")
        self.assertEqual(data["8.1"]["stage"], "video")

    def test_second_pass_labels_unfinished(self):
        data = {}
        with patch("selenium_pipeline.three_pc_worker.run_stage", return_value=(False, "blocked")):
            process_job(self.root, "8.2", 9222, 2, self.root / "logs",
                        self.root / "lane", 10, 60, data, lambda: None)
        self.assertEqual(data["8.2"]["status"], "deferred")
        self.assertEqual(data["8.2"]["round"], 2)

    def test_published_video_without_receipt_is_preserved_on_both_passes(self):
        source_dir = self.root / "8" / "8.1"
        video = source_dir / "slides.mp4"
        contents = b"previously published video - do not overwrite"
        video.write_bytes(contents)
        for attempt, expected in ((1, "deferred"), (2, "deferred")):
            report = {}
            with patch("selenium_pipeline.three_pc_worker.run_stage",
                       side_effect=AssertionError("must never regenerate published media")):
                result = process_job(
                    self.root, "8.1", 9222, attempt, self.root / "logs",
                    self.root / "lane", 900, 3600, report, lambda: None
                )
            self.assertFalse(result)
            self.assertEqual(report["8.1"]["status"], expected)
            self.assertEqual(report["8.1"]["stage"], "video")
            self.assertIn("compliant renderer", report["8.1"]["error"])
            self.assertEqual(video.read_bytes(), contents)

    def test_valid_completion_receipt_skips_every_stage(self):
        report = {}
        with patch("selenium_pipeline.three_pc_worker.completed_lecture", return_value=True):
            with patch("selenium_pipeline.three_pc_worker.run_stage",
                       side_effect=AssertionError("must skip completed lecture")):
                self.assertFalse(process_job(
                    self.root, "8.2", 9222, 1, self.root / "logs",
                    self.root / "lane", 900, 3600, report, lambda: None
                ))
        self.assertEqual(report["8.2"]["status"], "deferred")
        self.assertIn("Historical video completion", report["8.2"]["error"])

    def test_technically_verified_video_advances_without_human_review(self):
        source_dir=self.root/"8"/"8.1"
        source=(source_dir/"source.pdf")
        prior=source.read_bytes()
        log={}
        with patch("selenium_pipeline.production_video_contract.verify_series",
                   return_value={"status":"accepted_synchronized_series"}):
            with patch("selenium_pipeline.three_pc_worker.run_stage",
                       side_effect=AssertionError("must not regenerate or publish")):
                self.assertTrue(process_job(
                    self.root,"8.1",9222,1,self.root/"logs",
                    self.root/"lane",900,3600,log,lambda:None))
        self.assertEqual(log["8.1"]["stage"],"video")
        self.assertEqual(log["8.1"]["status"],"complete")
        self.assertEqual(log["8.1"]["acceptance_scope"],"technical_only")
        self.assertEqual(log["8.1"]["human_academic_review"],
                         "optional_not_required_for_stage_progression")
        self.assertFalse(log["8.1"]["student_published"])
        self.assertEqual(source.read_bytes(),prior)
        self.assertFalse((source_dir/"lecture_human_approval.json").exists())

    def test_prepared_element_media_runs_the_verified_video_stage(self):
        root=self.root/"8"/"8.1"
        (root/"slides.pdf").write_bytes(b"synthetic slides")
        (root/"element_narration_plan.json").write_text("{}",encoding="utf8")
        (root/"element_wav").mkdir()
        calls=[]
        def run(_root,_key,stage,*args):
            calls.append(stage)
            return True,""
        report={}
        from selenium_pipeline.production_video_contract import VideoContractError
        with patch("selenium_pipeline.three_pc_worker.run_stage",side_effect=run),patch(
                "selenium_pipeline.three_pc_worker.stage_recorded",return_value=True),patch(
                "selenium_pipeline.production_video_contract.verify_series",
                side_effect=[VideoContractError("not produced yet"),
                             {"status":"accepted_synchronized_series"}]):
            self.assertTrue(process_job(self.root,"8.1",9222,1,self.root/"logs",
                    self.root/"lane",900,3600,report,lambda:None))
        self.assertEqual(calls,["video"])
        self.assertEqual(report["8.1"]["contract"],"accepted_synchronized_series")
        self.assertFalse(report["8.1"]["student_published"])

    def test_prepared_element_media_failure_deferred_not_falsely_completed(self):
        root=self.root/"8"/"8.1"
        (root/"slides.pdf").write_bytes(b"synthetic slides")
        (root/"element_narration_plan.json").write_text("{}",encoding="utf8")
        (root/"element_wav").mkdir()
        report={}
        with patch("selenium_pipeline.three_pc_worker.run_stage",
                   return_value=(False,"missing source anchor")):
            self.assertFalse(process_job(self.root,"8.1",9222,2,self.root/"logs",
                    self.root/"lane",900,3600,report,lambda:None))
        self.assertEqual(report["8.1"]["status"],"unfinished")
        self.assertIn("missing source anchor",report["8.1"]["error"])

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
