"""Windows Gemini/ChatGPT route preflight never submits or retries content."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from selenium_pipeline.windows_provider_route_evidence_preflight import (
    recommend_routes, inspect,
)


class WindowsProviderRoutePreflightTests(unittest.TestCase):
    def setUp(self):
        self.gemini = {
            "provider": "gemini", "status": "AUTHENTICATED_COMPOSER_READY",
            "authenticated_ui_ready": True, "model_submission_performed": False,
        }
        self.chatgpt = {
            "provider": "chatgpt", "status": "LOGIN_REQUIRED",
            "authenticated_ui_ready": False, "model_submission_performed": False,
        }
        self.api = {
            "status": "PROVIDER_READINESS_NOT_A_LESSON_GENERATION",
            "api_model_metadata": "VETTED_MODEL_METADATA_REACHABLE",
            "api_key_count_nonsecret": 2,
            "paid_api_content_generation_performed": False,
            "new_model_generation_calls": 0,
        }
        self.browser_halt = {
            "new_generation_dispatch_allowed_by_health_policy": True,
        }
        self.api_halt = {
            "new_generation_dispatch_allowed_by_health_policy": True,
        }
        self.canary = {
            "backend": "browser", "outcome": "NO_VERIFIED_RESPONSE",
            "student_publication_authorized": False,
        }
        self.ui_error = {
            "known_gemini_ui_error_text_observed": True,
            "quarantine_payload_sha256_verified": True,
            "new_model_or_tts_calls": False,
            "original_source_retry_authorized": False,
        }

    def recommend(self, **kwargs):
        params = dict(
            gemini_browser=self.gemini, chatgpt_browser=self.chatgpt,
            api_preflight=self.api, browser_canary=self.canary,
            owned_ui_error=self.ui_error, browser_halt=self.browser_halt,
            api_halt=self.api_halt)
        params.update(kwargs)
        return recommend_routes(**params)

    def test_real_dell_pattern_blocks_browser_and_requires_new_paid_api_consent(self):
        r = self.recommend()
        self.assertEqual(
            r["suggested_new_unsent_job_route"],
            "GEMINI_API_METADATA_REACHABLE_COST_APPROVAL_REQUIRED")
        self.assertTrue(r["prior_source_free_browser_canary_unverified"])
        self.assertTrue(r["owned_gemini_ui_error_sha_verified"])
        self.assertTrue(r["gemini_browser_auto_selection_suppressed_by_prior_evidence"])
        self.assertTrue(r["api_distinct_new_source_candidate_with_separate_cost_authorization"])
        self.assertFalse(r["gemini_api_content_generation_proven_healthy"])
        self.assertFalse(r["automatic_browser_to_api_fallback_authorized"])
        self.assertFalse(r["old_uncertain_lecture_retry_authorized"])
        self.assertFalse(r["paid_api_generation_authorized"])
        self.assertFalse(r["new_model_or_tts_calls"])
        self.assertFalse(r["student_publication_authorized"])

    def test_authenticated_chatgpt_can_be_selected_only_for_distinct_new_job(self):
        alt = dict(self.chatgpt, status="AUTHENTICATED_COMPOSER_READY",
                   authenticated_ui_ready=True)
        r = self.recommend(chatgpt_browser=alt)
        self.assertEqual(
            r["suggested_new_unsent_job_route"],
            "CHATGPT_BROWSER_AVAILABLE_FOR_A_DISTINCT_NEW_JOB_ONLY")
        self.assertFalse(r["automatic_browser_to_api_fallback_authorized"])
        self.assertFalse(r["old_uncertain_lecture_retry_authorized"])

    def test_guest_chatgpt_composer_never_counted_as_authentication(self):
        guest = dict(self.chatgpt, status="LOGIN_REQUIRED",
                     authenticated_ui_ready=True)
        r = self.recommend(chatgpt_browser=guest)
        self.assertFalse(r["chatgpt_browser_authenticated"])
        self.assertNotIn("CHATGPT", r["suggested_new_unsent_job_route"])

    def test_api_metadata_only_no_paid_cost_approval(self):
        no_canary = self.recommend(browser_canary=None, owned_ui_error=None)
        self.assertEqual(
            no_canary["suggested_new_unsent_job_route"],
            "GEMINI_BROWSER_COMPOSER_READY_GENERATION_NOT_CERTIFIED")
        self.assertFalse(no_canary["gemini_browser_generation_proven_healthy"])
        self.assertFalse(no_canary["gemini_api_content_generation_proven_healthy"])
        self.assertFalse(no_canary["paid_api_generation_authorized"])

    def test_missing_key_or_metadata_not_usable_api_generation_proof(self):
        r = self.recommend(
            api_preflight=dict(self.api, api_key_count_nonsecret=0),
            chatgpt_browser=self.chatgpt)
        self.assertEqual(
            r["suggested_new_unsent_job_route"],
            "NO_GENERATION_TRANSPORT_CERTIFIED_FOR_AUTOMATIC_DISPATCH")
        self.assertFalse(
            r["api_distinct_new_source_candidate_with_separate_cost_authorization"])

    def test_browser_halt_stops_new_automatic_gemini_browser(self):
        r = self.recommend(
            browser_canary=None, owned_ui_error=None,
            browser_halt={"new_generation_dispatch_allowed_by_health_policy": False})
        self.assertTrue(r["gemini_browser_auto_selection_suppressed_by_prior_evidence"])
        self.assertEqual(
            r["suggested_new_unsent_job_route"],
            "GEMINI_API_METADATA_REACHABLE_COST_APPROVAL_REQUIRED")

    def test_verified_capacity_halt_stops_api_candidate_too(self):
        r = self.recommend(
            api_halt={"new_generation_dispatch_allowed_by_health_policy": False},
            browser_halt={"new_generation_dispatch_allowed_by_health_policy": False})
        self.assertEqual(
            r["suggested_new_unsent_job_route"],
            "NO_GENERATION_TRANSPORT_CERTIFIED_FOR_AUTOMATIC_DISPATCH")
        self.assertFalse(
            r["api_distinct_new_source_candidate_with_separate_cost_authorization"])

    def test_forged_ui_error_without_sha_is_not_accepted_as_verified(self):
        forged = dict(self.ui_error, quarantine_payload_sha256_verified=False)
        r = self.recommend(browser_canary=None, owned_ui_error=forged)
        self.assertFalse(r["owned_gemini_ui_error_sha_verified"])
        self.assertFalse(r["gemini_browser_auto_selection_suppressed_by_prior_evidence"])

    def test_second_key_metadata_can_qualify_new_route_when_first_key_fails(self):
        broken_first = dict(self.api, api_model_metadata="API_METADATA_LOOKUP_FAILED")
        verified_pool = {
            "status": "KEY_POOL_METADATA_CHECKED_AT_LEAST_ONE_REACHABLE",
            "metadata_eligible_new_source_key_ordinals": [2],
            "model_generate_content_calls": 0,
            "paid_api_content_generation_authorized": False,
        }
        r = self.recommend(
            api_preflight=broken_first,
            api_key_pool=verified_pool)
        self.assertEqual(
            r["suggested_new_unsent_job_route"],
            "GEMINI_API_METADATA_REACHABLE_COST_APPROVAL_REQUIRED")
        self.assertEqual(r["api_key_pool_metadata_verified_candidate_ordinals"], [2])
        self.assertFalse(r["gemini_api_content_generation_proven_healthy"])
        self.assertFalse(r["automatic_browser_to_api_fallback_authorized"])

    def test_fake_pool_with_prior_content_charge_never_qualifies_key(self):
        r = self.recommend(
            api_preflight=dict(self.api, api_model_metadata="API_METADATA_LOOKUP_FAILED"),
            api_key_pool={
                "status": "KEY_POOL_METADATA_CHECKED_AT_LEAST_ONE_REACHABLE",
                "metadata_eligible_new_source_key_ordinals": [2],
                "model_generate_content_calls": 1,
                "paid_api_content_generation_authorized": True,
            })
        self.assertEqual(r["api_key_pool_metadata_verified_candidate_ordinals"], [])
        self.assertEqual(
            r["suggested_new_unsent_job_route"],
            "NO_GENERATION_TRANSPORT_CERTIFIED_FOR_AUTOMATIC_DISPATCH")

    def test_verified_short_browser_canary_is_positive_but_not_long_form(self):
        prior = {
            "schema_version": 1, "backend": "browser",
            "outcome": "VALID_CANARY_RESPONSE",
            "status": "GENERIC_CANARY_TERMINAL",
            "response_character_count": 33,
            "new_model_generation_calls": 1,
            "paid_api_content_may_have_occurred": False,
            "source_pdf_transmitted": False,
            "student_publication_authorized": False,
        }
        result = self.recommend(browser_canary=prior, owned_ui_error=None)
        self.assertTrue(result["prior_short_browser_generation_success_recorded"])
        self.assertTrue(result["prior_short_success_never_certifies_current_long_form"])
        self.assertEqual(
            result["suggested_new_unsent_job_route"],
            "GEMINI_BROWSER_PRIOR_SHORT_CANARY_OK_LONG_FORM_UNTESTED")
        self.assertFalse(result["gemini_browser_generation_proven_healthy"])
        self.assertFalse(result["automatic_new_model_generation_authorized"])
        self.assertFalse(result["old_uncertain_lecture_retry_authorized"])
        self.assertFalse(result["paid_api_generation_authorized"])
        self.assertFalse(result["student_publication_authorized"])

        # Historical UI-error evidence remains a safe override. The prior
        # canary cannot erase a newer source-bound error or permit resends.
        blocked = self.recommend(browser_canary=prior)
        self.assertTrue(blocked["prior_short_browser_generation_success_recorded"])
        self.assertTrue(blocked["gemini_browser_auto_selection_suppressed_by_prior_evidence"])
        self.assertNotEqual(
            blocked["suggested_new_unsent_job_route"],
            "GEMINI_BROWSER_PRIOR_SHORT_CANARY_OK_LONG_FORM_UNTESTED")

        untrusted = dict(prior, source_pdf_transmitted=True)
        self.assertFalse(self.recommend(
            browser_canary=untrusted, owned_ui_error=None
        )["prior_short_browser_generation_success_recorded"])

    def test_source_sized_synthetic_canary_is_not_misreported_as_short_or_lecture(self):
        evidence = {
            "schema_version": 1, "backend": "browser",
            "outcome": "VALID_CANARY_RESPONSE",
            "status": "GENERIC_CANARY_TERMINAL",
            "probe_profile": "source_sized",
            "prompt_characters": 1535,
            "response_character_count": 39,
            "new_model_generation_calls": 1,
            "paid_api_content_may_have_occurred": False,
            "source_pdf_transmitted": False,
            "student_publication_authorized": False,
        }
        result = self.recommend(browser_canary=evidence, owned_ui_error=None)
        self.assertEqual(result["suggested_new_unsent_job_route"],
                         "GEMINI_BROWSER_PRIOR_SOURCE_SIZED_INPUT_OK_FULL_LESSON_UNTESTED")
        self.assertTrue(result["prior_source_sized_text_input_success_recorded"])
        self.assertFalse(result["prior_short_browser_generation_success_recorded"])
        self.assertTrue(result["prior_source_sized_input_never_certifies_full_lecture"])
        self.assertFalse(result["gemini_browser_generation_proven_healthy"])
        self.assertFalse(result["automatic_new_model_generation_authorized"])
        self.assertFalse(result["student_publication_authorized"])
        for changed in (
            {**evidence, "prompt_characters": 3001},
            {**evidence, "outcome": "NO_VERIFIED_RESPONSE"},
            {**evidence, "source_pdf_transmitted": True},
        ):
            self.assertFalse(self.recommend(
                browser_canary=changed, owned_ui_error=None
            )["prior_source_sized_text_input_success_recorded"])
        # An independently verified prior source-bound terminal UI error
        # always takes precedence over a positive source-free canary.
        blocked = self.recommend(browser_canary=evidence)
        self.assertTrue(blocked["gemini_browser_auto_selection_suppressed_by_prior_evidence"])
        self.assertNotEqual(
            blocked["suggested_new_unsent_job_route"],
            "GEMINI_BROWSER_PRIOR_SOURCE_SIZED_INPUT_OK_FULL_LESSON_UNTESTED")

    def test_preflight_invokes_no_model_transport_or_source_operations(self):
        with patch(
            "selenium_pipeline.rich_mapping_provider_readiness.inspect_provider",
            side_effect=lambda provider: self.gemini if provider == "gemini"
            else self.chatgpt,
        ) as browsers, patch(
            "selenium_pipeline.windows_provider_readiness_probe.inspect",
            return_value=self.api,
        ) as api, patch(
            "selenium_pipeline.windows_gemini_provider_halt.inspect_halt",
            side_effect=lambda backend: self.browser_halt
            if backend == "selenium" else self.api_halt,
        ) as halts:
            report = inspect(
                inspect_browsers=True, check_api_metadata=True)
        self.assertEqual(browsers.call_count, 2)
        api.assert_called_once_with(metadata_probe=True)
        self.assertEqual(halts.call_count, 2)
        self.assertFalse(report["new_model_or_tts_calls"])
        self.assertFalse(report["student_publication_authorized"])
        self.assertFalse(report["old_uncertain_lecture_retry_authorized"])


if __name__ == "__main__":
    unittest.main()
