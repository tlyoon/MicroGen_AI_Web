"""Synthetic GitHub PR branch dependency chain: never PR merge approval."""
import unittest

from selenium_pipeline.windows_github_pr_stack_readonly_audit import audit


class WindowsGitHubPRStackReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.latest = "a" * 40
        self.items = [
            {"number": 513, "state": "open", "draft": True,
             "head": {"ref": "feature/pr513", "sha": self.latest},
             "base": {"ref": "feature/pr512"}},
            {"number": 512, "state": "open", "draft": True,
             "head": {"ref": "feature/pr512", "sha": "b" * 40},
             "base": {"ref": "feature/pr511"}},
            {"number": 511, "state": "open", "draft": True,
             "head": {"ref": "feature/pr511", "sha": "c" * 40},
             "base": {"ref": "main"}},
        ]
        self.queries = []

    def fetch(self, url):
        self.queries.append(url)
        if "page=1" in url:
            return self.items
        self.fail("Unexpected extra metadata page")

    def call(self, **kwargs):
        return audit(repository="tlyoon/MicroGen_AI_Web",
                     expected_latest_head_sha=self.latest, fetch=self.fetch,
                     **kwargs)

    def test_fully_linked_open_draft_chain_is_plan_not_approval(self):
        outcome = self.call()
        self.assertEqual(outcome["status"],
                         "OPEN_DRAFT_PR_LINKS_RECONCILED_NOT_MERGE_APPROVED")
        self.assertEqual(outcome["open_pr_count_in_audited_pages"], 3)
        self.assertEqual(outcome["newest_open_pr"], 513)
        self.assertEqual(outcome["oldest_open_base_branch"], "main")
        self.assertTrue(outcome["chain_consistent_only_for_audited_open_prs"])
        self.assertEqual(
            outcome["newest_contiguous_draft_review_tranche_count"], 3)
        self.assertEqual(
            outcome["newest_contiguous_draft_review_tranche_oldest_pr"], 511)
        self.assertTrue(outcome["open_pr_catalog_pagination_complete"])
        self.assertFalse(outcome["historical_stack_fully_reviewed_or_approved"])
        self.assertFalse(outcome["may_merge_automatically"])
        self.assertFalse(outcome["student_publication_authorized"])
        self.assertFalse(outcome["new_model_or_tts_calls"])
        self.assertEqual(len(self.queries), 1)

    def test_unrelated_branch_breaks_chain_without_claiming_merge(self):
        self.items[0]["base"]["ref"] = "wrong_parent"
        outcome = self.call()
        self.assertEqual(outcome["status"],
                         "OPEN_PR_STACK_INCOMPLETE_OR_REVIEW_REQUIRED")
        self.assertEqual(outcome["total_adjacent_disagreement_count"], 1)
        self.assertEqual(outcome["newest_contiguous_draft_review_tranche_count"], 1)
        self.assertFalse(outcome["chain_consistent_only_for_audited_open_prs"])

    def test_non_draft_unapproved_pr_never_passes_conservative_contract(self):
        self.items[1]["draft"] = False
        self.assertFalse(self.call()["chain_consistent_only_for_audited_open_prs"])

    def test_stale_expected_current_head_rejected(self):
        r = audit(repository="tlyoon/MicroGen_AI_Web",
                  expected_latest_head_sha="d" * 40, fetch=self.fetch)
        self.assertFalse(r["expected_latest_head_sha_matches"])
        self.assertFalse(r["chain_consistent_only_for_audited_open_prs"])

    def test_truncated_page_cannot_be_complete(self):
        pages = []
        for n in range(600, 500, -1):
            pages.append({"number": n, "state": "open", "draft": True,
                          "head": {"ref": f"feature/pr{n}", "sha": "a" * 40},
                          "base": {"ref": f"feature/pr{n-1}"}})
        r = audit(repository="tlyoon/MicroGen_AI_Web", max_pages=1,
                  fetch=lambda url: pages)
        self.assertFalse(r["open_pr_catalog_pagination_complete"])
        self.assertFalse(r["chain_consistent_only_for_audited_open_prs"])

    def test_duplicate_pull_request_numbers_refused(self):
        self.items[1]["number"] = 513
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.call()

    def test_untrusted_head_sha_refused(self):
        self.items[0]["head"]["sha"] = "not a SHA"
        with self.assertRaisesRegex(ValueError, "Untrusted"):
            self.call()

    def test_invalid_repository_or_expected_sha_no_remote_calls(self):
        for repo in ("../other", "user/a/extra", "org/.."):
            with self.subTest(repo=repo):
                with self.assertRaises(ValueError):
                    audit(repository=repo, fetch=self.fetch)
        with self.assertRaises(ValueError):
            audit(repository="tlyoon/MicroGen_AI_Web",
                  expected_latest_head_sha="a" * 39, fetch=self.fetch)
        self.assertEqual(self.queries, [])


if __name__ == "__main__":
    unittest.main()
