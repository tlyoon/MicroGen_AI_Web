"""Synthetic native Windows progression: never submit textbook or provider requests."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, _new_atomic,
)
from selenium_pipeline.windows_lecture_progression_coordinator import (
    inspect_progress, advance_one,
)
from selenium_pipeline.windows_original_stage_sequence import _EXPECTED_OUTPUTS


class WindowsSourceProgressionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        self.source_root = self.root / "protected_publisher"
        self.original_folder = self.source_root / "77" / "77.9"
        self.original_folder.mkdir(parents=True)
        self.original = self.original_folder / "source.pdf"
        self.original.write_bytes(b"%PDF-1.7\n" + b"new synthetic original only " * 40)
        self.sha = file_sha256(self.original)
        self.trial = self.root / "versioned_external_trial"
        self.trial.mkdir()
        self.lecture = self.trial / "source_tree" / "77" / "77.9"
        self.workspace = self.lecture / ".microgen_work"
        self.health = Mock(return_value={
            "status": "NO_PROVIDER_HALT",
            "new_generation_dispatch_allowed_by_health_policy": True,
        })
        self.check = Mock(return_value=True)

    def plan(self):
        return inspect_progress(
            source_root=self.source_root, section="77.9",
            trial_dir=self.trial, technical_check=self.check,
            provider_inspect=self.health)

    def figures_ready(self, success=True):
        self.lecture.mkdir(parents=True)
        (self.lecture / "source.pdf").write_bytes(self.original.read_bytes())
        self.workspace.mkdir()
        (self.workspace / "source.pdf").write_bytes(self.original.read_bytes())
        _new_atomic(self.trial / "fresh_trial_contract.json", {
            "schema_version": 1,
            "status": "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL",
            "source_path": str(self.original),
            "source_sha256": self.sha,
            "staged_source_path": str(self.lecture / "source.pdf"),
            "stage_goal": "figures", "paid_tts_authorized": False,
            "student_publication_authorized": False,
        })
        _new_atomic(self.trial / "figures_attempt_started.json", {
            "schema_version": 1, "source_sha256": self.sha,
            "stage": "figures", "single_provider_attempt_only": True})
        if success is not None:
            _new_atomic(self.trial / "figures_attempt_result.json", {
                "schema_version": 1, "original_source_sha256": self.sha,
                "staged_original_sha256": self.sha,
                "status": (
                    "FIGURES_STAGE_RETURNED_SUCCESS_NOT_FULL_LECTURE" if success
                    else "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY"),
                "student_publication_authorized": False,
                "new_video_rendered": False,
                "figure_stage_exit_code": 0 if success else None,
            })

    def stage_pass(self, stage: str):
        sequence = ("slides", "narration", "script_qa")
        i = sequence.index(stage)
        prev = (self.trial / "figures_attempt_result.json" if i == 0
                else self.trial / f"stage_{sequence[i-1]}_result.json")
        _new_atomic(self.trial / f"stage_{stage}_started.json", {
            "schema_version": 1,
            "stage": stage,
            "source_sha256": self.sha,
            "predecessor_receipt_sha256": file_sha256(prev),
            "single_attempt_no_provider_resend": True,
            "student_publication_authorized": False,
        })
        hashes = {}
        for name in _EXPECTED_OUTPUTS[stage]:
            artifact = self.lecture / name
            artifact.write_bytes(b"synthetic no real lecture " + name.encode())
            hashes[name] = file_sha256(artifact)
        _new_atomic(self.trial / f"stage_{stage}_result.json", {
            "schema_version": 1, "stage": stage,
            "source_sha256": self.sha,
            "predecessor_receipt_sha256": file_sha256(prev),
            "output_sha256": hashes,
            "status": "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND",
            "student_publication_authorized": False,
        })

    def test_no_receipts_read_only_plan_is_first_figures(self):
        state = self.plan()
        self.assertEqual(state["status"], "NEXT_SOURCE_STAGE_READY_EXPLICIT_ONE_SHOT_ONLY")
        self.assertEqual(state["next_stage"], "figures")
        self.assertEqual(state["source_stage_attempts_per_operator_invocation_limit"], 1)
        self.assertTrue(state["individual_model_send_count_must_be_verified_from_stage_log"])
        self.assertNotIn("model_requests_per_operator_invocation_limit", state)
        self.assertFalse(any(self.trial.iterdir()))
        self.assertFalse(state["new_model_or_tts_calls"])
        self.assertFalse(state["student_publication_authorized"])

    def test_progress_all_three_forward_stages_then_real_media_handoff(self):
        self.figures_ready()
        self.assertEqual(self.plan()["next_stage"], "slides")
        self.stage_pass("slides")
        self.assertEqual(self.plan()["next_stage"], "narration")
        self.stage_pass("narration")
        self.assertEqual(self.plan()["next_stage"], "script_qa")
        self.stage_pass("script_qa")
        state = self.plan()
        self.assertEqual(state["status"],
                         "REVIEWED_AUDIO_HANDOFF_REQUIRED_NO_AUTOMATIC_TTS")
        self.assertIsNone(state["next_stage"])
        self.assertEqual(state["slides_pdf_sha256"],
                         file_sha256(self.lecture / "slides.pdf"))
        self.assertEqual(Path(state["source"]), self.lecture / "source.pdf")
        self.assertEqual(Path(state["publisher_source"]), self.original)
        self.assertEqual(state["staged_source_sha256"], self.sha)
        self.assertFalse(state["reviewed_tts_or_video_generated"])
        self.assertFalse(state["student_publication_authorized"])
        self.assertEqual(len(state["required_following_steps"]), 6)

    def model_violation_log(self, *, stage: str):
        file = ("figures_stage_stdout.raw.log" if stage == "figures"
                else f"stage_{stage}_stdout.raw.log")
        (self.trial / file).write_text(
            "[microgen] browser UI model: flash\n"
            "[2026-11-11 11:43:23] [INFO] Selected Gemini tab via mode "
            "picker: Open mode picker, currently Flash-Lite (phase=development)\n"
            "[2026-11-11 11:43:27] [INFO] Gemini submission registered via "
            "new-user-turn+composer-cleared.\n", encoding="utf8")

    def test_prior_figures_success_with_wrong_owned_mode_cannot_advance_slides(self):
        self.figures_ready(success=True)
        self.model_violation_log(stage="figures")
        result=self.plan()
        self.assertEqual(result["status"],
                         "HALTED_FIGURES_WRONG_UI_MODEL_FAMILY_NO_RESEND")
        self.assertIsNone(result["next_stage"])
        self.assertFalse(result["original_figures_resubmission_authorized"])
        blocked=advance_one(
            source_root=self.source_root,section="77.9",
            trial_dir=self.trial,execute_next=True,
            technical_check=self.check,provider_inspect=self.health,
            stage_runner=Mock(side_effect=AssertionError("unapproved Send")))
        self.assertEqual(blocked["status"],
                         "HALTED_FIGURES_WRONG_UI_MODEL_FAMILY_NO_RESEND")
        self.assertFalse((self.trial / "stage_slides_started.json").exists())

    def test_prior_slides_success_with_wrong_owned_mode_cannot_advance_narration(self):
        self.figures_ready()
        self.stage_pass("slides")
        self.model_violation_log(stage="slides")
        result=self.plan()
        self.assertEqual(result["status"],
                         "HALTED_ACCEPTED_STAGE_WRONG_UI_MODEL_FAMILY_NO_RESEND")
        self.assertEqual(result["halted_stage"],"slides")
        self.assertFalse(result["original_stage_resubmission_authorized"])
        self.assertFalse((self.trial / "stage_narration_started.json").exists())

    def test_tampered_sha_locked_figures_log_is_never_trusted_for_progress(self):
        self.figures_ready()
        self.model_violation_log(stage="figures")
        from selenium_pipeline.windows_gemini_stage_transport_triage import (
            persist_terminal_triage)
        persist_terminal_triage(trial_dir=self.trial,stage="figures")
        original=(self.trial/"figures_stage_stdout.raw.log")
        original.write_text(original.read_text()+"log altered",encoding="utf8")
        with self.assertRaises(CampaignRecoveryBlocked):
            self.plan()

    def test_historical_figures_claim_without_result_quarantined(self):
        self.figures_ready(success=None)
        state = self.plan()
        self.assertEqual(state["status"], "HALTED_PRIOR_FIGURES_SEND_UNRESOLVED")
        self.assertIsNone(state["next_stage"])
        never = Mock(side_effect=AssertionError("resubmission"))
        advanced = advance_one(
            source_root=self.source_root, section="77.9",
            trial_dir=self.trial, execute_next=True,
            figure_runner=never,
            technical_check=self.check, provider_inspect=self.health)
        self.assertEqual(advanced["status"], "HALTED_PRIOR_FIGURES_SEND_UNRESOLVED")
        never.assert_not_called()

    def test_prior_failed_stage_quarantined_no_auto_retry(self):
        self.figures_ready(success=False)
        state = self.plan()
        self.assertEqual(state["status"], "HALTED_PREVIOUS_FIGURES_FAILED_NO_RESEND")
        self.assertIsNone(state["next_stage"])

    def test_real_exact_one_stage_dispatch_then_stops(self):
        self.figures_ready()
        def one_stage(**kwargs):
            for name in ("slides.pdf", "slides.tex"):
                (self.lecture / name).write_bytes(name.encode())
            return subprocess.CompletedProcess([], 0)
        runner = Mock(side_effect=one_stage)
        with patch("selenium_pipeline.runner.check_valid",
                   return_value=True):
            result = advance_one(
                source_root=self.source_root, section="77.9",
                trial_dir=self.trial, execute_next=True,
                stage_runner=runner, technical_check=self.check,
                provider_inspect=self.health)
        self.assertEqual(result["attempted_stage"], "slides")
        self.assertEqual(result["status"],
                         "EXACTLY_ONE_SOURCE_STAGE_ATTEMPT_FINISHED_NO_AUTO_CHAIN")
        self.assertEqual(result["attempted_stage_status"],
                         "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND")
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(self.plan()["next_stage"], "narration")
        self.assertFalse((self.trial / "stage_narration_started.json").exists())

    def test_figures_first_execution_never_auto_advances_slides(self):
        worker = Mock(return_value=subprocess.CompletedProcess([], 1, "", ""))
        result = advance_one(
            source_root=self.source_root, section="77.9",
            trial_dir=self.trial, execute_next=True,
            figure_runner=worker, provider_inspect=self.health)
        self.assertEqual(result["attempted_stage"], "figures")
        self.assertEqual(result["attempted_stage_status"],
                         "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY")
        self.assertEqual(
            result["source_stage_receipt"]["bounded_figure_stage_deadline_seconds"],
            600)
        self.assertEqual(worker.call_count, 1)
        self.assertFalse((self.trial / "stage_slides_started.json").exists())
        self.assertEqual(self.plan()["status"],
                         "HALTED_PREVIOUS_FIGURES_FAILED_NO_RESEND")

    def test_source_byte_tamper_invalidates_forward_stage(self):
        self.figures_ready()
        self.stage_pass("slides")
        (self.lecture / "slides.pdf").write_bytes(b"altered")
        with self.assertRaisesRegex(CampaignRecoveryBlocked, "byte identity changed"):
            self.plan()

    def test_changed_publisher_pdf_fails_before_any_generation(self):
        self.figures_ready()
        self.original.write_bytes(self.original.read_bytes() + b" modified")
        with self.assertRaises(CampaignRecoveryBlocked):
            self.plan()

    def test_accepted_technical_fail_does_not_start_next_stage(self):
        self.figures_ready()
        self.check.return_value = False
        state = self.plan()
        self.assertEqual(state["status"],
                         "HALTED_FIGURES_TECHNICAL_QA_INCOMPLETE")
        self.assertFalse((self.trial / "stage_slides_started.json").exists())

    def test_provider_cooldown_blocks_one_shot(self):
        self.health.return_value = {
            "status": "HALT_NEW_GEMINI_TASKS_API_CAPACITY_PRECAUTION",
            "new_generation_dispatch_allowed_by_health_policy": False,
        }
        never = Mock(side_effect=AssertionError("submitted during 503"))
        result = advance_one(
            source_root=self.source_root, section="77.9",
            trial_dir=self.trial, execute_next=True, figure_runner=never,
            provider_inspect=self.health)
        self.assertEqual(result["status"],
                         "HALTED_PROVIDER_CAPACITY_NO_NEW_SUBMISSION")
        never.assert_not_called()
        self.assertFalse((self.trial / "figures_attempt_started.json").exists())

    def test_api_requires_explicit_per_invocation_approval(self):
        never = Mock(side_effect=AssertionError("unapproved paid API"))
        with self.assertRaisesRegex(CampaignRecoveryBlocked, "API content generation"):
            advance_one(
                source_root=self.source_root, section="77.9",
                trial_dir=self.trial, execute_next=True,
                communication_mode="api", figure_runner=never,
                provider_inspect=self.health)
        never.assert_not_called()
        self.assertFalse((self.trial / "fresh_trial_contract.json").exists())

    def test_stage_started_without_result_cannot_be_submitted(self):
        self.figures_ready()
        _new_atomic(self.trial / "stage_slides_started.json", {
            "schema_version": 1, "stage": "slides",
            "source_sha256": self.sha,
            "predecessor_receipt_sha256": file_sha256(
                self.trial / "figures_attempt_result.json"),
            "single_attempt_no_provider_resend": True,
        })
        self.assertEqual(self.plan()["status"],
                         "HALTED_PRIOR_STAGE_SEND_UNRESOLVED")
        self.assertFalse((self.trial / "stage_narration_started.json").exists())

    def test_script_qa_does_not_authorize_automatic_tts_or_video(self):
        self.figures_ready()
        self.stage_pass("slides")
        self.stage_pass("narration")
        self.stage_pass("script_qa")
        result = advance_one(
            source_root=self.source_root, section="77.9",
            trial_dir=self.trial, execute_next=True,
            technical_check=self.check, provider_inspect=self.health,
            stage_runner=Mock(side_effect=AssertionError("No model")))
        self.assertEqual(result["status"],
                         "REVIEWED_AUDIO_HANDOFF_REQUIRED_NO_AUTOMATIC_TTS")
        self.assertFalse((self.lecture / "slide1.wav").exists())
        self.assertFalse((self.lecture / "movie.mp4").exists())


if __name__ == "__main__":
    unittest.main()
