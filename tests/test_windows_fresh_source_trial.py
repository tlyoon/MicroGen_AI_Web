"""Bounded new original-source trial: synthetic fixtures, no browser/API."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from selenium_pipeline.windows_fresh_source_trial import run_trial
from selenium_pipeline.original_multisource_recovery_campaign import CampaignRecoveryBlocked
from selenium_pipeline.evidence_reuse_contract import file_sha256


class FreshIndependentOriginalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        self.publisher = self.root / "publisher"
        self.lecture = self.publisher / "22" / "22.1"
        self.lecture.mkdir(parents=True)
        self.src = self.lecture / "source.pdf"
        self.src.write_bytes(b"%PDF-1.7\n" + b"synthetic physical source" * 25)
        self.sha = file_sha256(self.src)
        self.trial = self.root / "external_trial"
        self.trial.mkdir()

    def test_new_source_plan_dry_run_without_models_or_voice(self):
        fake = Mock(return_value=subprocess.CompletedProcess([], 0, "", ""))
        result = run_trial(source_root=self.publisher, section="22.1",
                           trial_dir=self.trial, subprocess_run=fake)
        self.assertEqual(result["status"], "FRESH_SOURCE_SEVEN_STAGE_DRY_RUN_READY")
        self.assertFalse(result["new_model_or_tts_calls"])
        self.assertFalse(result["genuine_full_original_e2e_accepted"])
        self.assertEqual(file_sha256(self.src), self.sha)
        args = fake.call_args.args[0]
        self.assertEqual(fake.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(fake.call_args.kwargs["errors"], "replace")
        self.assertIn("--dry-run", args)
        self.assertNotIn("--confirm-gemini-api-cost", args)
        self.assertNotIn("--confirm-google-cloud-tts-cost", args)

    def test_one_real_figures_attempt_is_not_resent(self):
        fake = Mock(return_value=subprocess.CompletedProcess([], 1, "", ""))
        first = run_trial(source_root=self.publisher, section="22.1",
                          trial_dir=self.trial, attempt_figures=True,
                          subprocess_run=fake)
        second = run_trial(source_root=self.publisher, section="22.1",
                           trial_dir=self.trial, attempt_figures=True,
                           subprocess_run=fake)
        self.assertEqual(first["status"], "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY")
        self.assertEqual(second["status"], "PREVIOUS_PROVIDER_ATTEMPT_NOT_RESENT")
        self.assertEqual(fake.call_count, 1)
        self.assertEqual(fake.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(fake.call_args.kwargs["errors"], "replace")
        self.assertIsNone(first["new_model_or_tts_calls"])
        self.assertEqual(file_sha256(self.src), self.sha)

    def test_timeout_is_quarantined_and_no_resend(self):
        fake = Mock(side_effect=subprocess.TimeoutExpired("runner", timeout=30))
        result = run_trial(source_root=self.publisher, section="22.1",
                           trial_dir=self.trial, attempt_figures=True,
                           subprocess_run=fake, timeout_seconds=30)
        self.assertEqual(result["status"], "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY")
        second = run_trial(source_root=self.publisher, section="22.1",
                           trial_dir=self.trial, attempt_figures=True,
                           subprocess_run=fake)
        self.assertEqual(second["status"], "PREVIOUS_PROVIDER_ATTEMPT_NOT_RESENT")
        self.assertEqual(fake.call_count, 1)

    def test_stage_source_tamper_fails_closed(self):
        fake = Mock(return_value=subprocess.CompletedProcess([], 0, "", ""))
        run_trial(source_root=self.publisher, section="22.1",
                  trial_dir=self.trial, subprocess_run=fake)
        stage = self.trial / "source_tree" / "22" / "22.1" / "source.pdf"
        stage.write_bytes(stage.read_bytes() + b"corruption")
        with self.assertRaisesRegex(CampaignRecoveryBlocked, "Trial source changed"):
            run_trial(source_root=self.publisher, section="22.1",
                      trial_dir=self.trial, subprocess_run=fake)

    def test_missing_source_or_unsafe_section_rejected(self):
        fake = Mock(return_value=subprocess.CompletedProcess([], 0, "", ""))
        with self.assertRaises(CampaignRecoveryBlocked):
            run_trial(source_root=self.publisher, section="../../foo",
                      trial_dir=self.trial, subprocess_run=fake)
        with self.assertRaises(CampaignRecoveryBlocked):
            run_trial(source_root=self.publisher, section="22.2",
                      trial_dir=self.trial, subprocess_run=fake)


    def test_real_runner_contract_passes_one_send_budget_to_bounded_child(self):
        fake = Mock(return_value=subprocess.CompletedProcess([], 1, "", ""))
        with patch("selenium_pipeline.windows_bounded_stage_process.run_bounded",
                   fake), patch(
            "selenium_pipeline.windows_gemini_provider_halt.record_stage",
            return_value={"status": "MOCK_ONLY_NO_HEALTH_MUTATION"},
        ):
            result = run_trial(source_root=self.publisher, section="22.1",
                               trial_dir=self.trial, attempt_figures=True)
        self.assertEqual(result["status"], "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY")
        self.assertTrue((self.trial / "figures_transport_triage.json").is_file())
        self.assertEqual(
            result["automatic_transport_triage"]["model_requests_during_diagnosis"], 0)
        self.assertFalse(
            result["automatic_transport_triage"]["automatic_resubmission_authorized"])
        env = fake.call_args.kwargs["environ"]
        self.assertEqual(env["MICROGEN_SELENIUM_ATTEMPTS"], "1")
        self.assertEqual(env["MICROGEN_API_ATTEMPTS"], "1")
        self.assertEqual(env["MICROGEN_SINGLE_PROVIDER_SEND"], "1")
        self.assertEqual(fake.call_count, 1)

    def test_new_original_after_prior_503_uses_key_two_with_no_resend_budget(self):
        fake = Mock(return_value=subprocess.CompletedProcess([], 1, "", ""))
        with patch("selenium_pipeline.windows_gemini_provider_halt.inspect_halt",
                   return_value={
                       "status": "NO_PROVIDER_HALT",
                       "new_generation_dispatch_allowed_by_health_policy": True,
                       "new_source_preferred_gemini_key_ordinal": 2,
                   }), patch("selenium_pipeline.windows_bounded_stage_process.run_bounded",
                             fake), patch(
                       "selenium_pipeline.windows_gemini_provider_halt.record_stage",
                       return_value={"status": "MOCKED_TERMINAL_HEALTH"},
                   ):
            result = run_trial(source_root=self.publisher, section="22.1",
                               trial_dir=self.trial, attempt_figures=True)
        env = fake.call_args.kwargs["environ"]
        self.assertEqual(env["MICROGEN_GEMINI_SINGLE_SEND_KEY_ORDINAL"], "2")
        self.assertEqual(env["MICROGEN_SINGLE_PROVIDER_SEND"], "1")
        self.assertEqual(env["MICROGEN_API_ATTEMPTS"], "1")
        self.assertEqual(result["status"], "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY")
        self.assertEqual(fake.call_count, 1)

    def test_provider_cooldown_blocks_new_figures_before_attempt_ledger(self):
        fake = Mock(side_effect=AssertionError("should not send Gemini"))
        with patch("selenium_pipeline.windows_gemini_provider_halt.inspect_halt",
                   return_value={
                       "status": "HALT_NEW_GEMINI_TASKS",
                       "new_generation_dispatch_allowed_by_health_policy": False,
                       "paused_until_unix_utc": 12345,
                   }):
            result = run_trial(source_root=self.publisher, section="22.1",
                               trial_dir=self.trial, attempt_figures=True,
                               subprocess_run=fake)
        self.assertEqual(result["status"], "GEMINI_PROVIDER_COOLDOWN_NO_SUBMISSION")
        self.assertFalse((self.trial / "figures_attempt_started.json").exists())
        fake.assert_not_called()


if __name__ == "__main__":
    unittest.main()
