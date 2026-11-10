"""Windows Gemini transport triage: synthetic immutable offline evidence."""
import os
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.original_multisource_recovery_campaign import _new_atomic, _encode
from selenium_pipeline.windows_gemini_stage_transport_triage import (
    diagnose, persist_terminal_triage,
)


class GeminiStageTransportTriageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.local = Path(tmp.name)
        self.env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.local)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.trial = self.local / "trial"
        self.trial.mkdir()
        self.sha = "a" * 64
        _new_atomic(self.trial / "fresh_trial_contract.json", {
            "schema_version": 1,
            "status": "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL",
            "source_sha256": self.sha,
            "student_publication_authorized": False,
        })

    def begun(self, stage="figures"):
        prefix = "figures_attempt" if stage == "figures" else "stage_" + stage
        _new_atomic(self.trial / f"{prefix}_started.json", {
            "schema_version": 1, "stage": stage, "source_sha256": self.sha,
            "single_provider_attempt_only": True,
        })
        return prefix

    def finish(self, prefix, status, stage="figures"):
        value = {
            "schema_version": 1, "status": status,
            "source_sha256": self.sha,
            "student_publication_authorized": False,
        }
        if stage == "figures":
            value["original_source_sha256"] = self.sha
        _new_atomic(self.trial / f"{prefix}_result.json", value)

    def log(self, text, stage="figures"):
        file = ("figures_stage_stdout.raw.log" if stage == "figures"
                else f"stage_{stage}_stdout.raw.log")
        (self.trial / file).write_text(text, encoding="utf8")

    def test_realistic_local_extraction_and_browser_attach_timeout(self):
        p = self.begun()
        self.finish(p, "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY")
        self.log("[gemini] reusing active debug session on port 9222\n"
                 "Figure extraction completed successfully.\n"
                 "processing folder private; KEY_NOT_TO_REPORT")
        before = sorted(self.trial.iterdir())
        r = diagnose(trial_dir=self.trial)
        self.assertEqual(r["status"],
                         "LOCAL_EXTRACTION_DONE_BROWSER_SESSION_SEEN_SEND_UNVERIFIED")
        self.assertTrue(r["local_figure_extraction_finished_in_log"])
        self.assertTrue(r["browser_debug_session_seen_in_log"])
        self.assertFalse(r["owned_browser_send_registered"])
        self.assertFalse(r["provider_outage_proven"])
        self.assertFalse(r["browser_automation_or_capture_failure_proven"])
        self.assertFalse(r["original_submission_resend_authorized"])
        self.assertNotIn("KEY_NOT_TO_REPORT", str(r))
        self.assertEqual(before, sorted(self.trial.iterdir()))

    def test_registered_slide_send_with_unattributed_reply_is_not_resubmitted(self):
        prefix = self.begun("slides")
        self.finish(prefix, "STAGE_FAILED_OR_OUTPUT_INCOMPLETE_NO_RETRY",
                    stage="slides")
        self.log(
            "[2026-11-06 00:00:00] [INFO] Gemini submission registered via "
            "new-user-turn+composer-cleared.\n"
            "[2026-11-06 00:04:00] [WARN] [GEMINI-RESPONSE] "
            "POST_SUBMIT_NO_ATTRIBUTED_RESPONSE_NO_RESEND\n",
            stage="slides",
        )
        report = persist_terminal_triage(trial_dir=self.trial, stage="slides")
        self.assertEqual(report["status"],
                         "REGISTERED_BROWSER_SEND_NO_ATTRIBUTED_REPLY_NO_RESEND")
        self.assertTrue(report["owned_browser_send_registered"])
        self.assertTrue(report["post_submit_model_reply_attribution_unverified"])
        self.assertFalse(report["provider_outage_proven"])
        self.assertFalse(report["automatic_resubmission_authorized"])
        self.assertEqual(report["model_requests_during_diagnosis"], 0)
        again = persist_terminal_triage(trial_dir=self.trial, stage="slides")
        self.assertEqual(again["status"], "PRIOR_SHA_BOUND_TRIAGE_REUSED_NO_SEND")

    def test_owned_terminal_gemini_ui_error_does_not_prove_api_outage(self):
        prefix = self.begun("figures")
        self.finish(prefix, "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY")
        self.log(
            "[2026-11-06 00:00:00] [INFO] Gemini submission registered via "
            "new-user-turn+composer-cleared.\n"
            "[2026-11-06 00:00:01] [WARN] [GEMINI-RESPONSE] "
            "OWNED_VISIBLE_UI_TERMINAL_ERROR_NO_RESEND\n"
        )
        report = persist_terminal_triage(trial_dir=self.trial, stage="figures")
        self.assertEqual(report["status"],
                         "REGISTERED_BROWSER_SEND_OWNED_UI_ERROR_NO_RESEND")
        self.assertTrue(report["owned_browser_send_registered"])
        self.assertTrue(report["owned_visible_ui_terminal_error_verified"])
        self.assertFalse(report["provider_outage_proven"])
        self.assertFalse(report["automatic_resubmission_authorized"])
        self.assertEqual(report["model_requests_during_diagnosis"], 0)

    def nested_crop_log(self):
        staged = self.trial / "source_tree" / "10" / "10.1" / "source.pdf"
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(b"synthetic source")
        claim = self.trial / "fresh_trial_contract.json"
        value = json.loads(claim.read_text("utf-8"))
        value["staged_source_path"] = str(staged)
        claim.write_text(_encode(value), encoding="utf-8")
        nested = staged.parent / ".microgen_work" / "microgen_figures.log"
        nested.parent.mkdir()
        return nested

    def test_nested_crop_phase_is_detected_without_falsely_blaming_gemini(self):
        p = self.begun()
        self.finish(p, "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY")
        nested = self.nested_crop_log()
        nested.write_text(
            "$ python crop_figs_v3.py\n"
            "[microgen-phase] LOCAL_FIGURE_PDF_RENDER_START\n"
            "[microgen-phase] LOCAL_FIGURE_PDF_RENDER_DONE pages=3\n"
            "[microgen-phase] LOCAL_FIGURE_DOCLING_READY\n"
            "[microgen-phase] LOCAL_FIGURE_CROP_PAGE_START page=2\n",
            encoding="utf-8")
        state = diagnose(trial_dir=self.trial)
        self.assertEqual(state["status"],
                         "LOCAL_PDF_FIGURE_CROP_PROGRESSED_SEND_UNVERIFIED")
        self.assertEqual(state["local_crop_phase"], "LOCAL_FIGURE_CROP_PAGE_START")
        self.assertTrue(state["local_crop_process_seen_in_workspace"])
        self.assertTrue(state["local_crop_heartbeat_present"])
        self.assertFalse(state["owned_browser_send_registered"])
        self.assertFalse(state["provider_outage_proven"])
        first = persist_terminal_triage(trial_dir=self.trial, stage="figures")
        self.assertIsNotNone(first["local_crop_log_sha256"])
        nested.write_text(nested.read_text() + "more progress\\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "diagnosis or evidence changed"):
            persist_terminal_triage(trial_dir=self.trial, stage="figures")

    def test_windows_temp_directory_aliases_are_canonicalized_consistently(self):
        p = self.begun()
        self.finish(p, "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY")
        nested = self.nested_crop_log()
        nested.write_text("$ python crop_figs_v3.py", encoding="utf-8")
        # A lexical alias pointing to the SAME local trial must be compared
        # after both containment operands are canonicalized.
        (self.trial / "benign_alias").mkdir()
        alias = self.trial / "benign_alias" / ".."
        state = diagnose(trial_dir=alias)
        self.assertEqual(state["status"],
                         "LOCAL_PDF_FIGURE_CROP_PROGRESSED_SEND_UNVERIFIED")
        self.assertTrue(state["local_crop_process_seen_in_workspace"])

    def test_prior_diagnostic_before_phase_fields_reuses_without_overwrite(self):
        p = self.begun()
        self.finish(p, "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY")
        nested = self.nested_crop_log()
        diagnostic = self.trial / "figures_transport_triage.json"
        persist_terminal_triage(trial_dir=self.trial, stage="figures")
        legacy = json.loads(diagnostic.read_text("utf-8"))
        for field in ("local_crop_process_seen_in_workspace", "local_crop_phase",
                      "local_crop_heartbeat_present", "local_crop_log_sha256"):
            legacy.pop(field)
        diagnostic.write_text(_encode(legacy), encoding="utf-8")
        previous_bytes = diagnostic.read_bytes()
        nested.write_text("$ python crop_figs_v3.py", encoding="utf-8")
        reused = persist_terminal_triage(trial_dir=self.trial, stage="figures")
        self.assertEqual(reused["status"], "PRIOR_SHA_BOUND_TRIAGE_REUSED_NO_SEND")
        self.assertEqual(reused["new_readonly_classification"],
                         "LOCAL_PDF_FIGURE_CROP_PROGRESSED_SEND_UNVERIFIED")
        self.assertEqual(diagnostic.read_bytes(), previous_bytes)
        self.assertFalse(reused["original_submission_resend_authorized"])

    def test_auto_persist_terminal_source_log_sha_and_reject_tampering(self):
        name = self.begun()
        self.finish(name, "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY")
        self.log("[microgen-supervisor] OWNED_STAGE_TIMEOUT "
                 "NO_AUTOMATIC_RESUBMISSION SEND_STATUS_UNVERIFIED")
        before = sorted(self.trial.iterdir())
        first = persist_terminal_triage(trial_dir=self.trial, stage="figures")
        proof = self.trial / "figures_transport_triage.json"
        self.assertTrue(proof.is_file())
        self.assertEqual(len(list(self.trial.iterdir())), len(before) + 1)
        self.assertTrue(first["automatic_terminal_diagnosis"])
        self.assertEqual(first["model_requests_during_diagnosis"], 0)
        self.assertIsNotNone(first["terminal_log_sha256"])
        self.assertEqual(first["status"],
                         "OWNED_STAGE_TIMEOUT_WITHOUT_VERIFIED_BROWSER_SEND")
        second = persist_terminal_triage(trial_dir=self.trial, stage="figures")
        self.assertEqual(second["status"], "PRIOR_SHA_BOUND_TRIAGE_REUSED_NO_SEND")
        self.assertEqual(second["terminal_result_sha256"],
                         first["terminal_result_sha256"])
        self.log("[microgen-supervisor] OWNED_STAGE_TIMEOUT changed log")
        with self.assertRaisesRegex(ValueError, "diagnosis or evidence changed"):
            persist_terminal_triage(trial_dir=self.trial, stage="figures")
        self.assertFalse(first["automatic_resubmission_authorized"])
        self.assertFalse(first["provider_outage_proven"])

    def test_auto_persist_rejects_result_without_preceding_send_claim(self):
        _new_atomic(self.trial / "figures_attempt_result.json", {
            "schema_version": 1, "status": "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY",
            "original_source_sha256": self.sha,
            "student_publication_authorized": False,
        })
        with self.assertRaisesRegex(ValueError, "Result without pre-send"):
            persist_terminal_triage(trial_dir=self.trial, stage="figures")
        self.assertFalse((self.trial / "figures_transport_triage.json").exists())

    def test_supervisor_timeout_is_classified_without_fabricating_provider_outage(self):
        p = self.begun()
        self.finish(p, "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY")
        self.log("[microgen-supervisor] OWNED_STAGE_TIMEOUT "
                 "NO_AUTOMATIC_RESUBMISSION SEND_STATUS_UNVERIFIED")
        report = diagnose(trial_dir=self.trial)
        self.assertEqual(report["status"],
                         "OWNED_STAGE_TIMEOUT_WITHOUT_VERIFIED_BROWSER_SEND")
        self.assertTrue(report["owned_stage_supervisor_timeout_recorded"])
        self.assertTrue(report["unbuffered_child_output_evidence_present"])
        self.assertFalse(report["owned_browser_send_registered"])
        self.assertFalse(report["provider_outage_proven"])
        self.assertFalse(report["original_submission_resend_authorized"])

    def test_legacy_buffered_timeout_cannot_be_inferred_as_unbuffered(self):
        p = self.begun()
        self.finish(p, "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY")
        self.log("[microgen] loaded environment settings; no additional output")
        report = diagnose(trial_dir=self.trial)
        self.assertEqual(report["status"], "SOURCE_STAGE_HALTED_NO_REGISTERED_SEND")
        self.assertFalse(report["unbuffered_child_output_evidence_present"])
        self.assertFalse(report["provider_outage_proven"])

    def test_owned_browser_send_registered_without_accepted_output(self):
        p = self.begun()
        self.finish(p, "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY")
        self.log("[INFO] Gemini submission registered via new-user-turn+composer-cleared.")
        r = diagnose(trial_dir=self.trial)
        self.assertEqual(r["status"], "REGISTERED_BROWSER_SEND_BUT_NO_ACCEPTED_STAGE")
        self.assertTrue(r["owned_browser_send_registered"])
        self.assertFalse(r["original_submission_resend_authorized"])

    def test_suspicious_prompt_text_does_not_fake_send_proof(self):
        p = self.begun()
        self.finish(p, "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY")
        self.log("user payload: Gemini submission registered via new-user-turn+composer-cleared.")
        r = diagnose(trial_dir=self.trial)
        self.assertFalse(r["owned_browser_send_registered"])

    def test_started_but_no_result_is_no_resend(self):
        self.begun()
        r = diagnose(trial_dir=self.trial)
        self.assertEqual(r["status"],
                         "PRE_SEND_INTENT_WITH_NO_FINAL_RESULT_REVIEW_REQUIRED")
        self.assertFalse(r["original_submission_resend_authorized"])

    def test_no_started_receipt_is_not_a_success(self):
        r = diagnose(trial_dir=self.trial)
        self.assertEqual(r["status"], "NO_STORED_STAGE_SEND_INTENT")
        self.assertFalse(r["provider_outage_proven"])

    def test_successful_stage_receipt_is_not_full_lecture(self):
        p = self.begun()
        self.finish(p, "FIGURES_STAGE_RETURNED_SUCCESS_NOT_FULL_LECTURE")
        r = diagnose(trial_dir=self.trial)
        self.assertEqual(r["status"], "TECHNICAL_STAGE_RECEIPT_SUCCESS_NOT_FULL_LECTURE")
        self.assertTrue(r["stage_accepted_receipt_present"])
        self.assertFalse(r["student_publication_authorized"])

    def test_mismatched_original_sha_cannot_be_triaged_as_valid(self):
        p = self.begun()
        value = {
            "schema_version": 1, "status": "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY",
            "original_source_sha256": "b" * 64, "student_publication_authorized": False,
        }
        _new_atomic(self.trial / f"{p}_result.json", value)
        with self.assertRaisesRegex(ValueError, "original SHA"):
            diagnose(trial_dir=self.trial)

    def test_result_without_pre_send_ledger_refused(self):
        _new_atomic(self.trial / "figures_attempt_result.json", {
            "schema_version": 1, "status": "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY",
        })
        with self.assertRaisesRegex(ValueError, "Result without pre-send"):
            diagnose(trial_dir=self.trial)

    def test_slides_is_supported_without_figures_specific_assumptions(self):
        p = self.begun("slides")
        self.finish(p, "STAGE_TIMEOUT_UNKNOWN_PROVIDER_SEND_NO_RETRY", "slides")
        self.log("Selenium attached successfully.", "slides")
        r = diagnose(trial_dir=self.trial, stage="slides")
        self.assertEqual(r["stage"], "slides")
        self.assertEqual(r["status"], "BROWSER_SESSION_SEEN_SEND_UNVERIFIED")

    def test_api_does_not_infer_browser_send(self):
        p = "stage_narration"
        _new_atomic(self.trial / f"{p}_started.json", {
            "schema_version": 1, "stage": "narration",
            "source_sha256": self.sha, "communication_mode": "api",
            "paid_content_api_explicitly_authorized": True,
        })
        self.finish(p, "STAGE_PROCESS_ERROR_NO_RETRY", "narration")
        r = diagnose(trial_dir=self.trial, stage="narration")
        self.assertEqual(r["status"], "API_STAGE_TERMINAL_WITHOUT_VERIFIED_RESPONSE")
        self.assertFalse(r["owned_browser_send_registered"])
        self.assertFalse(r["original_submission_resend_authorized"])


    def test_current_vendor_registered_send_timing_is_shared_across_stages(self):
        # Real Dell-115 G2 figures 7.2 emitted this exact line structure.
        for stage in ("figures", "slides", "narration"):
            with self.subTest(stage=stage):
                prefix = self.begun(stage)
                status = ("FIGURES_STAGE_RETURNED_SUCCESS_NOT_FULL_LECTURE"
                          if stage == "figures" else
                          "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND")
                self.finish(prefix, status, stage=stage)
                line = ("[2026-11-10 13:33:14] [INFO] [TIMING] "
                        "attempt 1 verified send: 0.052s | registered=True\n")
                self.log(line * 3, stage=stage)
                report = diagnose(trial_dir=self.trial, stage=stage)
                self.assertTrue(report["owned_browser_send_registered"])
                self.assertEqual(report["registered_browser_send_count_in_stage_log"], 3)
                self.assertTrue(report["stage_accepted_receipt_present"])
                self.assertFalse(report["original_submission_resend_authorized"])

    def test_false_or_embedded_timing_marker_does_not_claim_model_send(self):
        prefix = self.begun()
        self.finish(prefix, "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY")
        self.log(
            "[2026-11-10 13:33:14] [INFO] [TIMING] "
            "attempt 1 verified send: 0.052s | registered=False\n"
            "[2026-11-10 13:33:14] [INFO] prompt snapshot: "
            "[TIMING] attempt 1 verified send: 0.052s | registered=True\n")
        result = diagnose(trial_dir=self.trial, stage="figures")
        self.assertFalse(result["owned_browser_send_registered"])
        self.assertEqual(result["registered_browser_send_count_in_stage_log"], 0)

    def test_prior_accepted_triage_is_sha_bound_reconciled_without_overwrite(self):
        import re
        prefix = self.begun()
        self.finish(prefix, "FIGURES_STAGE_RETURNED_SUCCESS_NOT_FULL_LECTURE")
        line = ("[2026-11-10 13:33:14] [INFO] [TIMING] "
                "attempt 1 verified send: 0.052s | registered=True\n")
        self.log(line * 3)
        # Simulate prior detector that missed the real vendor line, but did
        # preserve the exact SHA-bound result/log receipt.
        with patch("selenium_pipeline.windows_gemini_stage_transport_triage._SEND_PROOF",
                   re.compile(r"NONMATCHING_OLD_VENDOR_MARKER")):
            old = persist_terminal_triage(trial_dir=self.trial, stage="figures")
        self.assertFalse(old["owned_browser_send_registered"])
        proof = self.trial / "figures_transport_triage.json"
        original_bytes = proof.read_bytes()
        renewed = persist_terminal_triage(trial_dir=self.trial, stage="figures")
        self.assertEqual(renewed["status"], "PRIOR_SHA_BOUND_TRIAGE_REUSED_NO_SEND")
        self.assertTrue(renewed["new_readonly_owned_browser_send_registered"])
        self.assertEqual(renewed["new_readonly_registered_browser_send_count"], 3)
        self.assertEqual(proof.read_bytes(), original_bytes)
        self.assertFalse(renewed["original_submission_resend_authorized"])

if __name__ == "__main__":
    unittest.main()
