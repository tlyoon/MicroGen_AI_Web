"""V6 safe independent G2 readiness while Gemini PDF response is unavailable."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.g2_offline_source_readiness import (
    _receipt_path, _source_identifiers, inspect_and_checkpoint)


class OfflineSourceReadinessTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.folder=self.root/"source_tree"/"1"/"1.3"
        self.folder.mkdir(parents=True)
        self.queue=self.root/"queue";self.queue.mkdir()
        self.work=self.root/"work";self.work.mkdir()
        for n in ("source.pdf","slides.pdf","script.txt"):
            (self.folder/n).write_text("immutable fixture "+n,encoding="utf8")
        (self.queue/"queue.json").write_text('{"status":"FAKE_IMMUTABLE_QUEUE"}')
        self.events=[]
        from selenium_pipeline import g2_offline_source_readiness as module
        self.patchers=[
            patch("selenium_pipeline.windows_g2_autonomous_qa_supervisor._is_verified_folder",
                  side_effect=self.folder_identity),
            patch("selenium_pipeline.incremental_lecture_sync_queue.inspect_pre_tts_folder",
                  side_effect=lambda f:self.events.append("pre_tts") or {"status":"fixture"}),
            patch("selenium_pipeline.incremental_element_candidate_map.candidate_map",
                  side_effect=self.map_fixture),
            patch("selenium_pipeline.ai_academic_web_review.build_review_job",
                  side_effect=self.job_fixture),
            patch("selenium_pipeline.academic_visual_preflight.inspect",
                  side_effect=self.visual_fixture),
            patch("selenium_pipeline.ai_academic_review_consensus.reconcile_actual_review_queue",
                  side_effect=self.consensus_fixture),
        ]
        for p in self.patchers:
            p.start()
            self.addCleanup(p.stop)

    def folder_identity(self,folder,queue_root):
        return {},{n:file_sha256(self.folder/n)
                   for n in ("source.pdf","slides.pdf","script.txt")}

    def map_fixture(self,*,folder,queue=None):
        self.events.append("candidate_map")
        return {
            "status":"PER_UTTERANCE_SLIDE_ELEMENT_CANDIDATES_REVIEW_REQUIRED",
            "source_sha256":file_sha256(self.folder/"source.pdf"),
            "slides_sha256":file_sha256(self.folder/"slides.pdf"),
            "script_sha256":file_sha256(self.folder/"script.txt"),
            "slide_count":2,"utterance_count":3,
            "slides":[
                {"slide":1,"candidate_visual_targets":[
                    {"kind":"text_block"},{"kind":"image_whole"}],
                 "original_utterance_candidates":[
                    {"candidate_visual_targets":[{"target_id":"abc"}]}]},
                {"slide":2,"candidate_visual_targets":[
                    {"kind":"text_block"}],
                 "original_utterance_candidates":[
                    {"candidate_visual_targets":[]},
                    {"candidate_visual_targets":[{"target_id":"def"}]}]},
            ],
        }

    def job_fixture(self,*,folder,slide_numbers):
        self.events.append("build_job")
        self.assertEqual(slide_numbers,[2])
        return {
            "utterance_count":2,
            "verified_source_quote_candidates_v1":{
                "status":"PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1",
                "source_sha256":file_sha256(self.folder/"source.pdf"),
                "utterances":[
                    {"allowed_citations":[{"source_page":1,
                                          "quote_sha256":"a"*64}]},
                    {"allowed_citations":[]},
                ]
            }
        }

    def visual_fixture(self,pdf):
        self.events.append("visual_geometry")
        return {
            "pdf_sha256":file_sha256(self.folder/"slides.pdf"),
            "pages":2,"mathematical_correctness_verified":False,
            "blocker_count":1,"findings_total":2,
            "details":[
                {"findings":[]},
                {"findings":[{"reason":"possible_figure_review"},
                             {"reason":"clipped_figure"}]}]
        }

    def consensus_fixture(self,*,queue_root,folder):
        self.events.append("reconcile_consensus")
        return {
            "status":"INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE",
            "original_utterances":3,"accepted_ai_evidence":[{"id":"1"}],
            "pending_or_disputed":2
        }

    def run_audit(self,**kwargs):
        return inspect_and_checkpoint(
            folder=self.folder,queue_root=self.queue,work_root=self.work,
            next_slide=2,**kwargs)

    def test_real_integrated_offline_audit_writes_immutable_not_approved(self):
        result=self.run_audit()
        self.assertEqual(result["status"],
                         "G2_OFFLINE_READINESS_COMPLETED_NO_GEMINI_SEND")
        self.assertEqual(result["original_utterance_count"],3)
        self.assertEqual(result["slide_count"],2)
        self.assertEqual(result["original_two_pass_accepted"],1)
        self.assertEqual(result["original_pending_or_disputed"],2)
        self.assertEqual(
            result["verified_source_citation_candidate_count_for_next_slide"],1)
        self.assertEqual(result["technical_geometry_blocker_count"],1)
        record=json.loads(Path(result["offline_evidence_path"]).read_text())
        self.assertEqual(record["slide_inventory"][1][
            "utterances_without_ranked_targets"],1)
        self.assertFalse(record["figure_semantics_verified"])
        self.assertFalse(record["academic_approval"])
        self.assertFalse(record["independent_scientific_consensus_granted"])
        self.assertFalse(record["student_publication_authorized"])
        self.assertEqual(record["new_model_requests"],0)
        self.assertEqual(record["paid_tts_calls"],0)
        self.assertEqual(list(self.folder.glob("*.json")),[])

    def test_restart_reuses_without_regenerating_or_adding_stage(self):
        first=self.run_audit()
        count=len(self.events)
        second=self.run_audit()
        self.assertEqual(second["status"],
                         "G2_OFFLINE_READINESS_REUSED_NO_NEW_WORK")
        self.assertEqual(first["offline_evidence_sha256"],
                         second["offline_evidence_sha256"])
        self.assertEqual(len(self.events),count)
        self.assertEqual(len(list(self.work.rglob("*.json"))),1)

    def test_recover_fsynced_precommit_record_after_process_crash(self):
        first=self.run_audit()
        path=Path(first["offline_evidence_path"])
        torn=path.with_name(path.name+".incomplete")
        path.rename(torn)
        count=len(self.events)
        second=self.run_audit()
        self.assertEqual(second["status"],
                         "G2_OFFLINE_READINESS_REUSED_NO_NEW_WORK")
        self.assertEqual(len(self.events),count)
        self.assertTrue(path.is_file())
        self.assertFalse(torn.exists())

    def test_tampered_science_acceptance_fails_closed(self):
        first=self.run_audit()
        path=Path(first["offline_evidence_path"])
        record=json.loads(path.read_text())
        record["academic_approval"]=True
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,"may not be forged or promoted"):
            self.run_audit()

    def test_torn_corrupt_checkpoint_fails_closed(self):
        first=self.run_audit()
        path=Path(first["offline_evidence_path"])
        path.rename(path.with_name(path.name+".incomplete"))
        path.with_name(path.name+".incomplete").write_text("tampered")
        with self.assertRaises((ValueError,TypeError,json.JSONDecodeError)):
            self.run_audit()
        self.assertFalse(path.exists())

    def test_source_change_creates_new_content_addressed_proof(self):
        first=self.run_audit()
        (self.folder/"source.pdf").write_text("changed source only")
        second=self.run_audit()
        self.assertNotEqual(first["offline_evidence_sha256"],
                            second["offline_evidence_sha256"])
        self.assertNotEqual(first["offline_evidence_path"],
                            second["offline_evidence_path"])
        self.assertEqual(len(list(self.work.rglob("*.json"))),2)

    def test_ranker_version_change_invalidates_old_offline_audit(self):
        original=self.run_audit()
        before=len(self.events)
        # Exact same original PDFs/queue, but algorithm implementation
        # changed. Replaying an old candidate-map report is now unsafe.
        def changed_ranker_code(path):
            if Path(path).name=="element_plan_autodraft.py":
                return "f"*64
            return file_sha256(path)
        with patch("selenium_pipeline.g2_offline_source_readiness.file_sha256",
                   side_effect=changed_ranker_code):
            revised=self.run_audit()
        self.assertNotEqual(original["offline_evidence_path"],
                            revised["offline_evidence_path"])
        self.assertGreater(len(self.events),before)
        self.assertEqual(len(list(self.work.rglob("*.json"))),2)
        self.assertFalse(revised["scientific_approval"])
        self.assertEqual(revised["new_model_requests"],0)

    def test_read_only_creates_no_receipts_or_provider_calls(self):
        result=self.run_audit(execute=False)
        self.assertEqual(result["status"],
                         "G2_OFFLINE_READINESS_POSSIBLE_NO_DISPATCH")
        self.assertEqual(self.events,[])
        self.assertFalse(list(self.work.rglob("*.json")))

    def test_invalid_untrusted_next_slide_denied(self):
        with self.assertRaises(ValueError):
            inspect_and_checkpoint(folder=self.folder,queue_root=self.queue,
                                   work_root=self.work,next_slide=0)
        self.assertEqual(self.events,[])

    def test_missing_queue_cannot_masquerade_as_source_bound_audit(self):
        (self.queue/"queue.json").unlink()
        with self.assertRaisesRegex(ValueError,"immutable academic queue"):
            self.run_audit()

if __name__=="__main__":
    unittest.main()
