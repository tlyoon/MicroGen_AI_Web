"""Windows multi-source status controller: physical SHA/receipt restart tests.

Fixture campaign uses temporary synthetic PDFs, not user textbook materials.
"""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_original_multisource_recovery_campaign import RealTwoSourceFaultRecoveryTests
from selenium_pipeline.original_windows_batch_controller import run_batch
from selenium_pipeline.original_multisource_recovery_campaign import CampaignRecoveryBlocked


class WindowsMultiSourceControllerTests(unittest.TestCase):
    def setUp(self):
        self.seed = RealTwoSourceFaultRecoveryTests(
            "test_two_original_sources_produce_durable_distinct_readiness_receipts")
        self.seed.setUp()
        self.addCleanup(self.seed.doCleanups)
        self.seed.runit()
        self.jobs = self.seed.root / "external_windows_job"
        self.jobs.mkdir()

    def test_two_sections_recover_without_scientific_reinspection(self):
        with patch(
            "selenium_pipeline.original_source_e2e_acceptance.inspect_source_e2e",
            side_effect=AssertionError("duplicate scientific review"),
        ), patch(
            "selenium_pipeline.original_source_e2e_acceptance.execute_prepared",
            side_effect=AssertionError("unapproved batch renderer"),
        ):
            first = run_batch(campaign=self.seed.output, jobs_dir=self.jobs)
            second = run_batch(campaign=self.seed.output, jobs_dir=self.jobs)
        self.assertEqual(first["new_job_receipts"], 2)
        self.assertEqual(second["reused_job_receipts"], 2)
        self.assertEqual(second["new_job_receipts"], 0)
        self.assertEqual(first["blocked_input_sections"], 2)
        self.assertEqual(second["security_rejected_sections"], 0)
        self.assertEqual(first["automatically_rendered_original_sections"], 0)
        self.assertFalse(first["new_model_or_tts_calls"])
        self.assertFalse(first["student_publication_authorized"])

    def test_crash_after_first_ledger_write_recovers_only_remaining(self):
        def crash(section):
            raise RuntimeError("Synthetic process failure after " + section)
        with self.assertRaisesRegex(RuntimeError, "Synthetic process failure"):
            run_batch(campaign=self.seed.output, jobs_dir=self.jobs,
                      after_record=crash)
        self.assertTrue((self.jobs / "section_8_4_job.json").exists())
        resumed = run_batch(campaign=self.seed.output, jobs_dir=self.jobs)
        self.assertEqual(resumed["reused_job_receipts"], 1)
        self.assertEqual(resumed["new_job_receipts"], 1)

    def test_tampered_job_blocks_only_that_section(self):
        first = run_batch(campaign=self.seed.output, jobs_dir=self.jobs)
        self.assertEqual(first["new_job_receipts"], 2)
        p = self.jobs / "section_8_4_job.json"
        p.write_text(p.read_text(encoding="utf8") + " ", encoding="utf8")
        repeated = run_batch(campaign=self.seed.output, jobs_dir=self.jobs)
        self.assertEqual(repeated["status"], "SOURCE_SECURITY_REJECTED")
        self.assertEqual(repeated["security_rejected_sections"], 1)
        self.assertEqual(repeated["reused_job_receipts"], 1)
        self.assertEqual(repeated["sections"][0]["job_state"], "SECURITY_REJECTED")

    def test_source_modification_does_not_invalidate_other_section(self):
        first_source = Path(self.seed.specs[0]["lecture"]) / "source.pdf"
        with first_source.open("ab") as f:
            f.write(b"\nsource changed")
        result = run_batch(campaign=self.seed.output, jobs_dir=self.jobs)
        self.assertEqual(result["security_rejected_sections"], 1)
        self.assertEqual(result["new_job_receipts"], 1)
        self.assertFalse(result["student_publication_authorized"])

    def test_job_receipts_cannot_live_in_frozen_original_lecture(self):
        with self.assertRaisesRegex(CampaignRecoveryBlocked, "outside frozen"):
            run_batch(campaign=self.seed.output,
                      jobs_dir=Path(self.seed.specs[0]["lecture"]))

    def test_job_contract_rejects_changed_immutable_campaign(self):
        run_batch(campaign=self.seed.output, jobs_dir=self.jobs)
        c = self.jobs / "windows_multisource_job_contract.json"
        c.write_text(c.read_text("utf8").replace(
            "WINDOWS_ORIGINAL_MULTISOURCE_READ_ONLY_JOB",
            "DANGEROUS_MUTATED_JOB"), encoding="utf8")
        with self.assertRaises(CampaignRecoveryBlocked):
            run_batch(campaign=self.seed.output, jobs_dir=self.jobs)


if __name__ == "__main__":
    unittest.main()
