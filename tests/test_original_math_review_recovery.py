"""Adversarial tests for read-only original Thomas review recovery."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.original_math_review_recovery import (
    reconcile_original_math_recovery,
)
from selenium_pipeline.scoped_original_math_review_window import create_window


CONSENT = "USER_APPROVED_NEW_ORIGINAL_REVIEW_20261023_proceed"


def fake_original(root):
    root = Path(root)
    original = root / "original"
    original.mkdir()
    for name in ("source.pdf", "slides.pdf", "script.txt"):
        (original / name).write_bytes(("immutable-" + name).encode())
    q = root / "queue"
    q.mkdir()
    sha = {name: hashlib.sha256((original / name).read_bytes()).hexdigest()
           for name in ("source.pdf", "slides.pdf", "script.txt")}
    (q / "queue.json").write_text(json.dumps({
        "status": "IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
        "student_publication_authorized": False,
        "original_source_folder": str(original),
        "expected_utterances": 1,
        "slide_jobs": [{"slide": 1, "utterance_count": 1,
                        "original_source_sha256": sha["source.pdf"],
                        "original_slides_sha256": sha["slides.pdf"],
                        "original_script_sha256": sha["script.txt"]}],
    }))
    (q / "slide_001_initial_review.json").write_text('{"source_review":true}')
    for n in range(1, 4):
        (q / f"slide_001_independent_challenge_attempt_{n:02d}.json").write_text(
            json.dumps({
                "status": "FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED",
                "slide": 1, "attempt": n, "mode": "INDEPENDENT_CHALLENGE",
                "academically_approved": False,
            }))
    w = root / "separate_window"
    create_window(original_folder=original, queue_root=q, window_root=w,
                  approval_reference=CONSENT, now=1000)
    return original, q, w


def math_snapshot(agreed=0, pending=1):
    return {"original_utterances": 1,
            "source_validated_ai_math_agreements": agreed,
            "source_math_pending_or_disputed": pending,
            "student_publication_authorized": False}


class OriginalMathRecovery(unittest.TestCase):
    def test_real_history_and_no_verified_probe_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            f, q, w = fake_original(d)
            before = {p.name: p.read_bytes() for p in q.iterdir()}
            with patch("selenium_pipeline.original_math_review_recovery."
                       "summarize_original_review_readiness", return_value=math_snapshot()):
                r = reconcile_original_math_recovery(window_root=w, now=1000)
            self.assertEqual(r["historical_original_failed_attempt_receipts"], 3)
            self.assertEqual(r["separate_window_confirmed_submissions"], 0)
            self.assertIn("FRESH_VERIFIED_SAME_TAB_GEMINI_PROBE_MISSING",
                          r["blocking_reasons"])
            self.assertFalse(r["model_request_sent"])
            self.assertFalse(r["student_publication_authorized"])
            self.assertEqual(before, {p.name: p.read_bytes() for p in q.iterdir()})

    def test_verified_probe_is_still_non_dispatching(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, w = fake_original(d)
            response = w / "source_transport_health.response.json"
            response.write_text('{"probe":"microgen_source_transport_ok"}')
            (w / "source_transport_health.json").write_text(json.dumps({
                "status": "COMPLETE_STRUCTURED_TEXT_ONLY_RESPONSE",
                "same_owned_gemini_session": True, "model_stopped_generating": True,
                "exact_expected_json": True, "prompt_characters": 1500,
                "completed_unix_utc": 990,
                "verified_response_sha256": hashlib.sha256(response.read_bytes()).hexdigest(),
            }))
            with patch("selenium_pipeline.original_math_review_recovery."
                       "summarize_original_review_readiness", return_value=math_snapshot()):
                r = reconcile_original_math_recovery(window_root=w, now=1000)
            self.assertTrue(r["non_dispatching_preconditions_satisfied"])
            self.assertFalse(r["model_request_sent"])

    def test_existing_worker_lock_blocks_even_healthy_probe(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, w = fake_original(d)
            (w / "separate_window_checkpoint.json.lock").write_text("other-worker")
            with patch("selenium_pipeline.original_math_review_recovery."
                       "summarize_original_review_readiness", return_value=math_snapshot()):
                r = reconcile_original_math_recovery(window_root=w, now=1000)
            self.assertTrue(r["checkpoint_lock_present"])
            self.assertIn("EXISTING_CLAIM_LOCK_REQUIRES_OWNER_INSPECTION",
                          r["blocking_reasons"])

    def test_original_tamper_refuses_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            f, _, w = fake_original(d)
            (f / "source.pdf").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                reconcile_original_math_recovery(window_root=w, now=1000)

    def test_forged_historical_failure_refuses_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            _, q, w = fake_original(d)
            (q / "slide_001_independent_challenge_attempt_03.json").write_text(
                '{"status":"SUCCESS"}')
            with self.assertRaises(ValueError):
                reconcile_original_math_recovery(window_root=w, now=1000)

    def test_ledger_mismatch_refuses_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, w = fake_original(d)
            with patch("selenium_pipeline.original_math_review_recovery."
                       "summarize_original_review_readiness",
                       return_value=math_snapshot(agreed=1, pending=1)):
                with self.assertRaises(ValueError):
                    reconcile_original_math_recovery(window_root=w, now=1000)


if __name__ == "__main__":
    unittest.main()
