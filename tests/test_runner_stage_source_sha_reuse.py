"""Main runner's exact source/stage artifact byte reuse and repair invalidation."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.runner_stage_artifact_evidence import (
    SCHEMA,RunnerReuseError,build_stage_evidence,
    decide_stage_reuse,refresh_repaired_tts_evidence,
)

class RunnerRealStageEvidenceTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        for name,body in {
            "source.pdf":b"source-publisher-PDF",
            "Figure 8.3.png":b"source-image",
            "slides.pdf":b"slide-pdf",
            "slides.tex":b"mathematical-Beamer-TeX",
            "script.txt":b"slide narrative",
            "script_risk_report.json":b"{}",
            "script_risk_report.md":b"risk-review",
            "math_semantic_report.json":b"{}",
            "math_semantic_repair_prompt.json":b"{}",
            "tts_fidelity_report.json":b"{}",
            "tts_fidelity_report.md":b"pronunciation-report",
            "slide1.wav":b"RIFF"+b"A"*200,
            "slide2.wav":b"RIFF"+b"B"*200,
            "lecture_completion.json":b"{}",
            "part_01.mp4":b"recorded-encoded-H264",
        }.items():
            (self.root/name).write_bytes(body)
        self.source_sha=hashlib.sha256((self.root/"source.pdf").read_bytes()).hexdigest()

    def _record(self,stage):
        return build_stage_evidence(self.root,stage,self.source_sha)

    def test_original_source_and_all_seven_stages_have_scoped_hash_proofs(self):
        for stage in ("figures","slides","narration","script_qa",
                      "tts","tts_qa","video"):
            with self.subTest(stage=stage):
                result=self._record(stage)
                self.assertEqual(result["schema"],SCHEMA)
                self.assertEqual(result["original_source_sha256"],self.source_sha)
                self.assertFalse(result["student_publication_authorized"])
                self.assertTrue(result["input_sha256"])
                self.assertTrue(result["output_sha256"])

    def test_unchanged_model_source_and_output_must_reuse_exact_stage(self):
        for stage in ("slides","narration","script_qa","tts","tts_qa","video"):
            model="accepted-model"
            accepted={"model":model,"artifact_evidence":self._record(stage)}
            reused,legacy=decide_stage_reuse(
                folder=self.root,stage=stage,source_sha256=self.source_sha,
                accepted=accepted,model_stamp=model,validity_passed=True)
            self.assertFalse(legacy)
            self.assertEqual(reused,accepted["artifact_evidence"])

    def test_old_model_only_checkpoint_adopts_if_physical_outputs_valid(self):
        report,legacy=decide_stage_reuse(
            folder=self.root,stage="slides",source_sha256=self.source_sha,
            accepted={"model":"same-mode"},model_stamp="same-mode",
            validity_passed=True)
        self.assertTrue(legacy)
        self.assertEqual(report["output_sha256"]["slides.pdf"],
                         hashlib.sha256((self.root/"slides.pdf").read_bytes()).hexdigest())

    def test_changed_figures_invalidate_slide_reuse_not_source_equivalence(self):
        previous={"model":"flash","artifact_evidence":self._record("slides")}
        (self.root/"Figure 8.3.png").write_bytes(b"changed-original-graph-label")
        with self.assertRaises(RunnerReuseError):
            decide_stage_reuse(folder=self.root,stage="slides",
                source_sha256=self.source_sha,accepted=previous,
                model_stamp="flash",validity_passed=True)

    def test_mutated_wav_blocks_old_audio_and_video_snapshots(self):
        for stage in ("tts","tts_qa","video"):
            with self.subTest(stage=stage):
                old=self._record(stage)
                original=(self.root/"slide2.wav").read_bytes()
                (self.root/"slide2.wav").write_bytes(b"RIFF"+b"tampered")
                try:
                    with self.assertRaises(RunnerReuseError):
                        decide_stage_reuse(
                            folder=self.root,stage=stage,
                            source_sha256=self.source_sha,
                            accepted={"model":"m","artifact_evidence":old},
                            model_stamp="m",validity_passed=True)
                finally:
                    (self.root/"slide2.wav").write_bytes(original)

    def test_prior_missing_source_stage_output_blocks_costly_restart(self):
        old={"model":"m","artifact_evidence":self._record("narration")}
        (self.root/"script.txt").unlink()
        with self.assertRaises(RunnerReuseError):
            decide_stage_reuse(folder=self.root,stage="narration",
                               source_sha256=self.source_sha,accepted=old,
                               model_stamp="m",validity_passed=True)

    def test_legacy_old_receipt_with_invalid_qa_never_accepted(self):
        with self.assertRaises(RunnerReuseError):
            decide_stage_reuse(folder=self.root,stage="tts",
                source_sha256=self.source_sha,
                accepted={"model":"old"},model_stamp="old",validity_passed=False)

    def test_selectively_repaired_audio_refreshes_only_after_verified_QA(self):
        original={"model":"provider:model:voice",
                  "artifact_evidence":self._record("tts")}
        (self.root/"slide1.wav").write_bytes(b"RIFF"+b"C"*220)
        with self.assertRaises(RunnerReuseError):
            refresh_repaired_tts_evidence(
                folder=self.root,source_sha256=self.source_sha,
                accepted_tts=original,model_stamp=original["model"],
                tts_and_qa_valid=False)
        result=refresh_repaired_tts_evidence(
                folder=self.root,source_sha256=self.source_sha,
                accepted_tts=original,model_stamp=original["model"],
                tts_and_qa_valid=True)
        self.assertNotEqual(result["output_sha256"]["slide1.wav"],
                            original["artifact_evidence"]["output_sha256"]["slide1.wav"])
        self.assertFalse(result["student_publication_authorized"])

    def test_figure_free_source_page_crops_reused_if_physically_present(self):
        (self.root/"Figure 8.3.png").unlink()
        page=self.root/"pages"/"page_1"
        page.mkdir(parents=True)
        (page/"page_1.png").write_bytes(b"true-publisher-page-bitmap")
        receipt=self._record("figures")
        self.assertIn("pages/page_1/page_1.png",receipt["output_sha256"])

    def test_runner_stage_preflight_wired_to_actual_execution(self):
        code=(Path(__file__).resolve().parents[1]/
              "selenium_pipeline"/"runner.py").read_text(encoding="utf8")
        self.assertIn("decide_stage_reuse(",code)
        self.assertIn("build_stage_evidence(",code)
        self.assertIn("refresh_repaired_tts_evidence(",code)
        self.assertIn('previously_completed.get("model")==model_stamp',code)
        self.assertNotIn('state["completed"].get(stage, {}).get("model") == model_stamp and check_valid(stage, folder)',code)
if __name__=="__main__":
    unittest.main()
