"""Regression: exact one-shot API 503 triggers bounded precaution, zero model sends."""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from selenium_pipeline.windows_fresh_source_trial import run_trial

from selenium_pipeline.original_multisource_recovery_campaign import _new_atomic
from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.windows_gemini_differential_probe import _SHA, CONTENT_MODEL
from selenium_pipeline.windows_gemini_provider_halt import (
    record_api_capacity, inspect_halt,
)


class StructuredApiCapacityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        scope = patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)})
        scope.start()
        self.addCleanup(scope.stop)
        self.canary = self.root / "one_generic_diagnostic_only"
        self.canary.mkdir()
        self.health = self.root / "provider_health"
        self.claim = self.canary / "api_probe_started.json"
        self.proof = self.canary / "api_probe_result.json"

    def establish_api_proof(self, code=503, error_type="ServerError",
                            outcome="NO_VERIFIED_RESPONSE"):
        _new_atomic(self.claim, {
            "schema_version": 1, "backend": "api",
            "content_model": CONTENT_MODEL, "generic_prompt_sha256": _SHA,
            "one_submission_only": True, "explicit_api_content_cost": True,
            "no_original_source_attached": True,
            "student_publication_authorized": False,
        })
        _new_atomic(self.proof, {
            "schema_version": 1, "backend": "api",
            "content_model": CONTENT_MODEL,
            "error_type": error_type, "outcome": outcome,
            "verified_api_http_status": code,
            "paid_api_content_may_have_occurred": True,
            "claim_sha256": file_sha256(self.claim),
            "student_publication_authorized": False,
        })
        return self.proof.stat().st_mtime

    def test_api_503_halts_new_browser_and_api_gen_for_30_minutes(self):
        t = self.establish_api_proof()
        receipt = record_api_capacity(canary_root=self.canary,
                                      folder=self.health, now=t+5)
        self.assertEqual(receipt["status"],
                         "STRUCTURED_API_CAPACITY_PROOF_RECORDED")
        self.assertEqual(receipt["new_api_generation_calls"], 0)
        for backend in ("selenium", "api"):
            state = inspect_halt(folder=self.health, backend=backend, now=t+10)
            self.assertEqual(state["status"],
                             "HALT_NEW_GEMINI_TASKS_API_CAPACITY_PRECAUTION")
            self.assertEqual(state["verified_api_capacity_http_status"], 503)
            self.assertFalse(state["new_generation_dispatch_allowed_by_health_policy"])
            self.assertFalse(state["provider_server_failure_proven"])
            self.assertFalse(state["existing_ambiguous_source_resubmission_authorized"])
            self.assertEqual(state["paused_until_unix_utc"], t+1800)
            self.assertEqual(inspect_halt(folder=self.health, backend=backend,
                                          now=t+1801)["status"], "NO_PROVIDER_HALT")
        prior = record_api_capacity(canary_root=self.canary,
                                    folder=self.health, now=t+20)
        self.assertEqual(prior["status"], "PRIOR_STRUCTURED_API_CAPACITY_PROOF_REUSED")
        self.assertEqual(len(list((self.health / "api_capacity_events").glob("*.json"))), 1)

    def test_verified_api_504_prioritizes_key_two_only_on_distinct_new_task(self):
        t = self.establish_api_proof(code=504)
        record_api_capacity(canary_root=self.canary, folder=self.health, now=t+1)
        status = inspect_halt(folder=self.health, backend="api", now=t+3)
        self.assertFalse(status["new_generation_dispatch_allowed_by_health_policy"])
        self.assertEqual(status["verified_api_capacity_http_status"], 504)
        self.assertEqual(status["new_source_preferred_gemini_key_ordinal"], 2)
        # Cooldown expiry does not authorize a second attempt on this canary.
        after = inspect_halt(folder=self.health, backend="api", now=t+1801)
        self.assertEqual(after["status"], "NO_PROVIDER_HALT")
        self.assertEqual(after["new_source_preferred_gemini_key_ordinal"], 2)
        self.assertFalse(after["existing_ambiguous_source_resubmission_authorized"])

    def test_post_cooldown_new_source_uses_configured_key_two_with_one_send(self):
        import subprocess
        t = self.establish_api_proof()
        record_api_capacity(canary_root=self.canary, folder=None, now=t+1)
        publisher = self.root / "fresh_publisher"
        section = publisher / "22" / "22.8"
        section.mkdir(parents=True)
        (section / "source.pdf").write_bytes(b"%PDF-1.7\n" + b"synthetic" * 90)
        new_trial = self.root / "new_external_source_trial"
        new_trial.mkdir()
        fake = Mock(return_value=subprocess.CompletedProcess([], 1))
        # Keep production health evidence intact and use a synthetic
        # source-scoped external trial; no actual Gemini content call.
        with patch.dict(os.environ, {
            "LOCALAPPDATA": str(self.root),
        }), patch(
            "selenium_pipeline.windows_gemini_provider_halt.time.time",
            return_value=t+1801,
        ), patch(
            "selenium_pipeline.windows_bounded_stage_process.run_bounded",
            fake,
        ), patch(
            "selenium_pipeline.windows_gemini_provider_halt.record_stage",
            return_value={"status": "MOCKED_STAGE_RECEIPT"},
        ), patch(
            "selenium_pipeline.windows_new_source_browser_admission."
            "inspect_new_source_browser_admission",
            return_value={"new_source_stage_send_eligible": True},
        ):
            # This test isolates historic cooldown/key selection ONLY.
            # The independent source-free admission gate is tested in
            # test_windows_new_source_browser_admission, never bypassed live.
            result = run_trial(
                source_root=publisher, section="22.8", trial_dir=new_trial,
                attempt_figures=True,
            )
        self.assertEqual(result["status"], "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY")
        self.assertEqual(fake.call_count, 1)
        env = fake.call_args.kwargs["environ"]
        self.assertEqual(env["MICROGEN_SINGLE_PROVIDER_SEND"], "1")
        self.assertEqual(env["MICROGEN_GEMINI_SINGLE_SEND_KEY_ORDINAL"], "2")

    def test_unauthenticated_or_noncapacity_error_never_opens_pause(self):
        self.establish_api_proof(code=401, error_type="ClientError")
        with self.assertRaisesRegex(ValueError, "one-shot API 429/503"):
            record_api_capacity(canary_root=self.canary, folder=self.health)
        self.assertFalse(self.health.exists())

    def test_503_result_with_wrong_server_error_type_refused(self):
        self.establish_api_proof(code=503, error_type="ValueError")
        with self.assertRaisesRegex(ValueError, "one-shot API 429/503"):
            record_api_capacity(canary_root=self.canary, folder=self.health)

    def test_positive_accepted_response_does_not_invent_capacity_failure(self):
        self.establish_api_proof(code=503, outcome="VALID_CANARY_RESPONSE")
        with self.assertRaises(ValueError):
            record_api_capacity(canary_root=self.canary, folder=self.health)

    def test_event_tampering_blocks_dispatch_rather_than_ignoring_evidence(self):
        t = self.establish_api_proof()
        record_api_capacity(canary_root=self.canary, folder=self.health, now=t+1)
        event = next((self.health / "api_capacity_events").glob("*.json"))
        data = event.read_text(encoding="utf8")
        event.write_text(data.replace("503", "429"), encoding="utf8")
        with self.assertRaises(ValueError):
            inspect_halt(folder=self.health, backend="selenium", now=t+5)

    def test_original_result_change_does_not_make_a_new_request(self):
        t = self.establish_api_proof()
        record_api_capacity(canary_root=self.canary, folder=self.health, now=t+1)
        self.proof.write_text(self.proof.read_text(encoding="utf8")+" ",encoding="utf8")
        with self.assertRaises(ValueError):
            inspect_halt(folder=self.health, backend="api", now=t+5)

    def test_real_source_admission_respects_api_capacity_without_sending(self):
        t = self.establish_api_proof()
        record_api_capacity(canary_root=self.canary, now=t+1)
        publisher = self.root / "publisher"
        book = publisher / "22" / "22.7"
        book.mkdir(parents=True)
        (book / "source.pdf").write_bytes(
            b"%PDF-1.7\\n" + b"Synthetic only no academic data." * 12)
        source_trial = self.root / "source_trial"
        source_trial.mkdir()
        never = Mock(side_effect=AssertionError("Gemini content sent"))
        state = run_trial(source_root=publisher, section="22.7",
                          trial_dir=source_trial, attempt_figures=True,
                          subprocess_run=never)
        self.assertEqual(state["status"],
                         "GEMINI_PROVIDER_COOLDOWN_NO_SUBMISSION")
        self.assertFalse((source_trial / "figures_attempt_started.json").exists())
        never.assert_not_called()

    def test_historical_evidence_does_not_pretend_new_outage(self):
        t = self.establish_api_proof()
        record_api_capacity(canary_root=self.canary, folder=self.health, now=t+9000)
        self.assertEqual(inspect_halt(folder=self.health, now=t+9000)["status"],
                         "NO_PROVIDER_HALT")


if __name__ == "__main__":
    unittest.main()
