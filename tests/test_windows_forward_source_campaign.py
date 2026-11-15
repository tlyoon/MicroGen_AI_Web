"""Cross-source autonomous forward progress without repeating a blocked PDF.

All synthetic source data is new, local, separate from publisher material.
No Gemini Send, TTS, media encoder, or network access in these tests.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked,_new_atomic,
)
from selenium_pipeline.windows_forward_source_campaign import (
    run_forward_campaign,
)


class IndependentForwardSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)/"LOCALAPPDATA"
        self.home.mkdir()
        self.publisher=Path(self.tmp.name)/"publisher"
        self.publisher.mkdir()
        self.registry=self.home/"scoped_trial_registry"
        self.registry.mkdir()
        scope=patch.dict(os.environ,{"LOCALAPPDATA":str(self.home)})
        scope.start()
        self.addCleanup(scope.stop)
        self.pdfs={}
        for section in ("77.9","78.1","79.4"):
            folder=self.publisher/section.split(".")[0]/section
            folder.mkdir(parents=True)
            pdf=folder/"source.pdf"
            pdf.write_bytes(b"%PDF-1.7\n"+("New synthetic source "+section).encode()*35)
            self.pdfs[section]=pdf
        self.calls=[]
        self.statuses={}
        self.inspect_calls=[]
        self.success="FRESH_SOURCE_SEVEN_STAGE_DRY_RUN_READY"

    def fake_runner(self,*,source_root,section,trial_dir,attempt_figures):
        self.assertFalse(attempt_figures)
        self.assertEqual(source_root,self.publisher)
        self.assertTrue(trial_dir.is_relative_to(self.registry))
        self.calls.append(section)
        sha=file_sha256(self.pdfs[section])
        return {
            "status":self.statuses.get(section,self.success),
            "original_source_sha256":sha,
            "staged_original_sha256":sha,
            "new_model_or_tts_calls":False,
            "student_publication_authorized":False,
            "new_video_rendered":False,
        }

    def inspect(self,*,source_root,section,trial_dir):
        self.inspect_calls.append(section)
        return {
            "status":"HALTED_UNVERIFIED_GEMINI_BROWSER_ROUTE_NO_SEND",
            "new_model_or_tts_calls":False,
            "student_publication_authorized":False,
        }

    def forward(self,**kwargs):
        return run_forward_campaign(
            publisher_root=self.publisher,registry_root=self.registry,
            campaign_name="fresh_independent_sources",
            max_sources=3,dryrun_runner=self.fake_runner,
            stage_inspector=self.inspect,**kwargs)

    def test_all_new_sources_progress_in_order_and_resume_without_rerun(self):
        result=self.forward()
        self.assertEqual(self.calls,["77.9","78.1","79.4"])
        self.assertEqual(result["new_independent_source_dry_runs"],3)
        self.assertEqual(result["new_provider_sends"],0)
        self.assertFalse(result["verified_pdf_to_mp4_complete"])
        self.assertEqual(result["rejected_source_sections"],0)
        self.assertTrue(all(
            x["current_next_stage_status"]==
                "HALTED_UNVERIFIED_GEMINI_BROWSER_ROUTE_NO_SEND"
            for x in result["section_results"]))
        again=self.forward()
        self.assertEqual(again["new_independent_source_dry_runs"],0)
        self.assertEqual(again["reused_source_dry_runs"],3)
        self.assertEqual(self.calls,["77.9","78.1","79.4"])
        self.assertEqual(len(self.inspect_calls),6)

    def test_one_failed_dryrun_does_not_block_next_distinct_source(self):
        self.statuses["78.1"]="FRESH_SOURCE_DRY_RUN_TIMEOUT"
        result=self.forward()
        self.assertEqual(result["new_independent_source_dry_runs"],3)
        self.assertEqual(result["section_results"][1]["dry_run_status"],
                         "FRESH_SOURCE_DRY_RUN_TIMEOUT")
        self.assertEqual(result["section_results"][1]["current_next_stage_status"],
                         "SOURCE_DRY_RUN_INCOMPLETE_NO_LIVE_STAGE")
        self.assertEqual(self.calls[-1],"79.4")
        again=self.forward()
        self.assertEqual(again["reused_source_dry_runs"],3)
        self.assertEqual(self.calls,["77.9","78.1","79.4"])

    def test_crash_after_first_durable_receipt_resumes_unfinished_sources(self):
        def crash(section):
            raise RuntimeError("Synthetic interrupted after "+section)
        with self.assertRaisesRegex(RuntimeError,"interrupted"):
            self.forward(after_record=crash)
        self.assertEqual(self.calls,["77.9"])
        resumed=self.forward()
        self.assertEqual(resumed["reused_source_dry_runs"],1)
        self.assertEqual(resumed["new_independent_source_dry_runs"],2)
        self.assertEqual(self.calls,["77.9","78.1","79.4"])

    def test_tampered_one_source_receipt_is_isolated_not_overwritten(self):
        self.forward()
        campaign=self.registry/"fresh_independent_sources"
        receipt=next(campaign.glob("source_77_9_*.dryrun.json"))
        receipt.write_text(receipt.read_text("utf8")+" ")
        original=receipt.read_bytes()
        again=self.forward()
        self.assertEqual(again["rejected_source_sections"],1)
        self.assertEqual(again["reused_source_dry_runs"],2)
        self.assertEqual(again["section_results"][0]["job_state"],
                         "SOURCE_SECURITY_OR_INTEGRITY_REJECTED_NO_SEND")
        self.assertEqual(original,receipt.read_bytes())
        self.assertEqual(self.calls,["77.9","78.1","79.4"])

    def test_source_mutation_blocks_only_that_source(self):
        self.forward()
        pdf=self.pdfs["78.1"]
        pdf.write_bytes(pdf.read_bytes()+b" changed after claim")
        again=self.forward()
        self.assertEqual(again["rejected_source_sections"],1)
        self.assertEqual(again["reused_source_dry_runs"],2)
        self.assertEqual(again["section_results"][2]["source_sha256"],
                         file_sha256(self.pdfs["79.4"]))
        self.assertEqual(self.calls,["77.9","78.1","79.4"])

    def test_older_source_immutable_claim_is_excluded_during_selection(self):
        old=self.registry/"historical_provider_attempt"
        old.mkdir()
        _new_atomic(old/"figures_attempt_started.json",{
            "schema_version":1,"stage":"figures",
            "source_sha256":file_sha256(self.pdfs["78.1"]),
            "single_provider_attempt_only":True})
        result=self.forward()
        self.assertEqual(result["selected_distinct_original_sources"],2)
        self.assertEqual(self.calls,["77.9","79.4"])
        self.assertEqual(result["new_provider_sends"],0)

    def test_all_sources_preclaimed_creates_no_new_generation(self):
        for section,pdf in self.pdfs.items():
            old=self.registry/("historical_"+section.replace(".","_"))
            old.mkdir()
            _new_atomic(old/"figures_attempt_started.json",{
                "schema_version":1,"stage":"figures",
                "source_sha256":file_sha256(pdf),
                "single_provider_attempt_only":True})
        result=self.forward()
        self.assertEqual(result["status"],
                         "NO_NEW_SOURCES_IN_SCOPED_INVENTORY")
        self.assertEqual(result["new_independent_source_dry_runs"],0)
        self.assertEqual(self.calls,[])

    def test_corrupt_campaign_contract_rejects_without_rerun(self):
        self.forward()
        root=self.registry/"fresh_independent_sources"
        contract=root/"forward_source_campaign_contract.json"
        contract.write_text(contract.read_text("utf8")+" ")
        with self.assertRaises(CampaignRecoveryBlocked):
            self.forward()
        self.assertEqual(self.calls,["77.9","78.1","79.4"])

    def test_runner_claiming_paid_calls_is_rejected_and_next_still_runs(self):
        def unsafe(**kwargs):
            record=self.fake_runner(**kwargs)
            if kwargs["section"]=="77.9":
                record["new_model_or_tts_calls"]=True
            return record
        result=run_forward_campaign(
            publisher_root=self.publisher,registry_root=self.registry,
            campaign_name="unsafe_stage",
            dryrun_runner=unsafe,stage_inspector=self.inspect)
        self.assertEqual(result["rejected_source_sections"],1)
        self.assertEqual(result["new_independent_source_dry_runs"],2)
        self.assertFalse(any(
            x["job_state"]=="NEW_BOUNDED_SOURCE_DRY_RUN_RECORDED"
            for x in result["section_results"][:1]))

    def test_randomized_restart_stress_preserves_one_run_per_source(self):
        # Repeated restarts with a deterministic campaign never regenerate.
        for _ in range(30):
            self.forward()
        self.assertEqual(self.calls,["77.9","78.1","79.4"])
        self.assertEqual(len(list(
            (self.registry/"fresh_independent_sources").glob(
                "source_*.dryrun.json"))),3)

    def test_two_concurrent_invocations_cannot_reprocess_same_source(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        entered=Event()
        release=Event()
        def slow_runner(**kwargs):
            if kwargs["section"]=="77.9":
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("Synthetic test timed out")
            return self.fake_runner(**kwargs)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(run_forward_campaign,
                publisher_root=self.publisher,registry_root=self.registry,
                campaign_name="concurrent_source_campaign",max_sources=3,
                dryrun_runner=slow_runner,stage_inspector=self.inspect)
            self.assertTrue(entered.wait(3))
            try:
                with self.assertRaisesRegex(
                    CampaignRecoveryBlocked,"Another forward campaign"):
                    run_forward_campaign(
                        publisher_root=self.publisher,registry_root=self.registry,
                        campaign_name="concurrent_source_campaign",max_sources=3,
                        dryrun_runner=self.fake_runner,stage_inspector=self.inspect)
            finally:
                release.set()
            self.assertEqual(first.result(timeout=8)[
                             "new_independent_source_dry_runs"],3)
        self.assertEqual(self.calls,["77.9","78.1","79.4"])
        again=run_forward_campaign(
            publisher_root=self.publisher,registry_root=self.registry,
            campaign_name="concurrent_source_campaign",max_sources=3,
            dryrun_runner=slow_runner,stage_inspector=self.inspect)
        self.assertEqual(again["reused_source_dry_runs"],3)
        self.assertEqual(self.calls,["77.9","78.1","79.4"])

    def test_fake_dryrun_that_creates_send_intent_cannot_be_accepted(self):
        def accidental_send(**kwargs):
            response=self.fake_runner(**kwargs)
            if kwargs["section"]=="78.1":
                _new_atomic(kwargs["trial_dir"]/"figures_attempt_started.json",{
                    "schema_version":1,"stage":"figures",
                    "source_sha256":file_sha256(self.pdfs["78.1"]),
                    "single_provider_attempt_only":True,
                })
            return response
        result=run_forward_campaign(
            publisher_root=self.publisher,registry_root=self.registry,
            campaign_name="provider_intent_negative_fixture",
            dryrun_runner=accidental_send,stage_inspector=self.inspect)
        self.assertEqual(result["rejected_source_sections"],1)
        self.assertEqual(result["new_independent_source_dry_runs"],2)
        self.assertFalse(any((
            self.registry/"provider_intent_negative_fixture").glob(
                "source_78_1_*.dryrun.json")))
        self.assertEqual(result["new_provider_sends"],0)

    def test_forged_source_path_and_invalid_name_blocked(self):
        with self.assertRaises(CampaignRecoveryBlocked):
            run_forward_campaign(
                publisher_root=self.publisher,registry_root=self.registry,
                campaign_name="../unsafe",max_sources=3)
        self.assertEqual(list(self.registry.iterdir()),[])
        with self.assertRaises(CampaignRecoveryBlocked):
            run_forward_campaign(
                publisher_root=self.publisher,registry_root=self.registry,
                campaign_name="safe",max_sources=13)

    def test_safety_of_existing_publisher_data_is_byte_exact(self):
        before={p:p.read_bytes() for p in self.pdfs.values()}
        self.forward()
        self.forward()
        self.assertEqual(before,{p:p.read_bytes() for p in self.pdfs.values()})
        self.assertFalse(any(self.publisher.rglob("*.dryrun.json")))


if __name__=="__main__":
    unittest.main()
