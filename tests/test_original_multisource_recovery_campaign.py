"""Real Windows multisource fault injection: idempotent original evidence reuse.

Two independent physical publisher/author PDF/source/script sets are tested,
not fake URLs. Crash after first persisted source report must resume only the
second, without rerunning the first or any model/TTS/video call.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from selenium_pipeline.rich_element_mapping_checkpoint import (
    require_automatic_mapping_or_checkpoint,ElementMappingCheckpointBlocked)
from selenium_pipeline.rich_element_safe_prose_fallback import stage_section
from selenium_pipeline.rich_unresolved_model_queue import prepare_queue
from selenium_pipeline.original_multisource_recovery_campaign import (
    run_campaign,CampaignRecoveryBlocked)


class RealTwoSourceFaultRecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.specs=[]
        for sec in ("8.4","8.5"):
            lecture=self.root/"publisher"/"8"/sec
            lecture.mkdir(parents=True)
            source=lecture/"source.pdf"
            slides=lecture/"slides.pdf"
            script=lecture/"script.txt"
            text=(f"Section {sec} describes the original mathematical "
                  "model and its source conditions.")
            with pymupdf.open() as doc:
                p=doc.new_page()
                p.insert_text((65,94),text)
                doc.save(source)
            with pymupdf.open() as doc:
                p=doc.new_page()
                p.insert_text((65,94),text)
                p.draw_line((90,190),(230,206))
                doc.save(slides)
            script.write_text("**Slide 1 [12s]:\n"+text,encoding="utf8")
            external=self.root/("receipts_"+sec.replace(".","_"))
            external.mkdir()
            with self.assertRaises(ElementMappingCheckpointBlocked):
                require_automatic_mapping_or_checkpoint(
                    source=source,slides=slides,script=script,
                    checkpoint_root=external)
            checkpoint=next(external.glob("rich_element_map_*"))
            fallback=external/"accepted_prose"
            stage_section(source_folder=lecture,
                          checkpoint=checkpoint,destination=fallback)
            queue=external/"queue"
            prepare_queue(source_folder=lecture,checkpoint=checkpoint,
                          fallback_dir=fallback,destination=queue)
            self.specs.append({
                "section":sec,
                "lecture":str(lecture),
                "checkpoint":str(checkpoint),
                "fallback_dir":str(fallback),
                "queue_dir":str(queue),
                "model_responses":str(fallback),
            })
        self.output=self.root/"campaign"
        self.output.mkdir()
        self.original_files={
            sec["section"]:[(Path(sec["lecture"])/name).read_bytes()
                for name in ("source.pdf","slides.pdf","script.txt")]
            for sec in self.specs
        }

    def runit(self,**extra):
        return run_campaign(specs=self.specs,outdir=self.output,**extra)

    def test_two_original_sources_produce_durable_distinct_readiness_receipts(self):
        report=self.runit()
        self.assertEqual(report["original_sections"],2)
        self.assertEqual(report["new_original_sections_inspected"],2)
        self.assertEqual(report["reused_prior_section_receipts_without_rerunning"],0)
        self.assertEqual(report["status"],
                         "ORIGINAL_MULTISOURCE_CAMPAIGN_INCOMPLETE_SOURCE_GATES")
        self.assertFalse(report["new_paid_generation_performed"])
        self.assertFalse(report["student_publication_authorized"])
        for sec in self.specs:
            self.assertEqual(
                [(Path(sec["lecture"])/name).read_bytes()
                 for name in ("source.pdf","slides.pdf","script.txt")],
                self.original_files[sec["section"]])

    def test_restart_on_unchanged_source_skips_all_previous_expensive_scans(self):
        self.runit()
        with patch("selenium_pipeline.original_source_e2e_acceptance.inspect_source_e2e",
                   side_effect=AssertionError("All original receipts cached")) as run:
            response=self.runit()
        run.assert_not_called()
        self.assertEqual(response["reused_prior_section_receipts_without_rerunning"],2)
        self.assertEqual(response["new_original_sections_inspected"],0)

    def test_fault_after_first_accepted_section_resumes_second_not_first(self):
        def fault(name):
            if name=="8.4":
                raise RuntimeError("Simulated abrupt crash after first receipt")
        with self.assertRaisesRegex(RuntimeError,"Simulated abrupt crash"):
            self.runit(after_section=fault)
        first=(self.output/"section_8_4_e2e.json")
        self.assertTrue(first.is_file())
        first_bytes=first.read_bytes()
        seen=[]
        from selenium_pipeline.original_source_e2e_acceptance import inspect_source_e2e
        def inspector(**params):
            seen.append(Path(params["lecture"]).name)
            return inspect_source_e2e(**params)
        state=self.runit(inspector=inspector)
        self.assertEqual(seen,["8.5"])
        self.assertEqual(state["reused_prior_section_receipts_without_rerunning"],1)
        self.assertEqual(state["new_original_sections_inspected"],1)
        self.assertEqual(first.read_bytes(),first_bytes)

    def test_modified_original_pdf_refuses_old_campaign_and_never_redoes_work(self):
        self.runit()
        lecture=Path(self.specs[0]["lecture"])
        (lecture/"source.pdf").write_bytes(b"tampered original academic publisher")
        with self.assertRaisesRegex(CampaignRecoveryBlocked,
                                    "Different original source"):
            self.runit()

    def test_modified_prior_readiness_receipt_fails_closed_on_resume(self):
        self.runit()
        receipt=self.output/"section_8_4_e2e.json"
        receipt.write_bytes(receipt.read_bytes()+b" ")
        with self.assertRaisesRegex(CampaignRecoveryBlocked,
                                    "physical bytes were modified"):
            self.runit()

    def test_changed_model_evidence_requires_new_version_not_repeated_old_queue(self):
        self.runit()
        transcript=Path(self.specs[1]["model_responses"])/"slide_001.json"
        transcript.write_text(transcript.read_text("utf8")+" ",
                              encoding="utf8")
        with self.assertRaisesRegex(CampaignRecoveryBlocked,
                                    "Different original source"):
            self.runit()


if __name__=="__main__":
    unittest.main()
