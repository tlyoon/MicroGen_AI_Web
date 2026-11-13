"""No textbook / no API: one source-free model reply requalifies G2 transport.

The source global attempted-utterance ledger and immutable old request-state
files are never modified. All responses are mock one-turn browser objects.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json
import os
import re

from selenium_pipeline.series_gemini import OwnedGeminiResponse
from selenium_pipeline.academic_review_transport_circuit import (
    record_original_failure,inspect)
from selenium_pipeline.academic_provider_requalification import (
    probe_once,latest_success,verify_result,AcademicProbeError)

SRC="a"*64
BASE=1800000000


class SourceFreeAcademicRequalificationTests(TestCase):
    def setUp(self):
        t=TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.route=self.root/"route.json"
        self.route.write_text(json.dumps({
            "schema_version":1,"source_sha256":SRC,
            "selected_academic_model_family":"pro",
            "selected_thinking_level":"medium",
            "G2_approved":False,"academic_approval":False,
            "student_publication_authorized":False}),encoding="utf8")
        for name,token,when in (("old","b"*64,BASE),("new","c"*64,BASE+1)):
            folder=self.root/name/"job_01_checkpoint"
            folder.mkdir(parents=True)
            (folder/"request_state.json").write_text(json.dumps({
                "schema_version":1,
                "source_sha256":SRC,"request_fingerprint":token,
                "status":"SUBMITTED_OR_UNCERTAIN",
                "submission_may_have_occurred":True,
                "can_auto_retry":False,
                "academic_approval":False,
                "tts_authorized":False,
                "student_publication_authorized":False}),encoding="utf8")
            (folder/"dispatch_attempted.claim").write_text(
                token,encoding="utf8")
            record_original_failure(checkpoint=folder,
                route_receipt=self.route,checkpoint_parent=self.root,now=when)
        self.env=patch.dict(os.environ,{
            "MICROGEN_GEMINI_UI_MODE":"pro",
            "MICROGEN_GEMINI_THINKING_LEVEL":"medium"})
        self.env.start()
        self.addCleanup(self.env.stop)

    @staticmethod
    def success(prompt,port):
        assert port==9222
        match=re.search(
            r'\{"microgen_health":"ok","nonce":"[a-f0-9]{20}"\}',
            prompt)
        assert match and "No documents or original source" in prompt
        return OwnedGeminiResponse(
            match.group(0),
            registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
            new_turn_verified=True)

    def test_a_new_source_free_browser_reply_unblocks_only_after_last_failure(self):
        before=inspect(checkpoint_parent=self.root,source_sha=SRC,
                       family="pro",now=BASE+2000)
        self.assertFalse(before["automatic_new_academic_model_send_allowed"])
        self.assertTrue(before["source_free_health_probe_due"])
        calls=[]
        def transport(prompt,port):
            calls.append((prompt,port))
            return self.success(prompt,port)
        outcome=probe_once(checkpoint_parent=self.root,source_sha=SRC,
                           family="pro",chrome_port=9222,now=BASE+2000,
                           browser_request=transport)
        self.assertEqual(outcome["status"],
                         "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED")
        self.assertEqual(len(calls),1)
        after=inspect(checkpoint_parent=self.root,source_sha=SRC,
                      family="pro",now=BASE+2001)
        self.assertTrue(after["automatic_new_academic_model_send_allowed"])
        self.assertTrue(after["independent_source_free_reply_reverified"])
        self.assertFalse(after["G2_approved"])
        self.assertEqual(after["distinct_failed_requests"],2)
        self.assertFalse(after["old_request_retry_authorized"])
        self.assertEqual((self.root/"old"/"job_01_checkpoint"/
                          "dispatch_attempted.claim").read_text(),"b"*64)

    def test_uncertain_probe_never_replays_same_utc_day(self):
        count=[]
        def failure(prompt,port):
            count.append(prompt)
            raise TimeoutError("simulated untrusted browser reply")
        outcome=probe_once(checkpoint_parent=self.root,source_sha=SRC,
                           family="pro",chrome_port=9222,now=BASE+2000,
                           browser_request=failure)
        self.assertEqual(outcome["status"],"NO_VERIFIED_SOURCE_FREE_RESPONSE")
        self.assertEqual(len(count),1)
        same=probe_once(checkpoint_parent=self.root,source_sha=SRC,
                        family="pro",chrome_port=9222,now=BASE+2400,
                        browser_request=failure)
        self.assertTrue(same["reused_immutable_probe"])
        self.assertEqual(same["new_provider_requests"],0)
        self.assertEqual(len(count),1)
        still=inspect(checkpoint_parent=self.root,source_sha=SRC,
                      family="pro",now=BASE+2400)
        self.assertFalse(still["automatic_new_academic_model_send_allowed"])
        # A genuinely NEW next-day synthetic nonce permits ONE more source
        # free check, never resending either original source claim.
        newer=probe_once(checkpoint_parent=self.root,source_sha=SRC,
                         family="pro",chrome_port=9222,now=BASE+86400,
                         browser_request=self.success)
        self.assertEqual(newer["status"],
                         "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED")
        self.assertTrue(inspect(checkpoint_parent=self.root,
                                source_sha=SRC,family="pro",now=BASE+86401)
                        ["automatic_new_academic_model_send_allowed"])

    def test_plain_response_string_does_not_prove_registered_model_send(self):
        result=probe_once(checkpoint_parent=self.root,source_sha=SRC,
                          family="pro",chrome_port=9222,now=BASE+2000,
                          browser_request=lambda prompt,port:
                              self.success(prompt,port).__str__())
        self.assertEqual(result["status"],"NO_VERIFIED_SOURCE_FREE_RESPONSE")
        self.assertFalse(inspect(checkpoint_parent=self.root,
                                 source_sha=SRC,family="pro",now=BASE+2001)
                         ["automatic_new_academic_model_send_allowed"])

    def test_wrong_model_or_effort_never_touches_probe_claim(self):
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"flash"}):
            with self.assertRaises(AcademicProbeError):
                probe_once(checkpoint_parent=self.root,source_sha=SRC,
                           family="pro",now=BASE+2000,
                           browser_request=self.success)
        with patch.dict(os.environ,{
                "MICROGEN_GEMINI_THINKING_LEVEL":"low"}):
            with self.assertRaises(AcademicProbeError):
                probe_once(checkpoint_parent=self.root,source_sha=SRC,
                           family="pro",now=BASE+2000,
                           browser_request=self.success)
        self.assertIsNone(latest_success(checkpoint_parent=self.root,
            source_sha=SRC,family="pro",after_unix=BASE,now=BASE+2000))

    def test_forged_saved_proof_fails_closed(self):
        result=probe_once(checkpoint_parent=self.root,source_sha=SRC,
                          family="pro",now=BASE+2000,
                          browser_request=self.success)
        scoped=self.root/".microgen_academic_response_requalification"/SRC/"pro"
        path=next(scoped.glob("*/result.json"))
        obj=json.loads(path.read_text())
        obj["response_text"]='{"microgen_health":"ok","nonce":"wrong"}'
        path.write_text(json.dumps(obj),encoding="utf8")
        with self.assertRaises(AcademicProbeError):
            inspect(checkpoint_parent=self.root,source_sha=SRC,
                    family="pro",now=BASE+2001)

    def test_model_family_isolation(self):
        probe_once(checkpoint_parent=self.root,source_sha=SRC,
                   family="pro",now=BASE+2000,browser_request=self.success)
        # The Flash model has no two failed G2 claims at this source,
        # therefore it does not inherit Pro's blocked history.
        self.assertTrue(inspect(checkpoint_parent=self.root,
                                source_sha=SRC,family="flash",
                                now=BASE+2001)
                        ["automatic_new_academic_model_send_allowed"])
