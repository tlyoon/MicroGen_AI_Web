"""Offline, fail-closed tests for source-bound observed provider retry evidence."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.tts_attempt_evidence import (
    AttemptEvidence, TTSAttemptEvidenceError, GENESIS,
)
from selenium_pipeline.tts_effective_identity import DEFAULT, LITE, FLASH, CHIRP
from selenium_pipeline.tts import synthesize_folder


class ObservedAttemptJournalTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        (self.folder / "script.txt").write_text(
            "**Slide 1 [3 sec]:\nPhysics narration.", encoding="utf-8")
        self.items = [(1, "Physics narration.")]
        self.ledger = AttemptEvidence(self.folder, self.items)

    def failed(self, model=LITE, count=3):
        for round_number in range(1, count + 1):
            self.ledger.record(
                provider="gemini", model=model, slide=1,
                round_number=round_number,
                outcome="transient_failure", error_type="RuntimeError")

    def test_no_cloud_without_both_gemini_models(self):
        self.failed(LITE)
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"No verified"):
            self.ledger.verify_before("chirp3",CHIRP)

    def test_two_failures_are_insufficient(self):
        self.failed(LITE,2)
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"No verified"):
            self.ledger.verify_before("gemini",FLASH)

    def test_three_actual_observed_retryable_results_allow_flash(self):
        self.failed(LITE)
        verified=self.ledger.verify_before("gemini",FLASH)
        self.assertEqual(verified["lite"]["failed_slides"],[1])
        self.assertEqual(verified["lite"]["observed_attempts_by_slide"],{"1":3})
        self.assertEqual(len(self.ledger.read()),3)

    def test_lite_then_flash_retryable_outcomes_allow_cloud(self):
        self.failed(LITE)
        self.failed(FLASH)
        verified=self.ledger.verify_before("chirp3",CHIRP)
        self.assertEqual(verified["lite"]["failed_slides"],[1])
        self.assertEqual(verified["flash"]["failed_slides"],[1])
        self.assertEqual(verified["flash"]["observed_attempts_by_slide"],{"1":3})
        self.assertNotEqual(self.ledger.tip(),GENESIS)

    def test_permanent_error_never_enables_cloud(self):
        self.failed(LITE)
        for n in range(1,4):
            self.ledger.record(
                provider="gemini",model=FLASH,slide=1,round_number=n,
                outcome="permanent_failure",error_type="PermissionError")
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"No verified"):
            self.ledger.verify_before("chirp3",CHIRP)

    def test_success_never_counts_as_exhaustion(self):
        self.failed(LITE,2)
        self.ledger.record(provider="gemini",model=LITE,slide=1,round_number=3,
                           outcome="success")
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"No verified"):
            self.ledger.verify_before("gemini",FLASH)

    def test_altered_event_hash_is_rejected(self):
        self.failed(LITE)
        event=self.ledger.path/"000002.json"
        payload=json.loads(event.read_text())
        payload["outcome"]="success"
        event.write_text(json.dumps(payload))
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"hash/identity"):
            self.ledger.verify_before("gemini",FLASH)

    def test_missing_middle_event_is_rejected(self):
        self.failed(LITE)
        (self.ledger.path/"000002.json").unlink()
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"Gap"):
            self.ledger.verify_before("gemini",FLASH)

    def test_source_script_changed_cannot_reuse_ledger(self):
        self.failed(LITE)
        (self.folder/"script.txt").write_text("different original text",encoding="utf-8")
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"source/model changed"):
            AttemptEvidence(self.folder,self.items)

    def test_hash_chained_records_have_all_dispatch_outcomes(self):
        self.failed(LITE)
        records=self.ledger.read()
        self.assertEqual(records[0]["previous_sha256"],GENESIS)
        self.assertEqual(records[1]["previous_sha256"],records[0]["sha256"])
        self.assertEqual(records[2]["previous_sha256"],records[1]["sha256"])
        self.assertTrue(all(r["outcome"]=="transient_failure" for r in records))

    def test_prior_model_attempts_cannot_be_reordered(self):
        self.failed(LITE)
        self.failed(FLASH)
        self.ledger.record(provider="gemini",model=LITE,slide=1,round_number=4,
                           outcome="transient_failure",error_type="RuntimeError")
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"before Lite retries"):
            self.ledger.verify_before("chirp3",CHIRP)

    def test_extra_partial_event_refuses_escalation(self):
        self.failed(LITE)
        (self.ledger.path/"000004.json.partial").write_text("broken",encoding="utf-8")
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"unrecognized"):
            self.ledger.verify_before("gemini",FLASH)


if __name__=="__main__":
    unittest.main()
