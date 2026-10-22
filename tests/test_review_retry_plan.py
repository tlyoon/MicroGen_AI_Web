import tempfile,unittest,json,hashlib
from pathlib import Path
from selenium_pipeline.review_retry_plan import plan_manual_review_attempt
class ManualRetry(unittest.TestCase):
 def make(self,p):
    r=Path(p);s=r/"source";s.mkdir();q=r/"queue";q.mkdir()
    refs={}
    for name in ("source.pdf","slides.pdf","script.txt"):
        (s/name).write_text(name)
        refs[name]=hashlib.sha256(name.encode()).hexdigest()
    (q/"queue.json").write_text(json.dumps({"status":"IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
        "student_publication_authorized":False,"original_source_folder":str(s),
        "expected_utterances":1,"slide_jobs":[{"slide":1,"utterance_count":1,
            "original_source_sha256":refs["source.pdf"],
            "original_slides_sha256":refs["slides.pdf"],
            "original_script_sha256":refs["script.txt"]}]}))
    return q
 def test_explicit_only_and_exhaustion(self):
    with tempfile.TemporaryDirectory() as d:
        q=self.make(d);self.assertFalse(plan_manual_review_attempt(q,slide=1,mode="INITIAL_REVIEW")["dispatch_authorized"])
        for n in range(1,4):
            (q/f"slide_001_initial_review_attempt_{n:02d}.json").write_text(json.dumps({
                "status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED","slide":1,
                "mode":"INITIAL_REVIEW","attempt":n}))
        result=plan_manual_review_attempt(q,slide=1,mode="INITIAL_REVIEW")
        self.assertEqual(result["status"],"MAX_THREE_ATTEMPTS_EXHAUSTED")
        self.assertIsNone(result["next_possible_attempt"])
 def test_skipped_or_inconsistent_attempt_fails_closed(self):
    with tempfile.TemporaryDirectory() as d:
        q=self.make(d)
        (q/"slide_001_initial_review_attempt_02.json").write_text(json.dumps({
            "status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED","slide":1,
            "mode":"INITIAL_REVIEW","attempt":2}))
        with self.assertRaises(ValueError):plan_manual_review_attempt(q,slide=1,mode="INITIAL_REVIEW")
 def test_challenge_requires_real_first_pass(self):
    with tempfile.TemporaryDirectory() as d:
        q=self.make(d)
        result=plan_manual_review_attempt(q,slide=1,mode="INDEPENDENT_CHALLENGE")
        self.assertEqual(result["status"],"BLOCKED_MISSING_INITIAL_REVIEW")
