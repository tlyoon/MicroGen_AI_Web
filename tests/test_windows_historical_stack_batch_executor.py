"""Windows real-Git offline history runner: fault injection, no model/merge."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.original_multisource_recovery_campaign import CampaignRecoveryBlocked
from selenium_pipeline.windows_historical_stack_batch_executor import execute_batches


class HistoricalBatchExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.local = Path(self.temp.name)
        patcher = patch.dict(os.environ, {"LOCALAPPDATA": str(self.local)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.repo = self.local / "source_free_git_repo"
        self.repo.mkdir()
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "Offline fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.add("README.md", "Clean base\n")
        self.base=self.git("rev-parse", "HEAD")
        self.git("update-ref", "refs/remotes/origin/main", self.base)
        self.git("switch", "-c", "feature/offline-batches")
        self.add("selenium_pipeline/sample.py", "def value():\n    return 1\n")
        self.add("tests/test_sample.py", "def test_mock():\n    assert True\n")
        self.add("docs/work.md", "review only\n")

    def git(self,*args):
        result=subprocess.run(["git","-C",str(self.repo),*args],
                              capture_output=True,text=True,encoding="utf8",
                              errors="replace",timeout=30)
        if result.returncode:
            self.fail(repr((args,result.stderr)))
        return result.stdout.strip()

    def add(self,path,content):
        p=self.repo/path
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(content,encoding="utf8")
        self.git("add", "--", path)
        self.git("commit", "-m", "synthetic "+path)

    def audit(self,**kw):
        return execute_batches(repo=self.repo,batch_size=2,**kw)

    def test_two_batches_real_commits_are_checked_and_receipts_resume(self):
        before=self.git("rev-parse","HEAD")
        x=self.audit()
        self.assertEqual(x["status"],
                         "OFFLINE_BATCH_PATCH_CHECKS_COMPLETE_CODE_REVIEW_PENDING")
        self.assertEqual(x["batch_count_completed"],2)
        self.assertEqual(x["commits_checked_or_reused"],3)
        self.assertEqual(x["saved_receipts_reused"],0)
        self.assertEqual(x["quarantined_batch_numbers"],[])
        for b in x["batch_receipts"]:
            self.assertEqual(b["patch_check_failure_count"],0)
            self.assertEqual(b["model_or_tts_calls"],0)
            self.assertFalse(b["semantic_code_review_completed"])
            self.assertFalse(b["automatic_merge_authorized"])
            self.assertFalse(b["student_publication_authorized"])
            self.assertTrue(Path(b["receipt_path"]).is_file())
        # Fast checkpoint resume: any attempt to re-run patch checker is a bug.
        with patch("selenium_pipeline.windows_historical_stack_batch_executor._check_commit",
                   side_effect=AssertionError("Should reuse verified receipt")):
            y=self.audit()
        self.assertEqual(y["saved_receipts_reused"],2)
        self.assertEqual(self.git("rev-parse","HEAD"),before)
        self.assertEqual(self.git("status","--porcelain"),"")

    def test_real_git_intermediate_whitespace_bad_then_reverted_is_quarantined(self):
        # Newest batch's transient edit is visible even though endpoint
        # content is identical to the previous commit.
        self.add("selenium_pipeline/sample.py",
                 "def value():\n    return 1   \n")
        self.add("selenium_pipeline/sample.py",
                 "def value():\n    return 1\n")
        z=self.audit()
        self.assertIn(2,z["quarantined_batch_numbers"])
        self.assertEqual(z["status"],"OFFLINE_BATCH_PATCH_FINDINGS_REVIEW_REQUIRED")
        self.assertEqual(z["batch_count_completed"],3)
        self.assertEqual(z["batch_receipts"][1]["patch_check_failure_count"],1)
        self.assertEqual(z["batch_receipts"][2]["patch_check_failure_count"],0)
        self.assertFalse(z["automatic_merge_authorized"])
        self.assertFalse(z["student_publication_authorized"])
        # Existing source files are not rewritten or patched.
        self.assertEqual((self.repo/"selenium_pipeline"/"sample.py").read_text(),
                         "def value():\n    return 1\n")

    def test_disabled_registry_is_not_silently_bypassed(self):
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with self.assertRaises(CampaignRecoveryBlocked):
                self.audit()
        self.assertFalse((self.local/"MicroGen_AI_Web_Checkpoints").exists())

    def test_dirty_source_checkout_cannot_start_integrity_audit(self):
        (self.repo/"README.md").write_text("modified uncommitted")
        with self.assertRaises(CampaignRecoveryBlocked):
            self.audit()

    def test_receipt_corruption_fails_closed(self):
        x=self.audit(first_batch=1,last_batch=1)
        path=Path(x["batch_receipts"][0]["receipt_path"])
        obj=json.loads(path.read_text())
        obj["exact_head_sha"]="f"*40
        path.write_text(json.dumps(obj),encoding="utf8")
        with self.assertRaises(CampaignRecoveryBlocked):
            self.audit(first_batch=1,last_batch=1)

    def test_exact_new_head_produces_new_immutable_receipt(self):
        old=self.audit()
        self.add("README.md", "new bounded commit\n")
        new=self.audit()
        self.assertEqual(new["saved_receipts_reused"],0)
        self.assertNotEqual(new["exact_head_sha"],old["exact_head_sha"])
        self.assertNotEqual(new["batch_receipts"][0]["receipt_path"],
                            old["batch_receipts"][0]["receipt_path"])

    def test_unknown_batch_number_is_rejected(self):
        for opts in (dict(first_batch=0,last_batch=1),
                     dict(first_batch=2,last_batch=1),
                     dict(first_batch=1,last_batch=99)):
            with self.subTest(opts=opts):
                with self.assertRaises(CampaignRecoveryBlocked):
                    self.audit(**opts)

    def test_partial_resume_then_auto_forward_next_independent_batch(self):
        first=self.audit(first_batch=1,last_batch=1)
        self.assertEqual(first["batch_count_completed"],1)
        rest=self.audit()
        self.assertEqual(rest["batch_count_completed"],2)
        self.assertEqual(rest["saved_receipts_reused"],1)
        self.assertFalse(rest["full_historical_stack_reviewer_acceptance"])

    def test_subprocess_timeout_fails_closed(self):
        def timed_out(*args, **kw):
            raise subprocess.TimeoutExpired(args[0],30)
        with self.assertRaises(CampaignRecoveryBlocked):
            self.audit(first_batch=1,last_batch=1,run=timed_out)

    def test_normal_planner_cli_is_wired_to_executor(self):
        from io import StringIO
        from contextlib import redirect_stdout
        from selenium_pipeline.windows_historical_stack_batch_plan import main
        out=StringIO()
        with redirect_stdout(out):
            code=main(["--repo",str(self.repo),"--batch-size","2",
                       "--execute-offline-history-checks",
                       "--first-batch","1","--last-batch","1"])
        self.assertEqual(code,0)
        obj=json.loads(out.getvalue())
        self.assertEqual(obj["batch_count_completed"],1)
        self.assertFalse(obj["student_publication_authorized"])


if __name__=="__main__":
    unittest.main()
