"""Dell-only genuine Git format recovery with safe AST/no-model guards."""
from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.original_multisource_recovery_campaign import CampaignRecoveryBlocked
from selenium_pipeline.windows_head_whitespace_recovery import (
    inspect_head_patch, repair_safe_current_source)


class CumulativeHeadWhitespaceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.local=Path(self.tmp.name)
        ctx=patch.dict(os.environ,{"LOCALAPPDATA":str(self.local)})
        ctx.start();self.addCleanup(ctx.stop)
        self.repo=self.local/"synthetic_isolated"
        self.repo.mkdir()
        self.git("init","--initial-branch=main")
        self.git("config","user.name","Safety fixture")
        self.git("config","user.email","offline@example.invalid")
        self.put("README.md",b"Git history baseline\n")
        self.git("add",".")
        self.git("commit","-m","synthetic baseline")
        self.base=self.git("rev-parse","HEAD")
        self.git("update-ref","refs/remotes/origin/main",self.base)
        self.git("switch","-c","feature/format")

    def git(self,*args):
        p=subprocess.run(["git","-C",str(self.repo),*args],
                         capture_output=True,text=True,encoding="utf8",
                         errors="replace",timeout=25)
        if p.returncode:
            self.fail(f"Git failed {args}: {p.stderr}")
        return p.stdout.strip()

    def put(self,rel,raw):
        f=self.repo/rel
        f.parent.mkdir(parents=True,exist_ok=True)
        f.write_bytes(raw)

    def commit_files(self):
        self.git("add",".")
        self.git("commit","-m","synthetic one-source format defect")

    def test_real_git_safe_source_normalization_keeps_ast_bom_and_head(self):
        py="selenium_pipeline/module.py"
        md="docs/historical.md"
        original=b'\xef\xbb\xbfdef stable():\r\n    return 7\r\n\r\n'
        self.put(py,original)
        self.put(md,b'One safe trailing space \nNext line\n')
        self.commit_files()
        old=self.git("rev-parse","HEAD")
        pre=inspect_head_patch(repo=self.repo)
        self.assertFalse(pre["clean"])
        self.assertEqual(pre["patch_warning_count"],2)
        r=repair_safe_current_source(repo=self.repo)
        self.assertEqual(r["normalized_file_count"],2)
        self.assertEqual(r["repaired_historical_patch_warning_count"],2)
        self.assertTrue(r["python_ast_unchanged"])
        self.assertEqual(self.git("rev-parse","HEAD"),old)
        after=(self.repo/py).read_bytes()
        self.assertEqual(after,b'\xef\xbb\xbfdef stable():\r\n    return 7\r\n')
        self.assertEqual(ast.dump(ast.parse(original.decode("utf-8-sig"))),
                         ast.dump(ast.parse(after.decode("utf-8-sig"))))
        self.assertEqual((self.repo/md).read_bytes(),
                         b'One safe trailing space\nNext line\n')
        self.assertFalse(r["automatic_merge_authorized"])
        self.assertFalse(r["student_publication_authorized"])
        check=subprocess.run(["git","-C",str(self.repo),
                               "diff","--check","origin/main"],
                              capture_output=True,text=True)
        self.assertEqual(check.returncode,0,check.stdout)
        self.assertNotEqual(self.git("status","--porcelain"),"")

    def test_markdown_hard_break_two_spaces_is_never_auto_fixed(self):
        raw=b"Hard line break  \nNext\n"
        self.put("docs/preserve.md",raw)
        self.commit_files()
        with self.assertRaises(CampaignRecoveryBlocked):
            repair_safe_current_source(repo=self.repo)
        self.assertEqual((self.repo/"docs/preserve.md").read_bytes(),raw)

    def test_python_code_line_whitespace_not_in_safe_repair_set(self):
        raw=b"def stable():  \n    return 7\n"
        self.put("selenium_pipeline/code.py",raw)
        self.commit_files()
        with self.assertRaises(CampaignRecoveryBlocked):
            repair_safe_current_source(repo=self.repo)
        self.assertEqual((self.repo/"selenium_pipeline/code.py").read_bytes(),raw)

    def test_unsupported_diagnostic_prevents_even_prior_safe_changes(self):
        py="selenium_pipeline/safe.py"
        original=b"def value():\n    return 1\n\n"
        self.put(py,original)
        self.put("docs/hardbreak.md",b"Intentional markdown  \n")
        self.commit_files()
        with self.assertRaises(CampaignRecoveryBlocked):
            repair_safe_current_source(repo=self.repo)
        self.assertEqual((self.repo/py).read_bytes(),original)
        self.assertEqual(self.git("status","--porcelain"),"")

    def test_dirty_repo_cannot_be_reformatted(self):
        self.put("selenium_pipeline/x.py",b"x=1\n\n")
        self.commit_files()
        self.put("README.md",b"locally dirty\n")
        with self.assertRaises(CampaignRecoveryBlocked):
            repair_safe_current_source(repo=self.repo)

    def test_recovery_registry_retired_disallows_writes(self):
        self.put("selenium_pipeline/x.py",b"x=1\n\n")
        self.commit_files()
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with self.assertRaises(CampaignRecoveryBlocked):
                repair_safe_current_source(repo=self.repo)
        self.assertEqual(self.git("status","--porcelain"),"")

    def test_approved_noop_if_exact_head_clean(self):
        self.put("selenium_pipeline/x.py",b"x=1\n")
        self.commit_files()
        r=repair_safe_current_source(repo=self.repo)
        self.assertEqual(r["normalized_file_count"],0)
        self.assertEqual(r["status"],"CURRENT_CUMULATIVE_PATCH_ALREADY_CLEAN")
        self.assertEqual(self.git("status","--porcelain"),"")

    def test_current_cumulative_review_does_not_claim_semantic_acceptance(self):
        self.put("selenium_pipeline/x.py",b"x=1\n\n")
        self.commit_files()
        r=inspect_head_patch(repo=self.repo)
        self.assertEqual(r["status"],"CUMULATIVE_HEAD_PATCH_FORMAT_REQUIRES_REVIEW")
        self.assertFalse(r["automatic_merge_authorized"])
        self.assertFalse(r["student_publication_authorized"])
        self.assertEqual(self.git("status","--porcelain"),"")

    def test_real_preflight_missing_main_ref_still_fails_closed(self):
        self.put("selenium_pipeline/x.py", b"x=1\n")
        self.commit_files()
        self.git("update-ref", "-d", "refs/remotes/origin/main")
        with self.assertRaises(CampaignRecoveryBlocked):
            inspect_head_patch(repo=self.repo)
        with self.assertRaises(CampaignRecoveryBlocked):
            repair_safe_current_source(repo=self.repo)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_unexpected_git_stderr_cannot_be_silently_accepted(self):
        from selenium_pipeline import windows_head_whitespace_recovery as mod
        self.put("selenium_pipeline/x.py", b"x=1\n")
        self.commit_files()
        original = mod._git

        def bad_git(repo, *args):
            if args[0] == "diff":
                return subprocess.CompletedProcess(
                    args, 0, "", "fatal: unsupported object or source conflict")
            return original(repo, *args)

        with patch.object(mod, "_git", side_effect=bad_git):
            with self.assertRaises(CampaignRecoveryBlocked):
                inspect_head_patch(repo=self.repo)
            with self.assertRaises(CampaignRecoveryBlocked):
                repair_safe_current_source(repo=self.repo)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_source_pdf_cannot_be_normalized(self):
        self.put("slides.pdf",b"%PDF-1.4\n \n")
        self.commit_files()
        with self.assertRaises(CampaignRecoveryBlocked):
            repair_safe_current_source(repo=self.repo)


if __name__=="__main__":
    unittest.main()
