"""One original source -> changed-evidence Gemini browser review -> resume/skip.

No production Gemini calls: transport stub exercises REAL durable checkpoint,
physically verified academic response validator, persistent no-repeat claims.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from unittest.mock import Mock

from selenium_pipeline.ai_academic_web_review import build_review_job,review_instructions
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired,_sha
from selenium_pipeline.source_review_autonomous_campaign import (
    run, import_previous_claimed_review,
)
from tests.test_original_packet_evidence_audit import fixture


class BoundedAcademicSourceRetryTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.base=Path(t.name)
        self.folder=self.base/"original"
        fixture(self.folder)
        (self.folder/"script.txt").write_text(
            "**Slide 1 [1 sec]:\nA visible equation**\n",encoding="utf8")
        self.plan_dir=self.base/"plans"
        self.plan_dir.mkdir()
        self.root=self.base/"acceptance"
        self.root.mkdir()
        job=build_review_job(folder=self.folder,slide_numbers=[1])
        job.update(source_research_is_new_evidence_only=True)
        prompt=review_instructions(job,mode="INDEPENDENT_CHALLENGE")
        u=job["slides"][0]["utterances"][0]
        self.uid=u["id"]
        self.target=job["slides"][0]["visual_targets"][0]["id"]
        self.quote=job["verified_source_quote_candidates_v1"][
            "utterances"][0]["allowed_citations"][0]["verbatim_source_quote"]
        self.plan=self.plan_dir/"source_plan.json"
        self.plan.write_text(json.dumps({
            "schema_version":1,
            "status":"UNSENT_PHYSICALLY_CHANGED_G2_SOURCE_AND_VISUAL_EVIDENCE",
            "source_sha256":job["source_sha256"],
            "G2_approved":False,"student_publication_authorized":False,
            "jobs":[{
                "source_job":job,
                "eligible_original_unresolved_units":[self.uid],
                "source_job_request_sha256":
                    hashlib.sha256(prompt.encode("utf8")).hexdigest(),
            }],
        }),encoding="utf8")
        self.before={n:_sha(self.folder/n) for n in (
            "source.pdf","slides.pdf","script.txt")}

    def response(self, quote=None, verdict="SUPPORTED"):
        u=json.loads(self.plan.read_text())["jobs"][0]["source_job"][
            "slides"][0]["utterances"][0]
        return json.dumps({
            "status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
            "rows":[{
                "utterance_id":self.uid,
                "spoken_sha256":u["spoken_sha256"],
                "target_id":self.target,
                "source_page":1,
                "verbatim_source_quote":self.quote if quote is None else quote,
                "verdict":verdict,
                "math_explanation":"This candidate is an exact original source excerpt and an original visible PDF text target, but one review does not establish independent academic proof.",
            }],
        })

    def test_valid_one_send_then_reuses_stored_response_without_second_provider_call(self):
        fake=Mock(return_value=self.response())
        result=run(plan_path=self.plan,root=self.root,max_jobs=1,transport=fake)
        self.assertEqual(fake.call_count,1)
        self.assertEqual(result["new_requests_attempted"],1)
        self.assertEqual(result["jobs_completed"][0]["supported"],1)
        self.assertFalse(result["G2_approved"])
        self.assertEqual(
            json.loads((self.root/"job_01_checkpoint"/
                        "request_state.json").read_text())["status"],
            "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED")
        second=run(plan_path=self.plan,root=self.root,max_jobs=1,
                   transport=Mock(side_effect=RuntimeError("unexpected Send")))
        self.assertEqual(second["new_requests_attempted"],0)
        self.assertEqual(second["jobs_completed"][0]["status"],"REUSED_VERIFIED_RESULT")
        self.assertEqual(self.before,{n:_sha(self.folder/n) for n in self.before})

    def test_one_model_submission_that_fails_never_resends_same_claim(self):
        once=Mock(side_effect=TimeoutError("after uncertain model Send"))
        first=run(plan_path=self.plan,root=self.root,max_jobs=1,
                  transport=once)
        self.assertEqual(once.call_count,1)
        self.assertEqual(first["jobs_not_rerun"][0]["status"],
                         "TRANSPORT_OR_VALIDATION_BLOCKED_NO_RETRY")
        never=Mock(side_effect=RuntimeError("no second Send allowed"))
        second=run(plan_path=self.plan,root=self.root,max_jobs=1,
                   transport=never)
        never.assert_not_called()
        self.assertEqual(second["new_requests_attempted"],0)
        self.assertEqual(second["jobs_not_rerun"][0]["status"],
                         "PREVIOUS_SEND_UNCERTAIN_NO_RETRY")

    def test_crash_between_global_and_local_claim_resumes_unsent_request(self):
        from unittest.mock import patch
        import selenium_pipeline.source_review_autonomous_campaign as module
        original=module._new
        once=[True]
        def fail_local_after_global(path,payload):
            if (path==self.root/"claimed"/"job_01.json" and once[0]):
                once[0]=False
                raise OSError("injected crash before any Send")
            return original(path,payload)
        with patch.object(module,"_new",side_effect=fail_local_after_global):
            with self.assertRaisesRegex(OSError,"injected crash"):
                run(plan_path=self.plan,root=self.root,max_jobs=1,
                    transport=Mock(side_effect=RuntimeError("no Send")))
        self.assertTrue((self.root/"job_01_checkpoint"/"request_state.json").is_file())
        fake=Mock(return_value=self.response())
        completed=run(plan_path=self.plan,root=self.root,max_jobs=1,
                      transport=fake)
        fake.assert_called_once()
        self.assertEqual(completed["jobs_completed"][0]["supported"],1)
        self.assertFalse(completed["G2_approved"])

    def test_real_no_send_model_picker_failure_reuses_same_global_claim_on_resume(self):
        from selenium_pipeline.gemini_selenium_only_policy import (
            GeminiSeleniumTemporaryFailure)
        def before_send(*_):
            error=GeminiSeleniumTemporaryFailure(
                "model picker was unavailable before browser Send",
                attempts_used=3,failure_phase="GEMINI_MODEL_PICKER_NOT_READY")
            error.gemini_send_registration_status="NOT_SENT"
            error.gemini_new_user_turn_verified=False
            raise error
        first=run(plan_path=self.plan,root=self.root,max_jobs=1,
                  transport=Mock(side_effect=before_send))
        self.assertEqual(first["new_requests_attempted"],1)
        state=json.loads((self.root/"job_01_checkpoint"/"request_state.json").read_text("utf8"))
        self.assertEqual(state["status"],"CERTIFIED_PRESEND_UNSENT")
        self.assertFalse((self.root/"job_01_result.json").exists())
        marker=self.root/"claimed"/"job_01.json"
        marker_before=marker.read_bytes()
        claimed=list((self.base/".microgen_academic_source_once").rglob("*.json"))
        self.assertEqual(len(claimed),1)
        global_before=claimed[0].read_bytes()
        second_transport=Mock(return_value=self.response())
        result=run(plan_path=self.plan,root=self.root,max_jobs=1,
                   transport=second_transport)
        second_transport.assert_called_once()
        self.assertEqual(result["jobs_completed"][0]["status"],
                         "NEW_VALID_SOURCE_REVIEW")
        self.assertEqual(result["jobs_completed"][0]["supported"],1)
        self.assertEqual(marker.read_bytes(),marker_before)
        self.assertEqual(claimed[0].read_bytes(),global_before)
        self.assertEqual(self.before,{n:_sha(self.folder/n) for n in self.before})
        repeat_transport=Mock(side_effect=AssertionError("duplicate Send forbidden"))
        third=run(plan_path=self.plan,root=self.root,max_jobs=1,
                  transport=repeat_transport)
        repeat_transport.assert_not_called()
        self.assertEqual(third["jobs_completed"][0]["status"],
                         "REUSED_VERIFIED_RESULT")

    def test_real_model_unavailable_preflight_does_not_consume_any_review_claim(self):
        from unittest.mock import patch
        from selenium_pipeline.academic_gemini_presend_preflight import (
            AcademicGeminiPreSendBlocked)
        with patch(
                "selenium_pipeline.academic_gemini_presend_preflight."
                "select_ready_existing_session",
                side_effect=AcademicGeminiPreSendBlocked(
                    "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE")) as probe:
            result=run(plan_path=self.plan,root=self.root,max_jobs=1,
                       transport=None)
        probe.assert_called_once_with(primary_port=9222)
        self.assertEqual(result["new_requests_attempted"],0)
        self.assertEqual(result["jobs_not_rerun"][0]["status"],
                         "PROVIDER_CAPABILITY_PREFLIGHT_BLOCKED_NO_SEND")
        self.assertEqual(result["jobs_not_rerun"][0]["failure_phase"],
                         "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE")
        self.assertFalse((self.root/"claimed"/"job_01.json").exists())
        self.assertFalse((self.root/"job_01_checkpoint").exists())
        self.assertFalse(list(self.base.rglob("dispatch_attempted.claim")))
        self.assertEqual(self.before,{n:_sha(self.folder/n) for n in self.before})
        self.assertFalse(result["G2_approved"])

    def test_unclaimed_approved_alternate_session_routes_same_source_on_exact_flash(self):
        from unittest.mock import patch
        with patch("selenium_pipeline.academic_gemini_presend_preflight."
                   "select_ready_existing_session",return_value={
                       "status":"EXACT_OWNED_GEMINI_MODEL_AND_THINKING_READY_NO_SEND",
                       "verified_port":9225,
                       "alternate_account_used":True,
                       "model_family":"flash",
                       "thinking_level":"medium",
                       "gemini_requests_submitted":0,
                   }) as check,\
             patch("selenium_pipeline.source_review_autonomous_campaign."
                   "run_web_review",
                   side_effect=RuntimeError("synthetic stop before browser send")) as send:
            result=run(plan_path=self.plan,root=self.root,max_jobs=1,
                       transport=None)
        check.assert_called_once_with(primary_port=9222)
        self.assertEqual(send.call_count,1)
        self.assertEqual(send.call_args.kwargs["chrome_port"],9225)
        self.assertEqual(send.call_args.kwargs["mode"],"INDEPENDENT_CHALLENGE")
        self.assertEqual(result["new_requests_attempted"],1)
        self.assertEqual(result["jobs_not_rerun"][0]["status"],
                         "TRANSPORT_OR_VALIDATION_BLOCKED_NO_RETRY")
        self.assertFalse(result["G2_approved"])
        self.assertEqual(self.before,{n:_sha(self.folder/n) for n in self.before})

    def test_false_source_quotation_rejected_without_resubmission(self):
        bad=Mock(return_value=self.response(quote="FABRICATED EQUATION"))
        first=run(plan_path=self.plan,root=self.root,max_jobs=1,transport=bad)
        self.assertEqual(first["new_requests_attempted"],1)
        self.assertFalse(first["jobs_completed"])
        self.assertFalse(first["G2_approved"])
        after=run(plan_path=self.plan,root=self.root,max_jobs=1,
                  transport=Mock(side_effect=RuntimeError("repeat")))
        self.assertEqual(after["new_requests_attempted"],0)
        self.assertFalse(after["jobs_completed"])

    def test_prior_bona_fide_review_is_imported_not_sent_again(self):
        first=run(plan_path=self.plan,root=self.root,max_jobs=1,
                  transport=Mock(return_value=self.response()))
        self.assertEqual(first["new_requests_attempted"],1)
        fresh=self.base/"another_acceptance"
        fresh.mkdir()
        item=import_previous_claimed_review(
            old_plan=self.plan,position=1,
            result_path=self.root/"job_01_result.json",
            checkpoint=self.root/"job_01_checkpoint",
            campaign_root=fresh)
        self.assertEqual(item["utterance_count"],1)
        imported=run(plan_path=self.plan,root=fresh,max_jobs=1,
                     transport=Mock(side_effect=RuntimeError("must skip")))
        self.assertEqual(imported["new_requests_attempted"],0)
        self.assertEqual(imported["jobs_not_rerun"][0]["status"],
                         "ORIGINAL_UNITS_ALREADY_ATTEMPTED")

    def test_new_checkpoint_root_cannot_repeat_same_original_utterance(self):
        first=run(plan_path=self.plan,root=self.root,max_jobs=1,
                  transport=Mock(return_value=self.response()))
        self.assertEqual(first["new_requests_attempted"],1)
        another=self.base/"fresh_chat_checkpoint"
        another.mkdir()
        never=Mock(side_effect=RuntimeError("replayed original source unit"))
        second=run(plan_path=self.plan,root=another,max_jobs=1,
                   transport=never)
        never.assert_not_called()
        self.assertEqual(second["new_requests_attempted"],0)
        self.assertEqual(second["jobs_not_rerun"][0]["status"],
                         "ORIGINAL_UNITS_ALREADY_ATTEMPTED")
        self.assertFalse(second["G2_approved"])

    def test_modified_original_source_fails_before_any_send(self):
        (self.folder/"script.txt").write_text("changed narration!",encoding="utf8")
        fake=Mock()
        with self.assertRaises(FigureIdentityReviewRequired):
            run(plan_path=self.plan,root=self.root,max_jobs=1,transport=fake)
        fake.assert_not_called()
        self.assertFalse((self.root/"claimed").exists())

    def test_repackaged_prompt_has_no_automatic_permission(self):
        doc=json.loads(self.plan.read_text())
        doc["jobs"][0]["source_job"]["slides"][0]["utterances"][0][
            "spoken_text"]="Claim changed without new original source."
        self.plan.write_text(json.dumps(doc))
        with self.assertRaises(FigureIdentityReviewRequired):
            run(plan_path=self.plan,root=self.root,max_jobs=1,
                transport=Mock())
        self.assertFalse((self.root/"claimed").exists())


if __name__=="__main__":
    unittest.main()
