"""Generation route probe never submits model content or leaks credentials."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from selenium_pipeline.windows_provider_readiness_probe import inspect, CONTENT_MODEL


class WindowsProviderReadinessTests(unittest.TestCase):
    @patch("selenium_pipeline.windows_provider_readiness_probe.sys.platform", "win32")
    def test_offline_probe_never_uses_model_transport(self):
        def forbidden(key, model):
            raise AssertionError("Metadata transport must not be called")
        result = inspect(available_key_count=1,
                         metadata_transport=forbidden)
        self.assertEqual(result["api_model_metadata"], "NOT_CHECKED_NO_NETWORK")
        self.assertEqual(result["new_model_generation_calls"], 0)
        self.assertFalse(result["source_pdf_transmitted"])

    @patch("selenium_pipeline.windows_provider_readiness_probe.sys.platform", "win32")
    def test_explicit_metadata_uses_only_model_name_and_no_prompt(self):
        calls = []
        def metadata(key, model):
            calls.append(model)
            return SimpleNamespace(name="models/" + model)
        result = inspect(metadata_probe=True, available_key_count=2,
                         metadata_transport=metadata)
        self.assertEqual(calls, [CONTENT_MODEL])
        self.assertEqual(result["api_model_metadata"],
                         "VETTED_MODEL_METADATA_REACHABLE")
        self.assertFalse(result["paid_api_content_generation_performed"])
        self.assertFalse(result["student_publication_authorized"])
        self.assertFalse(result["existing_ambiguous_model_submission_retry_permitted"])

    @patch("selenium_pipeline.windows_provider_readiness_probe.sys.platform", "win32")
    def test_failed_metadata_cannot_leak_key_text(self):
        def bad(key, model):
            raise PermissionError("API_KEY_SECRET_SHOULD_NOT_LEAK")
        result = inspect(metadata_probe=True, available_key_count=1,
                         metadata_transport=bad)
        self.assertEqual(result["api_model_metadata"], "API_METADATA_LOOKUP_FAILED")
        self.assertEqual(result["api_model_metadata_error_type"], "PermissionError")
        self.assertNotIn("SECRET", str(result))

    @patch("selenium_pipeline.windows_provider_readiness_probe.sys.platform", "win32")
    def test_readonly_chrome_probe_does_not_trigger_api(self):
        result = inspect(available_key_count=1, inspect_gemini_browser=True,
                         browser_check=lambda name: {
                             "status": "AUTHENTICATED_COMPOSER_READY",
                             "authenticated_ui_ready": True,
                             "model_submission_performed": False})
        self.assertEqual(result["browser_ui_readiness"],
                         "AUTHENTICATED_COMPOSER_READY")
        self.assertEqual(result["new_model_generation_calls"], 0)

    @patch("selenium_pipeline.windows_provider_readiness_probe.sys.platform", "win32")
    def test_unknown_model_never_requested(self):
        result = inspect(metadata_probe=True,
                         model="gemini-unsafe-unverified-model",
                         available_key_count=1)
        self.assertEqual(result["status"], "VETTED_MODEL_ONLY")


if __name__ == "__main__":
    unittest.main()
