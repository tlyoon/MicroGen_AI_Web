"""Offline rich input-capacity and post-canary failed-job stop regressions.

No browser/network/Gemini Send. All synthetic evidence lives in temp paths.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
import unittest

from selenium_pipeline.windows_rich_mapping_capacity_admission import (
    inspect_rich_mapping_capacity,_newer_uncertain_claims,
)

LONG="source_sized_g2_rich_capacity_v7"
SHORT="source_sized_g2_rich_route_v6"
SOURCE="a"*64
HEALTH={"new_source_stage_send_eligible":True}
class RichWorkloadAdmissionTests(unittest.TestCase):
    def setUp(self):
        holder=tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root=Path(holder.name)/"MicroGen_AI_Web_Checkpoints"
        self.root.mkdir()
        self.canary=self.root/"latest"/"browser_probe_result.json"
        self.canary.parent.mkdir()
        self.canary.write_text("{}")
        os.utime(self.canary,(2000,2000))

    def latest(self,*,profile=SHORT,chars=2006,canary=None):
        if canary is None:
            canary=self.canary
        return {
            "status":"LATEST_IMMUTABLE_CANARY_IDENTIFIED",
            "canary_path":str(canary),
            "canary":{"outcome":"VALID_CANARY_RESPONSE",
                      "probe_profile":profile,
                      "prompt_characters":chars,
                      "gemini_new_user_turn_verified":True,
                      "source_pdf_transmitted":False},
        }

    def capacity(self,*,latest=None,chars=17881):
        return inspect_rich_mapping_capacity(
            prompt_characters=chars,base_admission=HEALTH,
            latest_inspect=lambda:latest or self.latest())

    def claim(self,*,created=2100,status="MAY_HAVE_SUBMITTED_RECONCILE_BEFORE_RESEND"):
        folder=self.root/".microgen_rich_mapping_once"/SOURCE
        folder.mkdir(parents=True,exist_ok=True)
        record={"schema_version":1,"global_original_source_slide_once":True,
                "created_unix":created,"slide":4,"status":status,
                "source_inputs_sha256":{"source.pdf":SOURCE}}
        path=folder/"slide_004.once.json"
        path.write_text(json.dumps(record))
        return path

    def test_verified_two_k_canary_does_not_certify_real_18k(self):
        result=self.capacity()
        self.assertEqual(result["status"],
                         "RICH_PROMPT_EXCEEDS_VERIFIED_CANARY_NO_SEND")
        self.assertEqual(result["latest_verified_canary_characters"],2006)
        self.assertFalse(result["rich_model_send_eligible"])
        self.assertFalse(result["new_model_or_tts_calls"])

    def test_small_new_task_can_use_owned_transport_proof(self):
        result=self.capacity(chars=1800)
        self.assertEqual(result["status"],
                         "RICH_SOURCE_BROWSER_CAPACITY_VERIFIED_FOR_ONE_STAGE")
        self.assertTrue(result["rich_model_send_eligible"])

    def test_exact_v7_long_valid_canary_allows_one_new_task(self):
        result=self.capacity(latest=self.latest(profile=LONG,chars=20300))
        self.assertTrue(result["rich_model_send_eligible"])
        self.assertEqual(result["rich_pending_claims_since_canary"],0)

    def test_recent_unresolved_original_after_v7_blocks_without_resend(self):
        self.claim()
        result=self.capacity(latest=self.latest(profile=LONG,chars=20300))
        self.assertEqual(result["status"],
                         "RICH_POST_CANARY_SOURCE_JOB_UNVERIFIED_NO_SEND")
        self.assertEqual(result["rich_pending_claims_since_canary"],1)
        self.assertFalse(result["rich_model_send_eligible"])

    def test_older_unresolved_claim_is_not_new_provider_failure(self):
        self.claim(created=1800)
        result=self.capacity(latest=self.latest(profile=LONG,chars=20300))
        self.assertEqual(result["rich_pending_claims_since_canary"],0)
        self.assertTrue(result["rich_model_send_eligible"])

    def test_completed_original_review_is_not_failure_circuit(self):
        self.claim(status="CAPTURED_SOURCE_VERIFIED_REVIEW_ONLY")
        result=self.capacity(latest=self.latest(profile=LONG,chars=20300))
        self.assertTrue(result["rich_model_send_eligible"])

    def test_corrupt_global_claim_fails_closed(self):
        path=self.claim()
        record=json.loads(path.read_text())
        record["source_inputs_sha256"]["source.pdf"]="b"*64
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,"UNTRUSTED"):
            self.capacity(latest=self.latest(profile=LONG,chars=20300))

    def test_health_without_fresh_source_free_owned_turn_blocks(self):
        result=inspect_rich_mapping_capacity(
            prompt_characters=1800,
            base_admission={"new_source_stage_send_eligible":False})
        self.assertEqual(result["status"],"RICH_SOURCE_BROWSER_ROUTE_UNVERIFIED_NO_SEND")
        self.assertFalse(result["rich_model_send_eligible"])

    @unittest.skipUnless(os.name=="nt","Physical original only on authorized Windows")
    def test_dell_original_slide_four_uncertain_after_v6(self):
        local=os.environ.get("LOCALAPPDATA")
        if not local: self.skipTest("No Dell checkpoint root")
        root=Path(local)/"MicroGen_AI_Web_Checkpoints"
        proof=root/"20261114_G2_RICH_ROUTE_V6"/"browser_probe_result.json"
        claim=root/".microgen_rich_mapping_once"/(
            "64b748468e6bdb12ddb127f1d8bea90a7f3f63d270fbb5378ba1d3ddeeb955fd"
        )/"slide_004.once.json"
        if not proof.is_file() or not claim.is_file():
            self.skipTest("Physical slide4/v6 Dell evidence absent")
        from selenium_pipeline.windows_gemini_differential_probe import _read
        latest={
            "status":"LATEST_IMMUTABLE_CANARY_IDENTIFIED",
            "canary_path":str(proof),"canary":_read(proof)
        }
        report=self.capacity(latest=latest,chars=17881)
        self.assertEqual(report["status"],
                         "RICH_POST_CANARY_SOURCE_JOB_UNVERIFIED_NO_SEND")
        self.assertGreaterEqual(report["rich_pending_claims_since_canary"],1)

if __name__=="__main__":
    unittest.main()
