"""Unified Windows no-resend/source-reuse recovery, synthetic inputs."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests.test_original_multisource_recovery_campaign import RealTwoSourceFaultRecoveryTests
from selenium_pipeline.original_windows_batch_controller import run_batch
from selenium_pipeline.windows_fresh_source_trial import run_trial
from selenium_pipeline.windows_recovery_integrity import audit
from selenium_pipeline.original_multisource_recovery_campaign import CampaignRecoveryBlocked


class RecoveryIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.seed = RealTwoSourceFaultRecoveryTests(
            "test_two_original_sources_produce_durable_distinct_readiness_receipts")
        self.seed.setUp()
        self.addCleanup(self.seed.doCleanups)
        self.seed.runit()
        self.jobs = self.seed.root / "jobs_external"
        self.jobs.mkdir()
        run_batch(campaign=self.seed.output, jobs_dir=self.jobs)
        self.publisher = self.seed.root / "independent_book"
        src = self.publisher / "22" / "22.1"
        src.mkdir(parents=True)
        (src / "source.pdf").write_bytes(b"%PDF-1.7\n" + b"independent source" * 30)
        self.trial = self.seed.root / "independent_trial"
        self.trial.mkdir()
        run_trial(source_root=self.publisher, section="22.1",
                  trial_dir=self.trial,
                  subprocess_run=Mock(
                      return_value=subprocess.CompletedProcess([], 0, "", "")))

    def test_current_completed_jobs_and_new_source_are_safe_to_inspect(self):
        with patch("selenium_pipeline.original_source_e2e_acceptance.inspect_source_e2e",
                   side_effect=AssertionError("scientific rescan")), patch(
            "selenium_pipeline.original_source_e2e_acceptance.execute_prepared",
            side_effect=AssertionError("video renderer invoked"),
        ):
            r = audit(jobs_dir=self.jobs, fresh_trial_dir=self.trial)
        self.assertEqual(r["source_job_receipts_current_and_sha_verified"], 2)
        self.assertEqual(r["source_job_receipts_security_or_version_rejected"], 0)
        self.assertEqual(r["fresh_original_figure_attempt_state"],
                         "NO_BROWSER_ATTEMPT_RECORDED")
        self.assertFalse(r["automatic_provider_retry_authorized"])
        self.assertFalse(r["eligible_for_student_publication"])
        self.assertFalse(r["genuine_full_source_to_video_completed"])

    def test_timed_out_attempt_recovery_never_resends_model(self):
        fake = Mock(side_effect=subprocess.TimeoutExpired("provider", 30))
        run_trial(source_root=self.publisher, section="22.1",
                  trial_dir=self.trial, attempt_figures=True,
                  timeout_seconds=30, subprocess_run=fake)
        r = audit(jobs_dir=self.jobs, fresh_trial_dir=self.trial)
        self.assertEqual(r["fresh_original_figure_attempt_state"],
                         "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY")
        self.assertFalse(r["automatic_provider_retry_authorized"])
        self.assertEqual(fake.call_count, 1)

    def test_tampered_one_job_does_not_erase_other_verified_job(self):
        target = self.jobs / "section_8_4_job.json"
        target.write_text(target.read_text("utf8") + " ", encoding="utf8")
        r = audit(jobs_dir=self.jobs, fresh_trial_dir=self.trial)
        self.assertEqual(r["source_job_receipts_security_or_version_rejected"], 1)
        self.assertEqual(r["source_job_receipts_current_and_sha_verified"], 1)
        self.assertEqual(r["status"], "SOURCE_JOB_RECONCILIATION_REQUIRED")

    def test_missing_section_job_is_resume_only_when_original_still_verifies(self):
        (self.jobs / "section_8_5_job.json").unlink()
        r = audit(jobs_dir=self.jobs, fresh_trial_dir=self.trial)
        self.assertEqual(r["source_job_receipts_missing_due_to_possible_interruption"], 1)
        self.assertEqual(r["source_job_receipts_current_and_sha_verified"], 1)

    def test_original_source_changed_blocks_reuse(self):
        source = Path(self.seed.specs[0]["lecture"]) / "source.pdf"
        with source.open("ab") as f:
            f.write(b"changed immutable original")
        r = audit(jobs_dir=self.jobs, fresh_trial_dir=self.trial)
        self.assertEqual(r["source_job_receipts_security_or_version_rejected"], 1)
        self.assertEqual(r["source_job_receipts_current_and_sha_verified"], 1)

    def test_independent_new_source_tamper_fails_closed(self):
        fresh = self.publisher / "22" / "22.1" / "source.pdf"
        with fresh.open("ab") as f:
            f.write(b"tamper")
        with self.assertRaisesRegex(CampaignRecoveryBlocked,
                                    "Fresh original source"):
            audit(jobs_dir=self.jobs, fresh_trial_dir=self.trial)


if __name__ == "__main__":
    unittest.main()
