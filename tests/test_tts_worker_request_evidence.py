"""No-network worker TTS request-ID handoff regressions."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from selenium_pipeline import tts, tts_worker
from selenium_pipeline.tts_attempt_evidence import (
    safe_provider_request_id, AttemptEvidence,
)
from selenium_pipeline.tts_worker_evidence import (
    TTSWorkerEvidenceError, write_observation, read_observation,
)


def wav_bytes():
    buf=io.BytesIO()
    with wave.open(buf,"wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(24000)
        out.writeframes(b"\x11\x22"*24000)
    return buf.getvalue()


class WorkerRequestEvidenceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.audio=self.root/"tts.wav"
        self.meta=self.root/"tts_observed.json"

    def test_success_sidecar_carries_provider_request_id_not_transcript(self):
        write_observation(self.audio,self.meta,outcome="success",
                          provider_request_id="real_google_req_abcdef01")
        self.assertEqual(read_observation(self.meta,outcome="success"),
                         "real_google_req_abcdef01")
        self.assertNotIn("secret",self.meta.read_text())

    def test_unavailable_request_id_stays_none(self):
        write_observation(self.audio,self.meta,outcome="success")
        self.assertIsNone(read_observation(self.meta,outcome="success"))

    def test_worker_error_sidecar_captures_id_only_from_exception(self):
        err=RuntimeError("HTTP 503 with secret in text")
        err.request_id="provider_http_request_0123"
        write_observation(self.audio,self.meta,outcome="exception",exception=err)
        self.assertEqual(read_observation(self.meta,outcome="exception"),
                         "provider_http_request_0123")
        content=self.meta.read_text()
        self.assertNotIn("secret",content)
        self.assertNotIn("HTTP 503",content)

    def test_response_id_is_not_mislabelled_as_provider_request_id(self):
        err=RuntimeError("503")
        err.response_id="interactions/response_is_not_http_request"
        self.assertIsNone(safe_provider_request_id(err))
        err.__cause__=RuntimeError("503")
        err.__cause__.request_id="real_transport_request_1"
        self.assertEqual(safe_provider_request_id(err),"real_transport_request_1")

    def test_invalid_id_is_rejected(self):
        with self.assertRaises(TTSWorkerEvidenceError):
            write_observation(self.audio,self.meta,outcome="success",
                              provider_request_id="Bearer secret token")

    def test_symlink_or_existing_output_rejected(self):
        self.meta.write_text("previous")
        with self.assertRaises(TTSWorkerEvidenceError):
            write_observation(self.audio,self.meta,outcome="success")
        self.assertEqual(self.meta.read_text(),"previous")

    def test_sidecar_wrong_outcome_or_invalid_json_rejected(self):
        write_observation(self.audio,self.meta,outcome="success")
        with self.assertRaisesRegex(TTSWorkerEvidenceError,"status mismatch"):
            read_observation(self.meta,outcome="exception")
        self.meta.write_text("{broken")
        with self.assertRaisesRegex(TTSWorkerEvidenceError,"Malformed"):
            read_observation(self.meta,outcome="success")

    def test_worker_mocked_success_writes_audio_plus_safe_sidecar(self):
        args=["--output",str(self.audio),"--evidence-output",str(self.meta),
              "--provider","gemini","--model","gemini-3.8-flash-lite-tts",
              "--voice","Kore","--number","1","--confirm-gemini-api-cost"]
        def fake_tts(text,n,model,voice,*,request_observation=None):
            self.assertEqual(text,"synthetic narration")
            request_observation["provider_request_id"]="http_req_safe_01234567"
            return wav_bytes()
        with patch.object(sys,"stdin",io.StringIO("synthetic narration")), \
             patch("selenium_pipeline.tts_worker._gemini_failover_request",
                   side_effect=fake_tts):
            self.assertEqual(tts_worker.main(args),0)
        self.assertEqual(self.audio.read_bytes(),wav_bytes())
        self.assertEqual(read_observation(self.meta,outcome="success"),
                         "http_req_safe_01234567")

    def test_worker_mocked_failure_no_audio_and_sanitized_sidecar(self):
        args=["--output",str(self.audio),"--evidence-output",str(self.meta),
              "--provider","gemini","--model","gemini-3.8-flash-lite-tts",
              "--voice","Kore","--number","1","--confirm-gemini-api-cost"]
        error=RuntimeError("503 fake-secret never disclose")
        error.request_id="http_failed_request_00001"
        with patch.object(sys,"stdin",io.StringIO("synthetic narration")), \
             patch("selenium_pipeline.tts_worker._gemini_failover_request",
                   side_effect=error):
            with self.assertRaisesRegex(RuntimeError,"fake-secret"):
                tts_worker.main(args)
        self.assertFalse(self.audio.exists())
        self.assertEqual(read_observation(self.meta,outcome="exception"),
                         "http_failed_request_00001")
        self.assertNotIn("fake-secret",self.meta.read_text())

    def test_gemini_sdk_model_success_captures_true_request_id(self):
        response=SimpleNamespace(
            request_id="sdk_http_request_abcdef01",
            response_id="generated_response_not_request",
            candidates=[SimpleNamespace(content=SimpleNamespace(
                parts=[SimpleNamespace(inline_data=SimpleNamespace(
                    data=wav_bytes()))]))])
        client=SimpleNamespace(models=SimpleNamespace(
            generate_content=lambda **kwargs: response))
        observed={}
        payload=tts._gemini_say(
            client,"lecture narration","gemini-3.8-flash-lite-tts","Kore",
            request_observation=observed)
        self.assertEqual(payload,wav_bytes())
        self.assertEqual(observed["provider_request_id"],
                         "sdk_http_request_abcdef01")

    def test_gemini_sdk_generated_response_id_is_not_http_id(self):
        import base64
        # Genuine Gemini3.8 now uses Interactions; output_audio is base64 WAV,
        # and its response_id must not be relabeled an HTTP request_id.
        response=SimpleNamespace(
            response_id="interactions_generated_1234567890",
            output_audio=SimpleNamespace(
                data=base64.b64encode(wav_bytes()).decode("ascii"),
                mime_type="audio/wav"))
        client=SimpleNamespace(interactions=SimpleNamespace(
            create=lambda **kwargs: response))
        observed={}
        self.assertEqual(tts._gemini_say(
            client,"lecture narration","gemini-3.8-flash-lite-tts","Kore",
            request_observation=observed),wav_bytes())
        self.assertIsNone(observed["provider_request_id"])

    def test_parent_watchdog_mocked_subprocess_collects_provider_id(self):
        payload=wav_bytes()
        def subprocess_success(cmd,**kwargs):
            output=Path(cmd[cmd.index("--output")+1])
            observed=Path(cmd[cmd.index("--evidence-output")+1])
            output.write_bytes(payload)
            write_observation(output,observed,outcome="success",
                              provider_request_id="provider_real_http_02000")
            return SimpleNamespace(returncode=0,stdout="",stderr="")
        with patch("selenium_pipeline.tts.subprocess.run",
                   side_effect=subprocess_success), \
             patch("selenium_pipeline.tts._tts_child_request_env",
                   return_value={}):
            result=tts._gemini_say_with_watchdog(
                "test narration",1,"gemini-3.8-flash-lite-tts","Kore",
                attempts_override=1)
        self.assertEqual(result,payload)
        self.assertEqual(tts._LAST_PROVIDER_REQUEST_ID.get(),
                         "provider_real_http_02000")

    def test_source_bound_attempt_journal_receives_actual_worker_id(self):
        folder=self.root/"subchapter_8_4"
        folder.mkdir()
        (folder/"script.txt").write_text(
            "**Slide 1 [3 sec]:\nUniversity physics lecture.",
            encoding="utf-8")
        keys=types.ModuleType("gemini_keys")
        keys.get_gemini_api_keys=lambda:["OFFLINE_TEST_ONLY"]
        def create_gemini_client():
            return object()
        create_gemini_client.__module__="gemini_keys"
        keys.create_gemini_client=create_gemini_client
        keys.call_with_client_failover=lambda *args,**kwargs: None
        def response(cmd,**kwargs):
            output=Path(cmd[cmd.index("--output")+1])
            meta=Path(cmd[cmd.index("--evidence-output")+1])
            output.write_bytes(wav_bytes())
            write_observation(output,meta,outcome="success",
                              provider_request_id="real_provider_http_20261017")
            return SimpleNamespace(returncode=0,stdout="",stderr="")
        with patch.dict(sys.modules,{"gemini_keys":keys}), \
             patch.dict(os.environ,{"MICROGEN_TTS_QUEUE_DELAY_SECONDS":"0"}), \
             patch("selenium_pipeline.tts.subprocess.run",
                   side_effect=response) as send, \
             patch("selenium_pipeline.tts._tts_child_request_env",
                   return_value={}):
            tts.synthesize_folder(
                folder,"gemini","gemini-3.8-flash-lite-tts","Kore")
        self.assertEqual(send.call_count,1)
        recorded=AttemptEvidence(folder,[(1,"University physics lecture.")]).read()
        self.assertEqual(len(recorded),1)
        self.assertEqual(recorded[0]["outcome"],"success")
        self.assertEqual(recorded[0]["provider_request_id"],
                         "real_provider_http_20261017")
        self.assertTrue((folder/"slide1.wav").is_file())

    def test_parent_worker_failure_propagates_provider_id(self):
        def subprocess_error(cmd,**kwargs):
            output=Path(cmd[cmd.index("--output")+1])
            observed=Path(cmd[cmd.index("--evidence-output")+1])
            error=RuntimeError("503 synthetic error")
            error.request_id="failure_req_10000001"
            write_observation(output,observed,outcome="exception",exception=error)
            return SimpleNamespace(returncode=1,stdout="",stderr="503 synthetic error")
        with patch("selenium_pipeline.tts.subprocess.run",
                   side_effect=subprocess_error), \
             patch("selenium_pipeline.tts._tts_child_request_env",
                   return_value={}):
            with self.assertRaises(RuntimeError) as caught:
                tts._gemini_say_with_watchdog(
                    "test narration",1,"gemini-3.8-flash-lite-tts","Kore",
                    attempts_override=1)
        self.assertEqual(safe_provider_request_id(caught.exception),
                         "failure_req_10000001")


if __name__=="__main__":
    unittest.main()
