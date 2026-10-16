"""Offline, non-API browser TTS capability gate tests."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.browser_tts_preflight import (
    evaluate,preflight,BrowserTTSBlocked,SURFACE,
)


class WebTTSPreflightTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        self.out=self.root/"browser_tts_preflight.json"
        self.calls=0

    def snapshot(self,**overrides):
        base={"url":SURFACE,"body":"",
              "control_labels":["No API key selected",
                 "Gemini 3.8 Flash TTS\ngemini-3.8-flash-tts"],
              "editable_count":0}
        base.update(overrides)
        return base

    def probe(self,**overrides):
        value=self.snapshot(**overrides)
        def transport(**kwargs):
            self.calls+=1
            self.assertIn("port",kwargs)
            return value
        return preflight(requested_model="gemini-3.8-flash-lite-tts",
                         requested_voice="Kore",output=self.out,
                         transport=transport)

    def test_actual_observed_ui_blocks_flash_lite_without_api(self):
        result=self.probe()
        self.assertEqual(result["status"],"BROWSER_TTS_GENERATION_UNVERIFIED")
        self.assertFalse(result["exact_model_visible"])
        self.assertFalse(result["speech_editor_available"])
        self.assertTrue(result["no_api_key_selected_visible"])
        self.assertFalse(result["downloadable_wav_verified"])
        self.assertFalse(result["usable_for_automatic_element_tts"])
        self.assertEqual(self.calls,1)
        self.assertEqual(json.loads(self.out.read_text()),result)

    def test_even_visible_model_voice_and_editor_cannot_claim_audio(self):
        data=self.snapshot(
           control_labels=["Gemini 3.8 Flash-Lite TTS gemini-3.8-flash-lite-tts",
                           "Kore voice", "Run"],
           editable_count=1)
        result=evaluate(data,requested_model="gemini-3.8-flash-lite-tts",
                        requested_voice="Kore")
        self.assertTrue(result["exact_model_visible"])
        self.assertTrue(result["voice_visible"])
        self.assertTrue(result["speech_editor_available"])
        self.assertFalse(result["usable_for_automatic_element_tts"])
        self.assertFalse(result["billing_free_generation_verified"])
        self.assertFalse(result["submitted_generation_request"])

    def test_original_flash_not_mistaken_for_flash_lite(self):
        r=evaluate(self.snapshot(),requested_model="gemini-3.8-flash-tts",
                   requested_voice="Kore")
        self.assertTrue(r["exact_model_visible"])
        self.assertFalse(r["usable_for_automatic_element_tts"])

    def test_fails_wrong_domain_before_writing_output(self):
        with self.assertRaises(BrowserTTSBlocked):
            self.probe(url="https://example.invalid/speech")
        self.assertFalse(self.out.exists())

    def test_probe_cannot_write_inside_protected_lecture_tree(self):
        protected=self.root/"teaching"/"8.4"
        protected.mkdir(parents=True)
        output=protected/"no_auto_billing.json"
        with self.assertRaisesRegex(ValueError,"Never create"):
            preflight(requested_model="gemini-3.8-flash-lite-tts",
                      requested_voice="Kore",output=output,
                      source_root=self.root/"teaching",
                      transport=lambda **_:self.snapshot())
        self.assertFalse(output.exists())

    def test_invalid_model_does_not_enable_network_calls(self):
        with self.assertRaisesRegex(ValueError,"Unapproved"):
            evaluate(self.snapshot(),requested_model="whisper-base",
                     requested_voice="Kore")
        self.assertFalse(self.out.exists())

    def test_never_overwrite_existing_capability_receipt(self):
        self.out.write_text("precious")
        with self.assertRaisesRegex(ValueError,"new isolated"):
            self.probe()
        self.assertEqual(self.calls,0)
        self.assertEqual(self.out.read_text(),"precious")

    def test_receipt_contains_no_account_email_or_raw_html(self):
        snap=self.snapshot(control_labels=[
            "Google Account: Private Person (private@example.com)",
            "No API key selected",
            "Gemini 3.8 Flash TTS gemini-3.8-flash-tts"
        ])
        result=evaluate(snap,requested_model="gemini-3.8-flash-lite-tts",
                        requested_voice="Kore")
        self.assertNotIn("private@example.com",json.dumps(result))
        self.assertFalse(result["student_publication"])
        self.assertFalse(result["human_academic_approval"])

    def test_unverified_voice_is_not_manufactured(self):
        data=self.snapshot(control_labels=["Gemini 3.8 Flash-Lite TTS",
                                           "No API key selected"])
        result=evaluate(data,requested_model="gemini-3.8-flash-lite-tts",
                        requested_voice="Kore")
        self.assertFalse(result["voice_visible"])

    def test_fake_free_claim_cannot_override_generation_proof(self):
        fake=self.snapshot(control_labels=[
            "Gemini 3.8 Flash-Lite TTS",
            "Kore voice","Free TTS","Run"])
        fake["editable_count"]=1
        fake["billing_free_generation_verified"]=True
        fake["downloadable_wav_verified"]=True
        report=evaluate(fake,requested_model="gemini-3.8-flash-lite-tts",
                        requested_voice="Kore")
        self.assertFalse(report["billing_free_generation_verified"])
        self.assertFalse(report["downloadable_wav_verified"])
        self.assertFalse(report["usable_for_automatic_element_tts"])


if __name__=="__main__":unittest.main()
