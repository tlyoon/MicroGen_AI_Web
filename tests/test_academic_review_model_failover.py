"""Exact owned Pro+Medium fallback only for an independently verified missing Flash."""
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from selenium_pipeline.academic_gemini_presend_preflight import (
    AcademicGeminiPreSendBlocked,
)
from selenium_pipeline.academic_review_model_failover import (
    run, RECEIPT_NAME, AcademicReviewRouteError,
)


class AcademicSourceModelFailoverTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.plan = self.root / "source_plan.json"
        self.plan.write_text(json.dumps({"source_sha256": "a"*64}), encoding="utf8")
        self.work = self.root / "external_receipts"
        self.work.mkdir()
        self.calls = []

    def _campaign(self, **kw):
        self.calls.append(("campaign", os.getenv("MICROGEN_GEMINI_UI_MODE"),
                           kw["chrome_port"], kw["max_jobs"]))
        return {"status": "BOUNDED_CHANGED_SOURCE_REVIEW_NOT_G2_APPROVED",
                "new_requests_attempted": 1, "G2_approved": False,
                "student_publication_authorized": False}

    def _offered(self, family, port=9222):
        return {"status": "EXACT_OWNED_GEMINI_MODEL_AND_THINKING_READY_NO_SEND",
                "model_family": family, "thinking_level": "medium",
                "verified_port": port, "gemini_requests_submitted": 0}

    def test_real_missing_flash_pro_medium_reuses_existing_campaign_no_bypass(self):
        def choice(*, primary_port):
            family = os.getenv("MICROGEN_GEMINI_UI_MODE") or "flash"
            self.calls.append(("inspect", family, primary_port))
            if family == "flash":
                raise AcademicGeminiPreSendBlocked(
                    "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE")
            return self._offered("pro", port=9222)

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MICROGEN_GEMINI_UI_MODE", None)
            result = run(plan_path=self.plan, root=self.work,
                         max_jobs=1, only_positions={5},
                         campaign=self._campaign, inspect_ready=choice)
            self.assertNotIn("MICROGEN_GEMINI_UI_MODE", os.environ)
        self.assertEqual(self.calls, [
            ("inspect", "flash", 9222),
            ("inspect", "pro", 9222),
            ("campaign", "pro", 9222, 1)])
        self.assertFalse(result["G2_approved"])
        route = json.loads((self.work/RECEIPT_NAME).read_text("utf8"))
        self.assertEqual(route["selected_academic_model_family"], "pro")
        self.assertEqual(route["requested_model_family"], "flash")
        self.assertFalse(route["model_family_equivalence_asserted"])
        self.assertFalse(route["element_tts_authorized"])
        # Crash-safe rerun of the identical existing selection keeps the
        # original receipt; the campaign owns its own no-resend checkpoint.
        with patch.dict(os.environ, {"MICROGEN_GEMINI_UI_MODE":"flash"}):
            same = run(plan_path=self.plan,root=self.work,max_jobs=1,
                       campaign=self._campaign,inspect_ready=choice)
        self.assertEqual(same["academic_model_route"], route)
        # Immutable route is immediately reused on resume; do not repeatedly
        # inspect both known-missing Flash sessions or use another model.
        self.assertEqual(self.calls[-2:], [
            ("inspect", "pro", 9222),
            ("campaign", "pro", 9222, 1)])
        self.assertNotIn("MICROGEN_LLM_MODEL", os.environ)

    def test_auth_or_browser_timeout_never_substitutes_model_or_claims_source(self):
        for reason in ("AUTHENTICATION_OR_BROWSER_VERIFICATION_REQUIRED",
                       "GEMINI_COMPOSER_OR_SEND_CONTROL_NOT_READY"):
            with self.subTest(reason=reason):
                self.calls.clear()
                with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"flash"}):
                    def blocked(*, primary_port):
                        self.calls.append(("inspect", primary_port))
                        raise AcademicGeminiPreSendBlocked(reason)
                    with self.assertRaises(AcademicGeminiPreSendBlocked):
                        run(plan_path=self.plan,root=self.work,
                            campaign=self._campaign,inspect_ready=blocked)
                self.assertEqual(self.calls,[("inspect",9222)])
                self.assertFalse((self.work/RECEIPT_NAME).exists())

    def test_wrong_selected_medium_and_family_never_enter_send_campaign(self):
        for evidence in (self._offered("pro"),
                         {**self._offered("flash"), "thinking_level":"high"},
                         {**self._offered("flash"),"gemini_requests_submitted":1}):
            with self.subTest(evidence=evidence):
                self.calls.clear()
                with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"flash"}):
                    with self.assertRaises(AcademicReviewRouteError):
                        run(plan_path=self.plan,root=self.work,
                            campaign=self._campaign,
                            inspect_ready=lambda **_: evidence)
                self.assertFalse(self.calls)
                self.assertFalse((self.work/RECEIPT_NAME).exists())

    def test_explicit_pro_does_not_fallback_to_any_other_model(self):
        self.calls.clear()
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"pro"}):
            def blocked(*, primary_port):
                self.calls.append("first")
                raise AcademicGeminiPreSendBlocked(
                    "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE")
            with self.assertRaises(AcademicGeminiPreSendBlocked):
                run(plan_path=self.plan,root=self.work,
                    campaign=self._campaign,inspect_ready=blocked)
        self.assertEqual(self.calls,["first"])

    def test_route_provenance_cannot_change_under_existing_claims(self):
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"flash"}):
            run(plan_path=self.plan,root=self.work,
                campaign=self._campaign,
                inspect_ready=lambda **_: self._offered("flash"))
        old=(self.work/RECEIPT_NAME).read_bytes()
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"flash"}):
            def alternate(*,primary_port):
                if os.environ["MICROGEN_GEMINI_UI_MODE"]=="flash":
                    raise AcademicGeminiPreSendBlocked(
                        "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE")
                return self._offered("pro")
            with self.assertRaises(AcademicGeminiPreSendBlocked):
                run(plan_path=self.plan,root=self.work,
                    campaign=self._campaign,inspect_ready=alternate)
        self.assertEqual((self.work/RECEIPT_NAME).read_bytes(),old)

    def test_zero_budget_never_opens_browser(self):
        result=run(plan_path=self.plan,root=self.work,max_jobs=0,
                   campaign=lambda **_:self.fail("No campaign"),
                   inspect_ready=lambda **_:self.fail("No browser preflight"))
        self.assertEqual(result["new_requests_attempted"],0)

    def test_normal_campaign_cli_automatically_routes_through_failover(self):
        from selenium_pipeline.source_review_autonomous_campaign import main
        args=["--plan","unused.json","--checkpoint-root","unused"]
        with patch("selenium_pipeline.academic_review_model_failover.main",
                   return_value=2) as routed:
            self.assertEqual(main(args),2)
        routed.assert_called_once_with(args)
