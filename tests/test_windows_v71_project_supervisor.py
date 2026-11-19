"""v7.1 outer supervisor: observable dispatch, restart, anti-stall failures."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked,
)
from selenium_pipeline import windows_v71_project_supervisor as v71


class OuterSupervisorContinuityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.local = Path(temp.name)
        env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.local)})
        env.start()
        self.addCleanup(env.stop)
        self.repo = self.local / "isolated_worktree"
        self.repo.mkdir()
        self.head = "a" * 40
        self.real_dispatch = v71._dispatch
        fake_plan = {
            "status": "HISTORICAL_STACK_READ_ONLY_BATCH_PLAN_AVAILABLE",
            "local_worktree_clean": True,
            "exact_head_sha": self.head,
        }
        pre = patch.object(v71, "_verify_repo", return_value=None)
        pre.start()
        self.addCleanup(pre.stop)
        planner = patch.object(v71, "plan_stack", return_value=fake_plan)
        planner.start()
        self.addCleanup(planner.stop)
        ci = patch.object(v71, "_board_ci_verified", return_value=True)
        ci.start()
        self.addCleanup(ci.stop)

    def _install_fake_dispatcher(self, *, fail=()):
        self.calls = []
        def observe(repo, state, head, task, events):
            self.calls.append(task["id"])
            accepted = task["id"] not in fail
            outcome = {
                **v71._identity(repo, head, task["id"]),
                "status": (
                    "SUPERVISOR_STAGE_CHECK_ACCEPTED_REVIEW_PENDING" if accepted
                    else "SUPERVISOR_STAGE_QUARANTINED"),
                "accepted": accepted,
                "observed_pid": 1000 + len(self.calls),
                "stage_evidence": {"source_only": True},
            }
            v71._event(events, "next_task_dispatched", task["id"],
                       observed_pid=outcome["observed_pid"])
            v71._atomic_create(
                state / (task["id"] + ".result.json"), outcome)
            v71._event(events, "checkpoint_committed", task["id"],
                       accepted=accepted,
                       observed_pid=outcome["observed_pid"])
            return outcome
        x = patch.object(v71, "_dispatch", side_effect=observe)
        x.start()
        self.addCleanup(x.stop)

    def test_success_checkpoint_dispatches_downstream_with_pid(self):
        self._install_fake_dispatcher()
        result = v71.supervise(self.repo)
        self.assertEqual(self.calls,
                         [x["id"] for x in v71.STAGES])
        self.assertEqual(result["new_stage_dispatches_this_process"], 6)
        self.assertEqual(result["observable_dispatch_pids"],
                         [1001, 1002, 1003, 1004, 1005, 1006])
        self.assertEqual(result["next_not_started_stages"], [])
        count, hash_value = v71._validated_log(
            Path(result["events_file"]))
        self.assertGreaterEqual(count, 6)
        self.assertEqual(len(hash_value), 64)
        self.assertFalse(result["scientific_qa_approved"])
        self.assertFalse(result["student_publication_authorized"])
        self.assertFalse(result["persistent_supervisor_installed_and_running_after_exit"])

    def test_last_local_queue_automatically_hands_off_global_gap(self):
        self._install_fake_dispatcher()
        result = v71.supervise(self.repo, max_new_dispatches=2)
        self.assertEqual(self.calls, [
            "curated_offline_source_regressions",
            "global_historical_source_gap_inventory",
        ])
        self.assertEqual(result["new_stage_dispatches_this_process"], 2)
        self.assertIn("independent_readonly_release_board",
                      result["next_not_started_stages"])
        self.assertFalse(result["background_continuation_verified"])

    def test_quarantine_then_independent_stage_starts(self):
        self._install_fake_dispatcher(fail={"curated_offline_source_regressions"})
        result = v71.supervise(self.repo)
        self.assertEqual(self.calls, [
            "curated_offline_source_regressions",
            "global_historical_source_gap_inventory",
            "original_g2_readonly_claim_reconciliation",
            "recent_uncovered_historical_patch_checks",
            "original_g2_v1_synthetic_presend_inventory",
        ])
        self.assertIn("independent_readonly_release_board",
                      result["next_not_started_stages"])

    def test_process_restarts_after_saved_checkpoint_and_starts_next_once(self):
        self._install_fake_dispatcher()
        first = v71.supervise(self.repo, max_new_dispatches=1)
        self.assertEqual(first["new_stage_dispatches_this_process"], 1)
        second = v71.supervise(self.repo, max_new_dispatches=1)
        self.assertEqual(second["new_stage_dispatches_this_process"], 1)
        self.assertEqual(self.calls[:2], [
            "curated_offline_source_regressions",
            "global_historical_source_gap_inventory",
        ])
        third = v71.supervise(self.repo, max_new_dispatches=1)
        self.assertEqual(third["new_stage_dispatches_this_process"], 1)
        fourth = v71.supervise(self.repo, max_new_dispatches=1)
        self.assertEqual(fourth["new_stage_dispatches_this_process"], 1)
        fifth = v71.supervise(self.repo, max_new_dispatches=1)
        self.assertEqual(fifth["new_stage_dispatches_this_process"], 1)
        sixth = v71.supervise(self.repo, max_new_dispatches=1)
        self.assertEqual(sixth["new_stage_dispatches_this_process"], 1)
        seventh = v71.supervise(self.repo)
        self.assertEqual(seventh["new_stage_dispatches_this_process"], 0)
        self.assertEqual(len(self.calls), 6)

    def test_uncertain_claim_does_not_replay_dispatch_and_fans_out(self):
        self._install_fake_dispatcher()
        state = v71._state_dir(self.repo, self.head)
        first = v71.STAGES[0]
        v71._atomic_create(state / (first["id"] + ".intent.json"),
                           {**v71._identity(self.repo, self.head, first["id"]),
                            "status": "SUPERVISOR_STAGE_DISPATCH_INTENT"})
        # The *actual* dispatcher sees an uncertain persisted claim and
        # quarantines it without launching an external child.
        original = self.real_dispatch
        def delegate(repo, state, head, task, events):
            return (original(repo, state, head, task, events)
                    if task["id"] == first["id"] else
                    self._fake_remaining(repo, state, head, task, events))
        with patch.object(v71, "_dispatch", side_effect=delegate):
            result = v71.supervise(self.repo, max_new_dispatches=2)
        self.assertEqual(result["new_stage_dispatches_this_process"], 2)
        self.assertIn("global_historical_source_gap_inventory", self.calls)
        self.assertEqual(
            v71._verified_result(state, self.repo, self.head, first)["status"],
            "SUPERVISOR_EXTERNAL_DISPATCH_UNCERTAIN",
        )

    def _fake_remaining(self, repo, state, head, task, events):
        self.calls.append(task["id"])
        data = {**v71._identity(repo, head, task["id"]),
                "status": "SUPERVISOR_STAGE_CHECK_ACCEPTED_REVIEW_PENDING",
                "accepted": True, "observed_pid": 4444,
                "stage_evidence": {"read_only": True}}
        v71._event(events, "next_task_dispatched", task["id"],
                   observed_pid=4444)
        v71._atomic_create(state / (task["id"] + ".result.json"), data)
        v71._event(events, "checkpoint_committed", task["id"],
                   accepted=True, observed_pid=4444)
        return data

    def test_true_dispatch_invokes_child_launcher_and_records_pid(self):
        state = v71._state_dir(self.repo, self.head)
        events = state / "events.jsonl"
        task = v71.STAGES[1]
        class Child:
            pid = 9123
            def wait(self, timeout):
                v71._atomic_create(
                    state / (task["id"] + ".worker-result.json"),
                    {
                        "schema_version": v71.SCHEMA,
                        "status": "WORKER_SOURCE_STAGE_RECORDED",
                        "stage_id": task["id"],
                        "worker_source_policy_sha256": v71._policy_hash(),
                        "outcome": {
                            "accepted": True,
                            "status": "PROJECT_SOURCE_GAP_CATALOGUED_NOT_APPROVED",
                        },
                        "student_publication_authorized": False,
                    },
                )
                return 0
        launcher = lambda command, **kwargs: Child()
        result = v71._dispatch(self.repo, state, self.head, task, events,
                               launcher=launcher)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["observed_pid"], 9123)
        log = (state / "events.jsonl").read_text(encoding="utf8")
        self.assertIn("next_task_dispatched", log)
        self.assertIn("9123", log)
        self.assertIn("checkpoint_committed", log)

    def test_durable_event_chain_tampering_fails_closed(self):
        self._install_fake_dispatcher()
        first = v71.supervise(self.repo, max_new_dispatches=1)
        p = Path(first["events_file"])
        p.write_text(p.read_text().replace('"observed_pid":1001',
                                           '"observed_pid":9999'), encoding="utf8")
        with self.assertRaises(CampaignRecoveryBlocked):
            v71.supervise(self.repo)

    def test_scheduled_source_only_skips_browser_owned_model_stage(self):
        self._install_fake_dispatcher()
        with patch.dict(os.environ,
                        {"MICROGEN_V71_BACKGROUND_SOURCE_ONLY": "1"}):
            result = v71.supervise(self.repo)
        self.assertEqual(result["new_stage_dispatches_this_process"], 5)
        self.assertNotIn(
            "original_g2_v1_synthetic_presend_inventory", self.calls)
        self.assertIn(
            "original_g2_v1_synthetic_presend_inventory",
            result["next_not_started_stages"])
        with patch.dict(os.environ,
                        {"MICROGEN_V71_BACKGROUND_SOURCE_ONLY": "1"}):
            second = v71.supervise(self.repo)
        self.assertEqual(second["new_stage_dispatches_this_process"], 0)
        interactive = v71.supervise(self.repo)
        self.assertEqual(interactive["new_stage_dispatches_this_process"], 1)
        self.assertEqual(self.calls.count(
            "original_g2_v1_synthetic_presend_inventory"), 1)
        again = v71.supervise(self.repo)
        self.assertEqual(again["new_stage_dispatches_this_process"], 0)

    def test_no_imaginary_persistent_runner_claim(self):
        self._install_fake_dispatcher()
        outcome = v71.supervise(self.repo, max_new_dispatches=1)
        self.assertFalse(outcome["persistent_supervisor_installed_and_running_after_exit"])
        self.assertFalse(outcome["background_continuation_verified"])
        self.assertIn("global_historical_source_gap_inventory",
                      outcome["next_not_started_stages"])

    def test_missing_hosted_ci_keeps_board_not_started(self):
        self._install_fake_dispatcher()
        with patch.object(v71, "_board_ci_verified", return_value=False):
            result = v71.supervise(self.repo)
        self.assertEqual(self.calls, [
            "curated_offline_source_regressions",
            "global_historical_source_gap_inventory",
            "original_g2_readonly_claim_reconciliation",
            "recent_uncovered_historical_patch_checks",
            "original_g2_v1_synthetic_presend_inventory",
        ])
        self.assertIn("independent_readonly_release_board",
                      result["next_not_started_stages"])
        self.assertFalse(result["background_continuation_verified"])
        self.assertIn("mandatory_stop",
                      Path(result["events_file"]).read_text())

    def test_new_sixth_stage_inspects_current_v1_model_without_send(self):
        from types import SimpleNamespace
        checkpoint = self.local / "MicroGen_AI_Web_Checkpoints"
        (checkpoint / "G2_20261115_SERWAY13_AI_ACADEMIC_REVIEW").mkdir(
            parents=True)
        old={"status":"DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED",
             "new_provider_requests":0,"new_source_review_send_allowed":False}
        preflight={"status":"V1_SYNTHETIC_PDF_PRESEND_UNAVAILABLE_NO_CLAIM",
                   "failure_phase":"GEMINI_MODEL_PICKER_NOT_READY",
                   "new_provider_requests":0,
                   "new_source_review_send_allowed":False}
        with patch.object(v71.subprocess,"run",return_value=SimpleNamespace(
                stdout=self.head+"\\n",returncode=0)):
            with patch(
                "selenium_pipeline.academic_dual_pdf_capability.existing_outcome",
                return_value=old) as previous:
                with patch(
                    "selenium_pipeline.academic_dual_pdf_capability._production_probe_presend_ready",
                    return_value=preflight) as inspected:
                    result=v71._worker_stage(
                        "original_g2_v1_synthetic_presend_inventory",
                        self.repo)
        self.assertTrue(result["accepted"])
        self.assertFalse(result["fresh_flash_model_available"])
        self.assertEqual(result["previous_claim_status"],
                         "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED")
        self.assertFalse(result["new_diagnostic_claim"])
        self.assertFalse(result["original_source_request_replayed"])
        self.assertFalse(result["academic_scientific_acceptance"])
        self.assertEqual(previous.call_count,2)
        inspected.assert_called_once_with("flash")

    def test_new_sixth_stage_rejects_forged_provider_send_result(self):
        from types import SimpleNamespace
        cp=self.local/"MicroGen_AI_Web_Checkpoints"
        (cp/"G2_20261115_SERWAY13_AI_ACADEMIC_REVIEW").mkdir(parents=True)
        invalid={"status":"EXACT_SYNTHETIC_PDF_MODEL_PRESEND_VERIFIED_NO_SEND",
                 "new_provider_requests":1,
                 "new_source_review_send_allowed":False}
        with patch.object(v71.subprocess,"run",return_value=SimpleNamespace(
                stdout=self.head+"\\n",returncode=0)):
            with patch(
                "selenium_pipeline.academic_dual_pdf_capability.existing_outcome",
                return_value=None):
                with patch(
                    "selenium_pipeline.academic_dual_pdf_capability._production_probe_presend_ready",
                    return_value=invalid):
                    with self.assertRaises(CampaignRecoveryBlocked):
                        v71._worker_stage(
                            "original_g2_v1_synthetic_presend_inventory",
                            self.repo)

    def test_v1_sixth_stage_registry_disabled_blocks_before_model_check(self):
        from types import SimpleNamespace
        cp=self.local/"MicroGen_AI_Web_Checkpoints"
        (cp/"G2_20261115_SERWAY13_AI_ACADEMIC_REVIEW").mkdir(parents=True)
        with patch.object(v71.subprocess,"run",return_value=SimpleNamespace(
                stdout=self.head+"\\n",returncode=0)):
            with patch(
                    "selenium_pipeline.recovery_registry.lookup_mechanism",
                    return_value=None):
                with patch(
                    "selenium_pipeline.academic_dual_pdf_capability._production_probe_presend_ready"
                ) as inspected:
                    with self.assertRaisesRegex(
                            CampaignRecoveryBlocked,
                            "no-Send handoff missing"):
                        v71._worker_stage(
                            "original_g2_v1_synthetic_presend_inventory",
                            self.repo)
                    inspected.assert_not_called()

    def test_g2_reconciliation_protects_original_provider_no_resend(self):
        from types import SimpleNamespace
        checkpoint = self.local / "MicroGen_AI_Web_Checkpoints"
        source = (checkpoint / "auto_captionless_6528f3cfd9929c3706de"
                  / "source_tree" / "1" / "1.3")
        queue = checkpoint / "G2_20261115_SERWAY13_AI_ACADEMIC_REVIEW"
        source.mkdir(parents=True)
        queue.mkdir()
        report = {
            "status": "READONLY_G2_FORWARD_RECOVERY_PLAN",
            "new_provider_requests": False,
            "new_paid_tts_dispatched": False,
            "current_report": {
                "original_source_sha256":
                    "181f0f361809d90daf72fce1bf50bcf2b88fbf37fc59ed181411266b53cb5ae8",
                "two_pass_ai_source_agreed_segments": 20,
                "pending_or_disputed_segments": 65,
                "expected_original_utterances": 85,
                "student_publication_authorized": False,
                "G2_academic_scientific_acceptance_claimed": False,
                "next_safe_academic_action": {
                    "status": "DEFERRED_SYNTHETIC_PDF_CAPABILITY_EXHAUSTED_NO_RESEND"
                },
            },
        }
        with patch.object(v71.subprocess, "run",
                          return_value=SimpleNamespace(stdout=self.head + "\n")):
            with patch("selenium_pipeline.g2_forward_recovery_engine.run",
                       return_value=report) as runner:
                result = v71._worker_stage(
                    "original_g2_readonly_claim_reconciliation", self.repo)
                self.assertTrue(result["accepted"])
                self.assertFalse(result["g2_academic_acceptance"])
                self.assertEqual(result["pending_or_disputed"], 65)
                self.assertFalse(result["original_claim_replayed"])
                self.assertFalse(result["new_model_or_paid_requests"])
                kwargs = runner.call_args.kwargs
                self.assertIs(kwargs["execute"], False)
                self.assertIs(kwargs["auto_media"], False)
                self.assertEqual(kwargs["max_cycles"], 1)
            with patch("selenium_pipeline.g2_forward_recovery_engine.run",
                       return_value={**report, "new_provider_requests": True}):
                with self.assertRaises(CampaignRecoveryBlocked):
                    v71._worker_stage(
                        "original_g2_readonly_claim_reconciliation", self.repo)
            with patch("selenium_pipeline.g2_forward_recovery_engine.run",
                       return_value={**report, "current_report": {
                           **report["current_report"],
                           "G2_academic_scientific_acceptance_claimed": True
                       }}):
                with self.assertRaises(CampaignRecoveryBlocked):
                    v71._worker_stage(
                        "original_g2_readonly_claim_reconciliation", self.repo)
            with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                       return_value=None):
                with self.assertRaisesRegex(
                        CampaignRecoveryBlocked,
                        "G2 no-Send handoff recovery missing"):
                    v71._worker_stage(
                        "original_g2_readonly_claim_reconciliation", self.repo)

    def test_new_history_patch_window_dispatches_existing_source_checker(self):
        from types import SimpleNamespace
        from selenium_pipeline.windows_offline_development_forward_controller import TASKS
        self.assertEqual(len(TASKS), 48)
        with patch.object(v71.subprocess, "run",
                          return_value=SimpleNamespace(stdout=self.head + "\n")):
            with patch.object(v71, "plan_stack", return_value={
                "status": "HISTORICAL_STACK_READ_ONLY_BATCH_PLAN_AVAILABLE",
                "local_worktree_clean": True, "exact_head_sha": self.head,
                "batches": [{"batch_number": i} for i in range(1, 50)]}):
                good = {
                    "status": "OFFLINE_BATCH_PATCH_CHECKS_COMPLETE_CODE_REVIEW_PENDING",
                    "exact_head_sha": self.head,
                    "first_batch": 49, "last_batch": 49,
                    "batch_count_completed": 1,
                    "commits_checked_or_reused": 6,
                    "quarantined_batch_numbers": [],
                    "model_or_tts_calls": 0,
                    "semantic_code_review_completed": False,
                    "automatic_merge_authorized": False,
                    "student_publication_authorized": False}
                with patch(
                    "selenium_pipeline.windows_historical_stack_batch_executor.execute_batches",
                    return_value=good) as executor:
                    result = v71._worker_stage(
                        "recent_uncovered_historical_patch_checks", self.repo)
                executor.assert_called_once_with(
                    repo=self.repo, first_batch=49, last_batch=49)
                self.assertTrue(result["accepted"])
                self.assertEqual(result["reviewed_source_windows"], [49])
                self.assertEqual(result["commits_checked_or_reused"], 6)
                self.assertFalse(result["semantic_code_review_completed"])
                self.assertFalse(result["student_publication_authorized"])
                self.assertEqual(result["model_or_tts_calls"], 0)
                with patch(
                    "selenium_pipeline.windows_historical_stack_batch_executor.execute_batches",
                    return_value={**good, "model_or_tts_calls": 1}):
                    with self.assertRaises(CampaignRecoveryBlocked):
                        v71._worker_stage(
                            "recent_uncovered_historical_patch_checks", self.repo)

    def test_source_history_gap_absent_needs_no_unsafe_git_patch_execution(self):
        from types import SimpleNamespace
        with patch.object(v71.subprocess, "run",
                          return_value=SimpleNamespace(stdout=self.head + "\n")):
            with patch.object(v71, "plan_stack", return_value={
                "status": "HISTORICAL_STACK_READ_ONLY_BATCH_PLAN_AVAILABLE",
                "local_worktree_clean": True, "exact_head_sha": self.head,
                "batches": [{"batch_number": i} for i in range(1, 49)]}):
                with patch(
                    "selenium_pipeline.windows_historical_stack_batch_executor.execute_batches",
                    side_effect=AssertionError("No uncurated window exists")):
                    result = v71._worker_stage(
                        "recent_uncovered_historical_patch_checks", self.repo)
                self.assertTrue(result["accepted"])
                self.assertEqual(result["reviewed_source_windows"], [])
                self.assertFalse(result["semantic_code_review_completed"])

    def test_unbounded_or_unregistered_history_gap_never_runs_checks(self):
        from types import SimpleNamespace
        with patch.object(v71.subprocess, "run",
                          return_value=SimpleNamespace(stdout=self.head + "\n")):
            source = {"status": "HISTORICAL_STACK_READ_ONLY_BATCH_PLAN_AVAILABLE",
                      "local_worktree_clean": True, "exact_head_sha": self.head,
                      "batches": [{"batch_number": i} for i in range(1, 54)]}
            with patch.object(v71, "plan_stack", return_value=source):
                with patch(
                    "selenium_pipeline.windows_historical_stack_batch_executor.execute_batches",
                    side_effect=AssertionError("Unbounded scan dispatched")):
                    with self.assertRaisesRegex(
                            CampaignRecoveryBlocked, "finite review bound"):
                        v71._worker_stage(
                            "recent_uncovered_historical_patch_checks", self.repo)
            with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                       return_value=None):
                with self.assertRaisesRegex(
                        CampaignRecoveryBlocked, "uncovered history handoff"):
                    v71._worker_stage(
                        "recent_uncovered_historical_patch_checks", self.repo)

    def test_normal_global_cli_default_includes_fifth_registered_stage(self):
        from selenium_pipeline.windows_historical_stack_batch_plan import main
        sentinel = {
            "status": "V71_GLOBAL_HANDOFF_VERIFIED_REVIEW_PENDING",
            "new_stage_dispatches_this_process": len(v71.STAGES),
            "next_not_started_stages": [],
            "student_publication_authorized": False,
        }
        buffer = io.StringIO()
        with patch.object(v71, "supervise", return_value=sentinel) as invoked:
            with redirect_stdout(buffer):
                code = main(["--repo", str(self.repo),
                             "--supervise-project-v71"])
        self.assertEqual(code, 0)
        invoked.assert_called_once_with(
            self.repo, max_new_dispatches=len(v71.STAGES))
        self.assertEqual(len(v71.STAGES), 6)

    def test_worker_cli_rejects_foreign_receipt_path(self):
        from selenium_pipeline.windows_v71_project_supervisor import main
        bad = self.local / "outside" / "global_historical_source_gap_inventory.worker-result.json"
        bad.parent.mkdir()
        output = io.StringIO()
        from types import SimpleNamespace
        with patch.object(v71.subprocess, "run", return_value=SimpleNamespace(
                stdout=self.head + "\\n", returncode=0)), redirect_stdout(output):
            code = main(["--repo", str(self.repo),
                         "--worker-stage", "global_historical_source_gap_inventory",
                         "--worker-result", str(bad)])
        self.assertEqual(code, 2)
        self.assertIn("V71_GLOBAL_SUPERVISOR_BLOCKED", output.getvalue())

    def test_registry_retirement_refuses_unsafe_supervision(self):
        with patch(
            "selenium_pipeline.recovery_registry.lookup_mechanism",
            return_value=None):
            with self.assertRaises(CampaignRecoveryBlocked):
                v71.supervise(self.repo)

    def test_normal_historical_cli_routes_to_real_supervisor(self):
        from selenium_pipeline.windows_historical_stack_batch_plan import main
        sentinel = {
            "status": "V71_GLOBAL_HANDOFF_VERIFIED_REVIEW_PENDING",
            "new_stage_dispatches_this_process": 2,
            "next_not_started_stages": [],
            "student_publication_authorized": False,
        }
        buf = io.StringIO()
        with patch.object(v71, "supervise", return_value=sentinel) as invoked:
            with redirect_stdout(buf):
                rc = main(["--repo", str(self.repo),
                           "--supervise-project-v71",
                           "--max-v71-new-dispatches", "2"])
        self.assertEqual(rc, 0)
        invoked.assert_called_once_with(self.repo, max_new_dispatches=2)
        self.assertIn("V71_GLOBAL_HANDOFF_VERIFIED", buf.getvalue())

    def test_normal_cli_rejects_ambiguous_supervisor_and_patch_mode(self):
        from selenium_pipeline.windows_historical_stack_batch_plan import main
        buf = io.StringIO()
        with patch.object(v71, "supervise",
                          side_effect=AssertionError("unsafe mode executed")):
            with redirect_stdout(buf):
                rc = main(["--repo", str(self.repo),
                           "--supervise-project-v71",
                           "--execute-offline-history-checks"])
        self.assertEqual(rc, 2)
        self.assertIn("HISTORICAL_STACK_BATCH_REVIEW_REJECTED",
                      buf.getvalue())


    def test_real_curated_launcher_receives_registered_long_bounded_wait(self):
        from selenium_pipeline.recovery_registry import lookup_mechanism
        task = v71.STAGES[0]
        self.assertGreater(task["timeout"], 900)
        self.assertLessEqual(task["timeout"], 3600)
        self.assertEqual(lookup_mechanism(
            "global_checkpoint_handoff", v71.LONG_QUEUE_TIMEOUT_SIGNATURE),
            v71.LONG_QUEUE_TIMEOUT_MECHANISM)
        state = v71._state_dir(self.repo, self.head)
        class SlowButCompletes:
            pid = 9129
            def wait(child, timeout):
                self.assertEqual(timeout, 2400)
                v71._atomic_create(
                    state / (task["id"] + ".worker-result.json"),
                    {
                        "schema_version": v71.SCHEMA,
                        "status": "WORKER_SOURCE_STAGE_RECORDED",
                        "stage_id": task["id"],
                        "worker_source_policy_sha256": v71._policy_hash(),
                        "outcome": {"accepted": True,
                                    "status": "OFFLINE_QUEUE_CHECKED",
                                    "selected_tasks": 48, "passed": 48},
                        "student_publication_authorized": False,
                    })
                return 0
        result = self.real_dispatch(
            self.repo, state, self.head, task, state / "events.jsonl",
            launcher=lambda command, **kwargs: SlowButCompletes())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["observed_pid"], 9129)
        events=(state / "events.jsonl").read_text()
        self.assertIn("next_task_dispatched", events)
        self.assertIn("checkpoint_committed", events)

    def test_curated_timeout_cleans_descendants_and_fans_out(self):
        self.calls = []
        class StalledChild:
            pid = 9228
            def wait(self, timeout):
                raise subprocess.TimeoutExpired("offline-curated", timeout)
        def select(repo, state, head, task, events):
            if task["id"] == "curated_offline_source_regressions":
                return self.real_dispatch(
                    repo, state, head, task, events,
                    launcher=lambda command, **kwargs: StalledChild())
            return self._fake_remaining(repo, state, head, task, events)
        with patch.object(v71, "kill_descendants") as cleanup:
            with patch.object(v71, "_dispatch", side_effect=select):
                report = v71.supervise(self.repo)
        cleanup.assert_called_once()
        self.assertEqual(report["new_stage_dispatches_this_process"], 5)
        state=v71._state_dir(self.repo, self.head)
        old=v71._verified_result(state,self.repo,self.head,v71.STAGES[0])
        self.assertFalse(old["accepted"])
        self.assertEqual(old["stage_evidence"]["exit_code"], 124)
        self.assertIn("global_historical_source_gap_inventory",self.calls)
        self.assertIn("original_g2_readonly_claim_reconciliation",self.calls)
        self.assertIn("independent_readonly_release_board",
                      report["next_not_started_stages"])

    def test_long_queue_timeout_registry_disabled_fails_before_child_claim(self):
        state=v71._state_dir(self.repo,self.head)
        events=state/"events.jsonl"
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with self.assertRaisesRegex(
                    CampaignRecoveryBlocked,"source-queue watchdog"):
                self.real_dispatch(
                    self.repo,state,self.head,v71.STAGES[0],events,
                    launcher=lambda *args,**kwargs:
                        self.fail("Unregistered worker must not be launched"))
        self.assertFalse((state/(v71.STAGES[0]["id"]+".intent.json")).exists())

    def test_old_premature_timeout_is_not_an_admissible_curated_policy(self):
        old={**v71.STAGES[0],"timeout":900}
        state=v71._state_dir(self.repo,self.head)
        with self.assertRaisesRegex(
                CampaignRecoveryBlocked,"source-queue watchdog"):
            self.real_dispatch(
                self.repo,state,self.head,old,state/"events.jsonl",
                launcher=lambda *args,**kwargs:
                    self.fail("900-second worker must fail before launch"))


if __name__ == "__main__":
    unittest.main()
