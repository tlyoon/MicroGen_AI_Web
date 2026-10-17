"""No-network acceptance for one-shot Gemini 3.8 Flash-Lite/Kore TTS API trial."""
from __future__ import annotations
import base64
import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from selenium_pipeline.tts_interactions_trial import (
    MODEL, VOICE, SENTENCE, interactions_request, run_trial,
    sdk_preflight, verify_wav,
)


def wav_bytes(*, rate=24000, channels=1, width=2, silent=False):
    bio=io.BytesIO()
    with wave.open(bio, "wb") as wav:
        wav.setframerate(rate)
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.writeframes((b"\x00\x00" if silent else b"\x22\x11") * rate * channels)
    return bio.getvalue()


def interaction(audio):
    return SimpleNamespace(output_audio=SimpleNamespace(
        mime_type="audio/wav", data=base64.b64encode(audio).decode("ascii")))


class InteractionsTrialTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.dest=self.root/"new_trial"

    def call(self, **kwargs):
        return run_trial(self.dest,sdk_version_override="2.25.0",**kwargs)

    def test_default_is_strictly_offline_even_if_sdk_and_credentials_exist(self):
        def no_client():
            self.fail("Dry-run may not construct a client")
        report=self.call(client_factory=no_client)
        self.assertFalse(report["api_request_started"])
        self.assertFalse(report["live_api_authorized"])
        self.assertFalse(report["real_audio_generated"])
        self.assertEqual(report["status"],"API_INTERACTIONS_PREFLIGHT_ONLY")
        self.assertFalse((self.dest/"synthetic_kore.wav").exists())
        self.assertEqual(json.loads((self.dest/"preflight.json").read_text()),report)
        self.assertFalse(report["student_publication"])

    def test_partial_authorization_flags_fail_before_any_file_or_api(self):
        sets=[{"confirm_live":True},
              {"confirm_gemini_api_cost":True},
              {"confirm_synthetic_trial":True},
              {"confirm_live":True,"confirm_gemini_api_cost":True},
              {"confirm_live":True,"confirm_synthetic_trial":True},
              {"confirm_gemini_api_cost":True,"confirm_synthetic_trial":True}]
        for flags in sets:
            with self.subTest(flags=flags):
                with self.assertRaisesRegex(ValueError,"Three explicit flags"):
                    self.call(client_factory=lambda:self.fail("no client"),**flags)
                self.assertFalse(self.dest.exists())

    def test_request_uses_exact_google_interactions_schema(self):
        request=interactions_request()
        self.assertEqual(request["model"],MODEL)
        self.assertEqual(request["generation_config"],
                         {"speech_config":[{"voice":VOICE}]})
        self.assertEqual(request["input"][0]["content"][0]["text"],SENTENCE)
        self.assertEqual(request["response_format"],{"type":"audio"})
        self.assertNotIn("contents",request)
        self.assertNotIn("response_modalities",request)

    def test_one_mock_request_returns_valid_wav_without_publication(self):
        class FakeClient:
            def __init__(self):
                self.calls=[]
                self.interactions=SimpleNamespace(create=self.send)
                self.closed=0
            def send(self,**kwargs):
                self.calls.append(kwargs)
                return interaction(wav_bytes())
            def close(self):
                self.closed+=1
        c=FakeClient()
        r=self.call(confirm_live=True,confirm_gemini_api_cost=True,
                    confirm_synthetic_trial=True,client_factory=lambda:c)
        self.assertEqual(len(c.calls),1)
        self.assertEqual(c.calls[0],interactions_request())
        self.assertEqual(c.closed,1)
        self.assertTrue(r["real_audio_generated"])
        self.assertFalse(r["speech_content_verified_by_asr"])
        self.assertFalse(r["voice_identity_acoustically_verified"])
        self.assertFalse(r["production_approved"])
        self.assertFalse(r["student_publication"])
        self.assertEqual(r["sample_rate"],24000)
        self.assertEqual(r["channels"],1)
        self.assertEqual(r["duration_seconds"],1.0)
        self.assertEqual(json.loads((self.dest/"trial_receipt.json").read_text()),r)
        self.assertEqual((self.dest/"synthetic_kore.wav").read_bytes(),wav_bytes())
        self.assertTrue((self.dest/"request_intent.json").exists())

    def test_invalid_output_audio_does_not_write_wav_or_retry(self):
        for payload in (b"not wave", wav_bytes(silent=True),
                        wav_bytes(rate=16000), wav_bytes(channels=2)):
            with self.subTest(payload=payload[:12]):
                class Fake:
                    def __init__(self):
                        self.n=0
                        self.interactions=SimpleNamespace(create=self.send)
                    def send(self,**_):
                        self.n+=1
                        return interaction(payload)
                client=Fake()
                with self.assertRaisesRegex(RuntimeError,"no retry"):
                    self.call(confirm_live=True,confirm_gemini_api_cost=True,
                              confirm_synthetic_trial=True,client_factory=lambda:client)
                self.assertEqual(client.n,1)
                self.assertFalse((self.dest/"synthetic_kore.wav").exists())
                self.assertFalse((self.dest/"trial_receipt.json").exists())
                self.assertTrue((self.dest/"request_intent.json").exists())
                failure=json.loads((self.dest/"trial_failed.json").read_text())
                self.assertTrue(failure["api_request_may_have_started"])
                self.assertFalse(failure["retry_permitted_automatically"])
                self.assertNotIn("secret",json.dumps(failure))
                import shutil
                shutil.rmtree(self.dest)

    def test_invalid_b64_mime_and_missing_audio_blocked(self):
        with self.assertRaises(ValueError):
            verify_wav(SimpleNamespace(output_audio=None))
        with self.assertRaises(ValueError):
            verify_wav(SimpleNamespace(output_audio=SimpleNamespace(
                mime_type="audio/l16",data=base64.b64encode(wav_bytes()).decode())))
        with self.assertRaises(ValueError):
            verify_wav(SimpleNamespace(output_audio=SimpleNamespace(
                data="% NOT BASE64 %")))

    def test_old_sdk_fails_before_any_live_request(self):
        with self.assertRaisesRegex(RuntimeError,"2.25.0"):
            run_trial(self.dest, sdk_version_override="2.24.9",
                confirm_live=True,confirm_gemini_api_cost=True,
                confirm_synthetic_trial=True,client_factory=lambda:self.fail("no client"))
        self.assertFalse(self.dest.exists())

    def test_sdk_preflight_version_edge_cases(self):
        self.assertFalse(sdk_preflight("2.24.99")["sdk_supports_documented_interactions"])
        self.assertTrue(sdk_preflight("2.25.0")["sdk_supports_documented_interactions"])
        self.assertTrue(sdk_preflight("2.26.0rc1")["sdk_supports_documented_interactions"])
        self.assertFalse(sdk_preflight("unknown")["sdk_supports_documented_interactions"])

    def test_refuse_existing_folder_and_protected_source_tree(self):
        self.dest.mkdir()
        sentinel=self.dest/"existing.wav"
        sentinel.write_bytes(b"important original")
        with self.assertRaisesRegex(ValueError,"NEW isolated"):
            self.call()
        self.assertEqual(sentinel.read_bytes(),b"important original")
        protected=self.root/"teaching"
        protected.mkdir()
        with self.assertRaisesRegex(ValueError,"protected source"):
            run_trial(protected/"trial",source_root=protected,
                      sdk_version_override="2.25.0")
        self.assertFalse((protected/"trial").exists())

    def test_no_key_or_account_fields_in_preflight(self):
        r=self.call()
        serialized=json.dumps(r)
        for sensitive in ("api_key", "token", "email", "google_cloud_credentials"):
            self.assertNotIn(sensitive,serialized.lower())
        self.assertEqual(r["model"],"gemini-3.8-flash-lite-tts")
        self.assertEqual(r["voice"],"Kore")


if __name__=="__main__":
    unittest.main()
