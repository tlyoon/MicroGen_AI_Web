"""Permanent source-free provider-route recovery checks for fresh PDF stages."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from selenium_pipeline.windows_new_source_browser_admission import (
    select_latest_claimed_browser_canary,
    evaluate_new_source_browser_admission, inspect_new_source_browser_admission,
)
from selenium_pipeline.windows_gemini_differential_probe import (
    _profile_spec, CONTENT_MODEL,
)
from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.original_multisource_recovery_campaign import _encode


def _browser():
    return {"provider":"gemini","status":"AUTHENTICATED_COMPOSER_READY",
            "authenticated_ui_ready":True,
            "model_submission_performed":False}


def _health():
    return {"new_generation_dispatch_allowed_by_health_policy":True}


class NewSourceRouteAdmissionTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.history=self.root/"MicroGen_AI_Web_Checkpoints"
        self.history.mkdir()

    def write_canary(self,name,*,profile="source_sized_g1_selenium_only_v3",
                     outcome="VALID_CANARY_RESPONSE",registered=None,
                     mtime=1000,source_transmitted=False):
        home=self.history/name
        home.mkdir()
        prompt,_,digest=_profile_spec(profile)
        claim={
            "schema_version":1,"backend":"browser",
            "content_model":CONTENT_MODEL,
            "generic_prompt_sha256":digest,
            "probe_profile":profile,
            "one_submission_only":True,
            "explicit_api_content_cost":False,
            "no_original_source_attached":True,
            "student_publication_authorized":False,
        }
        start=home/"browser_probe_started.json"
        start.write_text(_encode(claim),encoding="utf8")
        proof={
            "schema_version":1,"backend":"browser",
            "status":"GENERIC_CANARY_TERMINAL","probe_profile":profile,
            "outcome":outcome,"generic_prompt_sha256":digest,
            "claim_sha256":file_sha256(start),
            "prompt_characters":len(prompt),
            "response_character_count":40 if outcome=="VALID_CANARY_RESPONSE" else 0,
            "new_model_generation_calls":1,
            "source_pdf_transmitted":source_transmitted,
            "existing_original_source_retry_permitted":False,
            "gemini_new_user_turn_verified":registered,
            "student_publication_authorized":False,
        }
        target=home/"browser_probe_result.json"
        target.write_text(_encode(proof),encoding="utf8")
        os.utime(target,(mtime,mtime))
        return target

    def test_latest_valid_but_no_registered_turn_does_not_enable_new_pdf_send(self):
        self.write_canary("last",registered=None,mtime=2000)
        latest=select_latest_claimed_browser_canary(checkpoint_root=self.history)
        self.assertEqual("LATEST_IMMUTABLE_CANARY_IDENTIFIED",latest["status"])
        result=evaluate_new_source_browser_admission(
            latest=latest,browser=_browser(),health=_health())
        self.assertFalse(result["new_source_stage_send_eligible"])
        self.assertFalse(result["owned_new_user_turn_verified"])
        self.assertFalse(result["new_model_or_tts_calls"])

    def test_newer_failed_canary_overrides_older_registered_positive(self):
        self.write_canary("older_good",registered=True,mtime=1000)
        self.write_canary("newer_bad",outcome="NO_VERIFIED_RESPONSE",
                          registered=False,mtime=2000)
        latest=select_latest_claimed_browser_canary(checkpoint_root=self.history)
        self.assertEqual("NO_VERIFIED_RESPONSE",latest["canary"]["outcome"])
        self.assertFalse(evaluate_new_source_browser_admission(
            latest=latest,browser=_browser(),health=_health()
        )["new_source_stage_send_eligible"])

    def test_independently_registered_source_sized_positive_allows_one_stage(self):
        self.write_canary("registered",registered=True,mtime=2000)
        latest=select_latest_claimed_browser_canary(checkpoint_root=self.history)
        self.assertTrue(evaluate_new_source_browser_admission(
            latest=latest,browser=_browser(),health=_health()
        )["new_source_stage_send_eligible"])
        self.assertFalse(evaluate_new_source_browser_admission(
            latest=latest,browser={**_browser(),"authenticated_ui_ready":False},
            health=_health()
        )["new_source_stage_send_eligible"])
        self.assertFalse(evaluate_new_source_browser_admission(
            latest=latest,browser=_browser(),
            health={"new_generation_dispatch_allowed_by_health_policy":False}
        )["new_source_stage_send_eligible"])

    def test_verifiable_21k_owned_capacity_profile_is_accepted(self):
        from selenium_pipeline.gemini_g1_single_route_cli import (
            RICH_LONG_CAPACITY_PROFILE)
        path=self.write_canary(
            "large_owned",profile=RICH_LONG_CAPACITY_PROFILE,
            registered=True,mtime=2000)
        latest=select_latest_claimed_browser_canary(
            checkpoint_root=self.history)
        self.assertTrue(evaluate_new_source_browser_admission(
            latest=latest,browser=_browser(),health=_health()
        )["new_source_stage_send_eligible"])
        self.assertEqual(latest["canary_path"],str(path))
        self.assertGreater(latest["canary"]["prompt_characters"],18000)

    def test_short_positive_is_not_source_sized_qualification(self):
        self.write_canary("short",profile="short_g1_registered_turn_v4",
                          registered=True,mtime=2000)
        latest=select_latest_claimed_browser_canary(checkpoint_root=self.history)
        self.assertFalse(evaluate_new_source_browser_admission(
            latest=latest,browser=_browser(),health=_health()
        )["new_source_stage_send_eligible"])

    def test_corrupt_newer_immutable_claim_fails_closed(self):
        self.write_canary("good",registered=True,mtime=1000)
        bad=self.write_canary("newest",registered=True,mtime=2000)
        row=json.loads(bad.read_text(encoding="utf8"))
        row["claim_sha256"]="0"*64
        bad.write_text(json.dumps(row),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"(claim/result SHA|Immutable original checkpoint)"):
            select_latest_claimed_browser_canary(checkpoint_root=self.history)

    @unittest.skipUnless(os.name=="nt","Native Windows source trial")
    def test_real_stage_wiring_blocks_unsafe_route_before_send_intent(self):
        from selenium_pipeline.windows_fresh_source_trial import run_trial
        from selenium_pipeline.windows_lecture_progression_coordinator import (
            inspect_progress)
        publisher=self.root/"publisher"
        directory=publisher/"22"/"22.1"
        directory.mkdir(parents=True)
        (directory/"source.pdf").write_bytes(b"%PDF-1.7\n"+b"synthetic"*80)
        trial=self.root/"trial"
        trial.mkdir()
        fake=Mock(return_value=subprocess.CompletedProcess([],0,"",""))
        run_trial(source_root=publisher,section="22.1",trial_dir=trial,
                  subprocess_run=fake)
        unverified=lambda:{"status":"SOURCE_FREE_CANARY_UNVERIFIED",
                           "new_source_stage_send_eligible":False}
        state=inspect_progress(
            source_root=publisher,section="22.1",trial_dir=trial,
            provider_inspect=lambda **kwargs:_health(),
            browser_route_inspect=unverified)
        self.assertEqual("HALTED_UNVERIFIED_GEMINI_BROWSER_ROUTE_NO_SEND",
                         state["status"])
        result=run_trial(
            source_root=publisher,section="22.1",trial_dir=trial,
            attempt_figures=True,subprocess_run=fake,
            browser_route_inspect=unverified)
        self.assertEqual("GEMINI_SOURCE_ROUTE_UNVERIFIED_NO_SUBMISSION",
                         result["status"])
        self.assertFalse((trial/"figures_attempt_started.json").exists())
        fake.assert_called_once() # the earlier dry-run only

    @unittest.skipUnless(os.name=="nt","Native Windows source trial")
    def test_eligible_once_only_and_no_resend(self):
        from selenium_pipeline.windows_fresh_source_trial import run_trial
        publisher=self.root/"publisher"
        directory=publisher/"22"/"22.1"
        directory.mkdir(parents=True)
        (directory/"source.pdf").write_bytes(b"%PDF-1.7\n"+b"synthetic"*80)
        trial=self.root/"trial"
        trial.mkdir()
        fake=Mock(return_value=subprocess.CompletedProcess([],1,"",""))
        eligible=lambda:{"status":"NEW_SOURCE_GEMINI_ROUTE_VERIFIED_FOR_ONE_STAGE",
                         "new_source_stage_send_eligible":True}
        outcome=run_trial(source_root=publisher,section="22.1",trial_dir=trial,
                  subprocess_run=fake,attempt_figures=True,
                  browser_route_inspect=eligible)
        self.assertEqual("FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY",
                         outcome["status"])
        repeat=run_trial(source_root=publisher,section="22.1",trial_dir=trial,
                  subprocess_run=fake,attempt_figures=True,
                  browser_route_inspect=eligible)
        self.assertEqual("PREVIOUS_PROVIDER_ATTEMPT_NOT_RESENT",repeat["status"])
        self.assertEqual(1,fake.call_count)


if __name__=="__main__":
    unittest.main()
