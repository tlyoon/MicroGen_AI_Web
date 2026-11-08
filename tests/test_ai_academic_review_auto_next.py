"""Normal academic queue chooses next safe source claim, no manual slide input."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from selenium_pipeline.ai_academic_review_queue import (
    advance_one_safe_review,execute_one_review,
    prepare_resumable_review,select_next_safe_review)
from selenium_pipeline.academic_review_checkpoint import (
    prepare,mark_submission_maybe,record_observation)
from selenium_pipeline.ai_academic_web_review import build_review_job,review_instructions
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_original_packet_evidence_audit import fixture
from test_ai_academic_web_review import response


class AutomaticSourceBoundReviewQueue(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.folder=self.root/"original"
        fixture(self.folder)
        deck=self.folder/"slides.pdf"
        with pymupdf.open(deck) as pdf:
            page=pdf.new_page(width=300,height=300)
            page.insert_text((20,30),"A visible equation")
            pdf.save(self.root/"new_slides.pdf")
        (self.root/"new_slides.pdf").replace(deck)
        (self.folder/"script.txt").write_text(
            "**Slide 1 [1 sec]:\nA visible equation**\n"
            "**Slide 2 [1 sec]:\nA visible equation**\n",encoding="utf8")
        self.queue=self.root/"queue"
        prepare_resumable_review(folder=self.folder,output_root=self.queue,
                                 slide_numbers=[1,2])
        self.source_before={p.name:p.read_bytes()
                            for p in self.folder.iterdir() if p.is_file()}
        self.sent=[]

    def fake_response(self,prompt,files):
        for slide in (1,2):
            job=build_review_job(folder=self.folder,slide_numbers=[slide])
            if job["slides"][0]["utterances"][0]["id"] in prompt:
                draft=response()
                original=job["slides"][0]["utterances"][0]
                draft["rows"][0]["utterance_id"]=original["id"]
                draft["rows"][0]["spoken_sha256"]=original["spoken_sha256"]
                draft["rows"][0]["target_id"]=job["slides"][0]["visual_targets"][0]["id"]
                self.sent.append(slide)
                return json.dumps(draft)
        raise AssertionError("No source-grounded slide job present")

    def test_auto_choose_and_advance_all_without_ever_repeating_completed_pass(self):
        first=select_next_safe_review(queue_root=self.queue,folder=self.folder)
        self.assertEqual((first["next_slide"],first["next_mode"]),
                         (1,"INITIAL_REVIEW"))
        self.assertFalse(first["new_model_requests"])
        self.assertFalse(first["per_slide_approval_required"])
        expected=[(1,"INITIAL_REVIEW"),(1,"INDEPENDENT_CHALLENGE"),
                  (2,"INITIAL_REVIEW"),(2,"INDEPENDENT_CHALLENGE")]
        for slide,mode in expected:
            result=advance_one_safe_review(queue_root=self.queue,
                                           folder=self.folder,execute=True,
                                           transport=self.fake_response)
            self.assertEqual(result["status"],
                             "ONE_AUTONOMOUS_ACADEMIC_REVIEW_ATTEMPT_FINISHED")
            self.assertEqual(
                (result["selection"]["next_slide"],
                 result["selection"]["next_mode"]), (slide,mode))
            self.assertEqual(result["review"]["status"],
                             "GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED")
            self.assertTrue(result["no_auto_chain"])
            self.assertFalse(result["student_publication_authorized"])
        self.assertEqual(self.sent,[1,1,2,2])
        result=advance_one_safe_review(queue_root=self.queue,folder=self.folder,
                                       execute=True,transport=self.fake_response)
        self.assertEqual(result["status"],"ALL_ACADEMIC_REVIEW_PASSES_RECORDED")
        self.assertEqual(self.sent,[1,1,2,2])
        self.assertEqual(self.source_before,
                         {p.name:p.read_bytes() for p in self.folder.iterdir()
                          if p.is_file()})

    def test_prior_ambiguous_send_is_skipped_never_resubmitted(self):
        job=build_review_job(folder=self.folder,slide_numbers=[1])
        prompt=review_instructions(job,mode="INITIAL_REVIEW")
        checkpoint=self.queue/"slide_001_initial_review_attempt_01_request"
        refs={filename:job[k] for filename,k in
              (("source.pdf","source_sha256"),
               ("slides.pdf","slides_sha256"),
               ("script.txt","script_sha256"))}
        claimed=prepare(checkpoint=checkpoint,original_folder=self.folder,
                        request_text=prompt,source_hashes=refs,
                        review_mode="INITIAL_REVIEW")
        mark_submission_maybe(checkpoint,
                              expected_fingerprint=claimed["request_fingerprint"])
        planned=select_next_safe_review(queue_root=self.queue,
                                        folder=self.folder)
        self.assertEqual(planned["next_slide"],2)
        self.assertEqual(planned["next_mode"],"INITIAL_REVIEW")
        self.assertEqual(planned["blocked_other_slides"],[
            {"slide":1,"mode":"INITIAL_REVIEW",
             "reason":"AMBIGUOUS_OLD_SEND_NO_RESUBMISSION"}])
        result=advance_one_safe_review(queue_root=self.queue,
                                       folder=self.folder,execute=True,
                                       transport=self.fake_response)
        self.assertEqual(result["review"]["slide"],2)
        self.assertEqual(self.sent,[2])
        self.assertTrue((checkpoint/"dispatch_attempted.claim").is_file())

    def test_unknown_failed_receipt_does_not_reset_attempts(self):
        path=self.queue/"slide_001_initial_review_attempt_01.json"
        path.write_text(json.dumps({
            "status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED",
            "slide":1,"mode":"INITIAL_REVIEW","attempt":1,
            "provider_submission_state":"UNKNOWN_AFTER_POSSIBLE_SUBMISSION",
            "manual_retry_eligible":False,
        }),encoding="utf8")
        planned=select_next_safe_review(queue_root=self.queue,
                                        folder=self.folder)
        self.assertEqual(planned["next_slide"],2)
        self.assertEqual(planned["blocked_other_slides"][0]["reason"],
                         "RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND")
        self.assertEqual(self.sent,[])

    def test_auto_reconciles_same_saved_response_without_second_send(self):
        job=build_review_job(folder=self.folder,slide_numbers=[1])
        prompt=review_instructions(job,mode="INITIAL_REVIEW")
        checkpoint=self.queue/"slide_001_initial_review_attempt_01_request"
        refs={filename:job[key] for filename,key in
              (("source.pdf","source_sha256"),
               ("slides.pdf","slides_sha256"),
               ("script.txt","script_sha256"))}
        state=prepare(checkpoint=checkpoint,original_folder=self.folder,
                      request_text=prompt,source_hashes=refs,
                      review_mode="INITIAL_REVIEW")
        mark_submission_maybe(
            checkpoint,expected_fingerprint=state["request_fingerprint"])
        raw=self.fake_response(prompt,[])
        self.sent.clear()
        record_observation(
            checkpoint,raw=raw,
            expected_fingerprint=state["request_fingerprint"])
        planned=select_next_safe_review(queue_root=self.queue,folder=self.folder)
        self.assertEqual(planned["next_slide"],1)
        self.assertEqual(planned["action"],"RECONCILE_PRIOR_RESPONSE_NO_SEND")
        with patch("selenium_pipeline.ai_academic_web_review._browser_request",
                   side_effect=AssertionError("saved reply must not resend")) as send:
            recovered=advance_one_safe_review(
                queue_root=self.queue,folder=self.folder,execute=True)
        send.assert_not_called()
        self.assertEqual(recovered["review"]["status"],
                         "GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED")
        self.assertEqual(self.sent,[])
        self.assertEqual(recovered["new_provider_sends_this_invocation_upper_bound"],1)
        self.assertFalse(recovered["new_provider_send_proved_by_this_summary"])

    def test_invalid_claimed_source_quote_does_not_hold_unrelated_slides(self):
        path=self.queue/"slide_001_initial_review_attempt_01.json"
        path.write_text(json.dumps({
            "status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED",
            "slide":1,"mode":"INITIAL_REVIEW","attempt":1,
            "provider_submission_state":"RETURNED_RESPONSE_INVALID",
            "manual_retry_eligible":False,
            "requires_owner_reconciliation":False,
            "requires_new_independent_source_evidence":True,
        }),encoding="utf8")
        planned=select_next_safe_review(queue_root=self.queue,folder=self.folder)
        self.assertEqual(planned["next_slide"],2)
        self.assertEqual(planned["blocked_other_slides"][0]["reason"],
                         "SOURCE_MATH_QUOTE_EVIDENCE_REJECTED_NO_SAME_REQUEST_REPEAT")
        self.assertEqual(self.sent,[])

    def test_source_drift_aborts_automatic_queue_without_send(self):
        (self.folder/"script.txt").write_text("changed")
        with self.assertRaises((FigureIdentityReviewRequired,ValueError)):
            advance_one_safe_review(queue_root=self.queue,
                                    folder=self.folder,execute=True,
                                    transport=self.fake_response)
        self.assertFalse(self.sent)


    def _three_slide_queue_with_two_unattributed_requests(self):
        # Unrelated fixture: never uses the real Serway textbook or its
        # private browser. Both independent browser operations were claimed,
        # and neither has an attributable completion receipt.
        deck=self.folder/"slides.pdf"
        with pymupdf.open(deck) as doc:
            page=doc.new_page(width=300,height=300)
            page.insert_text((20,30),"A visible equation")
            doc.save(self.root/"three_slides.pdf")
        (self.root/"three_slides.pdf").replace(deck)
        with (self.folder/"script.txt").open("a",encoding="utf8") as out:
            out.write("**Slide 3 [1 sec]:\\nA visible equation**\\n")
        queue=self.root/"three_slide_queue"
        prepare_resumable_review(folder=self.folder,output_root=queue,
                                 slide_numbers=[1,2,3])
        for n in (1,2):
            receipt=queue/f"slide_{n:03d}_initial_review_attempt_01.json"
            receipt.write_text(json.dumps({
                "status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED",
                "slide":n,"mode":"INITIAL_REVIEW","attempt":1,
                "provider_submission_state":"UNKNOWN_AFTER_POSSIBLE_SUBMISSION",
                "manual_retry_eligible":False,
            }),encoding="utf8")
        return queue

    def test_two_unattributed_browser_sends_pause_new_review_without_send(self):
        queue=self._three_slide_queue_with_two_unattributed_requests()
        planned=select_next_safe_review(queue_root=queue,folder=self.folder)
        self.assertEqual(planned["status"],
                         "DEFERRED_REPEATED_UNATTRIBUTED_BROWSER_SEND")
        self.assertEqual(planned["unattributed_prior_slides"],[1,2])
        self.assertEqual(planned["unattempted_candidate_slide"],3)
        self.assertFalse(planned["new_model_requests"])
        self.assertFalse(planned["per_slide_approval_required"])
        calls=[]
        def forbidden(*args):
            calls.append(args)
            raise AssertionError("No third Send after two ambiguous claims")
        deferred=advance_one_safe_review(
            queue_root=queue,folder=self.folder,
            execute=True,transport=forbidden)
        self.assertEqual(deferred["status"],planned["status"])
        with self.assertRaisesRegex(
                FigureIdentityReviewRequired,
                "DEFERRED_REPEATED_UNATTRIBUTED_BROWSER_SEND"):
            execute_one_review(
                queue_root=queue,folder=self.folder,slide=3,
                mode="INITIAL_REVIEW",transport=forbidden)
        self.assertFalse(calls)
        self.assertFalse(
            (queue/"slide_003_initial_review_attempt_01_request").exists())
        self.assertFalse(
            (queue/"slide_003_initial_review_attempt_01.json").exists())

    def test_existing_owned_saved_response_remains_reconcilable(self):
        queue=self._three_slide_queue_with_two_unattributed_requests()
        job=build_review_job(folder=self.folder,slide_numbers=[3])
        prompt=review_instructions(job,mode="INITIAL_REVIEW")
        claim=queue/"slide_003_initial_review_attempt_01_request"
        refs={name:job[key] for name,key in (
            ("source.pdf","source_sha256"),("slides.pdf","slides_sha256"),
            ("script.txt","script_sha256"))}
        prepared=prepare(checkpoint=claim,original_folder=self.folder,
                         request_text=prompt,source_hashes=refs,
                         review_mode="INITIAL_REVIEW")
        # A previously captured raw response is eligible for evidence-only
        # replay; it is NOT proof of valid scientific or source content.
        mark_submission_maybe(
            claim,expected_fingerprint=prepared["request_fingerprint"])
        record_observation(
            claim,raw='{"untrusted":"saved response"}',
            expected_fingerprint=prepared["request_fingerprint"])
        planned=select_next_safe_review(queue_root=queue,folder=self.folder)
        self.assertEqual(planned["next_slide"],3)
        self.assertEqual(planned["action"],"RECONCILE_PRIOR_RESPONSE_NO_SEND")
        self.assertFalse(planned["new_model_requests"])

if __name__=="__main__":
    unittest.main()
