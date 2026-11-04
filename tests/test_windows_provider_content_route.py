"""No-billing regression for vetted API content source-stage routing.

These tests use only synthetic source PDF bytes and simulated processes.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from selenium_pipeline.original_multisource_recovery_campaign import CampaignRecoveryBlocked
from selenium_pipeline.windows_fresh_source_trial import run_trial
from selenium_pipeline.windows_original_stage_sequence import run_stage


class ProviderContentRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        self.book = self.root / "publisher"
        self.section = self.book / "22" / "22.4"
        self.section.mkdir(parents=True)
        self.source = self.section / "source.pdf"
        self.source.write_bytes(b"%PDF-1.7\n" + b"test only" * 80)
        self.trial = self.root / "trial"
        self.trial.mkdir()
        self.mock = Mock(return_value=subprocess.CompletedProcess([], 1, "", ""))

    def test_api_attempt_requires_explicit_permission_before_any_ledger(self):
        with self.assertRaisesRegex(CampaignRecoveryBlocked,
                                    "Explicit --confirm-content-api-cost"):
            run_trial(source_root=self.book, section="22.4",
                      trial_dir=self.trial, attempt_figures=True,
                      communication_mode="api", subprocess_run=self.mock)
        self.assertFalse((self.trial / "figures_attempt_started.json").exists())
        self.assertFalse((self.trial / "fresh_trial_contract.json").exists())
        self.mock.assert_not_called()

    def test_explicit_api_is_bound_to_new_original_and_never_resent(self):
        first = run_trial(source_root=self.book, section="22.4",
                          trial_dir=self.trial, attempt_figures=True,
                          communication_mode="api",
                          confirm_content_api_cost=True,
                          subprocess_run=self.mock)
        self.assertEqual(first["status"], "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY")
        self.assertEqual(self.mock.call_count, 1)
        args = self.mock.call_args.args[0]
        self.assertEqual(args[args.index("--communication-mode")+1], "api")
        self.assertNotIn("--confirm-gemini-api-cost", args)
        ledger = json.loads((self.trial / "figures_attempt_started.json").read_text())
        self.assertTrue(ledger["paid_content_api_explicitly_authorized"])
        self.assertEqual(ledger["communication_mode"], "api")
        second = run_trial(source_root=self.book, section="22.4",
                           trial_dir=self.trial, attempt_figures=True,
                           communication_mode="api",
                           confirm_content_api_cost=True,
                           subprocess_run=self.mock)
        self.assertEqual(second["status"], "PREVIOUS_PROVIDER_ATTEMPT_NOT_RESENT")
        self.assertEqual(self.mock.call_count, 1)
        with self.assertRaises(CampaignRecoveryBlocked):
            run_trial(source_root=self.book, section="22.4",
                      trial_dir=self.trial, attempt_figures=True,
                      subprocess_run=self.mock)

    def test_api_fallback_automatic_after_ui_timeout_is_prohibited(self):
        with self.assertRaisesRegex(CampaignRecoveryBlocked, "No automatic API fallback"):
            run_trial(source_root=self.book, section="22.4",
                      trial_dir=self.trial, communication_mode="fallback")
        self.mock.assert_not_called()

    def test_stage_controller_api_requires_separate_stage_approval(self):
        # Even after a prior successful API figure receipt a new API slide
        # stage must not begin without independent cost permission.
        with self.assertRaisesRegex(CampaignRecoveryBlocked,
                                    "explicit per-stage cost approval"):
            run_stage(trial_dir=self.trial, stage="slides",
                      communication_mode="api",
                      stage_runner=self.mock)
        self.mock.assert_not_called()
        self.assertFalse((self.trial / "stage_slides_started.json").exists())


if __name__ == "__main__":
    unittest.main()
