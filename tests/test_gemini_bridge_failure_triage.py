"""Stage distinctions do not turn a generic bridge error into provider-overload proof."""
import json
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.series_bridge import SeriesBridgeError
from selenium_pipeline.gemini_bridge_failure_triage import classify_owned_gemini_failure
from selenium_pipeline.one_shot_gemini_source_health_probe import run_one_health_probe
from test_one_shot_gemini_source_health_probe import setup_window


class GeminiBridgeStageTriage(unittest.TestCase):
    def test_exact_known_bridge_boundaries(self):
        fixtures = {
            "Could not type Gemini storyboard instruction": "OWNED_COMPOSER_INPUT_FAILED",
            "Could not submit Gemini storyboard instruction": "OWNED_SEND_NOT_CONFIRMED",
            "No stable complete Gemini JSON; untrusted response quarantined at PRIVATE": "OWNED_RESPONSE_UNVERIFIED_QUARANTINED",
            "Gemini JSON capture failed and recovery quarantine could not be written": "OWNED_CAPTURE_EVIDENCE_WRITE_FAILED",
            "Vendored Gemini Selenium client unavailable": "LOCAL_BROWSER_CLIENT_UNAVAILABLE",
            "Bad chrome session PRIVATE": "BRIDGE_STAGE_UNDETERMINED",
        }
        for detail, expected in fixtures.items():
            report = classify_owned_gemini_failure(SeriesBridgeError(detail))
            self.assertEqual(report["stage"], expected)
            self.assertFalse(report["gemini_provider_overload_proven"])
            self.assertFalse(report["private_error_detail_recorded"])
            self.assertNotIn("PRIVATE", str(report))
            self.assertFalse(report["retry_or_scientific_approval_authorized"])

    def test_timeout_is_not_evidence_of_gemini_capacity_exhaustion(self):
        for error in (TimeoutError("UI timed out"),
                      ConnectionError("CDP disconnected"),
                      RuntimeError("Unknown local state"),
                      ValueError("Unexpected Gemini reply")):
            result = classify_owned_gemini_failure(error)
            self.assertFalse(result["gemini_provider_overload_proven"])
            self.assertFalse(result["retry_or_scientific_approval_authorized"])

    def test_real_probe_records_only_sanitized_stage_not_secret_error(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, w = setup_window(d)
            def failure(_):
                raise SeriesBridgeError(
                    "Could not submit Gemini storyboard instruction; secret-account-token")
            result = run_one_health_probe(window_root=w, transport=failure, now=1000)
            self.assertEqual(result["transport_failure_stage"], "OWNED_SEND_NOT_CONFIRMED")
            self.assertIsNone(result["model_request_sent"])
            records = [json.loads(line) for line in
                       (w / "health_attempts.jsonl").read_text().splitlines()]
            self.assertEqual(records[-1]["failure_stage"], "OWNED_SEND_NOT_CONFIRMED")
            self.assertNotIn("secret-account-token", json.dumps(records))
            self.assertFalse(records[-1]["gemini_provider_overload_proven"])
            self.assertFalse((w / "source_transport_health.json").exists())


if __name__ == "__main__":
    unittest.main()
