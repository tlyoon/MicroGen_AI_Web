"""Adversarial offline tests: no Gemini traffic, original teaching assets untouched."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from selenium_pipeline import gemini_review_backoff_checkpoint as b

PROOF="a"*64
def make_paths(where):
    root=Path(where);folder=root/"original";folder.mkdir()
    for name in ("source.pdf","slides.pdf","script.txt"):
        (folder/name).write_bytes(name.encode("utf8"))
    cp=root/"checkpoint.json"
    return folder,cp

class DurableBackoff(unittest.TestCase):
    def new(self,root):
        folder,cp=make_paths(root)
        b.initialize(checkpoint=cp,original_folder=folder,
                     job_id="slide_001_diagnostic",now=1000)
        return folder,cp

    def test_initial_and_pre_submitted_claim(self):
        with tempfile.TemporaryDirectory() as path:
            f,cp=self.new(path)
            status=b.inspect(checkpoint=cp,original_folder=f,now=1000)
            self.assertTrue(status["eligible_for_single_authorized_dispatch"])
            claim=b.claim_due(checkpoint=cp,original_folder=f,now=1000)
            self.assertTrue(claim)
            self.assertIsNone(b.claim_due(checkpoint=cp,original_folder=f,now=1000))
            self.assertTrue(b.inspect(checkpoint=cp,original_folder=f)["requires_reconciliation"])
            with self.assertRaises(ValueError):
                b.submitted(checkpoint=cp,original_folder=f,claim=claim,
                            user_turn_created=False,composer_cleared=True)
            result=b.unsent(checkpoint=cp,original_folder=f,claim=claim,
                           reason="VERIFIED_HIDDEN_SEND",now=1001)
            self.assertEqual(result["confirmed_submissions"],0)
            self.assertEqual(result["status"],"WAITING")
            self.assertGreaterEqual(result["next_due_unix_utc"]-1001,300)
            self.assertIsNone(b.claim_due(checkpoint=cp,original_folder=f,now=1002))

    def test_three_terminal_submissions_backoff_and_exhaustion(self):
        with tempfile.TemporaryDirectory() as path:
            f,cp=self.new(path)
            due=1000
            for n,minimum in [(1,300),(2,900),(3,None)]:
                token=b.claim_due(checkpoint=cp,original_folder=f,now=due)
                self.assertTrue(token)
                record=b.submitted(checkpoint=cp,original_folder=f,claim=token,
                    user_turn_created=True,composer_cleared=True,now=due)
                self.assertEqual(record["confirmed_submissions"],n)
                with self.assertRaises(ValueError):
                    b.terminal_failure(checkpoint=cp,original_folder=f,claim=token,
                        original_tab_terminal_verified=False,
                        failure="SERVER_BUSY_429",proof_sha256=PROOF,now=due+1)
                result=b.terminal_failure(checkpoint=cp,original_folder=f,claim=token,
                    original_tab_terminal_verified=True,
                    failure="SERVER_BUSY_429",proof_sha256=PROOF,now=due+1)
                if n<3:
                    self.assertEqual(result["status"],"WAITING")
                    self.assertGreaterEqual(result["next_due_unix_utc"]-due-1,minimum)
                    due=result["next_due_unix_utc"]
                else:
                    self.assertEqual(result["status"],"EXHAUSTED")
                    self.assertIsNone(result["next_due_unix_utc"])
            self.assertIsNone(b.claim_due(checkpoint=cp,original_folder=f,now=100000))

    def test_unknown_submission_stays_blocked_after_reboot(self):
        with tempfile.TemporaryDirectory() as path:
            f,cp=self.new(path)
            token=b.claim_due(checkpoint=cp,original_folder=f,now=1000)
            b.submitted(checkpoint=cp,original_folder=f,claim=token,
                        user_turn_created=True,composer_cleared=True)
            self.assertIsNone(b.claim_due(checkpoint=cp,original_folder=f,now=20000))
            outcome=b.ambiguous(checkpoint=cp,original_folder=f,claim=token)
            self.assertEqual(outcome["status"],"RECONCILIATION_REQUIRED")
            self.assertFalse(b.inspect(checkpoint=cp,original_folder=f,now=999999)
                             ["eligible_for_single_authorized_dispatch"])

    def test_source_drift_and_checkpoint_tampering_fail_closed(self):
        with tempfile.TemporaryDirectory() as path:
            f,cp=self.new(path)
            (f/"script.txt").write_text("tampered")
            with self.assertRaises(ValueError):
                b.claim_due(checkpoint=cp,original_folder=f,now=1000)
            with self.assertRaises(ValueError):
                b.inspect(checkpoint=cp,original_folder=f)
        with tempfile.TemporaryDirectory() as path:
            f,cp=self.new(path)
            st=json.loads(cp.read_text());st["student_publication_authorized"]=True
            cp.write_text(json.dumps(st))
            with self.assertRaises(ValueError):
                b.claim_due(checkpoint=cp,original_folder=f,now=1000)

    def test_duplicate_worker_lock_never_stolen(self):
        with tempfile.TemporaryDirectory() as path:
            f,cp=self.new(path)
            lock=Path(str(cp)+".lock")
            lock.write_text("another process")
            with self.assertRaises(FileExistsError):
                b.claim_due(checkpoint=cp,original_folder=f,now=1000)
            self.assertTrue(lock.exists())

    def test_retry_after_overrides_default_but_is_bounded(self):
        with tempfile.TemporaryDirectory() as path:
            f,cp=self.new(path)
            token=b.claim_due(checkpoint=cp,original_folder=f,now=1000)
            b.submitted(checkpoint=cp,original_folder=f,claim=token,
                        user_turn_created=True,composer_cleared=True)
            result=b.terminal_failure(checkpoint=cp,original_folder=f,claim=token,
                original_tab_terminal_verified=True,failure="SERVER_BUSY_429",
                proof_sha256=PROOF,retry_after_s=3600,now=1010)
            self.assertGreaterEqual(result["next_due_unix_utc"]-1010,3600)
            self.assertLessEqual(result["next_due_unix_utc"]-1010,14400)

    def test_provider_retry_after_longer_than_four_hour_cap_is_honored(self):
        with tempfile.TemporaryDirectory() as path:
            f,cp=self.new(path)
            token=b.claim_due(checkpoint=cp,original_folder=f,now=1000)
            b.submitted(checkpoint=cp,original_folder=f,claim=token,
                        user_turn_created=True,composer_cleared=True)
            result=b.terminal_failure(checkpoint=cp,original_folder=f,claim=token,
                original_tab_terminal_verified=True,failure="SERVER_UNAVAILABLE_503",
                proof_sha256=PROOF,retry_after_s=21600,now=1010)
            self.assertGreaterEqual(result["next_due_unix_utc"]-1010,21600)

    def test_real_response_capture_never_claims_mathematical_approval(self):
        with tempfile.TemporaryDirectory() as path:
            f,cp=self.new(path)
            token=b.claim_due(checkpoint=cp,original_folder=f,now=1000)
            b.submitted(checkpoint=cp,original_folder=f,claim=token,
                        user_turn_created=True,composer_cleared=True)
            receipt=Path(path)/"genuine_owned_model_reply.json"
            receipt.write_text('{"candidate":"unverified"}')
            r=b.captured_unreviewed(checkpoint=cp,original_folder=f,
                         claim=token,response_receipt=receipt)
            self.assertEqual(r["status"],"RESPONSE_CAPTURED_UNVERIFIED")
            self.assertFalse(r["student_publication_authorized"])
            self.assertIsNone(b.claim_due(checkpoint=cp,original_folder=f,now=1e8))

    def test_original_academic_three_attempts_never_reset(self):
        with tempfile.TemporaryDirectory() as path:
            folder,cp=make_paths(path)
            q=Path(path)/"original_review_queue";q.mkdir()
            hashes={key:hashlib.sha256((folder/key).read_bytes()).hexdigest()
                    for key in ("source.pdf","slides.pdf","script.txt")}
            q.joinpath("queue.json").write_text(json.dumps({
                "status":"IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
                "student_publication_authorized":False,
                "original_source_folder":str(folder),
                "expected_utterances":1,
                "slide_jobs":[{"slide":1,"utterance_count":1,
                    "original_source_sha256":hashes["source.pdf"],
                    "original_slides_sha256":hashes["slides.pdf"],
                    "original_script_sha256":hashes["script.txt"]}]}))
            (q/"slide_001_initial_review.json").write_text('{"historical":"first pass"}')
            for n in range(1,4):
                (q/f"slide_001_independent_challenge_attempt_{n:02d}.json").write_text(
                    json.dumps({"slide":1,"mode":"INDEPENDENT_CHALLENGE",
                        "attempt":n,"status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED"}))
            initial=b.initialize(checkpoint=cp,original_folder=folder,
                 queue_root=q,job_id="slide_001_independent_challenge",now=1000)
            self.assertEqual(initial["status"],"EXHAUSTED")
            self.assertEqual(initial["confirmed_submissions"],3)
            self.assertIsNone(b.claim_due(checkpoint=cp,original_folder=folder,
                                          now=1e12))
