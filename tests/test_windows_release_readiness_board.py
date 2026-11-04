"""Windows final-release evidence stays blocked without real full original E2E."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.windows_release_readiness_board import (
    _windows_ci_only, inspect_release,
)


class WindowsReleaseReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo / ".git").write_text("gitdir: isolated", encoding="utf8")
        workflow = self.repo / ".github" / "workflows"
        workflow.mkdir(parents=True)
        (workflow / "windows.yml").write_text(
            "name: smoke\njobs:\n  test:\n    runs-on: windows-latest\n",
            encoding="utf8")
        self.recovery = {
            "source_job_receipts_security_or_version_rejected": 0,
            "source_job_receipts_current_and_sha_verified": 2,
            "fresh_original_publisher_and_stage_sha_verified": True,
            "fresh_original_figure_attempt_state": "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY",
            "automatic_provider_retry_authorized": False,
        }

    def fake_git(self, repo, *args):
        key = " ".join(args)
        mapping = {
            "branch --show-current": "feature/pr492-release-board",
            "rev-parse HEAD": "a" * 40,
            "rev-parse main": "c" * 40,
            "rev-parse origin/main": "b" * 40,
            "rev-list --count origin/main..HEAD": "764",
            "rev-list --count HEAD..origin/main": "0",
            "status --porcelain": "",
        }
        return mapping[key]

    def test_green_source_jobs_do_not_imply_full_e2e_release(self):
        with patch("selenium_pipeline.windows_release_readiness_board._git",
                   side_effect=self.fake_git), patch(
            "selenium_pipeline.windows_release_readiness_board.audit",
            return_value=self.recovery,
        ):
            report = inspect_release(repo=self.repo,
                                     jobs_dir=Path("jobs"),
                                     fresh_trial_dir=Path("trial"))
        self.assertTrue(report["required_release_gates"]["source_checkpoint_integrity"])
        self.assertTrue(report["required_release_gates"]["windows_ci_workflows_only"])
        self.assertEqual(report["commits_ahead_of_tracked_origin_main"], 764)
        self.assertFalse(report["required_release_gates"]["local_main_matches_tracked_origin_main"])
        self.assertFalse(report["release_candidate_ready"])
        self.assertFalse(report["may_merge_historical_stack_automatically"])
        self.assertFalse(report["student_publication_authorized"])
        self.assertFalse(report["required_release_gates"][
            "first_new_original_full_sourcebound_lecture_accepted"])

    def test_non_windows_ci_is_not_silently_approved(self):
        workflow = self.repo / ".github" / "workflows" / "other.yml"
        workflow.write_text("jobs:\n  x:\n    runs-on: ubuntu-latest\n", encoding="utf8")
        result = _windows_ci_only(self.repo)
        self.assertFalse(result["all_runner_declarations_windows"])
        self.assertEqual(len(result["non_windows_runner_declarations"]), 1)

    def test_git_dirty_or_diverged_is_not_release_candidate(self):
        def bad_git(repo, *args):
            key = " ".join(args)
            if key == "status --porcelain":
                return " M selenium_pipeline/runner.py"
            if key == "rev-list --count HEAD..origin/main":
                return "1"
            return self.fake_git(repo, *args)
        with patch("selenium_pipeline.windows_release_readiness_board._git",
                   side_effect=bad_git), patch(
            "selenium_pipeline.windows_release_readiness_board.audit",
            return_value=self.recovery,
        ):
            r = inspect_release(repo=self.repo, jobs_dir=Path("job"),
                                fresh_trial_dir=Path("trial"))
        self.assertFalse(r["required_release_gates"]["current_worktree_clean"])
        self.assertFalse(r["required_release_gates"]["tracked_origin_main_ancestor_no_divergence"])
        self.assertFalse(r["release_candidate_ready"])

    def test_security_rejected_source_stops_release_even_when_ci_were_green(self):
        bad = dict(self.recovery, source_job_receipts_security_or_version_rejected=1)
        with patch("selenium_pipeline.windows_release_readiness_board._git",
                   side_effect=self.fake_git), patch(
            "selenium_pipeline.windows_release_readiness_board.audit",
            return_value=bad,
        ):
            r = inspect_release(repo=self.repo, jobs_dir=Path("job"),
                                fresh_trial_dir=Path("trial"))
        self.assertFalse(r["required_release_gates"]["source_checkpoint_integrity"])
        self.assertFalse(r["release_candidate_ready"])


if __name__ == "__main__":
    unittest.main()
