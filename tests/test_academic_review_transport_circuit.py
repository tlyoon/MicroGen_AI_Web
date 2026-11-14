"""No-Send source-academic transport health from exact original state receipts."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import json

from selenium_pipeline.academic_review_transport_circuit import (
    record_original_failure, inspect, AcademicTransportCircuitError)

SOURCE="a"*64


class SourceLockedAcademicTransportCircuit(TestCase):
    def setUp(self):
        t=TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.route=self.root/"academic_model_route_v1.json"
        self.route.write_text(json.dumps({
            "schema_version":1,"source_sha256":SOURCE,
            "selected_academic_model_family":"pro",
            "selected_thinking_level":"medium",
            "G2_approved":False,"academic_approval":False,
            "student_publication_authorized":False}),encoding="utf8")

    def checkpoint(self,name,prompt):
        path=self.root/name/"job_01_checkpoint"
        path.mkdir(parents=True)
        (path/"request_state.json").write_text(json.dumps({
            "schema_version":1,
            "source_sha256":SOURCE,"request_fingerprint":prompt,
            "status":"SUBMITTED_OR_UNCERTAIN",
            "submission_may_have_occurred":True,
            "can_auto_retry":False,
            "academic_approval":False,
            "tts_authorized":False,
            "student_publication_authorized":False}),encoding="utf8")
        (path/"dispatch_attempted.claim").write_text(
            prompt,encoding="utf8")
        return path

    def test_two_distinct_failed_original_claims_halt_until_finite_cooldown(self):
        old=self.checkpoint("first","b"*64)
        new=self.checkpoint("second","c"*64)
        record_original_failure(checkpoint=old,route_receipt=self.route,
                                checkpoint_parent=self.root,now=1000)
        one=inspect(checkpoint_parent=self.root,source_sha=SOURCE,
                    family="pro",now=1000)
        self.assertEqual(one["distinct_failed_requests"],1)
        self.assertTrue(one["automatic_new_academic_model_send_allowed"])
        record_original_failure(checkpoint=new,route_receipt=self.route,
                                checkpoint_parent=self.root,now=1001)
        stopped=inspect(checkpoint_parent=self.root,source_sha=SOURCE,
                        family="pro",now=1001)
        self.assertEqual(stopped["distinct_failed_requests"],2)
        self.assertFalse(stopped["automatic_new_academic_model_send_allowed"])
        self.assertFalse(stopped["provider_outage_proven"])
        self.assertFalse(stopped["old_request_retry_authorized"])
        # Time alone is NOT proof Gemini recovered. Historical failure
        # receipts remain active even after the old 30-minute cooldown.
        expired=inspect(checkpoint_parent=self.root,
                        source_sha=SOURCE,family="pro",now=2802)
        self.assertFalse(expired["automatic_new_academic_model_send_allowed"])
        self.assertTrue(expired["source_free_health_probe_due"])
        self.assertEqual(expired["distinct_failed_requests"],2)
        self.assertEqual(expired["status"],
                         "ACADEMIC_GEMINI_SOURCE_FREE_REQUALIFICATION_REQUIRED")
        # Exact historical defect: 3600 seconds used to erase two genuine
        # failure observations and silently reopen ORIGINAL source Sends.
        beyond_old_window=inspect(checkpoint_parent=self.root,
                         source_sha=SOURCE,family="pro",now=1000+7200)
        self.assertEqual(beyond_old_window["distinct_failed_requests"],2)
        self.assertFalse(beyond_old_window[
            "automatic_new_academic_model_send_allowed"])
        self.assertTrue(beyond_old_window["source_free_health_probe_due"])

    def test_duplicate_failure_same_original_fingerprint_not_counted_twice(self):
        old=self.checkpoint("only","b"*64)
        one=record_original_failure(checkpoint=old,route_receipt=self.route,
                                    checkpoint_parent=self.root,now=1000)
        two=record_original_failure(checkpoint=old,route_receipt=self.route,
                                    checkpoint_parent=self.root,now=1010)
        self.assertEqual(one,two)
        self.assertEqual(inspect(checkpoint_parent=self.root,source_sha=SOURCE,
                                 family="pro",now=1010)
                         ["distinct_failed_requests"],1)

    def test_forged_and_tampered_source_state_fails_closed(self):
        old=self.checkpoint("only","b"*64)
        record_original_failure(checkpoint=old,route_receipt=self.route,
                                checkpoint_parent=self.root,now=1000)
        state=old/"request_state.json"
        obj=json.loads(state.read_text())
        obj["status"]="SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"
        state.write_text(json.dumps(obj),encoding="utf8")
        with self.assertRaises(AcademicTransportCircuitError):
            inspect(checkpoint_parent=self.root,source_sha=SOURCE,
                    family="pro",now=1001)

    def test_unconfirmed_presend_and_accepted_response_do_not_halt(self):
        old=self.checkpoint("only","b"*64)
        obj=json.loads((old/"request_state.json").read_text())
        obj["submission_may_have_occurred"]=False
        (old/"request_state.json").write_text(json.dumps(obj),encoding="utf8")
        with self.assertRaises(AcademicTransportCircuitError):
            record_original_failure(checkpoint=old,route_receipt=self.route,
                                    checkpoint_parent=self.root,now=1000)
        obj["submission_may_have_occurred"]=True
        (old/"request_state.json").write_text(json.dumps(obj),encoding="utf8")
        (old/"model_response_identity.json").write_text("{}",encoding="utf8")
        with self.assertRaises(AcademicTransportCircuitError):
            record_original_failure(checkpoint=old,route_receipt=self.route,
                                    checkpoint_parent=self.root,now=1000)

    def test_model_family_isolation_from_other_healthy_routes(self):
        self.checkpoint("first","b"*64)
        old=self.root/"first"/"job_01_checkpoint"
        new=self.checkpoint("second","c"*64)
        for time_mark,item in ((1000,old),(1001,new)):
            record_original_failure(checkpoint=item,route_receipt=self.route,
                                    checkpoint_parent=self.root,now=time_mark)
        self.assertTrue(inspect(checkpoint_parent=self.root,source_sha=SOURCE,
                                family="flash",now=1001)
                        ["automatic_new_academic_model_send_allowed"])
