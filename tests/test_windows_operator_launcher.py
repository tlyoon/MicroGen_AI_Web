"""Offline tests for native Windows operator without model/TTS/media side effects."""
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.windows_operator import diagnose, operate


class WindowsOperatorLauncherTests(unittest.TestCase):
    def test_doctor_stays_read_only_and_independent_of_provider(self):
        with patch("selenium_pipeline.original_windows_release.inspect_campaign",
                   side_effect=AssertionError("scientific reinspection forbidden")):
            report = diagnose(platform_name="win32", python_version=(3, 12))
        self.assertTrue(report["project_layout_present"])
        self.assertEqual(report["status"], "OPERATOR_AVAILABLE_FOR_READ_ONLY_INSPECTION")
        self.assertFalse(report["generation_readiness_certified"])
        self.assertFalse(report["new_model_or_tts_calls"])
        self.assertFalse(report["student_publication_authorized"])

    def test_rejects_wrong_platform_and_unsupported_python(self):
        self.assertEqual(diagnose(platform_name="linux")["status"],
                         "OPERATOR_PREREQUISITES_INCOMPLETE")
        self.assertEqual(diagnose(platform_name="win32", python_version=(3, 10))["status"],
                         "OPERATOR_PREREQUISITES_INCOMPLETE")

    def test_doctor_is_not_a_render_mode(self):
        code, report = operate(doctor=True, campaign=Path("not_a_campaign"))
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "INVALID_MIXED_DOCTOR_AND_CAMPAIGN_OPTIONS")

    def test_render_requires_exact_section(self):
        code, report = operate(campaign=Path("never_open"),
                               execute_prepared=True)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "EXPLICIT_SECTION_REQUIRED_FOR_RENDER")

    def test_inspect_reuses_existing_verifier_without_models(self):
        with patch("selenium_pipeline.windows_operator.sys.platform", "win32"), patch(
            "selenium_pipeline.original_windows_release.inspect_campaign",
            return_value={"sections": [{"status": "BLOCKED_ORIGINAL_MAPPING"}],
                          "new_model_or_tts_calls": False}
        ) as inspect:
            code, report = operate(campaign=Path("campaign"))
        self.assertEqual(code, 0)  # Read-only inspection of BLOCKED is not a release.
        self.assertEqual(report["sections"][0]["status"], "BLOCKED_ORIGINAL_MAPPING")
        inspect.assert_called_once()
        self.assertFalse(inspect.call_args.kwargs["execute_prepared"])

    def test_render_block_never_claims_success(self):
        with patch("selenium_pipeline.windows_operator.sys.platform", "win32"), patch(
            "selenium_pipeline.original_windows_release.inspect_campaign",
            return_value={"sections": [{"execution_status": "BLOCKED_BY_SOURCE_OR_MEDIA_GATE"}]}
        ):
            code, _ = operate(campaign=Path("campaign"),
                              section="8.4", execute_prepared=True)
        self.assertEqual(code, 2)

    def test_tampered_campaign_is_rejected(self):
        from selenium_pipeline.original_multisource_recovery_campaign import CampaignRecoveryBlocked
        with patch("selenium_pipeline.windows_operator.sys.platform", "win32"), patch(
            "selenium_pipeline.original_windows_release.inspect_campaign",
            side_effect=CampaignRecoveryBlocked("source digest changed")
        ):
            code, result = operate(campaign=Path("campaign"))
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "CAMPAIGN_REJECTED")
        self.assertFalse(result["student_publication_authorized"])


if __name__ == "__main__":
    unittest.main()
