"""PR562: a successful G2 slide resets failure streak, NOT Neon/High scope."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from selenium_pipeline.ai_academic_review_queue import (
    select_next_safe_review,execute_one_review,
    _sourcebound_neon_high_continuation,
)

INCIDENT="a"*64


class SourceBoundNeonContinuityTests(TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        self.source=root/"source";self.source.mkdir()
        self.queue=root/"queue";self.queue.mkdir()
        (self.queue/"queue.json").write_text(json.dumps({
            "status":"IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
            "original_source_folder":str(self.source),
            "slide_jobs":[{"slide":1,"utterance_count":2},
                          {"slide":2,"utterance_count":1}],
            "expected_utterances":3,
            "student_publication_authorized":False,
        }),encoding="utf8")
        self.proof={
            "status":"NEON_HIGH_TWO_PDF_SOURCE_FREE_RESPONSE_VERIFIED",
            "original_incident_sha256":INCIDENT,
            "source_free_neon_pdf_capability_verified":True,
            "verified_model_family":"neon",
            "verified_thinking_level":"high",
            "new_source_review_send_allowed":False,
            "student_publication_authorized":False,
        }

    def test_successful_previous_slide_resets_streak_but_neon_stays_selected(self):
        scopes=[
            {"planning_result":"EXISTING_PASS_MUST_NOT_BE_REPEATED",
             "suggested_next_stage":"INITIAL_REVIEW"},
            {"planning_result":"FRESH_ORIGINAL_SOURCE_REVIEW_READY",
             "suggested_next_stage":"INITIAL_REVIEW",
             "fresh_claimed_internal_selenium_review_ready":True},
        ]
        with patch("selenium_pipeline.review_queue_source_audit.inspect_source_bound_queue"),\
             patch("selenium_pipeline.source_review_eligibility_preflight.inspect_original_review_eligibility",
                   side_effect=scopes),\
             patch("selenium_pipeline.ai_academic_review_queue._sourcebound_neon_high_continuation",
                   return_value=self.proof) as proof:
            s=select_next_safe_review(queue_root=self.queue,folder=self.source,
                                      health_family="pro")
        self.assertEqual(s["status"],"ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY")
        self.assertEqual(s["next_slide"],2)
        self.assertEqual(s["next_mode"],"INITIAL_REVIEW")
        self.assertEqual(s["action"],"FRESH_FIRST_ATTEMPT")
        self.assertEqual(s["required_runtime_family"],"neon")
        self.assertEqual(s["required_thinking_level"],"high")
        self.assertEqual(s["synthetic_pdf_capability_incident"],INCIDENT)
        self.assertIs(s["original_request_replay_authorized"],False)
        self.assertIs(s["student_publication_authorized"],False)
        proof.assert_called_once()

    def test_no_actual_neon_proof_preserves_legacy_policy_without_new_approval(self):
        scopes=[
            {"planning_result":"EXISTING_PASS_MUST_NOT_BE_REPEATED",
             "suggested_next_stage":"INITIAL_REVIEW"},
            {"planning_result":"FRESH_ORIGINAL_SOURCE_REVIEW_READY",
             "suggested_next_stage":"INITIAL_REVIEW",
             "fresh_claimed_internal_selenium_review_ready":True},
        ]
        with patch("selenium_pipeline.review_queue_source_audit.inspect_source_bound_queue"),\
             patch("selenium_pipeline.source_review_eligibility_preflight.inspect_original_review_eligibility",
                   side_effect=scopes),\
             patch("selenium_pipeline.ai_academic_review_queue._sourcebound_neon_high_continuation",
                   return_value=None):
            s=select_next_safe_review(queue_root=self.queue,folder=self.source,
                                      health_family="pro")
        self.assertEqual(s["next_slide"],2)
        self.assertNotIn("required_runtime_family",s)
        self.assertIs(s["student_publication_authorized"],False)

    def test_helper_requires_exact_source_specific_pdf_qualification(self):
        with patch("selenium_pipeline.academic_neon_high_two_pdf_requalification.qualifying_proof",
                   return_value=self.proof) as called:
            with patch("selenium_pipeline.ai_academic_review_queue._sha",
                       return_value="1"*64):
                p=_sourcebound_neon_high_continuation(
                    queue_root=self.queue,folder=self.source)
        self.assertEqual(p,self.proof)
        self.assertEqual(called.call_args.kwargs["prior_slides"],[10,11])
        self.assertEqual(called.call_args.kwargs["checkpoint_parent"],self.queue.parent)
        for key,bad in (
            ("verified_model_family","pro"),
            ("verified_thinking_level","medium"),
            ("source_free_neon_pdf_capability_verified",False),
            ("new_source_review_send_allowed",True),
            ("student_publication_authorized",True),
        ):
            with self.subTest(key=key):
                tampered={**self.proof,key:bad}
                with patch("selenium_pipeline.academic_neon_high_two_pdf_requalification.qualifying_proof",
                           return_value=tampered):
                    with patch("selenium_pipeline.ai_academic_review_queue._sha",
                               return_value="1"*64):
                        self.assertIsNone(_sourcebound_neon_high_continuation(
                            queue_root=self.queue,folder=self.source))

    def test_real_source_executor_passes_neon_requirement_to_review_path(self):
        job={
            "source_sha256":"1"*64,"slides_sha256":"2"*64,
            "script_sha256":"3"*64,"review_count":1,
            "utterance_count":1,
        }
        review={
            "review_count":1,
            "status":"SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS",
            "source_only_downgrade_audit":{"model_returned_utterance_count":1},
        }
        with patch("selenium_pipeline.ai_academic_review_queue._check_queue",
                   return_value={"utterance_count":1}),\
             patch("selenium_pipeline.ai_academic_review_queue.build_review_job",
                   return_value=job),\
             patch("selenium_pipeline.ai_academic_review_queue._sourcebound_neon_high_continuation",
                   return_value=self.proof),\
             patch("selenium_pipeline.ai_academic_review_queue.run_web_review",
                   return_value=review) as request:
            result=execute_one_review(
                queue_root=self.queue,folder=self.source,
                slide=2,mode="INITIAL_REVIEW",health_family="pro",
                attempt=1,transport=None)
        self.assertEqual(result["status"],"GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED")
        self.assertEqual(request.call_args.kwargs["required_model_family"],"neon")
        self.assertTrue((self.queue/"slide_002_initial_review.json").is_file())


if __name__=="__main__":
    import unittest
    unittest.main()
