"""Offline, fail-closed tests for source-bound observed provider retry evidence."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.tts_attempt_evidence import (
    AttemptEvidence, TTSAttemptEvidenceError, GENESIS,
)
from selenium_pipeline.tts_effective_identity import DEFAULT, LITE, FLASH, CHIRP
from selenium_pipeline.tts import synthesize_folder


class ObservedAttemptJournalTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        (self.folder / "script.txt").write_text(
            "**Slide 1 [3 sec]:\nPhysics narration.", encoding="utf-8")
        self.items = [(1, "Physics narration.")]
        self.ledger = AttemptEvidence(self.folder, self.items)

    def failed(self, model=LITE, count=3):
        for round_number in range(1, count + 1):
            self.ledger.record(
                provider="gemini", model=model, slide=1,
                round_number=round_number,
                outcome="transient_failure", error_type="RuntimeError")

    def test_no_cloud_without_both_gemini_models(self):
        self.failed(LITE)
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"No verified"):
            self.ledger.verify_before("chirp3",CHIRP)

    def test_two_failures_are_insufficient(self):
        self.failed(LITE,2)
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"No verified"):
            self.ledger.verify_before("gemini",FLASH)

    def test_three_actual_observed_retryable_results_allow_flash(self):
        self.failed(LITE)
        verified=self.ledger.verify_before("gemini",FLASH)
        self.assertEqual(verified["lite"]["failed_slides"],[1])
        self.assertEqual(verified["lite"]["observed_attempts_by_slide"],{"1":3})
        self.assertEqual(len(self.ledger.read()),3)

    def test_lite_then_flash_retryable_outcomes_allow_cloud(self):
        self.failed(LITE)
        self.failed(FLASH)
        verified=self.ledger.verify_before("chirp3",CHIRP)
        self.assertEqual(verified["lite"]["failed_slides"],[1])
        self.assertEqual(verified["flash"]["failed_slides"],[1])
        self.assertEqual(verified["flash"]["observed_attempts_by_slide"],{"1":3})
        self.assertNotEqual(self.ledger.tip(),GENESIS)

    def test_permanent_error_never_enables_cloud(self):
        self.failed(LITE)
        for n in range(1,4):
            self.ledger.record(
                provider="gemini",model=FLASH,slide=1,round_number=n,
                outcome="permanent_failure",error_type="PermissionError")
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"No verified"):
            self.ledger.verify_before("chirp3",CHIRP)

    def test_success_never_counts_as_exhaustion(self):
        self.failed(LITE,2)
        self.ledger.record(provider="gemini",model=LITE,slide=1,round_number=3,
                           outcome="success")
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"No verified"):
            self.ledger.verify_before("gemini",FLASH)

    def test_altered_event_hash_is_rejected(self):
        self.failed(LITE)
        event=self.ledger.path/"000002.json"
        payload=json.loads(event.read_text())
        payload["outcome"]="success"
        event.write_text(json.dumps(payload))
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"hash/identity"):
            self.ledger.verify_before("gemini",FLASH)

    def test_missing_middle_event_is_rejected(self):
        self.failed(LITE)
        (self.ledger.path/"000002.json").unlink()
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"Gap"):
            self.ledger.verify_before("gemini",FLASH)

    def test_source_script_changed_cannot_reuse_ledger(self):
        self.failed(LITE)
        (self.folder/"script.txt").write_text("different original text",encoding="utf-8")
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"source/model changed"):
            AttemptEvidence(self.folder,self.items)

    def test_hash_chained_records_have_all_dispatch_outcomes(self):
        self.failed(LITE)
        records=self.ledger.read()
        self.assertEqual(records[0]["previous_sha256"],GENESIS)
        self.assertEqual(records[1]["previous_sha256"],records[0]["sha256"])
        self.assertEqual(records[2]["previous_sha256"],records[1]["sha256"])
        self.assertTrue(all(r["outcome"]=="transient_failure" for r in records))

    def test_prior_model_attempts_cannot_be_reordered(self):
        self.failed(LITE)
        self.failed(FLASH)
        self.ledger.record(provider="gemini",model=LITE,slide=1,round_number=4,
                           outcome="transient_failure",error_type="RuntimeError")
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"before Lite retries"):
            self.ledger.verify_before("chirp3",CHIRP)

    def test_actual_tts_queue_observes_three_calls_at_boundary(self):
        """Synthetic provider exceptions are logged AFTER call outcomes."""
        fake = types.ModuleType("gemini_keys")
        fake.get_gemini_api_keys = lambda: ["offline-fake-key"]
        fake.create_gemini_client = lambda: object()
        fake.call_with_client_failover = (
            lambda client_factory, callback, **kwargs: callback(client_factory()))
        with patch.dict(sys.modules, {"gemini_keys":fake}), \
             patch.dict(os.environ, {
                "MICROGEN_TTS_QUEUE_ROUNDS":"1",
                "MICROGEN_TTS_QUEUE_DELAY_SECONDS":"0",
                "MICROGEN_TTS_ENABLE_PROVIDER_FALLBACK":"1",
                "MICROGEN_TTS_ENABLE_BATCH_FALLBACK":"1"}), \
             patch("selenium_pipeline.tts._gemini_say",
                   side_effect=RuntimeError("503 synthetic provider failure")) as say, \
             patch("selenium_pipeline.tts._whole_batch_fallback") as fallback:
            synthesize_folder(self.folder,"gemini",LITE,"Kore")
            self.assertEqual(say.call_count,3)
            fallback.assert_called_once()
            self.assertIsInstance(
                fallback.call_args.kwargs["attempt_evidence"], AttemptEvidence)
        after = AttemptEvidence(self.folder,self.items)
        observed=after.read()
        self.assertEqual(len(observed),3)
        self.assertEqual([e["round"] for e in observed],[1,2,3])
        self.assertEqual([e["outcome"] for e in observed],
                         ["transient_failure"]*3)
        self.assertEqual(after.verify_before("gemini",FLASH)["lite"]["failed_slides"],[1])
        self.assertFalse((self.folder/"slide1.wav").exists())

    def test_full_mocked_lite_flash_cloud_transition_records_real_path(self):
        """Zero-network Lite failure x3, Flash failure x3, then one Cloud WAV."""
        import io
        import wave
        fake=types.ModuleType("gemini_keys")
        fake.get_gemini_api_keys=lambda:["offline-fake-key"]
        fake.create_gemini_client=lambda:object()
        fake.call_with_client_failover=(
            lambda client_factory, callback, **kwargs: callback(client_factory()))
        out=io.BytesIO()
        with wave.open(out,"wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(24000)
            stream.writeframes(b"\\x00\\x01"*24000)
        audio=out.getvalue()
        with patch.dict(sys.modules,{"gemini_keys":fake}), \
             patch.dict(os.environ,{
                "MICROGEN_TTS_QUEUE_ROUNDS":"1",
                "MICROGEN_TTS_QUEUE_DELAY_SECONDS":"0",
                "MICROGEN_TTS_ENABLE_PROVIDER_FALLBACK":"1",
                "MICROGEN_TTS_ENABLE_BATCH_FALLBACK":"1"}), \
             patch("selenium_pipeline.tts._gemini_say",
                   side_effect=RuntimeError("503 synthetic provider outage")) as gemini, \
             patch("selenium_pipeline.tts._chirp_say_with_watchdog",
                   return_value=audio) as chirp:
            synthesize_folder(self.folder,"gemini",LITE,"Kore")
            self.assertEqual(gemini.call_count,6)
            chirp.assert_called_once()
        manifest=json.loads((self.folder/"tts_input_manifest.json").read_text())
        self.assertEqual(manifest["primary"]["provider"],"chirp3")
        self.assertEqual(manifest["primary"]["model"],CHIRP)
        self.assertEqual(manifest["primary"]["voice"],"en-US-Chirp3-HD-Corey")
        self.assertEqual(manifest["fallback_chain"],[LITE,FLASH])
        self.assertEqual((self.folder/"slide1.wav").read_bytes(),audio)
        proof=manifest["attempt_evidence"]
        self.assertEqual(proof["effective_model"],CHIRP)
        ledger=AttemptEvidence(self.folder,self.items)
        observed=ledger.read()
        self.assertEqual(len(observed),7)
        self.assertEqual([e["outcome"] for e in observed],
                         ["transient_failure"]*6+["success"])
        self.assertEqual(ledger.tip(),proof["sha256"])
        self.assertEqual(
            AttemptEvidence.verify_saved(self.folder,self.items,proof)["flash"]["failed_slides"],
            [1])

    def test_conditional_cloud_qa_rejects_manifest_only_claim_before_credentials(self):
        from selenium_pipeline.tts_qa_repair import main
        manifest={
            "primary":{"provider":"chirp3","model":"chirp3-hd",
                       "voice":"en-US-Chirp3-HD-Corey"},
            "all_slides_one_effective_voice":True,
            "fallback_chain":[LITE,FLASH],
            "requested_primary":DEFAULT,
            "slides":[],
        }
        (self.folder/"tts_input_manifest.json").write_text(
            json.dumps(manifest),encoding="utf-8")
        args=["--folder",str(self.folder),"--model","gemini-3.8-flash",
              "--threshold","99","--provider","chirp3",
              "--tts-model","chirp3-hd",
              "--voice","en-US-Chirp3-HD-Corey",
              "--conditional-cloud-fallback"]
        with patch("selenium_pipeline.tts_qa_repair.load_microvid_env") as loader, \
             patch("selenium_pipeline.tts_qa_repair.repair") as repair:
            with self.assertRaisesRegex(TTSAttemptEvidenceError,
                                        "Missing or unbound"):
                main(args)
            loader.assert_not_called()
            repair.assert_not_called()

    def test_extra_partial_event_refuses_escalation(self):
        self.failed(LITE)
        (self.ledger.path/"000004.json.partial").write_text("broken",encoding="utf-8")
        with self.assertRaisesRegex(TTSAttemptEvidenceError,"unrecognized"):
            self.ledger.verify_before("gemini",FLASH)


if __name__=="__main__":
    unittest.main()
