"""Synthetic fail-closed controller tests with source-free offline fake tasks."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked,
)
from selenium_pipeline import windows_offline_development_forward_controller as dev


def _accepted(_repo, _modules):
    return {
        "status": "OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING",
        "success": True, "exit_code": 0, "reported_test_count": 2,
        "reported_skip_count": 0, "captured_output_sha256": "1" * 64,
    }


class OfflineDevelopmentAutoforwardTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.local = Path(tmp.name)
        env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.local)})
        env.start()
        self.addCleanup(env.stop)
        self.repo = self.local / "isolated_dev"
        self.repo.mkdir()
        self.head = "9" * 40
        paths = set(name for task in dev.TASKS
                    for name in task["modules"])
        for name in paths:
            source = self.repo / (name.replace(".", "/") + ".py")
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("# source-verified offline test\n")
        self.plan = {
            "status": "HISTORICAL_STACK_READ_ONLY_BATCH_PLAN_AVAILABLE",
            "local_worktree_clean": True,
            "commits_behind_origin_main": 0,
            "exact_head_sha": self.head,
            "batches": [],
        }
        for i in range(1, 49):
            t = next((task for task in dev.TASKS
                      if task["batch"] == i), None)
            first = ((t["first_commit_prefix"] if t else "f" * 7)
                     + "a" * 33)[:40]
            end = ((t["last_commit_prefix"] if t else "e" * 7)
                   + "b" * 33)[:40]
            if t and t["last_commit_prefix"] == "<HISTORICAL_ANCHOR_MEMBER>":
                end = self.head
            self.plan["batches"].append({
                "batch_number": i, "first_commit_sha": first,
                "end_inclusive_sha": end,
                "all_touched_paths_sha256": "c" * 64,
            })
        pre = patch.object(dev, "_verify_repo", return_value=None)
        pre.start()
        self.addCleanup(pre.stop)
        plan = patch.object(dev, "plan_stack", return_value=self.plan)
        plan.start()
        self.addCleanup(plan.stop)
        def check_history(*, repo, first_batch, last_batch):
            self.assertEqual(first_batch, last_batch)
            self.assertIn(first_batch, tuple(t["batch"] for t in dev.TASKS))
            return {
                "exact_head_sha": self.head,
                "batch_count_completed": 1,
                "student_publication_authorized": False,
                "quarantined_batch_numbers": [],
            }
        hist = patch.object(dev, "execute_batches",
                            side_effect=check_history)
        hist.start()
        self.addCleanup(hist.stop)
        self.real_historical_anchor_check = dev._require_historical_anchor
        anchor = patch.object(dev, "_require_historical_anchor", return_value=None)
        anchor.start()
        self.addCleanup(anchor.stop)

    def test_three_independent_milestones_advance_without_confirmation(self):
        calls = []
        def observed(repo, modules):
            calls.append(modules)
            return _accepted(repo, modules)
        first = dev.advance_offline(repo=self.repo, max_steps=3, runner=observed)
        self.assertEqual(first["tasks_executed_or_reused"], 3)
        self.assertEqual(first["new_tasks_completed_this_process"], 3)
        self.assertEqual(first["offline_source_regression_pass_count"], 3)
        self.assertEqual(len(calls), 3)
        self.assertTrue(first["automatic_forward_on_verified_task"])
        self.assertFalse(first["automatic_merge_authorized"])
        self.assertFalse(first["historical_semantic_review_completed"])
        self.assertFalse(first["student_publication_authorized"])
        # Next process reuses the first three receipts and automatically
        # advances the next three independent milestones without replaying.
        again = dev.advance_offline(
            repo=self.repo, max_steps=3, runner=observed,
        )
        self.assertEqual(again["new_tasks_completed_this_process"], 3)
        self.assertEqual(again["tasks_executed_or_reused"], 6)
        self.assertEqual(len(calls), 6)
        self.assertTrue(all(x["receipt_reused_after_restart"]
                            for x in again["tasks"][:3]))

    def test_one_step_per_invocation_resumes_to_next_pending(self):
        seen = []
        def observed(repo, modules):
            seen.append(modules)
            return _accepted(repo, modules)
        for expected in range(1, 4):
            r = dev.advance_offline(
                repo=self.repo, max_steps=1, runner=observed)
            self.assertEqual(r["new_tasks_completed_this_process"], 1)
            self.assertEqual(len(seen), expected)
            self.assertEqual(r["tasks_executed_or_reused"], expected)

    def test_abrupt_offline_worker_failure_resumes_claim_with_finite_retry(self):
        def simulated_process_exit(_repo, _modules):
            raise KeyboardInterrupt("Simulated process terminated after claim")
        with self.assertRaises(KeyboardInterrupt):
            dev.advance_offline(
                repo=self.repo, max_steps=1, runner=simulated_process_exit)
        resumed = dev.advance_offline(
            repo=self.repo, max_steps=1, runner=_accepted)
        self.assertEqual(resumed["new_tasks_completed_this_process"], 1)
        self.assertTrue(resumed["tasks"][0]["prior_crash_attempt_resumed"])
        self.assertEqual(resumed["tasks"][0]["attempt_count"], 2)
        self.assertFalse(resumed["tasks"][0]["receipt_reused_after_restart"])

    def test_exhausted_interrupted_task_quarantines_and_moves_forward(self):
        def died(_repo, _modules):
            raise KeyboardInterrupt("Synthetic two-process crash")
        for _ in range(2):
            with self.assertRaises(KeyboardInterrupt):
                dev.advance_offline(
                    repo=self.repo, max_steps=1, runner=died)
        result = dev.advance_offline(
            repo=self.repo, max_steps=3, runner=_accepted)
        self.assertEqual(result["tasks"][0]["status"],
                         "OFFLINE_SOURCE_REGRESSION_EXHAUSTED_QUARANTINED")
        self.assertFalse(result["tasks"][0]["success"])
        # The quarantined stage is not retried and the independent next batch
        # advances without an operator acknowledgement.
        self.assertEqual(result["new_tasks_completed_this_process"], 3)
        self.assertEqual(result["tasks_executed_or_reused"], 3)
        self.assertEqual(result["offline_source_regression_pass_count"], 2)

    def test_saved_result_corruption_blocks_reuse(self):
        r = dev.advance_offline(
            repo=self.repo, max_steps=1, runner=_accepted)
        saved = Path(r["tasks"][0]["result_receipt_path"])
        saved.write_text('{"status":"PASS","semantic_review":true}')
        with self.assertRaises(CampaignRecoveryBlocked):
            dev.advance_offline(
                repo=self.repo, runner=lambda *_:
                self.fail("Corrupt result improperly reused"))

    def test_source_modified_after_intent_cannot_resume(self):
        def died(_repo, _modules):
            raise KeyboardInterrupt("Claim consumed")
        with self.assertRaises(KeyboardInterrupt):
            dev.advance_offline(repo=self.repo, max_steps=1, runner=died)
        source = self.repo / (dev.TASKS[0]["modules"][0].replace(
            ".", "/") + ".py")
        source.write_text("# changed supposedly immutable test source\n")
        with self.assertRaises(CampaignRecoveryBlocked):
            dev.advance_offline(repo=self.repo, max_steps=1, runner=_accepted)

    def test_git_root_containing_dotdot_is_canonicalized_for_source_boundary(self):
        # Hosted Windows CI temp paths may be exposed via short-path aliases.
        # A lexical containment check rejects legitimate local test source
        # even when both paths resolve to the SAME verified repository.
        nested = self.repo / "source_alias"
        nested.mkdir()
        noncanonical = nested / ".."
        source = dev._source_modules(noncanonical, dev.TASKS[0])
        self.assertEqual(len(source), len(dev.TASKS[0]["modules"]))
        self.assertTrue(all(len(x["source_sha256"]) == 64 for x in source))

    def test_forged_batch_membership_stops_before_test(self):
        self.plan["batches"][18]["first_commit_sha"] = "0" * 40
        with self.assertRaises(CampaignRecoveryBlocked):
            dev.advance_offline(
                repo=self.repo, runner=lambda *_:
                self.fail("Forged source range caused execution"))

    def test_disabled_registry_blocks_controller(self):
        with patch(
            "selenium_pipeline.recovery_registry.lookup_mechanism",
            return_value=None,
        ):
            with self.assertRaises(CampaignRecoveryBlocked):
                dev.advance_offline(
                    repo=self.repo, runner=lambda *_:
                    self.fail("Retired recovery mechanism invoked"))

    def test_offline_socket_guard_rejects_network_attempt(self):
        fake = self.repo / "tests"
        fake.mkdir(exist_ok=True)
        (fake / "__init__.py").write_text("# synthetic import\n")
        (fake / "test_network_attempt.py").write_text(
            "import socket,unittest\n"
            "class NetworkAttempt(unittest.TestCase):\n"
            " def test_unauthorized_socket(self):\n"
            "  socket.create_connection(('127.0.0.1',6551),timeout=1)\n"
        )
        result = dev._subprocess_offline_tests(
            self.repo, ("tests.test_network_attempt",))
        self.assertFalse(result["success"])
        self.assertEqual(result["status"],
                         "OFFLINE_SOURCE_REGRESSION_FAILED_QUARANTINED")
        self.assertEqual(result["reported_test_count"], 1)

    def test_persisted_roadmap_tamper_prevents_restart(self):
        out = dev.advance_offline(repo=self.repo, max_steps=1, runner=_accepted)
        roadmap = Path(out["persistent_roadmap_path"])
        self.assertTrue(roadmap.is_file())
        roadmap.write_text('{"schema_version":1,"status":"ALL_G2_APPROVED"}')
        with self.assertRaises(CampaignRecoveryBlocked):
            dev.advance_offline(repo=self.repo, runner=_accepted)

    def test_forged_pass_with_recomputed_self_hash_refused(self):
        import json
        out = dev.advance_offline(repo=self.repo, max_steps=1, runner=_accepted)
        receipt = Path(out["tasks"][0]["result_receipt_path"])
        value = json.loads(receipt.read_text(encoding="utf8"))
        value["reported_test_count"] = 0
        value["integrity_sha256"] = dev._integrity(value)
        receipt.write_text(json.dumps(value), encoding="utf8")
        with self.assertRaises(CampaignRecoveryBlocked):
            dev.advance_offline(repo=self.repo, runner=_accepted)

    def test_no_test_rerun_when_reported_failure_is_quarantined(self):
        n = {"count": 0}
        def fails(repo, modules):
            n["count"] += 1
            return {
                "status": "OFFLINE_SOURCE_REGRESSION_FAILED_QUARANTINED",
                "success": False, "exit_code": 1,
                "reported_test_count": 1, "reported_skip_count": 0,
                "captured_output_sha256": "e" * 64,
            }
        first = dev.advance_offline(
            repo=self.repo, max_steps=1, runner=fails)
        self.assertFalse(first["tasks"][0]["success"])
        again = dev.advance_offline(repo=self.repo, max_steps=1, runner=fails)
        self.assertEqual(n["count"], 2)
        self.assertTrue(again["tasks"][0]["receipt_reused_after_restart"])
        self.assertEqual(again["tasks"][1]["batch_number"], 20)

    def test_normal_historical_plan_cli_routes_to_executable_controller(self):
        from contextlib import redirect_stdout
        import io
        from selenium_pipeline.windows_historical_stack_batch_plan import main
        output = io.StringIO()
        sentinel = {
            "status": "BOUNDED_OFFLINE_DEVELOPMENT_QUEUE_ADVANCED_REVIEW_PENDING",
            "offline_source_regression_pass_count": 1,
            "tasks": [{"student_publication_authorized": False}],
            "automatic_merge_authorized": False,
            "student_publication_authorized": False,
        }
        with patch(
            "selenium_pipeline.windows_offline_development_forward_controller.advance_offline",
            return_value=sentinel,
        ) as execute, redirect_stdout(output):
            rc = main([
                "--repo", str(self.repo),
                "--advance-offline-development",
                "--max-offline-development-tasks", "1",
            ])
        self.assertEqual(rc, 0)
        execute.assert_called_once_with(repo=self.repo, max_steps=1)
        self.assertIn("ADVANCED_REVIEW_PENDING", output.getvalue())
        self.assertNotIn("student_publication_authorized\\\": true",
                         output.getvalue().lower())

    def test_normal_plan_cli_refuses_mixed_batch_and_development_modes(self):
        from contextlib import redirect_stdout
        import io
        from selenium_pipeline.windows_historical_stack_batch_plan import main
        with patch(
            "selenium_pipeline.windows_offline_development_forward_controller.advance_offline",
            side_effect=AssertionError("Forbidden ambiguous mode ran"),
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                result = main([
                    "--repo", str(self.repo),
                    "--advance-offline-development",
                    "--execute-offline-history-checks",
                ])
        self.assertEqual(result, 2)
        self.assertIn("HISTORICAL_STACK_BATCH_REVIEW_REJECTED",
                      output.getvalue())

    def test_verified_earlier_milestones_automatically_advance_to_final_history(self):
        observed = []
        def run(repo, modules):
            observed.append(modules)
            return _accepted(repo, modules)
        start = dev.advance_offline(
            repo=self.repo, max_steps=3, runner=run)
        self.assertEqual(start["tasks_executed_or_reused"], 3)
        self.assertEqual(start["new_tasks_completed_this_process"], 3)
        self.assertEqual(len(observed), 3)
        next_run = dev.advance_offline(
            repo=self.repo, max_steps=27, runner=run)
        self.assertEqual(next_run["tasks_executed_or_reused"], len(dev.TASKS))
        self.assertEqual(next_run["new_tasks_completed_this_process"], 27)
        self.assertEqual(next_run["offline_source_regression_pass_count"],
                         len(dev.TASKS))
        self.assertEqual(len(observed), len(dev.TASKS))
        self.assertEqual([x["batch_number"] for x in next_run["tasks"]],
                         list(range(19, 49)))
        self.assertFalse(next_run["historical_semantic_review_completed"])
        self.assertFalse(next_run["student_publication_authorized"])
        again = dev.advance_offline(
            repo=self.repo,
            runner=lambda *_: self.fail("Finished milestone replayed"))
        self.assertEqual(again["new_tasks_completed_this_process"], 0)
        self.assertTrue(all(t["receipt_reused_after_restart"]
                            for t in again["tasks"]))

    def test_original_terminal_window_accepts_later_head_and_rechecks_anchor(self):
        final = dev.TASKS[-1]
        self.assertEqual(final["batch"], 48)
        self.assertEqual(final["last_commit_prefix"],
                         "<HISTORICAL_ANCHOR_MEMBER>")
        self.assertEqual(final["historical_anchor_prefix"], "048c0cf")
        self.plan["batches"][47]["end_inclusive_sha"] = "e" * 40
        self.plan["batches"].append({
            "batch_number": 49, "first_commit_sha": "9" * 40,
            "end_inclusive_sha": self.head,
            "all_touched_paths_sha256": "f" * 64,
        })
        passed = dev.advance_offline(
            repo=self.repo, runner=_accepted)
        self.assertEqual(passed["tasks_executed_or_reused"], 30)
        with patch.object(dev, "_require_historical_anchor",
                          side_effect=CampaignRecoveryBlocked(
                              "old anchor not in original batch")):
            with self.assertRaises(CampaignRecoveryBlocked):
                dev.advance_offline(repo=self.repo, runner=_accepted)

    def test_real_git_anchor_membership_not_borrowed_from_later_window(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            def git(*args):
                p = subprocess.run(
                    ["git", "-C", str(repo), *args],
                    capture_output=True, text=True, timeout=15)
                self.assertEqual(p.returncode, 0, p.stderr)
                return p.stdout.strip()
            git("init")
            git("config", "user.name", "Offline QA")
            git("config", "user.email", "offline@example.invalid")
            commits = []
            for i in range(3):
                (repo / "file.txt").write_text(str(i))
                git("add", "file.txt")
                git("commit", "-m", "offline source sha " + str(i))
                commits.append(git("rev-parse", "HEAD"))
            b = {
                "start_exclusive_sha": commits[0],
                "end_inclusive_sha": commits[2],
                "commit_count": 2,
            }
            self.real_historical_anchor_check(repo, b, commits[1][:7])
            with self.assertRaises(CampaignRecoveryBlocked):
                self.real_historical_anchor_check(repo, b, commits[0][:7])
            with self.assertRaises(CampaignRecoveryBlocked):
                self.real_historical_anchor_check(
                    repo, {**b, "commit_count": 3}, commits[1][:7])

    def test_bounded_max_tasks_rejects_unlimited_work(self):
        with self.assertRaises(CampaignRecoveryBlocked):
            dev.advance_offline(
                repo=self.repo, max_steps=len(dev.TASKS)+1,
                runner=lambda *_: self.fail("Unbounded developer work"))

    def test_all_skipped_runner_cannot_claim_pass(self):
        def empty(repo, modules):
            return {
                "status": "OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING",
                "success": True, "exit_code": 0,
                "reported_test_count": 3, "reported_skip_count": 3,
                "captured_output_sha256": "a" * 64,
            }
        with self.assertRaises(CampaignRecoveryBlocked):
            dev.advance_offline(repo=self.repo, max_steps=1, runner=empty)

    def test_failed_task_does_not_stop_independent_next(self):
        observed = []
        def one_fails(_repo, modules):
            observed.append(modules)
            if len(observed) == 1:
                return {"status": "OFFLINE_SOURCE_REGRESSION_FAILED_QUARANTINED",
                        "success": False, "exit_code": 1,
                        "reported_test_count": 2, "reported_skip_count": 0,
                        "captured_output_sha256": "4" * 64}
            return _accepted(_repo, modules)
        out = dev.advance_offline(repo=self.repo, max_steps=3, runner=one_fails)
        self.assertEqual(len(observed), 3)
        self.assertEqual(out["offline_source_regression_pass_count"], 2)
        self.assertEqual(out["status"],
                         "BOUNDED_OFFLINE_DEVELOPMENT_WITH_QUARANTINED_TASKS")


if __name__ == "__main__":
    unittest.main()
