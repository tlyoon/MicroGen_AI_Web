"""Generic original-G2 vs one-shot new-evidence accounting; no provider traffic."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.academic_review_checkpoint import submit_once
from selenium_pipeline.ai_academic_web_review import (
    review_instructions, validate_model_review)
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired, _sha
from selenium_pipeline.source_citation_targeted_challenge import (
    prepare_targeted_challenge)
from selenium_pipeline.source_citation_challenge_reconciler import reconcile
from tests.test_source_citation_targeted_challenge import NewEvidenceChallengeTests


class GenericG2ReconciliationTests(unittest.TestCase):
    def setUp(self):
        # Reuse the real-PDF/real-claim test fixture, not a fabricated file
        # path or a dummy source. No Chrome, Gemini, Whisper, TTS or MP4.
        old=NewEvidenceChallengeTests(
            methodName="test_only_original_unresolved_units_with_new_quotes_enter_fresh_challenge")
        old.setUp()
        self.addCleanup(old.doCleanups)
        self.old=old
        self.obj=prepare_targeted_challenge(
            original_job=old.job_path,
            original_checkpoint=old.checkpoint,
            new_source_quotes=old.latest)
        self.job=self.obj["source_job"]
        self.new_plan=old.root/"new_targeted_plan.json"
        self.new_plan.write_text(json.dumps(self.obj),encoding="utf8")
        self.new_checkpoint=old.root/"one_shot_new_challenge"
        self.new_result=old.root/"new_verified_response.json"
        self.baseline=old.root/"immutable_original_ledger.json"
        original=old.job
        ledger={
            "schema_version":1,
            "status":"PARTIAL_ONE_PASS_SOURCE_REVIEW_WITH_GAPS",
            "source_sha256":original["source_sha256"],
            "slides_sha256":original["slides_sha256"],
            "script_sha256":original["script_sha256"],
            "original_utterance_count":2,
            "review_batch_count":1,
            "source_supported":0,
            "source_unresolved":2,
            "source_incorrect":0,
            "untrusted_utterances":0,
            "not_yet_reviewed_utterances":0,
            "academic_science_independently_verified":False,
            "release_approved":False,
            "jobs":[{"job":old.job_path.name,"original_utterances":2}],
        }
        self.baseline.write_text(json.dumps(ledger),encoding="utf8")
        self.entries=[{"original_job":str(old.job_path),
                       "original_checkpoint":str(old.checkpoint),
                       "new_source_quotes":str(old.latest),
                       "new_plan":str(self.new_plan),
                       "new_result":str(self.new_result),
                       "new_checkpoint":str(self.new_checkpoint)}]

    def record_new(self):
        quote=self.old.quote_two
        units=self.job["slides"][0]["utterances"]
        target=self.job["slides"][0]["visual_targets"][0]["id"]
        response={"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
                  "rows":[{
                    "utterance_id":u["id"],"spoken_sha256":u["spoken_sha256"],
                    "target_id":target,"source_page":quote["source_page"],
                    "verbatim_source_quote":quote["verbatim_source_quote"],
                    "verdict":"SUPPORTED",
                    "math_explanation":"The physical citation appears in the actual source PDF; math remains unverified."
                  } for u in units]}
        request=review_instructions(self.job,mode="INDEPENDENT_CHALLENGE")
        # A deterministic callback stands in for browser responses ONLY for
        # testing the actual one-Send checkpoint/validator/reconciliation.
        result=submit_once(
            checkpoint=self.new_checkpoint,
            original_folder=self.old.folder,
            request_text=request,
            source_hashes={
                "source.pdf":self.job["source_sha256"],
                "slides.pdf":self.job["slides_sha256"],
                "script.txt":self.job["script_sha256"]},
            review_mode="INDEPENDENT_CHALLENGE",
            transport=lambda prompt,attachments: json.dumps(response),
            validator=lambda raw:validate_model_review(
                folder=self.old.folder,job=self.job,
                response=json.loads(raw),mode="INDEPENDENT_CHALLENGE"))
        self.new_result.write_text(json.dumps(result),encoding="utf8")

    def run_reconcile(self, **kw):
        return reconcile(baseline_ledger=self.baseline,entries=self.entries,
                         **kw)

    def test_real_one_shot_response_is_rechecked_without_academic_approval(self):
        originals=[x.read_bytes() for x in (
            self.old.source,self.old.slides,self.old.script,
            self.old.job_path,self.old.checkpoint/"model_response_untrusted.txt")]
        self.record_new()
        report=self.run_reconcile(allow_partial=False)
        self.assertEqual(report["original_utterance_count"],2)
        self.assertEqual(report["new_challenge_utterances_reviewed"],2)
        self.assertEqual(report["new_independently_source_witnessed_model_supported"],2)
        self.assertEqual(report["source_supported_with_new_challenges"],2)
        self.assertEqual(report["source_unresolved_with_new_challenges"],0)
        self.assertFalse(report["academic_science_independently_verified"])
        self.assertFalse(report["full_element_narration_synchronization_verified"])
        self.assertFalse(report["independent_acoustic_approval"])
        self.assertFalse(report["G2_approved"])
        self.assertFalse(report["student_publication_authorized"])
        self.assertEqual([x.read_bytes() for x in (
            self.old.source,self.old.slides,self.old.script,
            self.old.job_path,self.old.checkpoint/"model_response_untrusted.txt")],
            originals)

    def test_no_saved_response_cannot_be_implicitly_counted(self):
        report=self.run_reconcile()
        self.assertEqual(report["source_supported_with_new_challenges"],0)
        self.assertEqual(report["source_unresolved_with_new_challenges"],2)
        self.assertEqual(report["new_challenge_utterances_not_confirmed"],2)
        with self.assertRaises(FigureIdentityReviewRequired):
            self.run_reconcile(allow_partial=False)

    def test_tampered_model_reply_or_claimed_result_rejected(self):
        self.record_new()
        response=self.new_checkpoint/"model_response_untrusted.txt"
        response.write_bytes(response.read_bytes()+b"\n")
        with self.assertRaises(FigureIdentityReviewRequired):
            self.run_reconcile()

    def test_fake_supported_verdict_in_summary_rejected(self):
        self.record_new()
        result=json.loads(self.new_result.read_text("utf8"))
        result["rows"][0]["verdict"]="INCORRECT"
        self.new_result.write_text(json.dumps(result),encoding="utf8")
        with self.assertRaises(FigureIdentityReviewRequired):
            self.run_reconcile()

    def test_cross_job_reuse_of_manifest_entry_is_rejected(self):
        self.record_new()
        self.entries.append(self.entries[0])
        with self.assertRaises(FigureIdentityReviewRequired):
            self.run_reconcile()


if __name__=="__main__":
    unittest.main()
