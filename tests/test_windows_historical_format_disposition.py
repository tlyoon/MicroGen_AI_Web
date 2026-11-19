"""Synthetic native Windows Git history + forensic cosmetic warning classification."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked,
)
from selenium_pipeline.windows_historical_format_disposition import (
    _historical_blob, _inspect_sha, _source_disposition, classify_history,
)


class SourceBoundHistoricalFormatDispositionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.local = Path(self.temp.name)
        p = patch.dict(os.environ, {"LOCALAPPDATA": str(self.local)})
        p.start()
        self.addCleanup(p.stop)
        self.repo = self.local / "isolated_dev"
        self.repo.mkdir()
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "Test Reviewer")
        self.git("config", "user.email", "git-fixture@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.put("README.md", b"verified baseline\n")
        self.commit("Source-free baseline")
        self.git("update-ref", "refs/remotes/origin/main",
                 self.git("rev-parse", "HEAD"))
        self.git("switch", "-c", "feature/fixture")
        self.put("tests/extra.py", b"value = 3\n\n")
        self.commit("Add extra Python EOF")
        self.python_sha = self.git("rev-parse", "HEAD")
        self.put("docs/contract.md", b"Intended hard break  \nNext line\n")
        self.commit("Intentional Markdown hard break")
        self.hardbreak_sha = self.git("rev-parse", "HEAD")
        self.put("docs/notes.md", b"Unintended single trailing space \nNext\n")
        self.commit("Accidental Markdown trailing space")
        self.single_sha = self.git("rev-parse", "HEAD")
        # Current cumulative diff deliberately clean, but the original
        # three warning commits persist in immutable Git objects.
        self.put("tests/extra.py", b"value = 3\n")
        self.put("docs/contract.md", b"Intended hard break\nNext line\n")
        self.put("docs/notes.md", b"Unintended single trailing space\nNext\n")
        self.commit("Fix cumulative patch without rewriting past source")
        self.exact_head = self.git("rev-parse", "HEAD")

    def git(self, *args: str) -> str:
        r = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            capture_output=True, text=True, encoding="utf-8",
            timeout=20, errors="replace",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def put(self, rel: str, value: bytes):
        target = self.repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value)

    def commit(self, message: str):
        self.git("add", ".")
        self.git("commit", "-m", message)

    def test_actual_git_source_warnings_are_distinct_and_reproducible(self):
        py = _inspect_sha(self.repo, self.python_sha)
        two = _inspect_sha(self.repo, self.hardbreak_sha)
        one = _inspect_sha(self.repo, self.single_sha)
        self.assertEqual(len(py), 1)
        self.assertEqual(len(two), 1)
        self.assertEqual(len(one), 1)
        self.assertEqual(py[0]["disposition"],
                         "HISTORICAL_PYTHON_EOF_AST_INVARIANT")
        self.assertEqual(two[0]["disposition"],
                         "HISTORICAL_INTENTIONAL_MARKDOWN_HARDBREAK")
        self.assertEqual(one[0]["disposition"],
                         "HISTORICAL_SINGLE_MARKDOWN_TRAILING_SPACE")
        self.assertFalse(one[0]["semantic_code_review_approved"])
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_end_to_end_receipts_reused_without_release(self):
        first = classify_history(repo=self.repo)
        self.assertEqual(first["exact_head_sha"], self.exact_head)
        self.assertEqual(first["historical_failing_commit_count"], 3)
        self.assertEqual(first["historical_diagnostic_count"], 3)
        self.assertEqual(first["class_counts"], {
            "HISTORICAL_PYTHON_EOF_AST_INVARIANT": 1,
            "HISTORICAL_SINGLE_MARKDOWN_TRAILING_SPACE": 1,
            "HISTORICAL_INTENTIONAL_MARKDOWN_HARDBREAK": 1,
        })
        self.assertFalse(first["receipt_reused_after_restart"])
        second = classify_history(repo=self.repo)
        self.assertTrue(second["receipt_reused_after_restart"])
        self.assertFalse(second["semantic_code_review_completed"])
        self.assertFalse(second["automatic_merge_authorized"])
        self.assertFalse(second["student_publication_authorized"])
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_tampered_disposition_receipt_stops_restart(self):
        result = classify_history(repo=self.repo)
        receipt = Path(result["receipt_path"])
        receipt.write_text('{"status":"APPROVED"}', encoding="utf-8")
        with self.assertRaises(CampaignRecoveryBlocked):
            classify_history(repo=self.repo)

    def test_history_registry_disabled_prevents_execution(self):
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with self.assertRaises(CampaignRecoveryBlocked):
                classify_history(repo=self.repo)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_history_source_sample_mismatch_fails_closed(self):
        with patch(
            "selenium_pipeline.windows_historical_format_disposition._historical_blob",
            return_value=b"Unsafe different content\n",
        ):
            with self.assertRaises(CampaignRecoveryBlocked):
                _inspect_sha(self.repo, self.hardbreak_sha)

    def test_non_python_eof_cannot_be_excused(self):
        with self.assertRaises(CampaignRecoveryBlocked):
            _source_disposition(
                path="tests/unsafe.txt", line=2,
                kind="new blank line at EOF",
                source=b"Binary content\n\n", addition=None,
            )

    def test_source_with_meaningful_python_change_never_classified_cosmetic(self):
        with self.assertRaises(CampaignRecoveryBlocked):
            _source_disposition(
                path="selenium_pipeline/broken.py", line=2,
                kind="new blank line at EOF",
                source=b"def broken(:\n\n", addition=None,
            )

    def test_markdown_sample_forgery_and_missing_source_rejected(self):
        with self.assertRaises(CampaignRecoveryBlocked):
            _source_disposition(
                path="docs/contract.md", line=1,
                kind="trailing whitespace",
                source=b"Genuine double space  \n",
                addition="+Forged single space ",
            )
        with self.assertRaises(CampaignRecoveryBlocked):
            _historical_blob(self.repo, self.hardbreak_sha,
                             "docs/../../secret.md")

    def test_remaining_current_patch_warning_blocks_disposition(self):
        # Make a new HEAD containing a persistent new formatting warning;
        # neither the old source review nor cached receipt may override it.
        self.put("docs/new.md", b"New unfixed space \n")
        self.commit("New cumulative whitespace regression")
        with self.assertRaises(CampaignRecoveryBlocked):
            classify_history(repo=self.repo)
        self.assertEqual(self.git("status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
