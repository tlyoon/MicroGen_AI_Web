"""Model-picker family selection is not proof of exact Gemini model version."""
import unittest
from selenium_pipeline.gemini_model import (
    GeminiModelError, browser_model_evidence, _matches_mode,
)


class BrowserEvidenceTests(unittest.TestCase):
    def test_flash_family_verified_exact_identity_remains_unknown(self):
        for label in (
            "Open mode picker, currently Gemini Flash",
            "Open mode picker, currently Gemini 3.8 Flash",
        ):
            with self.subTest(label=label):
                proof=browser_model_evidence(
                    label,requested_mode="flash",
                    requested_model_id="gemini-3.8-flash")
                self.assertTrue(proof["selected_family_verified"])
                self.assertFalse(proof["exact_model_id_verified"])
                self.assertIsNone(proof["observed_provider_model_id"])
                self.assertEqual(proof["requested_model_id"],"gemini-3.8-flash")
                self.assertFalse(proof["student_or_academic_approval"])

    def test_false_flash_substrings_and_unselected_text_rejected(self):
        for label in (
            "Open mode picker, currently Gemini Flash Lite",
            "Open mode picker, currently Gemini Pro Flash",
            "Open mode picker, currently Gemini Flash Pro",
            "Open mode picker, currently Gemini Pro",
            "Available Gemini Flash",
            "Open mode picker, previously Gemini Flash",
            "",
        ):
            with self.subTest(label=label):
                self.assertFalse(_matches_mode(label,"flash"))
                with self.assertRaises(GeminiModelError):
                    browser_model_evidence(label,requested_mode="flash",
                                           requested_model_id="gemini-3.8-flash")

    def test_pro_is_explicit_family_not_flash(self):
        label="Open mode picker, currently Gemini Pro"
        self.assertTrue(_matches_mode(label,"pro"))
        self.assertFalse(_matches_mode(label,"flash"))
        p=browser_model_evidence(label,requested_mode="pro",
                                 requested_model_id="gemini-3.1-pro-preview")
        self.assertFalse(p["exact_model_id_verified"])

    def test_requested_api_name_must_match_ui_family(self):
        for model in ("gemini-3.1-pro-preview","gemini-3.8-flash-lite-tts"):
            with self.subTest(model=model),self.assertRaises(GeminiModelError):
                browser_model_evidence(
                    "Open mode picker, currently Gemini Flash",
                    requested_mode="flash",requested_model_id=model)

    def test_unsupported_selection_or_empty_target_fails(self):
        with self.assertRaises(GeminiModelError):
            browser_model_evidence("Open mode picker, currently Gemini Flash",
                                   requested_mode="unknown",
                                   requested_model_id="gemini-3.8-flash")
        with self.assertRaises(GeminiModelError):
            browser_model_evidence("Open mode picker, currently Gemini Flash",
                                   requested_mode="flash",requested_model_id="")


if __name__=="__main__":
    unittest.main()
