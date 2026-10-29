"""Offline, non-API browser TTS capability gate tests."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.browser_tts_preflight import (
    evaluate,preflight,BrowserTTSBlocked,SURFACE,local_configuration_presence,
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

    def test_local_config_exists_despite_ai_studio_no_key_selection(self):
        local=self.root/"AppData"/"Local"
        micro=local/"Microvid"
        micro.mkdir(parents=True)
        for name in (".env","google_cloud_credentials.json",
                     "drive-oauth-client.json"):
            (micro/name).write_text("DO_NOT_READ_THIS_FIXTURE")
        (local/"gemini_automation_TEST").mkdir()
        (local/"Google"/"Chrome"/"User Data").mkdir(parents=True)
        evidence=local_configuration_presence({"LOCALAPPDATA":str(local)})
        self.assertTrue(evidence["local_microvid_config_present"])
        self.assertTrue(evidence["local_persistent_gemini_profile_present"])
        self.assertFalse(evidence["local_credential_contents_read"])
        receipt=preflight(
            requested_model="gemini-3.8-flash-lite-tts",
            requested_voice="Kore",output=self.out,
            transport=lambda **_:self.snapshot(),
            local_environ={"LOCALAPPDATA":str(local)})
        self.assertTrue(receipt["local_microvid_config_present"])
        self.assertTrue(receipt["no_api_key_selected_visible"])
        self.assertFalse(receipt["usable_for_automatic_element_tts"])
        self.assertFalse(receipt["api_called_by_microgen"])
        self.assertNotIn("DO_NOT_READ_THIS_FIXTURE",self.out.read_text())

    def test_no_localappdata_does_not_search_repository_for_credentials(self):
        result=local_configuration_presence({})
        self.assertFalse(result["local_microvid_config_present"])
        self.assertFalse(result["local_credential_contents_read"])
        self.assertTrue(result["local_credentials_not_browser_key_selection"])

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

    def test_missing_selenium_has_a_persisted_fail_closed_receipt(self):
        def broken(**_):
            raise BrowserTTSBlocked("selenium_python_dependency_unavailable")
        report=preflight(requested_model="gemini-3.8-flash-lite-tts",
                         requested_voice="Kore",output=self.out,transport=broken)
        self.assertEqual(report["status"],"BROWSER_TTS_PREFLIGHT_UNAVAILABLE")
        self.assertEqual(report["blockers"],["selenium_python_dependency_unavailable"])
        self.assertEqual(report["visible_model_ids"],[])
        self.assertFalse(report["no_api_key_selected_visible"])
        self.assertFalse(report["usable_for_automatic_element_tts"])
        self.assertEqual(json.loads(self.out.read_text()),report)

    def test_unavailable_browser_does_not_leak_exception_text(self):
        def broken(**_):
            raise BrowserTTSBlocked("untrusted personal details secret@example.com")
        report=preflight(requested_model="gemini-3.8-flash-lite-tts",
                         requested_voice="Kore",output=self.out,transport=broken)
        self.assertEqual(report["blockers"],["browser_ui_unavailable"])
        self.assertNotIn("secret@example.com",json.dumps(report))

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


    def test_invalid_intent_never_connects_to_browser(self):
        def forbidden(**_):
            self.fail("Invalid model/voice must be rejected before browser work")
        for model,voice in (("unapproved-tts","Kore"),
                            ("gemini-3.8-flash-lite-tts","bad voice")):
            with self.subTest(model=model,voice=voice):
                with self.assertRaises(ValueError):
                    preflight(requested_model=model,requested_voice=voice,
                              output=self.out,transport=forbidden)
        self.assertFalse(self.out.exists())

    def test_exact_https_origin_and_path_required(self):
        for url in (
                "https://aistudio.google.com.evil.example/generate-speech",
                "https://aistudio.google.com/generate-speech.evil",
                "http://aistudio.google.com/generate-speech",
                "https://example.org/aistudio.google.com/generate-speech",
                "https://aistudio.google.com@evil.example/generate-speech",
                "https://aistudio.google.com:444/generate-speech"):
            with self.subTest(url=url):
                with self.assertRaises(BrowserTTSBlocked):
                    evaluate(self.snapshot(url=url),
                             requested_model="gemini-3.8-flash-lite-tts",
                             requested_voice="Kore")

    def test_model_card_and_voice_label_do_not_verify_selection(self):
        result=evaluate(self.snapshot(control_labels=[
             "gemini-3.8-flash-lite-tts", "Kore",
             "No API key selected"],editable_count=1),
             requested_model="gemini-3.8-flash-lite-tts",
             requested_voice="Kore")
        self.assertTrue(result["exact_model_visible"])
        self.assertTrue(result["voice_visible"])
        self.assertFalse(result["selected_model_verified"])
        self.assertFalse(result["selected_voice_verified"])
        self.assertIn("selected_model_not_verified",result["blockers"])
        self.assertFalse(result["usable_for_automatic_element_tts"])

    def test_unavailable_browser_marks_selection_unknown(self):
        result=preflight(requested_model="gemini-3.8-flash-lite-tts",
                         requested_voice="Kore",output=self.out,
                         transport=lambda **_: (_ for _ in ()).throw(
                             BrowserTTSBlocked("browser_ui_unavailable")))
        self.assertFalse(result["selected_model_verified"])
        self.assertFalse(result["selected_voice_verified"])

    def test_receipt_path_symlink_is_rejected_before_open(self):
        target=self.root/"outside_receipt.json"
        try:
            self.out.symlink_to(target)
        except (OSError,NotImplementedError):
            self.skipTest("Symlink creation unavailable on this computer")
        with self.assertRaisesRegex(ValueError,"new isolated"):
            self.probe()
        self.assertFalse(target.exists())


    def test_official_documentation_deeplink_still_never_attests_model(self):
        data=self.snapshot(
            url=SURFACE,
            control_labels=["gemini-3.8-flash-lite-tts","Kore"],
            editable_count=1,
            official_model_link_requested=True,
            official_link_query_retained=True)
        result=evaluate(data,requested_model="gemini-3.8-flash-lite-tts",
                        requested_voice="Kore")
        self.assertTrue(result["official_model_link_requested"])
        self.assertTrue(result["official_link_query_retained"])
        self.assertFalse(result["official_link_is_selection_proof"])
        self.assertFalse(result["selected_model_verified"])
        self.assertFalse(result["selected_voice_verified"])
        self.assertFalse(result["usable_for_automatic_element_tts"])

    def test_official_model_route_is_sanitized_and_safe_to_probe(self):
        seen=[]
        def fake_transport(**kwargs):
            seen.append(kwargs["entrypoint"])
            return self.snapshot(official_model_link_requested=True,
                                 official_link_query_retained=False)
        report=preflight(requested_model="gemini-3.8-flash-lite-tts",
                         requested_voice="Kore",output=self.out,
                         entrypoint="official_model_link",
                         transport=fake_transport)
        self.assertEqual(seen,["official_model_link"])
        self.assertTrue(report["official_model_link_requested"])
        self.assertFalse(report["official_link_query_retained"])
        self.assertFalse(report["selected_model_verified"])
        self.assertFalse(report["submitted_generation_request"])
        self.assertFalse(report["api_called_by_microgen"])
        self.assertEqual(json.loads(self.out.read_text()),report)

    def test_official_link_rejects_non_flash_lite_without_browser(self):
        def forbidden(**_):
            self.fail("Invalid deep-link model must not attach Chrome")
        with self.assertRaisesRegex(ValueError,"exact Flash-Lite"):
            preflight(requested_model="gemini-3.8-flash-tts",
                      requested_voice="Kore",output=self.out,
                      entrypoint="official_model_link",
                      transport=forbidden)
        self.assertFalse(self.out.exists())

    def test_unapproved_entrypoint_rejected_before_browser(self):
        with self.assertRaisesRegex(ValueError,"entrypoint"):
            preflight(requested_model="gemini-3.8-flash-lite-tts",
                      requested_voice="Kore",output=self.out,
                      entrypoint="https://evil.example",
                      transport=lambda **_:self.snapshot())
        self.assertFalse(self.out.exists())

    def test_url_model_parameter_is_not_browser_selection(self):
        r=evaluate(self.snapshot(
            url=SURFACE+"?model=gemini-3.8-flash-lite-tts",
            control_labels=["No API key selected"]),
            requested_model="gemini-3.8-flash-lite-tts",
            requested_voice="Kore")
        self.assertFalse(r["exact_model_visible"])
        self.assertFalse(r["selected_model_verified"])
        self.assertFalse(r["usable_for_automatic_element_tts"])

if __name__=="__main__":unittest.main()
