"""One-stage original-source checkpointing, recovery, and no-resend tests.

No browser, Gemini, paid TTS or actual publisher PDF is accessed by tests.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from selenium_pipeline.original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, _new_atomic,
)
from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.windows_original_stage_sequence import run_stage


class WindowsOriginalStageSequenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        self.publisher = self.root / "publisher" / "22" / "22.2"
        self.publisher.mkdir(parents=True)
        self.original = self.publisher / "source.pdf"
        self.original.write_bytes(b"%PDF-1.7\n" + b"Independent PDF" * 40)
        self.sha = file_sha256(self.original)
        self.trial = self.root / "trial_external"
        self.trial.mkdir()
        self.lecture = self.trial / "source_tree" / "22" / "22.2"
        self.lecture.mkdir(parents=True)
        (self.lecture / "source.pdf").write_bytes(self.original.read_bytes())
        self.workspace = self.lecture / ".microgen_work"
        self.workspace.mkdir()
        (self.workspace / "source.pdf").write_bytes(self.original.read_bytes())
        _new_atomic(self.trial / "fresh_trial_contract.json", {
            "schema_version": 1,
            "status": "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL",
            "source_path": str(self.original),
            "source_sha256": self.sha,
            "staged_source_path": str(self.lecture / "source.pdf"),
            "stage_goal": "figures",
            "paid_tts_authorized": False,
            "student_publication_authorized": False,
        })

    def figure_receipt(self, successful=True):
        _new_atomic(self.trial / "figures_attempt_result.json", {
            "status": ("FIGURES_STAGE_RETURNED_SUCCESS_NOT_FULL_LECTURE"
                       if successful else "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY"),
            "figure_stage_exit_code": 0 if successful else None,
            "original_source_sha256": self.sha,
            "staged_original_sha256": self.sha,
            "new_video_rendered": False,
            "student_publication_authorized": False,
        })

    def emit(self, *names):
        def runner(**kwargs):
            for name in names:
                (self.lecture / name).write_bytes(b"valid synthetic " + name.encode())
            return subprocess.CompletedProcess([], 0)
        return Mock(side_effect=runner)

    @patch("selenium_pipeline.runner.check_valid", return_value=True)
    def test_sequential_forward_stages_and_receipt_reuse(self, _valid):
        self.figure_receipt()
        slides = self.emit("slides.tex", "slides.pdf")
        first = run_stage(trial_dir=self.trial, stage="slides",
                          stage_runner=slides)
        self.assertEqual(first["status"], "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND")
        self.assertEqual(slides.call_count, 1)
        _valid.assert_any_call("figures", self.workspace)
        _valid.assert_any_call("slides", self.workspace)
        self.assertIn("--from-stage", slides.call_args.kwargs["command"])
        limited = slides.call_args.kwargs["environ"]
        self.assertEqual(limited["MICROGEN_SELENIUM_ATTEMPTS"], "1")
        self.assertEqual(limited["MICROGEN_API_ATTEMPTS"], "1")
        self.assertEqual(limited["SLIDES_MAX_ATTEMPTS"], "1")
        self.assertEqual(limited["MICROGEN_SINGLE_PROVIDER_SEND"], "1")
        self.assertNotIn("--confirm-gemini-api-cost",
                         slides.call_args.kwargs["command"])
        self.assertFalse(first["new_tts_calls"])
        self.assertFalse(first["new_video_rendered"])
        second = run_stage(trial_dir=self.trial, stage="slides",
                           stage_runner=slides)
        self.assertEqual(second["status"], "REUSED_PREVIOUS_SOURCE_STAGE")
        self.assertEqual(slides.call_count, 1)
        narration = self.emit("script.txt")
        n = run_stage(trial_dir=self.trial, stage="narration",
                      stage_runner=narration)
        self.assertEqual(n["status"], "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND")
        math = self.emit("script_risk_report.json", "math_semantic_report.json")
        m = run_stage(trial_dir=self.trial, stage="script_qa",
                      stage_runner=math)
        self.assertEqual(m["status"], "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND")
        self.assertFalse(m["new_model_or_tts_calls"])
        self.assertEqual(file_sha256(self.original), self.sha)
        self.assertFalse((self.lecture / "element_wav").exists())
        self.assertFalse((self.lecture / "lecture_completion.json").exists())

    @patch("selenium_pipeline.runner.check_valid", return_value=True)
    def test_predecessor_timeout_blocks_next_stage_before_browser(self, _valid):
        self.figure_receipt(successful=False)
        never = Mock(side_effect=AssertionError("model submitted"))
        with self.assertRaises(CampaignRecoveryBlocked):
            run_stage(trial_dir=self.trial, stage="slides",
                      stage_runner=never)
        never.assert_not_called()
        self.assertFalse((self.trial / "stage_slides_started.json").exists())

    @patch("selenium_pipeline.runner.check_valid", return_value=True)
    def test_stage_timeout_is_quarantined_and_not_resent(self, _valid):
        self.figure_receipt()
        timeout = Mock(side_effect=subprocess.TimeoutExpired("stage", 30))
        first = run_stage(trial_dir=self.trial, stage="slides",
                          stage_runner=timeout, timeout_seconds=30)
        self.assertEqual(first["status"],
                         "STAGE_TIMEOUT_UNKNOWN_PROVIDER_SEND_NO_RETRY")
        second = run_stage(trial_dir=self.trial, stage="slides",
                           stage_runner=timeout)
        self.assertEqual(second["status"], "PREVIOUS_STAGE_ATTEMPT_NOT_RESENT")
        self.assertEqual(timeout.call_count, 1)

    @patch("selenium_pipeline.runner.check_valid", return_value=True)
    def test_real_slide_stage_auto_records_triage_without_another_send(self, _valid):
        self.figure_receipt()
        with patch("selenium_pipeline.windows_original_stage_sequence.run_bounded",
                   side_effect=subprocess.TimeoutExpired("slides", 30)) as runner, patch(
                   "selenium_pipeline.windows_gemini_provider_halt.record_stage",
                   return_value={"status": "MOCK_HEALTH"}):
            report = run_stage(trial_dir=self.trial, stage="slides",
                               timeout_seconds=30)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(report["status"], "STAGE_TIMEOUT_UNKNOWN_PROVIDER_SEND_NO_RETRY")
        self.assertTrue((self.trial / "stage_slides_transport_triage.json").is_file())
        self.assertEqual(
            report["automatic_transport_triage"]["model_requests_during_diagnosis"], 0)
        self.assertFalse(
            report["automatic_transport_triage"]["automatic_resubmission_authorized"])
        no_second_run = Mock(side_effect=AssertionError("duplicate model send"))
        replay = run_stage(trial_dir=self.trial, stage="slides",
                           stage_runner=no_second_run)
        self.assertEqual(replay["status"], "PREVIOUS_STAGE_ATTEMPT_NOT_RESENT")
        no_second_run.assert_not_called()

    @patch("selenium_pipeline.runner.check_valid", return_value=True)
    def test_source_and_accepted_artifact_mutation_fail_closed(self, _valid):
        self.figure_receipt()
        slides = self.emit("slides.tex", "slides.pdf")
        run_stage(trial_dir=self.trial, stage="slides", stage_runner=slides)
        (self.lecture / "slides.pdf").write_bytes(b"stale modified slides")
        with self.assertRaises(CampaignRecoveryBlocked):
            run_stage(trial_dir=self.trial, stage="slides", stage_runner=slides)
        self.assertEqual(slides.call_count, 1)

    def test_wrong_original_workspace_source_stops_without_any_paid_stage(self):
        self.figure_receipt()
        (self.workspace / "source.pdf").write_bytes(b"wrong workspace input")
        never = Mock(side_effect=AssertionError("must not launch browser"))
        with self.assertRaises(CampaignRecoveryBlocked):
            run_stage(trial_dir=self.trial, stage="slides", stage_runner=never)
        never.assert_not_called()
        self.assertFalse((self.trial / "stage_slides_started.json").exists())

    def test_wrong_stage_or_original_source_change_rejected(self):
        with self.assertRaises(CampaignRecoveryBlocked):
            run_stage(trial_dir=self.trial, stage="tts", stage_runner=Mock())
        self.figure_receipt()
        self.original.write_bytes(b"edited publisher source")
        with self.assertRaises(CampaignRecoveryBlocked):
            run_stage(trial_dir=self.trial, stage="slides", stage_runner=Mock())

    @patch("selenium_pipeline.runner.check_valid", return_value=True)
    def test_new_source_stage_selects_fallback_key_with_single_send(self, _valid):
        self.figure_receipt()
        slides = self.emit("slides.tex", "slides.pdf")
        with patch("selenium_pipeline.windows_gemini_provider_halt.inspect_halt",
                   return_value={
                       "status": "NO_PROVIDER_HALT",
                       "new_generation_dispatch_allowed_by_health_policy": True,
                       "new_source_preferred_gemini_key_ordinal": 2,
                   }):
            state = run_stage(trial_dir=self.trial, stage="slides",
                              stage_runner=slides)
        self.assertEqual(state["status"], "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND")
        self.assertEqual(slides.call_count, 1)
        self.assertEqual(slides.call_args.kwargs["environ"][
            "MICROGEN_GEMINI_SINGLE_SEND_KEY_ORDINAL"], "2")
        self.assertEqual(slides.call_args.kwargs["environ"][
            "MICROGEN_SINGLE_PROVIDER_SEND"], "1")

    @patch("selenium_pipeline.runner.check_valid", return_value=True)
    def test_shared_gemini_cooldown_blocks_new_send_before_stage_claim(self, _valid):
        self.figure_receipt()
        never = Mock(side_effect=AssertionError("should not send Gemini"))
        with patch("selenium_pipeline.windows_gemini_provider_halt.inspect_halt",
                   return_value={
                       "status": "HALT_NEW_GEMINI_TASKS",
                       "new_generation_dispatch_allowed_by_health_policy": False,
                       "paused_until_unix_utc": 12345,
                   }):
            result = run_stage(trial_dir=self.trial, stage="slides",
                               stage_runner=never)
        self.assertEqual(result["status"], "GEMINI_PROVIDER_COOLDOWN_NO_SUBMISSION")
        self.assertFalse((self.trial / "stage_slides_started.json").exists())
        never.assert_not_called()


if __name__ == "__main__":
    unittest.main()
