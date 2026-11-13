"""Source-free regression for short source-review job scheduling and global claims."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from selenium_pipeline.academic_source_microbatch import (
    unclaimed_microbatch_plan, ensure_microbatch_dispatch)

SOURCE="a"*64


class AcademicShortSourceJobTests(TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base=Path(temp.name)
        self.checkpoints=self.base/"checkpoints"
        self.checkpoints.mkdir()
        self.legacy=self.checkpoints/"original_plan"
        self.legacy.mkdir()
        self.path=self.legacy/"plan.json"
        self.work=self.checkpoints/"one_shot_campaign"
        self.work.mkdir()
        self.ids=["s014.utterance.001","s014.utterance.002",
                  "s014.utterance.003","s014.utterance.004"]
        self.job={
            "source_sha256":SOURCE,
            "status":"SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED",
            "source_research_is_new_evidence_only":True,
            "utterance_count":4,
            "selected_original_slides":[14],
            "slides":[{
                "slide":14,
                "visual_targets":[],
                "utterances":[{
                    "id":u,"spoken_text":u,"spoken_sha256":"b"*64
                } for u in self.ids]}],
            "verified_source_quote_candidates_v1":{
                "utterances":[{
                    "utterance_id":uid,
                    "allowed_citations":[]} for uid in self.ids]},
            "academic_approval":False,
            "student_publication_authorized":False}
        self.entry={
            "source_job":self.job,
            "source_job_request_sha256":"b"*64,
            "eligible_original_unresolved_units":self.ids,
            "change_reasons":{u:{"new_exact_quote":True} for u in self.ids},
            "actual_model_request_submitted":False}
        self.original={
            "schema_version":1,
            "status":"UNSENT_PHYSICALLY_CHANGED_G2_SOURCE_AND_VISUAL_EVIDENCE",
            "source_sha256":SOURCE,
            "original_utterances":4,
            "jobs":[self.entry],
            "G2_approved":False,
            "student_publication_authorized":False}
        self.path.write_text(json.dumps(self.original),encoding="utf8")
        self.verifier=patch(
            "selenium_pipeline.academic_source_microbatch._assert_job",
            side_effect=lambda entry,sha:(
                entry["source_job"],self.base,"verified-old-prompt",
                [x["id"] for s in entry["source_job"]["slides"]
                 for x in s["utterances"]]))
        self.verifier.start()
        self.addCleanup(self.verifier.stop)

    def _claim(self,uids,name="d"*64):
        claim_dir=self.checkpoints/".microgen_academic_source_once"/SOURCE
        claim_dir.mkdir(parents=True,exist_ok=True)
        (claim_dir/(name+".json")).write_text(json.dumps({
            "schema_version":1,"type":"THIRD_PASS_CHANGED_SOURCE_REVIEW",
            "source_sha256":SOURCE,"utterance_ids":uids,
            "request_sha256":name}),encoding="utf8")

    def test_no_claims_shrink_four_into_two_source_locked_journals(self):
        result=unclaimed_microbatch_plan(
            original_plan=self.path,checkpoint_parent=self.checkpoints)
        self.assertEqual(result["previous_consumed_units_excluded"],0)
        self.assertEqual(result["remaining_original_unclaimed_units"],4)
        self.assertEqual([x["eligible_original_unresolved_units"] for x in
                          result["jobs"]],[self.ids[:2],self.ids[2:]])
        self.assertEqual([x["source_job"]["utterance_count"] for x in
                          result["jobs"]],[2,2])
        self.assertFalse(result["G2_approved"])
        self.assertEqual(self.path.read_text(),
                         json.dumps(self.original))

    def test_prior_9_unit_consumed_claim_blocks_any_repackaging(self):
        self._claim(self.ids[:3])
        result=unclaimed_microbatch_plan(
            original_plan=self.path,checkpoint_parent=self.checkpoints)
        self.assertEqual(result["previous_consumed_units_excluded"],3)
        self.assertEqual([x["eligible_original_unresolved_units"] for x in
                          result["jobs"]],[self.ids[3:]])
        self.assertEqual(result["remaining_original_unclaimed_units"],1)

    def test_write_once_short_plan_reuses_then_versions_new_claim_snapshot(self):
        first_plan,first_root,record=ensure_microbatch_dispatch(
            original_plan=self.path,requested_root=self.work)
        again_plan,again_root,_=ensure_microbatch_dispatch(
            original_plan=self.path,requested_root=self.work)
        self.assertEqual((first_plan,first_root),(again_plan,again_root))
        self.assertEqual(json.loads(first_plan.read_text())["jobs"],record["jobs"])
        # Regression for prior v1 bug: sorting JSON keys altered the
        # request SHA after reopening its persisted source-bound plan.
        import hashlib
        from selenium_pipeline.ai_academic_web_review import review_instructions
        for entry in json.loads(first_plan.read_text())["jobs"]:
            encoded=review_instructions(entry["source_job"],
                                        mode="INDEPENDENT_CHALLENGE").encode("utf8")
            self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                             entry["source_job_request_sha256"])
        self.assertEqual(first_root.parent,self.checkpoints)
        self._claim(self.ids[:2])
        next_plan,next_root,next_record=ensure_microbatch_dispatch(
            original_plan=self.path,requested_root=self.work)
        self.assertNotEqual((first_plan,first_root),(next_plan,next_root))
        self.assertTrue(first_plan.is_file())
        self.assertEqual(next_record["remaining_original_unclaimed_units"],2)

    def test_invalid_or_foreign_global_claim_fails_closed(self):
        self._claim(self.ids[:2])
        folder=self.checkpoints/".microgen_academic_source_once"/SOURCE
        item=next(folder.glob("*.json"))
        forged=json.loads(item.read_text())
        forged["source_sha256"]="f"*64
        item.write_text(json.dumps(forged),encoding="utf8")
        with self.assertRaises(Exception):
            unclaimed_microbatch_plan(
                original_plan=self.path,checkpoint_parent=self.checkpoints)

    def test_source_verification_refusal_cannot_be_bypassed(self):
        self.verifier.stop()
        with patch(
            "selenium_pipeline.academic_source_microbatch._assert_job",
            side_effect=ValueError("Real source SHA drift")):
            with self.assertRaisesRegex(ValueError,"Real source SHA drift"):
                unclaimed_microbatch_plan(
                    original_plan=self.path,checkpoint_parent=self.checkpoints)

    def test_claimed_all_original_source_units_produces_no_send_plan(self):
        self._claim(self.ids)
        result=unclaimed_microbatch_plan(
            original_plan=self.path,checkpoint_parent=self.checkpoints)
        self.assertEqual(result["jobs"],[])
        with self.assertRaises(Exception):
            ensure_microbatch_dispatch(
                original_plan=self.path,requested_root=self.work)
