"""No-Send source dry-runs must not exhaust genuine source Send claims."""
import json
from pathlib import Path
import tempfile
import unittest

from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.original_multisource_recovery_campaign import _new_atomic, CampaignRecoveryBlocked
from selenium_pipeline.windows_original_source_candidate_inventory import (
    require_no_previous_sibling_source_claim)


class DryRunSendEligibilityTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.publisher = self.root / "publisher" / "1" / "1.3"
        self.publisher.mkdir(parents=True)
        self.source = self.publisher / "source.pdf"
        self.source.write_bytes(b"%PDF-1.7\n" + b"source-only trial content" * 30)
        self.sha = file_sha256(self.source)
        self.registry = self.root / "external_trial_registry"
        self.registry.mkdir()
        self.campaign = self.registry / "forward_source"
        self.campaign.mkdir()
        self.old = self.campaign / ("source_1_3_" + self.sha[:16])
        work = self.old / "source_tree" / "1" / "1.3"
        work.mkdir(parents=True)
        (work / "source.pdf").write_bytes(self.source.read_bytes())
        self.new = self.registry / "real_first_figures"
        self.new.mkdir()
        _new_atomic(self.old / "fresh_trial_contract.json", {
            "schema_version": 1,
            "status": "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL",
            "source_path": str(self.source),
            "source_sha256": self.sha,
            "staged_source_path": str(work / "source.pdf"),
            "stage_goal": "figures",
            "paid_tts_authorized": False,
            "student_publication_authorized": False,
        })
        _new_atomic(self.campaign / "forward_source_campaign_contract.json", {
            "schema_version": 1,
            "status": "WINDOWS_SOURCE_INDEPENDENT_DRYRUN_CAMPAIGN_V1",
            "single_source_stage_send_authorized": False,
            "model_tts_or_video_execution": False,
            "student_publication_authorized": False,
            "selected_distinct_sources": [{
                "section": "1.3",
                "source_sha256": self.sha,
                "source_bytes": self.source.stat().st_size,
            }],
        })
        self.receipt = self.campaign / (self.old.name + ".dryrun.json")
        _new_atomic(self.receipt, {
            "schema_version": 1,
            "status": "FRESH_SOURCE_SEVEN_STAGE_DRY_RUN_READY",
            "source_sha256": self.sha,
            "section": "1.3",
            "external_trial_dir": str(self.old),
            "model_or_tts_calls": False,
            "student_publication_authorized": False,
        })

    def check(self):
        return require_no_previous_sibling_source_claim(
            source_sha256=self.sha, trial_dir=self.new)

    def test_genuine_send_not_blocked_by_verified_source_only_campaign(self):
        self.assertGreater(self.check(), 0)
        self.assertEqual(list(self.new.iterdir()), [])

    def test_candidate_catalog_keeps_no_send_dryrun_eligible(self):
        from selenium_pipeline.windows_original_source_candidate_inventory import find_candidates
        found = find_candidates(publisher_root=self.root / "publisher",
                                trial_registry_root=self.registry)
        self.assertEqual([x["section"] for x in found["potential_new_candidates"]],
                         ["1.3"])
        self.assertEqual(found["known_inert_source_only_dryrun_count"], 1)
        self.assertFalse(found["automatic_model_generation_allowed"])

    def test_missing_dryrun_receipt_blocks_send(self):
        self.receipt.unlink()
        with self.assertRaises(CampaignRecoveryBlocked):
            self.check()

    def test_real_previous_model_send_claim_blocks_even_with_dryrun_receipt(self):
        _new_atomic(self.old / "figures_attempt_started.json", {
            "schema_version": 1, "source_sha256": self.sha,
            "stage": "figures", "single_provider_attempt_only": True,
        })
        with self.assertRaises(CampaignRecoveryBlocked):
            self.check()

    def test_forged_dryrun_or_changed_staged_source_blocks(self):
        payload = json.loads(self.receipt.read_text())
        payload["model_or_tts_calls"] = True
        self.receipt.unlink()
        _new_atomic(self.receipt, payload)
        with self.assertRaises(CampaignRecoveryBlocked):
            self.check()
        self.receipt.unlink()
        payload["model_or_tts_calls"] = False
        _new_atomic(self.receipt, payload)
        staged = self.old / "source_tree" / "1" / "1.3" / "source.pdf"
        staged.write_bytes(staged.read_bytes() + b"modified")
        with self.assertRaises(CampaignRecoveryBlocked):
            self.check()


if __name__ == "__main__":
    unittest.main()
