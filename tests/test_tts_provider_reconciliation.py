"""Pure offline provider-export and aggregate billing reconciliation regressions."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.tts_attempt_evidence import (
    AttemptEvidence, safe_provider_request_id,
)
from selenium_pipeline.tts_effective_identity import LITE, FLASH
from selenium_pipeline.tts_provider_reconciliation import (
    TTSExternalEvidenceError, audit, main,
)


class ProviderEvidenceReconciliationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.folder = self.root / "lecture"
        self.folder.mkdir()
        self.items = [(1, "Physics example with an equation.")]
        (self.folder / "script.txt").write_text(
            "**Slide 1 [1 min]:\nPhysics example with an equation.",
            encoding="utf-8")
        self.ledger = AttemptEvidence(self.folder, self.items)
        self.log_path = self.root / "provider-log-export.json"
        self.bill_path = self.root / "billing-export.json"
        self.ledger.record(
            provider="gemini", model=LITE, slide=1, round_number=1,
            outcome="transient_failure", error_type="ServiceUnavailable",
            provider_request_id="provider_req_11111")
        self.ledger.record(
            provider="gemini", model=LITE, slide=1, round_number=2,
            outcome="transient_failure", error_type="ServiceUnavailable",
            provider_request_id="provider_req_22222")
        self.ledger.record(
            provider="gemini", model=LITE, slide=1, round_number=3,
            outcome="transient_failure", error_type="ServiceUnavailable")
        self.records = self.ledger.read()
        self.provider = {
            "schema_version": 1,
            "kind": "provider_request_export",
            "source_system": "google_ai_studio_logs",
            "exported_at_utc": "2026-10-17T18:00:00Z",
            "rows": [
                {
                    "provider": "gemini", "model": LITE,
                    "provider_request_id": self.records[i]["provider_request_id"],
                    "event_time_utc": self.records[i]["observed_at_utc"],
                    "http_status": 503,
                } for i in range(2)
            ],
        }
        # Derive the aggregate billing window from the observed local UTC
        # attempt. Fixed calendar dates caused this test to fail the next day.
        observed = datetime.fromisoformat(
            self.records[0]["observed_at_utc"].replace("Z", "+00:00"))
        window_start = observed.replace(hour=0, minute=0, second=0,
                                        microsecond=0)
        start = window_start.isoformat().replace("+00:00", "Z")
        end = (window_start + timedelta(days=1)).isoformat().replace(
            "+00:00", "Z")
        self.billing = {
            "schema_version": 1,
            "kind": "billing_aggregate_export",
            "source_system": "google_cloud_billing_bigquery",
            "exported_at_utc": "2026-10-18T08:00:00Z",
            "rows": [{
                "project_id": "synthetic-google-project",
                "service": "Gemini API",
                "sku": "Synthetic metered usage",
                "usage_start_utc": start,
                "usage_end_utc": end,
                "currency": "USD",
                "cost": "0.067",
            }],
        }
        self.save()

    def save(self):
        self.log_path.write_text(json.dumps(self.provider), encoding="utf-8")
        self.bill_path.write_text(json.dumps(self.billing), encoding="utf-8")

    def test_absent_exports_are_not_falsely_counted_as_provider_proof(self):
        report = audit(self.folder)
        self.assertEqual(report["provider_request_correlation"]["status"], "NO_PROVIDER_EXPORT")
        self.assertFalse(report["real_provider_receipt_proven"])
        self.assertEqual(report["billing"]["status"], "NO_BILLING_EXPORT")
        self.assertEqual(report["billable_api_calls_performed"], 0)

    def test_matching_two_ids_leaves_one_unverifiable_local_failure(self):
        report = audit(self.folder, provider_export=self.log_path)
        found = report["provider_request_correlation"]
        self.assertEqual(found["status"], "PARTIAL_ID_MATCH")
        self.assertEqual(len(found["matched_requests"]), 2)
        self.assertEqual(len(found["unmatched_local_events"]), 1)
        self.assertEqual(found["unmatched_local_events"][0]["reason"],
                         "no_provider_request_id_in_local_event")
        self.assertFalse(report["real_provider_receipt_proven"])

    def test_full_id_coverage_still_cannot_authenticate_exported_json(self):
        self.ledger.record(
            provider="gemini", model=LITE, slide=1, round_number=4,
            outcome="transient_failure", error_type="ServiceUnavailable",
            provider_request_id="provider_req_44444")
        # Change only the third unknown ID by seeding a fresh synthetic job.
        # All-event ID match can be tested against a two-record journal.
        with tempfile.TemporaryDirectory() as other:
            other_dir = Path(other)
            (other_dir / "script.txt").write_bytes(
                (self.folder / "script.txt").read_bytes())
            local = AttemptEvidence(other_dir, self.items)
            for i in range(2):
                local.record(provider="gemini", model=LITE, slide=1,
                             round_number=i+1, outcome="transient_failure",
                             error_type="ServiceUnavailable",
                             provider_request_id=self.records[i]["provider_request_id"])
            result = audit(other_dir, provider_export=self.log_path)
        self.assertEqual(result["provider_request_correlation"]["status"],
                         "ALL_EVENTS_ID_MATCHED")
        self.assertFalse(result["real_provider_receipt_proven"])
        self.assertEqual(result["provider_request_correlation"]["source_authentication"],
                         "external_json_not_cryptographically_authenticated")

    def test_external_http_200_does_not_validate_503_failure(self):
        self.provider["rows"][0]["http_status"] = 200
        self.save()
        report = audit(self.folder, provider_export=self.log_path)
        found = report["provider_request_correlation"]
        self.assertEqual(found["status"], "PARTIAL_ID_MATCH")
        self.assertTrue(any(g["reason"] == "provider_log_disagrees_on_model_status_or_time"
                            for g in found["unmatched_local_events"]))

    def test_other_model_cannot_validate_lite_error(self):
        self.provider["rows"][0]["model"] = FLASH
        self.save()
        report = audit(self.folder, provider_export=self.log_path)
        self.assertEqual(len(report["provider_request_correlation"]["matched_requests"]), 1)

    def test_timestamp_outside_tolerance_is_not_matched(self):
        self.provider["rows"][0]["event_time_utc"] = "2024-01-01T00:00:00Z"
        self.save()
        report = audit(self.folder, provider_export=self.log_path)
        self.assertEqual(len(report["provider_request_correlation"]["matched_requests"]), 1)

    def test_duplicate_provider_request_id_rejected(self):
        self.provider["rows"][1]["provider_request_id"] = self.provider["rows"][0]["provider_request_id"]
        self.save()
        with self.assertRaisesRegex(TTSExternalEvidenceError, "Duplicate"):
            audit(self.folder, provider_export=self.log_path)

    def test_billing_is_period_context_not_an_exact_request_receipt(self):
        report = audit(self.folder, billing_export=self.bill_path)
        self.assertEqual(report["billing"]["status"], "USAGE_WINDOW_OVERLAP_ONLY")
        self.assertEqual(report["billing"]["matched_usage_windows"], 1)
        self.assertEqual(report["billing"]["cost_by_currency"], {"USD": "0.067"})
        self.assertIn("not_per_request", report["billing"]["attribution"])
        self.assertFalse(report["real_provider_receipt_proven"])
        self.assertEqual(report["provider_request_correlation"]["status"], "NO_PROVIDER_EXPORT")

    def test_billing_nonoverlap_is_not_falsely_attributed(self):
        self.billing["rows"][0]["usage_start_utc"] = "2024-01-01T00:00:00Z"
        self.billing["rows"][0]["usage_end_utc"] = "2024-01-02T00:00:00Z"
        self.save()
        report = audit(self.folder, billing_export=self.bill_path)
        self.assertEqual(report["billing"]["status"], "NO_WINDOW_OVERLAP")
        self.assertEqual(report["billing"]["cost_by_currency"], {})

    def test_nonfinite_or_negative_billing_data_fails(self):
        for amount in ("NaN", "-1", "Infinity"):
            with self.subTest(amount=amount):
                self.billing["rows"][0]["cost"] = amount
                self.save()
                with self.assertRaisesRegex(TTSExternalEvidenceError, "billing usage window"):
                    audit(self.folder, billing_export=self.bill_path)

    def test_tampered_local_retry_record_rejected(self):
        event = self.ledger.path / "000001.json"
        obj = json.loads(event.read_text(encoding="utf-8"))
        obj["outcome"] = "success"
        event.write_text(json.dumps(obj), encoding="utf-8")
        with self.assertRaisesRegex(TTSExternalEvidenceError, "journal"):
            audit(self.folder, provider_export=self.log_path)

    def test_source_text_changed_rejects_existing_attempt_log(self):
        (self.folder / "script.txt").write_text("new words", encoding="utf-8")
        with self.assertRaisesRegex(TTSExternalEvidenceError, "narration"):
            audit(self.folder)

    def test_read_only_audit_does_not_write_files(self):
        before = {
            str(p.relative_to(self.root)): p.read_bytes()
            for p in self.root.rglob("*") if p.is_file()
        }
        audit(self.folder, provider_export=self.log_path, billing_export=self.bill_path)
        after = {
            str(p.relative_to(self.root)): p.read_bytes()
            for p in self.root.rglob("*") if p.is_file()
        }
        self.assertEqual(before, after)

    def test_request_id_from_sdk_exception_only_when_safe(self):
        error = RuntimeError("HTTP 503")
        error.request_id = "abc-12345-provider"
        self.assertEqual(safe_provider_request_id(error), "abc-12345-provider")
        error.request_id = "Bearer SECRET token with whitespace"
        self.assertIsNone(safe_provider_request_id(error))

    def test_cli_offline_without_exports(self):
        self.assertEqual(main(["--folder", str(self.folder)]), 0)


if __name__ == "__main__":
    unittest.main()
