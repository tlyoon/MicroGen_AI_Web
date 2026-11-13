"""Trusted source-stage auditor must accept ONLY fully proved adaptive UI route."""
from __future__ import annotations
import unittest

from selenium_pipeline.windows_gemini_stage_transport_triage import (
    audit_original_stage_model_family)

T="[2026-11-13 12:10:00] [INFO] "
R="EXACT_PREFERRED_ABSENT_STAGE_COMPATIBLE_FALLBACK"
ER="REQUESTED_LEVEL_UNAVAILABLE_VERIFIED_NON_DOWNGRADING"


def stage_raw(*,preferred="flash",actual="pro",effort="medium",
              route=True,offered="flash-lite,pro",figure=False,
              thinking=True,thinking_fallback=False):
    display={
        "flash":"Flash Medium","flash-lite":"Flash-Lite",
        "pro":"Pro Medium"}[actual]
    lines=[
      f"[microgen] browser UI model: {preferred}",
      ("[microgen] browser thinking level: not_required"
       if figure else "[microgen] browser thinking level: medium"),
    ]
    if route:
        lines.append(
            T+"[GEMINI-MODE] ADAPTIVE_VERIFIED_FALLBACK "+
            f"requested={preferred} selected={actual} "+
            f"offered={offered} reason={R}")
    lines.extend([
        T+f"Selected Gemini tab via mode picker: Open mode picker, currently {display} (phase=development)",
        T+f"[GEMINI-MODE] PRE_SEND_OWNED_FAMILY_VERIFIED Open mode picker, currently {display}",
    ])
    if thinking_fallback:
        lines.append(
            T+"[GEMINI-THINKING] ADAPTIVE_VERIFIED_EFFORT "+
            f"requested=medium selected={effort} "+
            f"offered=high,low reason={ER}")
    if thinking:
        lines.extend([
            T+f"[GEMINI-THINKING] OWNED_LEVEL_VERIFIED_AFTER_NEW_CHAT {effort}",
            T+f"[GEMINI-THINKING] PRE_SEND_OWNED_LEVEL_VERIFIED {effort}",
        ])
    return "\n".join(lines)+"\n"


class GeminiOwnedStageRouteWitnessTests(unittest.TestCase):
    def test_realistic_flash_absent_pro_verified_is_not_false_family_failure(self):
        x=audit_original_stage_model_family(
            stage_raw(),registered_send=True)
        self.assertEqual(x["adaptive_ui_model_and_thinking_route"],
                         "VERIFIED_ADAPTIVE_UI_ROUTE")
        self.assertEqual(x["effective_owned_ui_family_after_verified_fallback"],"pro")
        self.assertTrue(x["adaptive_ui_model_fallback_verified"])
        self.assertFalse(x["owned_worker_wrong_ui_family_observed"])
        self.assertTrue(x["owned_worker_requested_family_verified_immediately_before_send"])
        self.assertTrue(x["owned_worker_requested_thinking_verified_before_send"])
        self.assertFalse(x["owned_worker_thinking_contract_breach_observed"])

    def test_pro_without_valid_route_is_still_a_wrong_model(self):
        x=audit_original_stage_model_family(
            stage_raw(route=False),registered_send=True)
        self.assertFalse(x["adaptive_ui_model_fallback_verified"])
        self.assertTrue(x["owned_worker_wrong_ui_family_observed"])
        self.assertFalse(x["owned_worker_requested_family_verified_immediately_before_send"])

    def test_preferred_flash_present_pro_switch_is_not_auto_approved(self):
        x=audit_original_stage_model_family(
            stage_raw(offered="flash,pro"),registered_send=True)
        self.assertTrue(x["adaptive_ui_route_rejected"])
        self.assertTrue(x["owned_worker_wrong_ui_family_observed"])

    def test_unknown_fallback_family_does_not_override_contract(self):
        x=audit_original_stage_model_family(
            stage_raw(offered="hydrogen,pro"),registered_send=True)
        self.assertTrue(x["adaptive_ui_route_rejected"])
        self.assertFalse(x["owned_worker_requested_family_verified_immediately_before_send"])

    def test_figure_lite_to_full_flash_requires_both_medium_proofs(self):
        x=audit_original_stage_model_family(
            stage_raw(preferred="flash-lite",actual="flash",
                      offered="flash,pro",figure=True),registered_send=True)
        self.assertTrue(x["adaptive_ui_model_fallback_verified"])
        self.assertFalse(x["owned_worker_thinking_contract_breach_observed"])
        self.assertTrue(x["owned_worker_requested_thinking_verified_before_send"])
        y=audit_original_stage_model_family(
            stage_raw(preferred="flash-lite",actual="flash",
                      offered="flash,pro",figure=True,thinking=False),
            registered_send=True)
        self.assertTrue(y["owned_worker_thinking_contract_breach_observed"])
        self.assertFalse(y["owned_worker_requested_thinking_verified_before_send"])

    def test_preferred_medium_missing_checked_high_is_valid_but_no_downgrade(self):
        x=audit_original_stage_model_family(
            stage_raw(effort="high",thinking_fallback=True),
            registered_send=True)
        self.assertTrue(x["adaptive_ui_effort_fallback_verified"])
        self.assertEqual(x["effective_owned_thinking_level_after_verified_fallback"],
                         "high")
        self.assertTrue(x["owned_worker_requested_thinking_verified_before_send"])

    def test_invalid_effort_route_blocks_replacing_medium(self):
        x=audit_original_stage_model_family(
            stage_raw(effort="high",thinking_fallback=False),
            registered_send=True)
        self.assertFalse(x["adaptive_ui_effort_fallback_verified"])
        self.assertTrue(x["owned_worker_thinking_contract_breach_observed"])

    def test_malformed_adaptive_marker_cannot_authorize_send(self):
        raw=stage_raw().replace("offered=flash-lite,pro", "offered=4hydrogen")
        x=audit_original_stage_model_family(raw,registered_send=True)
        self.assertTrue(x["adaptive_ui_route_rejected"])
        self.assertFalse(x["owned_worker_requested_family_verified_immediately_before_send"])

    def test_no_registration_never_proves_a_successful_model_request(self):
        x=audit_original_stage_model_family(
            stage_raw(),registered_send=False)
        self.assertFalse(x["owned_worker_requested_family_verified_immediately_before_send"])
        self.assertFalse(x["owned_worker_requested_thinking_verified_before_send"])


if __name__=="__main__":
    unittest.main()
