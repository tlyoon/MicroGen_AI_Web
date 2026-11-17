"""A v1 failure can permit exactly one distinct profile-repaired PDF experiment."""
import json
import os
import re
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from selenium_pipeline.academic_dual_pdf_capability import (
    probe_once as v1_probe, qualifying_proof as queue_proof, ROOT as ROOT1)
from selenium_pipeline.academic_dual_pdf_profile_repair_v2 import (
    probe_once, qualifying_proof, existing_outcome, newly_eligible, ROOT)
from selenium_pipeline.series_gemini import OwnedGeminiResponse

SHA="a"*64

class RepairedProfilePdfProbeTests(TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.parent=Path(temp.name)
        self.queue=self.parent/"queue"
        self.queue.mkdir()
        self.slides=[10,11]
        self.sent=[]
        for i in self.slides:
            c=self.queue/f"slide_{i:03d}_initial_review_attempt_01_request"
            c.mkdir()
            f=(f"{i:064x}")
            (c/"request_state.json").write_text(json.dumps({
                "schema_version":1,"source_sha256":SHA,
                "request_fingerprint":f, "status":"SUBMITTED_OR_UNCERTAIN",
                "submission_may_have_occurred":True,"can_auto_retry":False,
                "student_publication_authorized":False}))
            (c/"dispatch_attempted.claim").write_text(f)
            stamp=time.time()-120
            os.utime(c/"request_state.json",(stamp,stamp))
        # One old diagnostic, actually consumed and unverified, is immutable.
        def lost(prompt, files):
            self.sent.append("v1")
            raise TimeoutError("Historical PDF response absent")
        v1_probe(queue_root=self.queue,checkpoint_parent=self.parent,
                 source_sha=SHA,prior_slides=self.slides,
                 family="pro",now=time.time()-60,transport=lost)
        self.assertEqual(self.sent,["v1"])

    def kwargs(self):
        return dict(queue_root=self.queue,checkpoint_parent=self.parent,
                    source_sha=SHA,prior_slides=self.slides,family="pro")

    def response(self, prompt, files):
        self.sent.append("v2")
        nonce=re.search(r'\{"probe":"([0-9a-f]{18})"',prompt)[1]
        self.assertEqual([p.name for p in files],
                         ["SyntheticA.pdf","SyntheticB.pdf"])
        from fitz import open as open_pdf
        secrets=[]
        for f in files:
            with open_pdf(str(f)) as doc:
                m=re.search(r"PDF_CODE: ([0-9A-F]{18})",doc[0].get_text())
                self.assertIsNotNone(m)
                secrets.append(m[1])
        self.assertNotIn(secrets[0],prompt)
        self.assertNotIn(secrets[1],prompt)
        return OwnedGeminiResponse(json.dumps({"probe":nonce,"a":secrets[0],
                                      "b":secrets[1]}),
            registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
            new_turn_verified=True)

    def test_live_modality_semantics_and_restart_without_replay(self):
        self.assertTrue(newly_eligible(**self.kwargs()))
        self.assertIsNone(queue_proof(**self.kwargs()))
        proof=probe_once(**self.kwargs(),transport=self.response)
        self.assertTrue(proof["new_source_review_send_allowed"])
        self.assertEqual(proof["new_provider_requests"],1)
        self.assertEqual(proof["status"],"DUAL_SYNTHETIC_PDF_RESPONSE_VERIFIED")
        self.assertEqual(self.sent,["v1","v2"])
        saved=queue_proof(**self.kwargs())
        self.assertTrue(saved["new_source_review_send_allowed"])
        self.assertFalse(saved["academic_approval"])
        self.assertEqual(saved["incident_sha256"],proof["incident_sha256"])
        self.assertEqual(probe_once(**self.kwargs(),transport=self.response)["new_provider_requests"],0)
        self.assertEqual(self.sent,["v1","v2"])
        self.assertFalse(newly_eligible(**self.kwargs()))
        self.assertEqual(len(list((self.parent/ROOT).rglob("claim.json"))),1)
        self.assertEqual(len(list((self.parent/ROOT1).rglob("claim.json"))),1)

    def test_failed_new_request_is_never_replayed(self):
        def lost(prompt,files):
            self.sent.append("v2")
            raise TimeoutError("no visible assistant response")
        outcome=probe_once(**self.kwargs(),transport=lost)
        self.assertFalse(outcome["new_source_review_send_allowed"])
        self.assertIsNone(qualifying_proof(**self.kwargs()))
        self.assertEqual(probe_once(**self.kwargs(),transport=self.response)["new_provider_requests"],0)
        self.assertEqual(self.sent,["v1","v2"])

    def test_ordinary_string_without_owned_turn_cannot_qualify(self):
        def raw(prompt,files):
            return str(self.response(prompt,files))
        out=probe_once(**self.kwargs(),transport=raw)
        self.assertFalse(out["new_source_review_send_allowed"])
        self.assertIsNone(queue_proof(**self.kwargs()))

    def test_crash_after_claim_has_no_resend(self):
        probe_once(**self.kwargs(),transport=self.response)
        result=next((self.parent/ROOT).rglob("result.json"))
        result.unlink()
        out=probe_once(**self.kwargs(),transport=self.response)
        self.assertEqual(out["status"],"PRIOR_REPAIRED_PDF_SEND_UNCERTAIN_NO_RESEND")
        self.assertEqual(out["new_provider_requests"],0)
        self.assertEqual(self.sent,["v1","v2"])

    def test_v1_original_result_mutation_fails_closed(self):
        receipt=next((self.parent/ROOT1).rglob("result.json"))
        receipt.write_text("{}")
        with self.assertRaises((ValueError, Exception)):
            probe_once(**self.kwargs(),transport=self.response)
        self.assertEqual(self.sent,["v1"])

    def test_disabled_registry_prohibits_v2(self):
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with self.assertRaises(Exception):
                probe_once(**self.kwargs(),transport=self.response)
        self.assertEqual(self.sent,["v1"])

    def test_source_claim_fingerprint_change_fails_closed(self):
        (self.queue/"slide_010_initial_review_attempt_01_request"/
         "dispatch_attempted.claim").write_text("c"*64)
        with self.assertRaises(Exception):
            probe_once(**self.kwargs(),transport=self.response)
        self.assertEqual(self.sent,["v1"])

    def test_mutated_v2_model_secret_fails_closed(self):
        probe_once(**self.kwargs(),transport=self.response)
        result=next((self.parent/ROOT).rglob("result.json"))
        x=json.loads(result.read_text())
        x["model_response_json"]["a"]="FORGED"
        result.write_text(json.dumps(x))
        with self.assertRaises(Exception):
            qualifying_proof(**self.kwargs())
