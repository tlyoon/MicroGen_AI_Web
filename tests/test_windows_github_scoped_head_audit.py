"""Active-head GitHub branch-graph recovery; no PR merge or publication."""
import copy
import unittest
from unittest.mock import patch
from selenium_pipeline.windows_github_pr_stack_readonly_audit import audit

A = "a" * 40
B = "b" * 40
C = "c" * 40
D = "d" * 40
E = "e" * 40


def fixture():
    return [
        {"number": 530, "state": "open", "draft": True,
         "head": {"ref": "b530", "sha": A},
         "base": {"ref": "b529", "sha": B}},
        {"number": 529, "state": "open", "draft": True,
         "head": {"ref": "b529", "sha": B},
         "base": {"ref": "b527", "sha": C}},
        # This unrelated historical PR must not break a valid current chain.
        {"number": 528, "state": "open", "draft": False,
         "head": {"ref": "unrelated", "sha": E},
         "base": {"ref": "not-open", "sha": D}},
        {"number": 527, "state": "open", "draft": True,
         "head": {"ref": "b527", "sha": C},
         "base": {"ref": "main", "sha": D}},
    ]


class ExactHeadChainTests(unittest.TestCase):
    def run_case(self, items=None, *, expected=A, max_pages=7):
        items = copy.deepcopy(items if items is not None else fixture())
        def fetch(url):
            if "page=1" in url:
                return items
            self.fail("Unexpected second page")
        return audit(repository="tlyoon/MicroGen_AI_Web",
                     expected_latest_head_sha=expected,
                     max_pages=max_pages, fetch=fetch)

    def chain(self, report):
        return report["active_exact_head_dependency_chain"]

    def test_number_gap_and_unrelated_non_draft_are_isolated(self):
        result = self.run_case()
        self.assertEqual(result["status"],
                         "OPEN_PR_STACK_INCOMPLETE_OR_REVIEW_REQUIRED")
        self.assertFalse(result["chain_consistent_only_for_audited_open_prs"])
        chain = self.chain(result)
        self.assertTrue(chain["linked_open_draft_chain_verified"])
        self.assertTrue(chain["root_reached_main"])
        self.assertEqual(chain["preview_pr_numbers"], [530, 529, 527])
        self.assertEqual(chain["verified_parent_links"], 2)
        self.assertFalse(chain["may_merge_automatically"])
        self.assertFalse(result["student_publication_authorized"])

    def test_target_base_sha_mismatch_blocks(self):
        items = fixture()
        items[0]["base"]["sha"] = D
        result = self.run_case(items)
        chain = self.chain(result)
        self.assertEqual(chain["status"], "ACTIVE_PARENT_BRANCH_SHA_MISMATCH")
        self.assertFalse(chain["linked_open_draft_chain_verified"])
        self.assertEqual(chain["verified_parent_links"], 0)

    def test_duplicate_parent_branch_blocks(self):
        items = fixture()
        items.append({"number": 526, "state": "open", "draft": True,
                      "head": {"ref": "b529", "sha": B},
                      "base": {"ref": "main", "sha": D}})
        chain = self.chain(self.run_case(items))
        self.assertEqual(chain["status"], "AMBIGUOUS_MULTIPLE_OPEN_PARENT_HEADS")
        self.assertFalse(chain["linked_open_draft_chain_verified"])

    def test_branch_cycle_is_rejected_even_if_shas_match(self):
        items = fixture()
        items[1]["base"] = {"ref": "b530", "sha": A}
        chain = self.chain(self.run_case(items))
        self.assertEqual(chain["status"], "CYCLIC_PR_PARENT_LINKS_REJECTED")
        self.assertFalse(chain["linked_open_draft_chain_verified"])

    def test_unlisted_parent_not_a_verified_root(self):
        items = fixture()
        items[1]["base"] = {"ref": "absent-open-parent", "sha": D}
        chain = self.chain(self.run_case(items))
        self.assertEqual(chain["status"], "ACTIVE_DRAFT_CHAIN_UNLISTED_BASE_UNVERIFIED")
        self.assertEqual(chain["stopped_at_base_branch"], "absent-open-parent")
        self.assertFalse(chain["root_reached_main"])

    def test_non_draft_on_real_chain_blocks(self):
        items = fixture()
        items[1]["draft"] = False
        chain = self.chain(self.run_case(items))
        self.assertEqual(chain["status"], "NON_DRAFT_PR_IN_ACTIVE_CHAIN")
        self.assertFalse(chain["linked_open_draft_chain_verified"])

    def test_newer_unrelated_pr_does_not_displace_exact_head(self):
        items = fixture()
        items.append({"number": 531, "state": "open", "draft": False,
                      "head": {"ref": "new-unrelated-topic", "sha": D},
                      "base": {"ref": "main", "sha": E}})
        result = self.run_case(items, expected=A)
        self.assertFalse(result["expected_latest_head_sha_matches"])
        chain = self.chain(result)
        self.assertTrue(chain["requested_head_sha_found_exactly_once"])
        self.assertEqual(chain["anchored_head_pr"], 530)
        self.assertTrue(chain["linked_open_draft_chain_verified"])
        self.assertEqual(chain["preview_pr_numbers"], [530, 529, 527])
        self.assertFalse(chain["may_merge_automatically"])

    def test_duplicate_exact_requested_head_sha_is_ambiguous(self):
        items = fixture()
        items.append({"number": 531, "state": "open", "draft": True,
                      "head": {"ref": "competing-copy", "sha": A},
                      "base": {"ref": "main", "sha": E}})
        chain = self.chain(self.run_case(items, expected=A))
        self.assertEqual(chain["status"],
                         "MISSING_OR_AMBIGUOUS_EXACT_HEAD_SHA_NO_SCOPED_PROOF")
        self.assertFalse(chain["linked_open_draft_chain_verified"])

    def test_stale_head_blocks_scoped_proof(self):
        chain = self.chain(self.run_case(expected=D))
        self.assertEqual(chain["status"], "MISSING_OR_AMBIGUOUS_EXACT_HEAD_SHA_NO_SCOPED_PROOF")
        self.assertFalse(chain["linked_open_draft_chain_verified"])

    def test_retired_registry_mechanism_blocks(self):
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            chain = self.chain(self.run_case())
        self.assertEqual(chain["status"], "SCOPED_HEAD_CHAIN_REMEDY_NOT_REGISTERED")
        self.assertFalse(chain["linked_open_draft_chain_verified"])

    def test_catalog_not_exhausted_blocks(self):
        items = fixture()
        items += [{"number": n, "state": "open", "draft": True,
                   "head": {"ref": f"legacy{n}", "sha": E},
                   "base": {"ref": "main", "sha": D}}
                  for n in range(526, 430, -1)]
        self.assertEqual(len(items), 100)
        def page(url):
            return items
        result = audit(repository="tlyoon/MicroGen_AI_Web",
                       expected_latest_head_sha=A,max_pages=1,fetch=page)
        self.assertFalse(self.chain(result)["linked_open_draft_chain_verified"])
        self.assertEqual(self.chain(result)["status"],
                         "INCOMPLETE_CATALOG_NO_SCOPED_PROOF")


    def test_active_cli_exit_is_not_global_merge_approval(self):
        from io import StringIO
        from contextlib import redirect_stdout
        from unittest.mock import patch
        from selenium_pipeline.windows_github_pr_stack_readonly_audit import main
        report = self.run_case()
        self.assertFalse(report["chain_consistent_only_for_audited_open_prs"])
        with patch(
                "selenium_pipeline.windows_github_pr_stack_readonly_audit.audit",
                return_value=report), redirect_stdout(StringIO()):
            self.assertEqual(main(["--active-head-chain-only"]), 0)
            self.assertEqual(main([]), 2)
        self.assertFalse(report["historical_stack_fully_reviewed_or_approved"])
        self.assertFalse(report["may_merge_automatically"])

    def test_active_cli_rejects_failed_parent_proof(self):
        from io import StringIO
        from contextlib import redirect_stdout
        from unittest.mock import patch
        from selenium_pipeline.windows_github_pr_stack_readonly_audit import main
        items = fixture()
        items[0]["base"]["sha"] = D
        with patch(
                "selenium_pipeline.windows_github_pr_stack_readonly_audit.audit",
                return_value=self.run_case(items)), redirect_stdout(StringIO()):
            self.assertEqual(main(["--active-head-chain-only"]), 2)

if __name__ == "__main__":
    unittest.main()
