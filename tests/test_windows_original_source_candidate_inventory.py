"""Synthetic native Windows source selection, no publisher mutation or model."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, _new_atomic,
)
from selenium_pipeline.windows_original_source_candidate_inventory import (
    find_candidates,
)
from selenium_pipeline.evidence_reuse_contract import file_sha256


class IndependentNewOriginalSourceInventoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.publisher = self.base / "publisher"
        self.publisher.mkdir()
        self.registry = self.base / "existing_attempt_ledger"
        self.registry.mkdir()
        self.one = self.source("77.9", b"new physical source A")
        self.two = self.source("78.1", b"previously submitted source B")
        self.three = self.source("79.4", b"another fresh candidate C")

    def source(self, section, content):
        chap = section.split(".")[0]
        folder = self.publisher / chap / section
        folder.mkdir(parents=True)
        out = folder / "source.pdf"
        out.write_bytes(b"%PDF-1.7\n" + content * 24)
        return out

    def ledger(self, pdf, name="old_attempt"):
        trial = self.registry / name
        trial.mkdir()
        claim = trial / "fresh_trial_contract.json"
        _new_atomic(claim, {
            "schema_version": 1,
            "status": "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL",
            "source_path": str(pdf),
            "source_sha256": file_sha256(pdf),
            "student_publication_authorized": False,
        })
        return claim

    def inspect(self):
        return find_candidates(
            publisher_root=self.publisher,
            trial_registry_root=self.registry)

    def test_read_only_inventory_excludes_any_original_claimed_in_prior_trial(self):
        claim = self.ledger(self.two)
        prior = {p: p.read_bytes() for p in
                 (self.one, self.two, self.three, claim)}
        result = self.inspect()
        self.assertEqual(result["status"],
                         "DIFFERENT_ORIGINAL_SOURCE_CANDIDATES_FOUND_READ_ONLY")
        self.assertEqual(
            {x["section"] for x in result["potential_new_candidates"]},
            {"77.9", "79.4"})
        self.assertEqual(result["known_trial_contracts_examined"], 1)
        self.assertEqual(result["publisher_source_files_examined"], 3)
        self.assertIn(
            "SAME_PDF_ALREADY_PRESENT_IN_PROVIDED_TRIAL_LEDGER",
            {x["reason"] for x in result["excluded_source_summaries"]})
        self.assertFalse(result["automatic_model_generation_allowed"])
        self.assertFalse(result["new_model_or_tts_calls"])
        self.assertFalse(result["registry_scope_covers_all_historical_attempts"])
        self.assertFalse(result["student_publication_authorized"])
        self.assertEqual(prior, {p: p.read_bytes() for p in prior})
        self.assertEqual(list(self.registry.rglob("*_started.json")), [])

    def test_nonempty_previous_contract_stops_same_sha_even_after_failed_send(self):
        self.ledger(self.two)
        result = self.inspect()
        for cand in result["potential_new_candidates"]:
            self.assertNotEqual(cand["source_sha256"], file_sha256(self.two))
            self.assertFalse(cand["globally_never_attempted_proven"])
            self.assertFalse(cand["model_or_tts_requests_authorized"])

    def test_empty_registry_cannot_claim_unused_original_verified(self):
        result = self.inspect()
        self.assertEqual(result["status"],
                         "CANDIDATE_CATALOG_UNVERIFIED_WITHOUT_TRIAL_HISTORY")
        self.assertEqual(len(result["potential_new_candidates"]), 3)
        self.assertFalse(result["automatic_model_generation_allowed"])

    def test_duplicate_source_pdf_is_not_an_independent_candidate(self):
        self.ledger(self.two)
        self.three.write_bytes(self.one.read_bytes())
        result = self.inspect()
        self.assertEqual(len(result["potential_new_candidates"]), 1)
        self.assertEqual(result["potential_new_candidates"][0]["section"], "77.9")
        self.assertIn(
            "DUPLICATE_SOURCE_PDF_BYTES_IN_PUBLISHER",
            {x["reason"] for x in result["excluded_source_summaries"]})

    def test_exact_historical_accepted_source_is_also_excluded(self):
        self.ledger(self.two)
        with patch(
            "selenium_pipeline.windows_original_source_candidate_inventory._PR362",
            {"source_sha256": file_sha256(self.one)},
        ):
            result = self.inspect()
        self.assertEqual(
            {x["section"] for x in result["potential_new_candidates"]},
            {"79.4"})
        self.assertIn(
            "ALREADY_ACCEPTED_HISTORICAL_ORIGINAL_NOT_A_NEW_SOURCE",
            {x["reason"] for x in result["excluded_source_summaries"]})

    def test_tampered_or_malformed_original_trial_claim_refuses_catalog(self):
        claim = self.ledger(self.two)
        claim.write_text('{"source_sha256":"forged"}', encoding="utf8")
        with self.assertRaises(CampaignRecoveryBlocked):
            self.inspect()

    def test_malformed_section_pdf_does_not_silently_qualify(self):
        self.ledger(self.two)
        bad = self.publisher / "80" / "bad" / "source.pdf"
        bad.parent.mkdir(parents=True)
        bad.write_bytes(b"%PDF-1.7\n" + b"not a real section" * 30)
        with self.assertRaisesRegex(CampaignRecoveryBlocked,
                                    "malformed original section"):
            self.inspect()

    def test_bounds_and_overlapping_source_registry_guard(self):
        self.ledger(self.two)
        with self.assertRaises(CampaignRecoveryBlocked):
            find_candidates(
                publisher_root=self.publisher, trial_registry_root=self.registry,
                max_source_pdfs=2)
        with self.assertRaises(CampaignRecoveryBlocked):
            find_candidates(
                publisher_root=self.publisher, trial_registry_root=self.publisher)



    def test_uncontracted_figures_send_intent_excludes_original(self):
        # A pre-Send attempt can outlive its trial contract. Never queue it
        # as a distinct original simply because the contract is missing.
        folder = self.registry / "orphan_figures"
        folder.mkdir()
        receipt = folder / "figures_attempt_started.json"
        _new_atomic(receipt, {
            "schema_version": 1, "stage": "figures",
            "source_sha256": file_sha256(self.two),
            "single_provider_attempt_only": True,
        })
        before = receipt.read_bytes()
        result = self.inspect()
        self.assertEqual(result["known_trial_contracts_examined"], 0)
        self.assertEqual(result["known_send_intent_receipts_examined"], 1)
        self.assertEqual(result["known_distinct_send_intent_sources"], 1)
        self.assertEqual({x["section"] for x in result["potential_new_candidates"]},
                         {"77.9", "79.4"})
        self.assertEqual(
            [x["reason"] for x in result["excluded_source_summaries"]],
            ["SAME_PDF_ALREADY_PRESENT_IN_PROVIDED_SEND_INTENT_LEDGER"])
        self.assertFalse(result["registry_scope_covers_all_historical_attempts"])
        self.assertFalse(result["automatic_model_generation_allowed"])
        self.assertEqual(before, receipt.read_bytes())

    def test_historical_narration_send_intent_excludes_original(self):
        folder = self.registry / "orphan_narration"
        folder.mkdir()
        _new_atomic(folder / "stage_narration_started.json", {
            "schema_version": 1, "stage": "narration",
            "source_sha256": file_sha256(self.two),
            "single_attempt_no_provider_resend": True,
        })
        result = self.inspect()
        self.assertEqual({x["section"] for x in result["potential_new_candidates"]},
                         {"77.9", "79.4"})

    def test_contract_and_intent_same_source_count_once(self):
        self.ledger(self.two, name="attempt_with_contract")
        _new_atomic(self.registry / "attempt_with_contract" /
                    "figures_attempt_started.json", {
            "schema_version": 1, "stage": "figures",
            "source_sha256": file_sha256(self.two),
            "single_provider_attempt_only": True,
        })
        result = self.inspect()
        self.assertEqual(result["known_trial_contracts_examined"], 1)
        self.assertEqual(result["known_send_intent_receipts_examined"], 1)
        self.assertEqual(len(result["excluded_source_summaries"]), 1)
        self.assertEqual(result["excluded_source_summaries"][0][
            "number_of_known_send_intents"], 1)

    def test_untrusted_or_forged_send_intent_fails_closed(self):
        folder = self.registry / "bad"
        folder.mkdir()
        path = folder / "figures_attempt_started.json"
        _new_atomic(path, {
            "schema_version": 1, "stage": "slides",
            "source_sha256": file_sha256(self.two),
            "single_provider_attempt_only": True,
        })
        with self.assertRaisesRegex(CampaignRecoveryBlocked,
                                    "Untrusted source-bound pre-Send"):
            self.inspect()
        path.unlink()
        _new_atomic(path, {
            "schema_version": 1, "stage": "figures",
            "source_sha256": file_sha256(self.two),
            "single_provider_attempt_only": False,
        })
        with self.assertRaises(CampaignRecoveryBlocked):
            self.inspect()

    def test_send_intent_counts_respect_total_registry_limit(self):
        folder = self.registry / "two_receipts"
        folder.mkdir()
        self.ledger(self.two)
        _new_atomic(folder / "figures_attempt_started.json", {
            "schema_version": 1, "stage": "figures",
            "source_sha256": file_sha256(self.two),
            "single_provider_attempt_only": True,
        })
        with self.assertRaises(CampaignRecoveryBlocked):
            find_candidates(
                publisher_root=self.publisher,
                trial_registry_root=self.registry,
                max_trial_receipts=1)


if __name__ == "__main__":
    unittest.main()
