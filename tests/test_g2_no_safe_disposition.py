"""No-Send G2 blocked-history checkpoint fault injections (no Gemini transport)."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.g2_no_safe_disposition import (
    preserve_g2_no_safe_disposition,RECOVERY_REGISTRY)

class OriginalG2NoSafeCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name)
        self.folder=base/"original"
        self.queue=base/"queue"
        self.work=base/"work"
        for p in (self.folder,self.queue,self.work):p.mkdir()
        (self.folder/"source.pdf").write_bytes(b"%PDF-1.4 Original test source (do not send)")
        self.sha=hashlib.sha256((self.folder/"source.pdf").read_bytes()).hexdigest()
        self.plan={
            "status":"IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
            "original_source_folder":str(self.folder),
            "slide_jobs":[{"slide":1,"original_source_sha256":self.sha},
                          {"slide":4,"original_source_sha256":self.sha}],
            "student_publication_authorized":False}
        self.save_queue()
        self.one=self.queue/"slide_001_initial_review_attempt_01.json"
        self.one.write_text(json.dumps({
            "slide":1,"mode":"INITIAL_REVIEW","attempt":1,
            "status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED",
            "provider_submission_state":"UNKNOWN_AFTER_POSSIBLE_SUBMISSION",
            "manual_retry_eligible":False}),encoding="utf8")
        self.claim=self.queue/"slide_001_initial_review_attempt_01_request"
        self.claim.mkdir()
        (self.claim/"dispatch_attempted.claim").write_text("owned claimant",encoding="utf8")
        self.four=self.queue/"slide_004_independent_challenge_attempt_01_request"
        self.four.mkdir()
        (self.four/"dispatch_attempted.claim").write_text("owned claimant",encoding="utf8")
        self.selection={
            "status":"NO_SAFE_REVIEW_UNIT_REMAINING",
            "new_model_requests":False,"student_publication_authorized":False,
            "blocked_other_slides":[
                {"slide":1,"mode":"INITIAL_REVIEW",
                 "reason":"RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND"},
                {"slide":4,"mode":"INDEPENDENT_CHALLENGE",
                 "reason":"AMBIGUOUS_OLD_SEND_NO_RESUBMISSION"},
            ]}
    def save_queue(self):
        (self.queue/"queue.json").write_text(
            json.dumps(self.plan),encoding="utf8")
    def call(self,registry_path=None):
        return preserve_g2_no_safe_disposition(
            queue_root=self.queue,folder=self.folder,work_root=self.work,
            source_sha=self.sha,selection=self.selection,
            registry_path=registry_path)
    def test_persist_source_bound_disposition_idempotently(self):
        result=self.call()
        self.assertEqual(result["status"],"G2_HISTORICAL_CLAIMS_PRESERVED_NO_SEND")
        self.assertEqual(result["blocked_review_units"],2)
        self.assertEqual(result["new_provider_requests"],0)
        self.assertFalse(result["old_original_claims_replayed"])
        self.assertFalse(result["offline_work_executed"])
        saved=Path(result["receipt"])
        self.assertTrue(saved.is_file())
        self.assertEqual(self.call()["receipt"],str(saved))
        self.assertEqual(len(list(saved.parent.glob("*.json"))),1)
        data=json.loads(saved.read_text())
        self.assertEqual(data["original_source_sha256"],self.sha)
        self.assertFalse(data["student_publication_authorized"])
    def test_missing_original_response_never_becomes_permission_to_send(self):
        result=self.call()
        self.assertTrue(Path(result["receipt"]).is_file())
        self.assertEqual(result["new_provider_requests"],0)
        self.assertFalse(result["student_publication_authorized"])
    def test_saved_response_in_uncertain_claim_requires_reconciliation(self):
        (self.claim/"model_response_untrusted.txt").write_text(
            "unvalidated answer",encoding="utf8")
        with self.assertRaises(Exception):self.call()
        self.assertFalse((self.work/"g2_no_safe_dispositions").exists())
    def test_changed_original_source_fails_closed(self):
        (self.folder/"source.pdf").write_bytes(b"tampered")
        with self.assertRaises(Exception):self.call()
    def test_unknown_reason_fails_closed(self):
        self.selection["blocked_other_slides"][0]["reason"]="AUTO_SEND_REPLACEMENT"
        with self.assertRaises(Exception):self.call()
    def test_eligible_unit_cannot_be_recorded_as_blocked(self):
        self.selection["status"]="ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY"
        with self.assertRaises(Exception):self.call()
    def test_missing_historical_claim_fails_closed(self):
        (self.four/"dispatch_attempted.claim").unlink()
        with self.assertRaises(Exception):self.call()
    def test_registry_disabled_and_foreign_mechanisms_block(self):
        conf=json.loads(RECOVERY_REGISTRY.read_text(encoding="utf8"))
        path=self.work/"registry.json"
        conf["enabled"]=False
        path.write_text(json.dumps(conf),encoding="utf8")
        with self.assertRaises(Exception):self.call(path)
        conf["enabled"]=True
        conf["mechanism"]="REPLAY_AMBIGUOUS_GEMINI_SEND"
        path.write_text(json.dumps(conf),encoding="utf8")
        with self.assertRaises(Exception):self.call(path)
    def test_tampered_prior_disposition_not_silently_overwritten(self):
        output=self.call()
        Path(output["receipt"]).write_text('{"status":"forged"}',encoding="utf8")
        with self.assertRaises(Exception):self.call()

if __name__=="__main__":unittest.main()


def test_pre_send_request_state_without_completed_attempt_is_preserved():
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as temp:
        root = Path(temp)
        original, queue, work = [root / n for n in ("original", "queue", "work")]
        for x in (original, queue, work):
            x.mkdir()
        source = original / "source.pdf"
        slides = original / "slides.pdf"
        script = original / "script.txt"
        for path, data in ((source, b"%PDF-1.4 genuine source"),
                           (slides, b"%PDF-1.4 slides"),
                           (script, b"source-narrated script")):
            path.write_bytes(data)
        digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
        (queue / "queue.json").write_text(json.dumps({
            "status": "IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
            "original_source_folder": str(original),
            "slide_jobs": [{"slide":4, "original_source_sha256":digest(source)}],
            "student_publication_authorized": False,
        }))
        claim_root = queue / "slide_004_independent_challenge_attempt_01_request"
        claim_root.mkdir()
        (claim_root / "dispatch_attempted.claim").write_text("original")
        state = {
            "schema_version": 1, "status": "SUBMITTED_OR_UNCERTAIN",
            "review_mode": "INDEPENDENT_CHALLENGE",
            "source_sha256": digest(source),
            "slides_sha256": digest(slides), "script_sha256": digest(script),
            "can_auto_retry": False, "submission_may_have_occurred": True,
        }
        state_file = claim_root / "request_state.json"
        state_file.write_text(json.dumps(state))
        selection = {
            "status": "NO_SAFE_REVIEW_UNIT_REMAINING",
            "new_model_requests": False, "student_publication_authorized": False,
            "blocked_other_slides": [{"slide":4, "mode":"INDEPENDENT_CHALLENGE",
                                      "reason": "AMBIGUOUS_OLD_SEND_NO_RESUBMISSION"}],
        }
        call = lambda: preserve_g2_no_safe_disposition(
            queue_root=queue, folder=original, work_root=work,
            source_sha=digest(source), selection=selection)
        result = call()
        row = json.loads(Path(result["receipt"]).read_text())["blocked"][0]["attempts"][0]
        assert row["status"] == "SUBMITTED_OR_UNCERTAIN_NO_REPLY"
        assert row["claim_present"] is True
        assert row["quarantine_capture"]["retry_authorized"] is False
        assert result["new_provider_requests"] == 0
        assert call()["receipt"] == result["receipt"]
        # Forged request-state source identity must never be accepted.
        state["slides_sha256"] = "0" * 64
        state_file.write_text(json.dumps(state))
        with __import__("pytest").raises(ValueError):
            call()
