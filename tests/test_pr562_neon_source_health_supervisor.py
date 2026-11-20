"""PR562: G2 normal supervisor rechecks Neon High proof, never old Pro gate."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock,patch

from selenium_pipeline.windows_g2_autonomous_qa_supervisor import (
    _verified_neon_high_source_health,step,
)

SHA="1"*64
INCIDENT="a"*64


class NeonHighSupervisorHealthTests(TestCase):
    def setUp(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.queue=self.root/"academic_review";self.queue.mkdir()
        self.source=self.root/"original_lecture";self.source.mkdir()
        self.selection={
            "status":"ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY",
            "action":"FRESH_FIRST_ATTEMPT",
            "attempt":1,"next_slide":13,"next_mode":"INITIAL_REVIEW",
            "required_runtime_family":"neon",
            "required_thinking_level":"high",
            "original_request_replay_authorized":False,
            "student_publication_authorized":False,
            "synthetic_pdf_capability_incident":INCIDENT,
        }
        self.proof={
            "status":"NEON_HIGH_TWO_PDF_SOURCE_FREE_RESPONSE_VERIFIED",
            "source_sha256":SHA,"original_incident_sha256":INCIDENT,
            "source_free_neon_pdf_capability_verified":True,
            "verified_model_family":"neon",
            "verified_thinking_level":"high",
            "original_source_uploaded":False,
            "academic_approval":False,
            "student_publication_authorized":False,
            "new_source_review_send_allowed":False,
        }

    def check(self,**changes):
        selection={**self.selection,**changes}
        observed=[]
        def proof(**kwargs):
            observed.append(kwargs)
            return self.proof
        health=_verified_neon_high_source_health(
            selection=selection,queue_root=self.queue,
            checkpoint_parent=self.root,source_sha=SHA,qualifier=proof)
        self.assertEqual(len(observed),1)
        self.assertEqual(observed[0]["prior_slides"],[10,11])
        self.assertEqual(observed[0]["source_sha"],SHA)
        return health

    def test_verified_new_model_health_allows_only_fresh_one_send(self):
        result=self.check()
        self.assertEqual(result["model_family"],"neon")
        self.assertEqual(result["thinking_level"],"high")
        self.assertTrue(result["new_source_review_send_allowed"])
        self.assertTrue(result["source_free_pdf_capability_verified"])
        self.assertEqual(result["actual_model_requests_submitted"],0)
        self.assertFalse(result["old_original_claims_replayed"])
        self.assertFalse(result["academic_approval"])
        self.assertFalse(result["student_publication_authorized"])

    def test_no_proof_wrong_model_wrong_effort_or_source_all_fail_closed(self):
        for field,value in (
            ("source_sha256","different"*8),
            ("original_incident_sha256","b"*64),
            ("verified_model_family","pro"),
            ("verified_thinking_level","medium"),
            ("source_free_neon_pdf_capability_verified",False),
            ("original_source_uploaded",True),
            ("academic_approval",True),
            ("student_publication_authorized",True),
            ("new_source_review_send_allowed",True),
        ):
            with self.subTest(field=field):
                candidate={**self.proof,field:value}
                with self.assertRaises(ValueError):
                    _verified_neon_high_source_health(
                        selection=self.selection,queue_root=self.queue,
                        checkpoint_parent=self.root,source_sha=SHA,
                        qualifier=lambda **k:candidate)

    def test_wrong_original_selection_or_replayed_attempt_fails(self):
        for key,value in (
            ("required_runtime_family","pro"),
            ("required_thinking_level","medium"),
            ("original_request_replay_authorized",True),
            ("student_publication_authorized",True),
            ("attempt",2),
            ("action","RETRY_UNATTRIBUTED_SEND"),
        ):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    self.check(**{key:value})

    def test_wrong_checkpoint_parent_or_retired_registry_fails_closed(self):
        wrong=self.root/"other";wrong.mkdir()
        with self.assertRaises(ValueError):
            _verified_neon_high_source_health(
                selection=self.selection,queue_root=self.queue,
                checkpoint_parent=wrong,source_sha=SHA,
                qualifier=lambda **kwargs:self.proof)
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with self.assertRaises(ValueError):
                self.check()

    def test_real_supervisor_routes_fresh_neon_directly_past_old_pro_gate(self):
        # Production step orchestration with real source hash+queue and fake
        # provider transport (NO actual Chrome or model Send).
        originals={}
        for filename,body in {
            "source.pdf":b"original source",
            "slides.pdf":b"lecture slides",
            "script.txt":b"slide 13 science",
        }.items():
            (self.source/filename).write_bytes(body)
            originals[filename]=hashlib.sha256(body).hexdigest()
        self.queue.joinpath("queue.json").write_text(json.dumps({
            "status":"IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
            "original_source_folder":str(self.source),
            "slide_jobs":[{
                "slide":13,"utterance_count":1,
                "original_source_sha256":originals["source.pdf"],
                "original_slides_sha256":originals["slides.pdf"],
                "original_script_sha256":originals["script.txt"],
            }],
            "expected_utterances":1,
            "student_publication_authorized":False,
        }))
        selected={**self.selection,"next_slide":13}
        fake_health={
            "status":"G2_NEON_HIGH_SOURCE_FREE_TWO_PDF_REQUALIFIED_NO_SEND",
            "new_source_review_send_allowed":True,
            "model_family":"neon","thinking_level":"high",
            "student_publication_authorized":False,
        }
        pending={
            "status":"INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE",
            "original_utterances":1,"accepted_ai_evidence":[],
            "pending_or_disputed":1,"student_publication_authorized":False,
        }
        actual_dispatch=Mock(return_value={"status":"BOUNDED_REVIEW_LIMIT_REACHED"})
        with patch("selenium_pipeline.ai_academic_review_queue._check_queue",
                   return_value={}),patch(
            "selenium_pipeline.ai_academic_review_queue.select_next_safe_review",
            return_value=selected),patch(
            "selenium_pipeline.windows_g2_autonomous_qa_supervisor._verified_neon_high_source_health",
            return_value=fake_health) as requalified,patch(
            "selenium_pipeline.academic_queue_fresh_send_health.check",
            side_effect=AssertionError("Retired Pro health cannot deny verified Neon")):
            result=step(
                folder=self.source,queue_root=self.queue,work_root=self.root,
                execute=True,max_units=1,auto_media=False,health_family="pro",
                review_advance=actual_dispatch,
                consensus_reader=lambda **kwargs:pending)
        self.assertEqual(result["status"],
                         "G2_ACADEMIC_QA_INCOMPLETE_REVIEW_OR_SOURCE_REPAIR")
        self.assertEqual(result["provider_health"],fake_health)
        self.assertFalse(result["new_paid_tts_dispatched"])
        self.assertFalse(result["student_publication_authorized"])
        actual_dispatch.assert_called_once()
        self.assertEqual(actual_dispatch.call_args.kwargs["max_units"],1)
        requalified.assert_called_once()


if __name__=="__main__":
    import unittest
    unittest.main()
