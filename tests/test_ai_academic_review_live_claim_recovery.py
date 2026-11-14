"""Normal source-grounded reviewer uses durable one-send claims and saved-response reuse."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.academic_review_checkpoint import (
    prepare, mark_submission_maybe, record_observation, fingerprint)
from selenium_pipeline.ai_academic_review_queue import (
    prepare_resumable_review, execute_one_review)
from selenium_pipeline.ai_academic_web_review import (
    build_review_job, review_instructions)
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

from test_ai_academic_web_review import response
from test_original_packet_evidence_audit import fixture


class RealAcademicQueueCrashSafety(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.folder = self.root / "source"
        fixture(self.folder)
        (self.folder / "script.txt").write_text(
            "**Slide 1 [1 sec]:\nA visible equation**\n", encoding="utf-8")
        self.queue = self.root / "queue"
        prepare_resumable_review(
            folder=self.folder, output_root=self.queue, slide_numbers=[1])
        self.job = build_review_job(folder=self.folder, slide_numbers=[1])
        self.checkpoint = self.queue / "slide_001_initial_review_attempt_01_request"
        self.source_before = {x.name: x.read_bytes()
                              for x in self.folder.iterdir() if x.is_file()}

    def candidate(self):
        proposal = response()
        unit = self.job["slides"][0]["utterances"][0]
        proposal["rows"][0]["spoken_sha256"] = unit["spoken_sha256"]
        proposal["rows"][0]["target_id"] = (
            self.job["slides"][0]["visual_targets"][0]["id"])
        return json.dumps(proposal)

    def prove_source_preserved(self):
        self.assertEqual(self.source_before,
                         {x.name: x.read_bytes()
                          for x in self.folder.iterdir() if x.is_file()})

    def stage_claim_without_dispatch(self):
        hashes = {name:self.job[key] for name,key in (
            ("source.pdf", "source_sha256"),
            ("slides.pdf", "slides_sha256"),
            ("script.txt", "script_sha256"))}
        prompt = review_instructions(self.job, mode="INITIAL_REVIEW")
        state = prepare(
            checkpoint=self.checkpoint, original_folder=self.folder,
            request_text=prompt, source_hashes=hashes,
            review_mode="INITIAL_REVIEW")
        claim = mark_submission_maybe(
            self.checkpoint, expected_fingerprint=state["request_fingerprint"])
        self.assertTrue(claim["submission_may_have_occurred"])
        return state

    def test_live_browser_receives_claim_before_single_send(self):
        calls = []

        def browser(prompt, files, **kwargs):
            calls.append(1)
            self.assertTrue((self.checkpoint / "dispatch_attempted.claim").is_file())
            live = json.loads(
                (self.checkpoint / "request_state.json").read_text(encoding="utf-8"))
            self.assertEqual(live["status"], "SUBMITTED_OR_UNCERTAIN")
            self.assertEqual([p.name for p in files],
                             ["source.pdf", "slides.pdf"])
            return self.candidate()

        with patch("selenium_pipeline.ai_academic_web_review._browser_request",
                   side_effect=browser):
            accepted = execute_one_review(
                queue_root=self.queue, folder=self.folder, slide=1,
                mode="INITIAL_REVIEW", attempt=1)
        self.assertEqual(accepted["status"],
                         "GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED")
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            json.loads((self.checkpoint/"request_state.json")
                       .read_text(encoding="utf-8"))["status"],
            "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED")
        self.assertTrue((self.queue/"slide_001_initial_review.json").is_file())
        with self.assertRaises(FigureIdentityReviewRequired):
            execute_one_review(queue_root=self.queue,folder=self.folder,
                               slide=1,mode="INITIAL_REVIEW",attempt=2)
        self.assertEqual(len(calls), 1)
        self.prove_source_preserved()

    def test_crash_after_saved_reply_recovers_same_bytes_without_send(self):
        state = self.stage_claim_without_dispatch()
        record_observation(
            self.checkpoint, raw=self.candidate(),
            expected_fingerprint=state["request_fingerprint"])
        with patch("selenium_pipeline.ai_academic_web_review._browser_request",
                   side_effect=AssertionError("New browser Send prohibited")) as browser:
            accepted=execute_one_review(
                queue_root=self.queue,folder=self.folder,
                slide=1,mode="INITIAL_REVIEW")
        self.assertEqual(accepted["status"],
                         "GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED")
        browser.assert_not_called()
        self.assertTrue((self.queue/"slide_001_initial_review.json").is_file())
        self.assertEqual(json.loads((self.checkpoint/"request_state.json")
                                   .read_text())["status"],
                         "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED")
        self.prove_source_preserved()

    def test_invalid_claimed_browser_reply_cannot_replay_same_request(self):
        with patch("selenium_pipeline.ai_academic_web_review._browser_request",
                   return_value='{"status":"not a valid source review"}') as browser:
            failed = execute_one_review(
                queue_root=self.queue,folder=self.folder,
                slide=1,mode="INITIAL_REVIEW",attempt=1)
        self.assertEqual(failed["status"],
                         "FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED")
        self.assertEqual(failed["provider_submission_state"],
                         "RETURNED_RESPONSE_INVALID")
        self.assertFalse(failed["manual_retry_eligible"])
        self.assertFalse(failed["requires_owner_reconciliation"])
        self.assertTrue(failed["requires_new_independent_source_evidence"])
        self.assertTrue(failed["can_advance_other_unattempted_slides"])
        self.assertEqual(browser.call_count, 1)
        self.assertTrue((self.checkpoint/"dispatch_attempted.claim").exists())
        with self.assertRaises(FigureIdentityReviewRequired):
            execute_one_review(queue_root=self.queue,folder=self.folder,
                               slide=1,mode="INITIAL_REVIEW",attempt=2)
        self.assertEqual(browser.call_count, 1)
        self.prove_source_preserved()

    def test_ambiguous_send_never_resubmits_even_with_retry_number(self):
        self.stage_claim_without_dispatch()
        with patch("selenium_pipeline.ai_academic_web_review._browser_request",
                   side_effect=AssertionError("Old Send must not repeat")) as browser:
            failure=execute_one_review(
                queue_root=self.queue,folder=self.folder,
                slide=1,mode="INITIAL_REVIEW")
        self.assertEqual(failure["status"],
                         "FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED")
        self.assertEqual(failure["provider_submission_state"],
                         "UNKNOWN_AFTER_POSSIBLE_SUBMISSION")
        self.assertTrue(failure["requires_owner_reconciliation"])
        self.assertFalse(failure["manual_retry_eligible"])
        browser.assert_not_called()
        with self.assertRaises(FigureIdentityReviewRequired):
            execute_one_review(queue_root=self.queue,folder=self.folder,
                               slide=1,mode="INITIAL_REVIEW",attempt=2)
        self.prove_source_preserved()


if __name__ == "__main__":
    unittest.main()
