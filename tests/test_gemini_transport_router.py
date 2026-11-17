"""One-Send Gemini route selection: verified Selenium-only, no paid API."""
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.gemini_transport_router import (
    GeminiTransportNotAuthorized,verified_browser_route,gemini_api_status,
    execute_gemini_api,
)
from selenium_pipeline.ai_academic_web_review import _academic_browser_request


def proof(port=9222):
    return {
        "status":"EXACT_OWNED_GEMINI_MODEL_AND_THINKING_READY_NO_SEND",
        "verified_port":port,"model_family":"pro","thinking_level":"medium",
        "alternate_account_used":port==9225,"existing_profile_only":True,
        "gemini_requests_submitted":0,"files_uploaded":0,
        "model_prompt_typed":False,"academic_approval":False,
        "student_publication_authorized":False}


class GeminiRouteTests(unittest.TestCase):
    def run_route(self,evidence,**kw):
        return verified_browser_route(
            family="pro",claimed_send_state="NEW_CLAIM_BEFORE_SEND",
            evidence_provider=lambda **_:evidence,**kw)

    def test_primary_model_and_medium_selects_existing_selenium(self):
        result=self.run_route(proof())
        self.assertEqual(result.port,9222)
        self.assertEqual(result.transport,"selenium_owned")
        self.assertEqual(result.thinking_level,"medium")
        self.assertFalse(result.alternate_account_used)
        self.assertEqual(result.new_model_requests,0)
        self.assertFalse(result.paid_api_authorized)

    def test_authorized_existing_alternate_requires_same_exact_pro_medium(self):
        alternate=self.run_route(proof(9225))
        self.assertEqual(alternate.port,9225)
        self.assertTrue(alternate.alternate_account_used)
        for change in (
            {"thinking_level":None},{"model_family":"flash-lite"},
            {"existing_profile_only":False},
            {"gemini_requests_submitted":1},
            {"files_uploaded":2},{"student_publication_authorized":True},
            {"verified_port":9227},{"alternate_account_used":False},
            {"model_prompt_typed":True},
        ):
            with self.subTest(change=change):
                with self.assertRaises(GeminiTransportNotAuthorized):
                    self.run_route({**proof(9225),**change})

    def test_never_replay_consumed_or_switch_to_unauthorized_paid_api(self):
        for state in ("SUBMITTED_OR_UNCERTAIN","NO_RESPONSE_UNRESOLVED",
                      "REJECTED_RESPONSE_UNTRUSTED","CERTIFIED_PRESEND_UNSENT"):
            with self.subTest(state=state):
                with self.assertRaises(GeminiTransportNotAuthorized):
                    verified_browser_route(
                        family="pro",claimed_send_state=state,
                        evidence_provider=lambda **kw:self.fail(
                            "A consumed state must not inspect or Send"))
        with patch.dict(os.environ,{"MICROGEN_GEMINI_API_ENABLED":"1",
                                    "GEMINI_API_KEY":"DUMMY_NOT_REAL"}):
            with self.assertRaises(GeminiTransportNotAuthorized):
                verified_browser_route(
                    family="pro",claimed_send_state="NEW_CLAIM_BEFORE_SEND",
                    backend="api")
            with self.assertRaises(GeminiTransportNotAuthorized):
                execute_gemini_api()
        self.assertFalse(gemini_api_status()["paid_api_authorized"])

    def test_registry_disable_and_absent_exact_session_fail_before_send(self):
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with self.assertRaises(GeminiTransportNotAuthorized):
                self.run_route(proof())
        with self.assertRaises(GeminiTransportNotAuthorized):
            verified_browser_route(
                family="pro",claimed_send_state="NEW_CLAIM_BEFORE_SEND",
                evidence_provider=lambda **_: (_ for _ in ()).throw(
                    RuntimeError("No authenticated Gemini")))

    def test_normal_academic_pro_worker_uses_preverified_alternate_once(self):
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"pro",
                                     "MICROGEN_LLM_MODEL":"gemini-3.1-pro"}):
            def received(prompt,files,**kw):
                self.assertEqual(kw["port"],9225)
                self.assertEqual(os.environ["MICROGEN_ACTIVE_GENERATION_STAGE"],
                                 "academic_review")
                return "owned response"
            with patch(
                "selenium_pipeline.gemini_transport_router."
                "verified_browser_route",return_value=self.run_route(proof(9225))
            ) as routed,patch(
                "selenium_pipeline.ai_academic_web_review._browser_request",
                side_effect=received
            ) as sent:
                output=_academic_browser_request("question",[
                    Path("source.pdf"),Path("slides.pdf")],
                    chrome_port=9222,wait_cap_s=120)
            self.assertEqual(output,"owned response")
            routed.assert_called_once()
            sent.assert_called_once()

    def test_route_failure_is_typed_before_send_and_preserves_immutable_claim(self):
        from selenium_pipeline.gemini_selenium_only_policy import (
            GeminiSeleniumPreSendBlocked)
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"pro"}),patch(
            "selenium_pipeline.gemini_transport_router."
            "verified_browser_route",
            side_effect=GeminiTransportNotAuthorized("No route")
        ),patch("selenium_pipeline.ai_academic_web_review._browser_request",
                side_effect=AssertionError("Never send")):
            with self.assertRaises(GeminiSeleniumPreSendBlocked) as got:
                _academic_browser_request("question",[],chrome_port=9222,
                                          wait_cap_s=120)
        self.assertFalse(got.exception.gemini_send_boundary_entered)
        self.assertEqual(got.exception.gemini_failure_phase,
                         "GEMINI_BROWSER_OR_WEBDRIVER_NOT_READY")
