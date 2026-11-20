"""Fault injection: one new-family Neon PDF challenge; no old Send replay."""
from __future__ import annotations
import json
import os
import re
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from selenium_pipeline.academic_dual_pdf_capability import probe_once as old_v1
from selenium_pipeline.academic_dual_pdf_profile_repair_v2 import probe_once as old_v2
from selenium_pipeline.academic_neon_high_two_pdf_requalification import (
    probe_once,qualifying_proof,ROOT,STATUS_OK,STATUS_BAD,_path)
from selenium_pipeline.series_gemini import OwnedGeminiResponse

SHA="a"*64
READY={
    "status":"EXACT_NEON_HIGH_SOURCE_FREE_PDF_PROBE_ONLY_READY_NO_SEND",
    "model_family":"neon","thinking_level":"high","verified_port":9222,
    "gemini_requests_submitted":0,"files_uploaded":0,
    "new_source_review_send_allowed":False,
    "student_publication_authorized":False,
}


class IndependentNeonHighPDFQualificationTests(TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.queue=self.root/"queue";self.queue.mkdir()
        self.slides=[10,11]
        for slide in self.slides:
            home=self.queue/f"slide_{slide:03d}_initial_review_attempt_01_request"
            home.mkdir()
            fp=f"{slide:064x}"
            (home/"request_state.json").write_text(json.dumps({
                "schema_version":1,"source_sha256":SHA,
                "request_fingerprint":fp,"status":"SUBMITTED_OR_UNCERTAIN",
                "submission_may_have_occurred":True,"can_auto_retry":False,
                "student_publication_authorized":False}))
            (home/"dispatch_attempted.claim").write_text(fp)
            oldtime=time.time()-150
            os.utime(home/"request_state.json",(oldtime,oldtime))
        # Both historical Pro incidents remain permanently consumed/unverified.
        def lost(*_):
            raise TimeoutError("simulated old provider response absent")
        self.assertEqual(old_v1(
            queue_root=self.queue,checkpoint_parent=self.root,
            source_sha=SHA,prior_slides=self.slides,family="pro",
            now=time.time()-60,transport=lost)["status"],
            "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED")
        self.assertEqual(old_v2(
            queue_root=self.queue,checkpoint_parent=self.root,
            source_sha=SHA,prior_slides=self.slides,family="pro",
            transport=lost)["status"],
            "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED")
        self.sent=0

    def args(self):
        return dict(queue_root=self.queue,checkpoint_parent=self.root,
                    source_sha=SHA,prior_slides=self.slides)

    def good(self,prompt,files,**kwargs):
        self.sent+=1
        self.assertEqual(kwargs,{"expected_runtime_family":"neon",
                                  "expected_thinking_level":"high"})
        self.assertEqual([f.name for f in files],
                         ["SyntheticA.pdf","SyntheticB.pdf"])
        ids=[re.search(rb"PDF_CODE: ([A-F0-9]{18})",f.read_bytes())[1].decode()
             for f in files]
        self.assertNotIn(ids[0],prompt)
        self.assertNotIn(ids[1],prompt)
        nonce=re.search(r'"probe":"([a-f0-9]{18})"',prompt)[1]
        return OwnedGeminiResponse(
            json.dumps({"probe":nonce,"a":ids[0],"b":ids[1]}),
            registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
            new_turn_verified=True,
            verified_model_family="neon",
            verified_thinking_level="high")

    def test_exact_neon_high_two_pdf_real_bytes_once_and_restart(self):
        original_states={
            slide:(self.queue/f"slide_{slide:03d}_initial_review_attempt_01_request"/
                   "request_state.json").read_bytes()
            for slide in self.slides}
        first=probe_once(**self.args(),presend=lambda:READY,
                         transport=self.good)
        self.assertEqual(first["status"],STATUS_OK)
        self.assertEqual(first["new_provider_requests"],1)
        self.assertFalse(first["new_source_review_send_allowed"])
        self.assertFalse(first["academic_approval"])
        self.assertFalse(first["student_publication_authorized"])
        self.assertEqual(self.sent,1)
        saved=qualifying_proof(**self.args())
        self.assertIsNotNone(saved)
        self.assertTrue(saved["source_free_neon_pdf_capability_verified"])
        self.assertEqual(probe_once(**self.args(),
                         presend=lambda:None,transport=self.good)
                         ["new_provider_requests"],0)
        self.assertEqual(self.sent,1)
        for slide,initial in original_states.items():
            self.assertEqual((self.queue/
                f"slide_{slide:03d}_initial_review_attempt_01_request"/
                "request_state.json").read_bytes(),initial)

    def test_wrong_model_in_owned_wrapper_never_qualifies(self):
        def false_model(prompt,files,**kw):
            real=self.good(prompt,files,**kw)
            return OwnedGeminiResponse(
                str(real),
                registration_status=real.gemini_send_registration_status,
                new_turn_verified=True,
                verified_model_family="pro",
                verified_thinking_level="high")
        result=probe_once(**self.args(),presend=lambda:READY,
                          transport=false_model)
        self.assertEqual(result["status"],STATUS_BAD)
        self.assertIsNone(qualifying_proof(**self.args()))
        self.assertEqual(probe_once(**self.args(),
                         presend=lambda:READY,transport=self.good)
                         ["new_provider_requests"],0)
        self.assertEqual(self.sent,1)

    def test_misleading_raw_string_never_qualifies(self):
        result=probe_once(**self.args(),presend=lambda:READY,
                          transport=lambda p,f,**k:str(self.good(p,f,**k)))
        self.assertEqual(result["status"],STATUS_BAD)
        self.assertIsNone(qualifying_proof(**self.args()))

    def test_wrong_high_radio_does_not_consume_any_claim(self):
        bad={**READY,"thinking_level":"medium"}
        result=probe_once(**self.args(),presend=lambda:bad,
                          transport=self.good)
        self.assertIn("NO_CLAIM",result["status"])
        self.assertEqual(self.sent,0)
        self.assertEqual(list((self.root/ROOT).rglob("claim.json")),[])

    def test_unverified_browser_port_cannot_consume_claim(self):
        bad={**READY,"verified_port":9225}
        result=probe_once(**self.args(),presend=lambda:bad,
                          transport=self.good)
        self.assertIn("NO_CLAIM",result["status"])
        self.assertEqual(self.sent,0)

    def test_after_crash_no_model_send_or_response_replay(self):
        first=probe_once(**self.args(),presend=lambda:READY,
                         transport=self.good)
        self.assertEqual(first["status"],STATUS_OK)
        receipt=next((self.root/ROOT).rglob("result.json"))
        receipt.unlink()
        old=probe_once(**self.args(),presend=lambda:READY,
                       transport=self.good)
        self.assertEqual(old["status"],
                         "PRIOR_NEON_HIGH_PDF_SEND_UNCERTAIN_NO_RESEND")
        self.assertEqual(old["new_provider_requests"],0)
        self.assertEqual(self.sent,1)

    def test_stale_invalid_old_pro_result_fails_before_send(self):
        prior=next((self.root/
             ".microgen_g2_dual_pdf_after_profile_repair_v2").rglob("result.json"))
        prior.write_text("{}")
        with self.assertRaises(Exception):
            probe_once(**self.args(),presend=lambda:READY,
                       transport=self.good)
        self.assertEqual(self.sent,0)

    def test_modified_original_sent_claim_fails_before_send(self):
        path=self.queue/"slide_010_initial_review_attempt_01_request"/"dispatch_attempted.claim"
        path.write_text("c"*64)
        with self.assertRaises(Exception):
            probe_once(**self.args(),presend=lambda:READY,
                       transport=self.good)
        self.assertEqual(self.sent,0)

    def test_disabled_registry_fails_before_send(self):
        with patch("selenium_pipeline.academic_neon_high_two_pdf_requalification.lookup_mechanism",
                   return_value=None):
            with self.assertRaises(Exception):
                probe_once(**self.args(),presend=lambda:READY,
                           transport=self.good)
        self.assertEqual(self.sent,0)

    def test_corrupt_receipt_cannot_fabricate_accepted_response(self):
        probe_once(**self.args(),presend=lambda:READY,
                   transport=self.good)
        receipt=next((self.root/ROOT).rglob("result.json"))
        row=json.loads(receipt.read_text())
        row["verified_thinking_level"]="medium"
        receipt.write_text(json.dumps(row))
        with self.assertRaises(Exception):
            qualifying_proof(**self.args())


if __name__=="__main__":
    import unittest
    unittest.main()
