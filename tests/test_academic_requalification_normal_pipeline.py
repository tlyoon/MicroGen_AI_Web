"""Normal academic campaign must probe health before spending original claims.

The mocked academic campaign would report a Send if called; transport,
preflight and valid model reply are synthetic, with no browser/API/source.
"""
import json
import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from selenium_pipeline.academic_review_model_failover import run
from selenium_pipeline.academic_review_transport_circuit import (
    record_original_failure,inspect)
from selenium_pipeline.academic_provider_requalification import probe_once
from selenium_pipeline.series_gemini import OwnedGeminiResponse

SRC="a"*64


class NormalAcademicRequalification(TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.parent=Path(temp.name)
        self.work=self.parent/"campaign"
        self.work.mkdir()
        self.plan=self.parent/"plan.json"
        self.plan.write_text(json.dumps({"source_sha256":SRC}),encoding="utf8")
        self.calls=[]

    def ready(self,*,primary_port):
        self.calls.append(("preflight",os.getenv("MICROGEN_GEMINI_UI_MODE")))
        return {"status":"EXACT_OWNED_GEMINI_MODEL_AND_THINKING_READY_NO_SEND",
                "model_family":"pro","thinking_level":"medium",
                "verified_port":primary_port,"gemini_requests_submitted":0}

    def fake_campaign(self,**kwargs):
        self.calls.append(("SOURCE_JOB",os.getenv("MICROGEN_GEMINI_UI_MODE")))
        return {"status":"ACADEMIC_REVIEW_STILL_NOT_APPROVED",
                "new_requests_attempted":1,"jobs_completed":[],
                "jobs_not_rerun":[],"G2_approved":False,
                "student_publication_authorized":False}

    def historical_failure(self):
        # Existing source route is immutable. Initial dry mock campaign only
        # creates a route; no actual model or publisher invocation happens.
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"flash"}):
            def first_ready(*,primary_port):
                if os.environ["MICROGEN_GEMINI_UI_MODE"]=="flash":
                    from selenium_pipeline.academic_gemini_presend_preflight import (
                        AcademicGeminiPreSendBlocked)
                    raise AcademicGeminiPreSendBlocked(
                        "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE")
                return self.ready(primary_port=primary_port)
            run(plan_path=self.plan,root=self.work,
                campaign=self.fake_campaign,inspect_ready=first_ready)
        self.calls.clear()
        route=self.work/"academic_model_route_v1.json"
        base=time.time()-4000
        for name,token,when in (
                ("old","b"*64,base),("new","c"*64,base+1)):
            win=self.parent/name/"job_01_checkpoint"
            win.mkdir(parents=True)
            (win/"request_state.json").write_text(json.dumps({
                "schema_version":1,"source_sha256":SRC,
                "request_fingerprint":token,
                "status":"SUBMITTED_OR_UNCERTAIN",
                "submission_may_have_occurred":True,
                "can_auto_retry":False,
                "academic_approval":False,"tts_authorized":False,
                "student_publication_authorized":False}),encoding="utf8")
            (win/"dispatch_attempted.claim").write_text(token,encoding="utf8")
            record_original_failure(checkpoint=win,
                route_receipt=route,checkpoint_parent=self.parent,now=when)
        current=inspect(checkpoint_parent=self.parent,
                        source_sha=SRC,family="pro")
        self.assertTrue(current["source_free_health_probe_due"])
        self.assertFalse(current["automatic_new_academic_model_send_allowed"])

    def response(self,prompt,port):
        self.calls.append(("SOURCE_FREE_HEALTH",port))
        start=prompt.index('{"microgen_health":"ok"')
        value=prompt[start:]
        return OwnedGeminiResponse(value,
            registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
            new_turn_verified=True)

    def test_normal_campaign_validates_source_free_response_then_advances(self):
        self.historical_failure()
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"flash"}):
            result=run(plan_path=self.plan,root=self.work,max_jobs=4,
                campaign=self.fake_campaign,inspect_ready=self.ready,
                health_probe=lambda **kw:probe_once(
                    **kw,browser_request=self.response))
        self.assertEqual(result["bounded_original_source_jobs_budget"],1)
        self.assertEqual([x[0] for x in self.calls],
                         ["preflight","SOURCE_FREE_HEALTH","SOURCE_JOB"])
        self.assertEqual(result["new_requests_attempted"],1)
        self.assertFalse(result["G2_approved"])
        self.assertEqual(result["academic_transport_health"]["status"],
                         "ACADEMIC_GEMINI_REQUALIFIED_NEW_SOURCE_SEND_ALLOWED")
        # A repeated call reuses valid source-free proof with no new probe
        # and normal campaign still applies its own global claim index.
        self.calls.clear()
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"flash"}):
            resumed=run(plan_path=self.plan,root=self.work,max_jobs=4,
                campaign=self.fake_campaign,inspect_ready=self.ready,
                health_probe=lambda **_:self.fail("no duplicate probe"))
        self.assertEqual(resumed["bounded_original_source_jobs_budget"],1)
        self.assertEqual([x[0] for x in self.calls],
                         ["preflight","SOURCE_JOB"])

    def test_failed_source_free_probe_blocks_original_jobs_all_day(self):
        self.historical_failure()
        def broken(prompt,port):
            self.calls.append(("FAILED_HEALTH",port))
            raise TimeoutError("synthetic no response")
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"flash"}):
            result=run(plan_path=self.plan,root=self.work,
                campaign=self.fake_campaign,inspect_ready=self.ready,
                health_probe=lambda **kw:probe_once(
                    **kw,browser_request=broken))
        self.assertEqual([x[0] for x in self.calls],
                         ["preflight","FAILED_HEALTH"])
        self.assertEqual(result["new_requests_attempted"],0)
        self.assertEqual(result["academic_transport_health"]["status"],
                         "ACADEMIC_GEMINI_SOURCE_FREE_REQUALIFICATION_REQUIRED")
        self.calls.clear()
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"flash"}):
            again=run(plan_path=self.plan,root=self.work,
                campaign=self.fake_campaign,inspect_ready=self.ready,
                health_probe=lambda **kw:probe_once(
                    **kw,browser_request=broken))
        self.assertEqual([x[0] for x in self.calls],["preflight"])
        self.assertEqual(again["new_requests_attempted"],0)
        self.assertEqual(again["academic_source_free_probe"]
                         ["new_provider_requests"],0)
