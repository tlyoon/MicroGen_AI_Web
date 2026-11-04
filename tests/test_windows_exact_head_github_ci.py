"""GitHub exact-head CI remote attestation is SHA-bound and never publication."""
from __future__ import annotations

import unittest

from selenium_pipeline.windows_exact_head_github_ci import inspect_ci


class WindowsExactHeadGitHubCITests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.repo = "tlyoon/MicroGen_AI_Web"
        self.calls = []
        self.runs = [{
            "id": 101, "name": "MicroGen reliability regressions",
            "path": ".github/workflows/microgen-reliability-tests.yml@refs/pull/12/merge",
            "head_sha": self.sha, "event": "pull_request",
            "run_attempt": 1, "created_at": "2026-11-04T12:00:00Z",
            "status": "completed", "conclusion": "success",
        }]
        self.jobs = [{
            "name": "offline-regressions", "status": "completed",
            "conclusion": "success",
        }, {
            "name": "Full offline suite (Windows, Python 3.12)",
            "status": "completed", "conclusion": "success",
        }]

    def fetch(self, url):
        self.calls.append(url)
        if "/jobs?" in url:
            return {"jobs": self.jobs}
        if url.endswith("/git/ref/heads/main"):
            return {"object": {"sha": "b" * 40}}
        if "/actions/runs?" in url:
            return {"workflow_runs": self.runs}
        self.fail("Unexpected network route " + url)

    def inspect(self, **kwargs):
        return inspect_ci(repository=self.repo, head_sha=self.sha,
                          fetch=self.fetch, **kwargs)

    def test_exact_head_and_two_windows_jobs_pass_without_approval(self):
        r = self.inspect()
        self.assertEqual(r["status"],
                         "EXACT_HEAD_GITHUB_WINDOWS_CI_INDEPENDENTLY_VERIFIED")
        self.assertTrue(r["exact_head_windows_ci_verified"])
        self.assertEqual(r["github_run_id"], 101)
        self.assertEqual(len(self.calls), 2)
        self.assertIn(self.sha, self.calls[0])
        self.assertFalse(r["model_or_tts_called"])
        self.assertFalse(r["historical_stack_merge_authorized"])
        self.assertFalse(r["student_publication_authorized"])

    def test_live_main_sha_must_match_current_github(self):
        good = inspect_ci(
            repository=self.repo, head_sha=self.sha,
            tracked_main_sha="b" * 40, fetch=self.fetch)
        self.assertTrue(good["exact_head_windows_ci_verified"])
        self.assertTrue(good["remote_tracked_main_matches_current_github"])
        self.assertEqual(good["live_github_main_sha"], "b" * 40)
        self.assertEqual(len(self.calls), 3)

        self.calls.clear()
        stale = inspect_ci(
            repository=self.repo, head_sha=self.sha,
            tracked_main_sha="c" * 40, fetch=self.fetch)
        self.assertTrue(stale["exact_head_windows_ci_verified"])
        self.assertFalse(stale["remote_tracked_main_matches_current_github"])
        self.assertEqual(stale["status"],
                         "LOCAL_TRACKED_ORIGIN_MAIN_STALE_VS_GITHUB")

    def test_wrong_sha_cannot_reuse_previous_green(self):
        self.runs[0]["head_sha"] = "b" * 40
        r = self.inspect()
        self.assertEqual(r["status"],
                         "NO_EXACT_HEAD_PULL_REQUEST_WINDOWS_CI_RUN")
        self.assertFalse(r["exact_head_windows_ci_verified"])
        self.assertEqual(len(self.calls), 1)

    def test_latest_failing_run_overrides_older_green(self):
        older = dict(self.runs[0])
        older["id"] = 100
        older["created_at"] = "2026-11-04T11:00:00Z"
        self.runs.insert(0, older)
        self.runs[1]["id"] = 102
        self.runs[1]["created_at"] = "2026-11-04T13:00:00Z"
        self.runs[1]["conclusion"] = "failure"
        r = self.inspect()
        self.assertEqual(r["status"], "EXACT_HEAD_WINDOWS_CI_PENDING_OR_FAILED")
        self.assertEqual(r["github_run_id"], 102)
        self.assertFalse(r["exact_head_windows_ci_verified"])

    def test_latest_queued_run_cannot_be_bypassed_by_old_green(self):
        newer = dict(self.runs[0])
        newer["id"] = 103
        newer["created_at"] = "2026-11-04T14:00:00Z"
        newer["status"] = "queued"
        newer["conclusion"] = None
        self.runs.append(newer)
        r = self.inspect()
        self.assertEqual(r["github_run_id"], 103)
        self.assertFalse(r["exact_head_windows_ci_verified"])

    def test_failed_or_missing_job_stops_even_when_workflow_green(self):
        for modify in (
            lambda: self.jobs.pop(),
            lambda: self.jobs[0].update(conclusion="failure"),
            lambda: self.jobs[1].update(status="in_progress"),
        ):
            self.jobs = [
                {"name": "offline-regressions", "status": "completed",
                 "conclusion": "success"},
                {"name": "Full offline suite (Windows, Python 3.12)",
                 "status": "completed", "conclusion": "success"},
            ]
            modify()
            with self.subTest(jobs=self.jobs):
                self.assertEqual(
                    self.inspect()["status"], "EXACT_HEAD_WINDOWS_CI_JOBS_NOT_ALL_GREEN")

    def test_duplicate_job_names_reject_ambiguous_ci(self):
        self.jobs.append(dict(self.jobs[0]))
        r = self.inspect()
        self.assertEqual(r["status"], "EXACT_HEAD_CI_REMOTE_EVIDENCE_UNAVAILABLE")
        self.assertFalse(r["exact_head_windows_ci_verified"])

    def test_remote_failure_cannot_fake_good_result(self):
        def offline(_url):
            raise OSError("synthetic GitHub network outage")
        r = inspect_ci(repository=self.repo, head_sha=self.sha, fetch=offline)
        self.assertEqual(r["status"], "EXACT_HEAD_CI_REMOTE_EVIDENCE_UNAVAILABLE")
        self.assertEqual(r["safe_diagnostic"], "OSError")
        self.assertFalse(r["exact_head_windows_ci_verified"])

    def test_arbitrary_repository_or_bad_sha_cannot_send_network_request(self):
        for invalid in ("..", "../../other", "tlyoon/a?invalid", "user/a/third"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    inspect_ci(repository=invalid, head_sha=self.sha,
                               fetch=self.fetch)
        with self.assertRaises(ValueError):
            inspect_ci(repository=self.repo, head_sha="a" * 39,
                       fetch=self.fetch)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
