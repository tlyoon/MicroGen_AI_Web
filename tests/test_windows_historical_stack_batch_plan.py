"""Native Windows synthetic Git history; no network, checkout mutations to real repo."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked,
)
from selenium_pipeline.windows_historical_stack_batch_plan import plan_stack


class HistoricalStackReadOnlyBatchPlanTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.local = Path(temp.name)
        env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.local)})
        env.start()
        self.addCleanup(env.stop)
        self.repo = self.local / "isolated_synthetic_repo"
        self.repo.mkdir()
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "Offline test only")
        self.git("config", "user.email", "offline-test@example.invalid")
        self.commit("README.md", "base")
        self.base = self.git("rev-parse", "HEAD")
        self.git("update-ref", "refs/remotes/origin/main", self.base)
        self.git("switch", "-c", "feature/pr510-synthetic")
        self.commit("selenium_pipeline/core.py", "phase1")
        self.commit("tests/test_mock.py", "phase2")
        self.commit(".github/workflows/windows.yml", "phase3")
        self.commit("docs/final.md", "phase4")
        self.commit("pyproject.toml", "phase5")

    def git(self, *args):
        p = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            capture_output=True, text=True, encoding="utf8",
            errors="replace", timeout=30)
        if p.returncode:
            self.fail("Synthetic Git failed: " + repr(args) + p.stderr)
        return p.stdout.strip()

    def commit(self, name, contents):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf8")
        self.git("add", "--", name)
        self.git("commit", "-m", "test synthetic commit " + name)

    def test_real_git_history_groups_every_commit_without_merge_or_write(self):
        before = self.git("rev-parse", "HEAD")
        first = plan_stack(repo=self.repo, batch_size=2)
        second = plan_stack(repo=self.repo, batch_size=2)
        self.assertEqual(first, second)
        self.assertEqual(first["status"],
                         "HISTORICAL_STACK_READ_ONLY_BATCH_PLAN_AVAILABLE")
        self.assertEqual(first["commits_ahead_of_origin_main"], 5)
        self.assertEqual(first["review_batch_count"], 3)
        self.assertEqual([x["commit_count"] for x in first["batches"]],
                         [2, 2, 1])
        self.assertIn("PIPELINE_RUNTIME",
                      first["batches"][0]["review_risk_categories"])
        self.assertIn("WINDOWS_CI",
                      first["batches"][1]["review_risk_categories"])
        self.assertIn("WINDOWS_PACKAGING_OR_LAUNCHER",
                      first["batches"][2]["review_risk_categories"])
        self.assertEqual(first["exact_head_sha"], before)
        self.assertFalse(first["historical_stack_review_completed"])
        self.assertFalse(first["automatic_merge_or_release_authorized"])
        self.assertFalse(first["new_model_or_tts_calls"])
        self.assertFalse(first["student_publication_authorized"])
        self.assertFalse(first["git_changes_performed"])
        self.assertEqual(self.git("rev-parse", "HEAD"), before)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_real_git_create_then_delete_pdf_cannot_disappear_from_review(self):
        # A file absent at both endpoints must still appear if it was
        # introduced and removed in intermediate commit history.
        self.commit("source_diagnostic.pdf", "synthetic only")
        self.git("rm", "--", "source_diagnostic.pdf")
        self.git("commit", "-m", "delete synthetic source diagnostic")
        before = self.git("rev-parse", "HEAD")
        a = plan_stack(repo=self.repo, batch_size=20)
        b = plan_stack(repo=self.repo, batch_size=20)
        self.assertEqual(a, b)
        batch = a["batches"][0]
        self.assertEqual(batch["commit_count"], 7)
        self.assertIn("source_diagnostic.pdf",
                      batch["transient_or_reverted_path_examples"])
        self.assertGreaterEqual(batch["transient_or_reverted_path_count"], 1)
        self.assertGreater(batch["historical_touched_path_count"],
                           batch["net_diff_path_count"])
        self.assertIn("SOURCE_OR_AUDIO_MEDIA_ASSET",
                      batch["review_risk_categories"])
        self.assertRegex(batch["all_touched_paths_sha256"], r"^[a-f0-9]{64}$")
        self.assertFalse(batch["code_and_academic_review_complete"])
        self.assertFalse(batch["merge_or_publication_authorized"])
        self.assertEqual(before, self.git("rev-parse", "HEAD"))

    def test_both_exact_historical_test_roots_are_counted(self):
        # Reproduce the B34/B35 reporting mistake: a root-only audit
        # incorrectly concluded no tests changed in nested test windows.
        self.commit("selenium_pipeline/tests/test_nested_history.py", "nested")
        self.commit("tests/test_root_history.py", "root")
        self.commit("selenium_pipeline/test_not_a_test.py", "runtime")
        before = self.git("rev-parse", "HEAD")
        batch = plan_stack(repo=self.repo, batch_size=20)["batches"][0]
        self.assertEqual(
            batch["historically_touched_regression_test_root_counts"],
            {"tests/": 2, "selenium_pipeline/tests/": 1})
        self.assertEqual(
            batch["historically_touched_regression_test_path_count"], 3)
        self.assertIn("selenium_pipeline/tests/test_nested_history.py",
                      batch["historically_touched_regression_test_path_examples"])
        self.assertIn("tests/test_root_history.py",
                      batch["historically_touched_regression_test_path_examples"])
        self.assertNotIn("selenium_pipeline/test_not_a_test.py",
                         batch["historically_touched_regression_test_path_examples"])
        self.assertRegex(
            batch["historically_touched_regression_test_path_sha256"],
            r"^[a-f0-9]{64}$")
        self.assertTrue(
            batch["historical_test_path_inventory_not_semantic_acceptance"])
        self.assertFalse(batch["code_and_academic_review_complete"])
        self.assertEqual(before, self.git("rev-parse", "HEAD"))

    def test_deleted_nested_test_retained_as_original_history_evidence(self):
        self.commit("selenium_pipeline/tests/test_deleted.py", "synthetic")
        self.git("rm", "--", "selenium_pipeline/tests/test_deleted.py")
        self.git("commit", "-m", "remove synthetic nested test")
        batch = plan_stack(repo=self.repo, batch_size=20)["batches"][0]
        self.assertIn("selenium_pipeline/tests/test_deleted.py",
                      batch["historically_touched_regression_test_path_examples"])
        self.assertEqual(
            batch["historically_touched_regression_test_root_counts"][
                "selenium_pipeline/tests/"], 1)
        self.assertFalse(batch["merge_or_publication_authorized"])

    def test_disabled_new_root_coverage_registry_fails_closed(self):
        from selenium_pipeline import windows_historical_stack_batch_plan as mod

        def only_old_mechanism(match_type, signature):
            if match_type == "history_batch_inventory":
                return "EXACT_COMMIT_TOUCHED_PATH_UNION_WITH_NET_DIFF_GUARD"
            return None

        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   side_effect=only_old_mechanism):
            with self.assertRaisesRegex(
                    CampaignRecoveryBlocked,
                    "Historical test-root inventory recovery missing"):
                mod.plan_stack(repo=self.repo)

    def test_missing_commit_markers_blocks_entire_review_plan(self):
        from selenium_pipeline import windows_historical_stack_batch_plan as mod
        original = mod._git

        def incomplete(repo, *args):
            if args and args[0] == "log":
                return "MICROGEN_COMMIT_SHA:" + "f" * 40 + "\n"
            return original(repo, *args)

        with patch.object(mod, "_git", side_effect=incomplete):
            with self.assertRaises(CampaignRecoveryBlocked):
                plan_stack(repo=self.repo)

    def test_unanchored_changed_path_blocks_review_plan(self):
        from selenium_pipeline import windows_historical_stack_batch_plan as mod
        original = mod._git

        def unanchored(repo, *args):
            if args and args[0] == "log":
                return "selenium_pipeline/unowned.py"
            return original(repo, *args)

        with patch.object(mod, "_git", side_effect=unanchored):
            with self.assertRaises(CampaignRecoveryBlocked):
                plan_stack(repo=self.repo)

    def test_disabled_registry_prevents_incomplete_plan_fallback(self):
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with self.assertRaisesRegex(
                    CampaignRecoveryBlocked, "recovery missing or retired"):
                plan_stack(repo=self.repo)

    def test_dirty_worktree_does_not_become_reviewed_or_released(self):
        (self.repo / "README.md").write_text("changed locally", encoding="utf8")
        report = plan_stack(repo=self.repo)
        self.assertFalse(report["local_worktree_clean"])
        self.assertFalse(report["historical_stack_review_completed"])
        self.assertFalse(report["automatic_merge_or_release_authorized"])

    def test_divergent_tracked_main_blocks_stack_topology_plan(self):
        self.git("switch", "-c", "synthetic-other", self.base)
        self.commit("conflict.txt", "other")
        newer_main = self.git("rev-parse", "HEAD")
        self.git("update-ref", "refs/remotes/origin/main", newer_main)
        self.git("switch", "feature/pr510-synthetic")
        report = plan_stack(repo=self.repo)
        self.assertEqual(
            report["status"],
            "RELEASE_STACK_TOPOLOGY_NOT_VERIFIABLE_FROM_LOCAL_REFS")
        self.assertGreater(report["commits_behind_origin_main"], 0)
        self.assertEqual(report["batches"], [])
        self.assertFalse(report["automatic_merge_or_release_authorized"])

    def test_bound_too_small_and_invalid_batch_are_rejected(self):
        with self.assertRaisesRegex(CampaignRecoveryBlocked, "bounded"):
            plan_stack(repo=self.repo, batch_size=0)
        with self.assertRaisesRegex(CampaignRecoveryBlocked, "too large"):
            plan_stack(repo=self.repo, max_commits=3)

    def test_outside_localappdata_checkout_is_denied(self):
        with patch.dict(os.environ, {"LOCALAPPDATA": str(self.local / "empty")}):
            with self.assertRaises(CampaignRecoveryBlocked):
                plan_stack(repo=self.repo)

    def test_original_historical_main_without_new_commits_no_fake_release(self):
        self.git("switch", "-c", "synthetic-same", self.base)
        report = plan_stack(repo=self.repo)
        self.assertEqual(report["status"], "NO_COMMITS_AHEAD_OF_TRACKED_MAIN")
        self.assertEqual(report["review_batch_count"], 0)
        self.assertFalse(report["historical_stack_review_completed"])
        self.assertFalse(report["automatic_merge_or_release_authorized"])


if __name__ == "__main__":
    unittest.main()
