"""Safety regressions: health green receipts require exact downstream-parsable JSON."""
import json
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.one_shot_gemini_source_health_probe import (
    EXPECTED, run_one_health_probe, _validated_probe_history,
)
from selenium_pipeline.scoped_original_math_review_window import inspect_window
from test_one_shot_gemini_source_health_probe import setup_window, good


class HealthEvidenceIntegrity(unittest.TestCase):
    def test_markdown_fenced_json_never_becomes_success_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, w = setup_window(d)
            attempted = []
            result = run_one_health_probe(
                window_root=w,
                transport=lambda _: (attempted.append(1), {
                    "same_owned_gemini_session": True,
                    "model_stopped_generating": True,
                    "raw": "```json\n" + json.dumps(EXPECTED) + "\n```"
                })[1],
                now=1000)
            self.assertEqual(len(attempted), 1)
            self.assertEqual(result["status"], "GEMINI_TRANSPORT_STILL_UNHEALTHY")
            self.assertFalse((w / "source_transport_health.json").exists())
            self.assertFalse(inspect_window(window_root=w, now=1000)
                             ["eligible_for_single_authorized_dispatch"])

    def test_json_with_extra_claims_is_not_exact_probe(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, w = setup_window(d)
            result = run_one_health_probe(
                window_root=w, now=1000,
                transport=lambda _: {
                    **good(""),
                    "raw": json.dumps({**EXPECTED, "academic_approved": True})
                })
            self.assertEqual(result["status"], "GEMINI_TRANSPORT_STILL_UNHEALTHY")
            self.assertFalse((w / "source_transport_health.json").exists())

    def test_unmatched_terminal_log_refuses_new_transport(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, w = setup_window(d)
            (w / "health_attempts.jsonl").write_text(
                json.dumps({"event": "HEALTH_PROBE_SUCCESS", "id": "forged", "at": 900}) + "\n")
            with self.assertRaises(ValueError):
                run_one_health_probe(
                    window_root=w, transport=lambda _: self.fail("unexpected send"),
                    now=5000)
            self.assertFalse((w / "health_probe.claimlock").exists())

    def test_duplicate_attempt_or_reordered_time_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            journal = Path(d) / "health_attempts.jsonl"
            begin = {"event": "HEALTH_PROBE_BEGIN", "id": "a", "at": 1000}
            failed = {"event": "HEALTH_PROBE_FAILED_UNKNOWN", "id": "a", "at": 1010}
            for rows in ([begin, failed, begin],
                         [begin, {**failed, "at": 900}],
                         [{**begin, "at": 6000}, failed]):
                journal.write_text("".join(json.dumps(row) + "\n" for row in rows))
                with self.assertRaises(ValueError):
                    _validated_probe_history(journal, now=5000)

    def test_unclosed_inflight_claim_maintains_quarantine(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, w = setup_window(d)
            (w / "health_attempts.jsonl").write_text(json.dumps({
                "event": "HEALTH_PROBE_BEGIN", "id": "unresolved", "at": 1000
            }) + "\n")
            result = run_one_health_probe(
                window_root=w, transport=lambda _: self.fail("unexpected send"),
                now=5000)
            self.assertEqual(result["status"], "PREVIOUS_HEALTH_PROBE_UNRESOLVED")
            self.assertFalse(result["model_request_sent"])

    def test_valid_historical_pair_and_single_followup_remain_supported(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, w = setup_window(d)
            journal = w / "health_attempts.jsonl"
            journal.write_text("".join(json.dumps(row) + "\n" for row in (
                {"event": "HEALTH_PROBE_BEGIN",
                 "id": "historical_gemini_544_chars_20261023", "at": 1000},
                {"event": "HEALTH_PROBE_FAILED_UNKNOWN",
                 "id": "historical_gemini_544_chars_20261023", "at": 1149},
            )))
            result = run_one_health_probe(window_root=w, transport=good, now=5000)
            self.assertEqual(result["status"], "GEMINI_TRANSPORT_HEALTH_VERIFIED")
            self.assertTrue(inspect_window(window_root=w, now=5000)
                            ["live_source_transport_health_verified"])
            events = _validated_probe_history(journal, now=5000)
            self.assertEqual(len(events), 4)


if __name__ == "__main__":
    unittest.main()
