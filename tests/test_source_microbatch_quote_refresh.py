"""Normal short-source planning automatically refreshes stale citations.

Real synthetic PDF and serializer: no Gemini Send, no model/TTS, no change
to the original SHA-bound job. The same app path is used for all source PDFs.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import pymupdf

from selenium_pipeline.academic_source_microbatch import (
    ensure_microbatch_dispatch, unclaimed_microbatch_plan)
from selenium_pipeline.ai_academic_web_review import review_instructions
from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.pdf_text_source_span_witness import (
    prove_source_quote_occurrence)


def hashed(value):
    return hashlib.sha256(value.encode("utf8")).hexdigest()


class VersionedPhysicalCitationRefresh(TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home=Path(temp.name)
        self.assets=self.home/"synthetic_lesson"
        self.assets.mkdir()
        self.checkpoints=self.home/"checkpoints"
        self.checkpoints.mkdir()
        self.work=self.checkpoints/"active"
        self.work.mkdir()
        old_line=(
            "A skydiver moves downward through the air at constant speed.")
        new_line=(
            "After the skydiver opens a parachute, the upward drag increases "
            "and the downward velocity decreases because acceleration points upward.")
        with pymupdf.open() as document:
            page=document.new_page(width=720,height=520)
            page.insert_text((45,90),old_line,fontsize=11)
            page.insert_text((45,145),new_line,fontsize=11)
            document.save(self.assets/"source.pdf")
        with pymupdf.open() as slide:
            page=slide.new_page(width=720,height=520)
            page.insert_text((45,60),"Parachute opening and upward drag.",
                             fontsize=11)
            slide.save(self.assets/"slides.pdf")
        spoken=(
            "After the skydiver opens a parachute, how do upward drag "
            "and acceleration affect downward velocity?")
        (self.assets/"script.txt").write_text(spoken,encoding="utf8")
        self.uid="s001.utterance.001"
        self.source_sha=_sha(self.assets/"source.pdf")
        old_proof=prove_source_quote_occurrence(
            source_pdf=self.assets/"source.pdf",
            expected_sha256=self.source_sha,page_number=1,
            verbatim_quote=old_line)
        self.old_quote={
            "source_page":1,"verbatim_source_quote":old_line,
            "quote_sha256":old_proof["quote_sha256"],
            "source_text_bbox_pdf_pt":[45.0,75.0,550.0,95.0],
        }
        quote_packet={
            "status":"PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1",
            "source_sha256":self.source_sha,
            "slides_sha256":_sha(self.assets/"slides.pdf"),
            "script_sha256":_sha(self.assets/"script.txt"),
            "utterances":[{
                "utterance_id":self.uid,
                "spoken_sha256":hashed(spoken),
                "allowed_citations":[self.old_quote],
            }],
            "citations_are_scientific_proof":False,
            "all_mathematics_verified":False,
            "student_publication_authorized":False,
        }
        job={
            "status":"SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED",
            "original_folder":str(self.assets),
            "source_sha256":self.source_sha,
            "slides_sha256":_sha(self.assets/"slides.pdf"),
            "script_sha256":_sha(self.assets/"script.txt"),
            "source_research_is_new_evidence_only":True,
            "utterance_count":1,
            "selected_original_slides":[1],
            "slides":[{
                "slide":1,
                "visual_targets":[{
                    "id":"s001.text.001",
                    "kind":"text",
                    "visible_text":"Parachute opening and upward drag.",
                    "bbox_pdf_pt":[45.0,40.0,260.0,64.0],
                }],
                "utterances":[{
                    "id":self.uid,
                    "spoken_text":spoken,
                    "spoken_sha256":hashed(spoken),
                    "ranked_candidates":["s001.text.001"],
                }],
            }],
            "verified_source_quote_candidates_v1":quote_packet,
            "academic_approval":False,
            "student_publication_authorized":False,
        }
        prompt=review_instructions(job,mode="INDEPENDENT_CHALLENGE")
        entry={
            "source_job":job,
            "source_job_request_sha256":hashed(prompt),
            "eligible_original_unresolved_units":[self.uid],
            "change_reasons":{self.uid:{"new_exact_quote":True}},
            "actual_model_request_submitted":False,
            "student_publication_authorized":False,
        }
        original={
            "schema_version":1,
            "status":"UNSENT_PHYSICALLY_CHANGED_G2_SOURCE_AND_VISUAL_EVIDENCE",
            "source_sha256":self.source_sha,
            "original_utterances":1,
            "jobs":[entry],
            "G2_approved":False,
            "student_publication_authorized":False,
        }
        self.plan_path=self.home/"immutable_original_plan.json"
        self.plan_path.write_text(json.dumps(original,indent=2),
                                  encoding="utf8")
        self.original_bytes=self.plan_path.read_bytes()
        self.hashes={n:_sha(self.assets/n)
                     for n in ("source.pdf","slides.pdf","script.txt")}

    def test_normal_dispatch_rebuilds_current_verified_source_quotes(self):
        derived_path,root,plan=ensure_microbatch_dispatch(
            original_plan=self.plan_path,requested_root=self.work)
        self.assertEqual(plan["source_microbatch_revision"],3)
        self.assertTrue(derived_path.name.endswith("_microbatch_v3.json"))
        self.assertEqual(root.parent,self.checkpoints)
        self.assertTrue(plan["jobs"])
        row=plan["jobs"][0]
        fresh=row["source_job"]["verified_source_quote_candidates_v1"][
            "utterances"][0]["allowed_citations"]
        self.assertTrue(fresh)
        self.assertTrue(any("parachute" in c["verbatim_source_quote"].lower()
                            for c in fresh))
        self.assertNotEqual([self.old_quote],fresh)
        self.assertTrue(row["source_quote_refresh_v1"][
            "quotes_changed_since_frozen_plan"])
        self.assertEqual(row["source_quote_refresh_v1"][
            "only_original_unclaimed_units"],[self.uid])
        self.assertEqual(row["source_original_large_job_request_sha256"],
                         json.loads(self.original_bytes)["jobs"][0][
                             "source_job_request_sha256"])
        for citation in fresh:
            proof=prove_source_quote_occurrence(
                source_pdf=self.assets/"source.pdf",
                expected_sha256=self.source_sha,
                page_number=citation["source_page"],
                verbatim_quote=citation["verbatim_source_quote"])
            self.assertEqual(proof["quote_sha256"],
                             citation["quote_sha256"])
        self.assertEqual(self.plan_path.read_bytes(),self.original_bytes)
        self.assertEqual({n:_sha(self.assets/n) for n in self.hashes},
                         self.hashes)
        self.assertFalse(plan["G2_approved"])
        self.assertEqual(plan["new_Gemini_or_TTS_requests"],0)
        again=ensure_microbatch_dispatch(
            original_plan=self.plan_path,requested_root=self.work)
        self.assertEqual((again[0],again[1]),(derived_path,root))

    def test_prior_claim_prevents_quote_refresh_or_resubmission(self):
        directory=self.checkpoints/".microgen_academic_source_once"/self.source_sha
        directory.mkdir(parents=True)
        token="c"*64
        (directory/(token+".json")).write_text(json.dumps({
            "schema_version":1,
            "type":"THIRD_PASS_CHANGED_SOURCE_REVIEW",
            "source_sha256":self.source_sha,
            "utterance_ids":[self.uid],
            "request_sha256":token,
        }),encoding="utf8")
        with patch("selenium_pipeline.academic_source_microbatch."
                   "build_verified_source_candidates",
                   side_effect=AssertionError("Old consumed request reopened")):
            result=unclaimed_microbatch_plan(
                original_plan=self.plan_path,
                checkpoint_parent=self.checkpoints)
        self.assertEqual(result["jobs"],[])
        self.assertEqual(result["previous_consumed_units_excluded"],1)
        self.assertEqual(self.plan_path.read_bytes(),self.original_bytes)

    def test_source_mutation_fails_before_any_derived_dispatch(self):
        with (self.assets/"source.pdf").open("ab") as file:
            file.write(b"\n")
        with self.assertRaises(Exception):
            ensure_microbatch_dispatch(
                original_plan=self.plan_path,requested_root=self.work)
        self.assertFalse(list(self.checkpoints.glob(
            ".microgen_academic_microbatch_plans/*.json")))

    def test_foreign_rebuilt_quote_scope_fails_closed(self):
        from selenium_pipeline.academic_source_microbatch import (
            build_verified_source_candidates as actual)
        def untrusted(*,folder,job):
            result=actual(folder=folder,job=job)
            return {**result,"source_sha256":"f"*64}
        with patch("selenium_pipeline.academic_source_microbatch."
                   "build_verified_source_candidates",side_effect=untrusted):
            with self.assertRaises(Exception):
                unclaimed_microbatch_plan(
                    original_plan=self.plan_path,
                    checkpoint_parent=self.checkpoints)
        self.assertEqual(self.plan_path.read_bytes(),self.original_bytes)
