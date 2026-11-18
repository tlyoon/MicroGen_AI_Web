"""v6.1 mock/fault-injection tests: NO claims of a real Gemini recovery."""
import unittest
from pathlib import Path

from selenium_pipeline.recovery_proof_gate import pdf_critical_path_verdict


SOURCE="a"*64
INCIDENT="b"*64
RECEIPT="c"*64
NEXT="d"*64


class ProductionRecoveryEvidenceGateTests(unittest.TestCase):
    def blocked(self, **override):
        return pdf_critical_path_verdict(
            source_sha256=SOURCE,original_accepted=20,original_total=85,
            supporting_work_completed=True,**override)

    def capability(self):
        return {
            "status":"DUAL_SYNTHETIC_PDF_RESPONSE_VERIFIED",
            "source_sha256":SOURCE,"incident_sha256":INCIDENT,
            "new_source_review_send_allowed":True,
            "gemini_new_user_turn_verified":True,
            "send_registration_status":"NEW_USER_TURN_AND_COMPOSER_CLEARED",
            "claim_sha256":"e"*64,
            "model_response_json":{"probe":"N"*18,"a":"A"*18,"b":"B"*18},
            "original_source_uploaded":False,"academic_approval":False,
        }

    def source_review(self):
        return {
            "status":"ORIGINAL_SOURCE_TWO_PASS_REVIEW_ACCEPTED",
            "source_sha256":SOURCE,"pdf_incident_sha256":INCIDENT,
            "accepted_before":20,"accepted_after":25,
            "verified_receipt_sha256":RECEIPT,
        }

    def advanced(self):
        return {
            "status":"NEXT_ELIGIBLE_MILESTONE_ACTUALLY_ENTERED",
            "source_sha256":SOURCE,
            "prior_accepted_receipt_sha256":RECEIPT,
            "checkpoint_sha256":NEXT,
        }

    def test_offline_progress_never_resolves_the_original_pdf_blocker(self):
        answer=self.blocked()
        self.assertEqual(answer["status"],"BLOCKED_EXTERNAL_DEPENDENCY")
        self.assertTrue(answer["supporting_work_completed"])
        self.assertFalse(answer["supporting_work_is_primary_repair"])
        self.assertFalse(answer["live_pdf_modality_verified"])
        self.assertFalse(answer["original_operation_recovered"])
        self.assertFalse(answer["next_milestone_advanced"])
        self.assertFalse(answer["retry_consumed_original_send_authorized"])
        self.assertFalse(answer["paid_operations_authorized"])

    def test_fake_source_acceptance_or_advancement_without_modality_fails_closed(self):
        for fake in (
            {"accepted_original_operation_receipt":self.source_review()},
            {"next_milestone_receipt":self.advanced()},
            {"accepted_original_operation_receipt":self.source_review(),
             "next_milestone_receipt":self.advanced()},
        ):
            with self.subTest(fake=fake):
                with self.assertRaisesRegex(ValueError,"without live modality"):
                    self.blocked(**fake)

    def test_a_two_pdf_capability_proof_is_not_source_operation_recovery(self):
        result=self.blocked(verified_modality_receipt=self.capability())
        self.assertEqual(result["status"],"LIVE_CAPABILITY_VERIFIED")
        self.assertTrue(result["live_pdf_modality_verified"])
        self.assertFalse(result["original_operation_recovered"])
        self.assertFalse(result["next_milestone_advanced"])
        self.assertFalse(result["scientific_approval_fabricated"])

    def test_unattributed_or_wrong_source_canary_proof_is_not_accepted(self):
        for change in (
            {"status":"DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED"},
            {"source_sha256":"f"*64},
            {"new_source_review_send_allowed":False},
            {"gemini_new_user_turn_verified":False},
            {"academic_approval":True},
            {"incident_sha256":"not-a-sha"},
            {"original_source_uploaded":True},
        ):
            with self.subTest(change=change):
                proof={**self.capability(),**change}
                with self.assertRaisesRegex(ValueError,"not independently qualified"):
                    self.blocked(verified_modality_receipt=proof)

    def test_only_real_original_acceptance_evidence_would_change_state(self):
        # Simulated evidence shape; not a live provider test or approval.
        result=self.blocked(
            verified_modality_receipt=self.capability(),
            accepted_original_operation_receipt=self.source_review())
        self.assertEqual(result["status"],"ORIGINAL_OPERATION_RECOVERED")
        self.assertTrue(result["original_operation_recovered"])
        self.assertFalse(result["next_milestone_advanced"])
        self.assertFalse(result["paid_operations_authorized"])

    def test_source_review_requires_measurable_and_linked_acceptance(self):
        for change in (
            {"accepted_after":20},
            {"accepted_before":19},
            {"accepted_after":86},
            {"source_sha256":"f"*64},
            {"pdf_incident_sha256":"f"*64},
            {"verified_receipt_sha256":"not-an-actual-sha"},
        ):
            with self.subTest(change=change):
                review={**self.source_review(),**change}
                with self.assertRaisesRegex(ValueError,"not been accepted"):
                    self.blocked(verified_modality_receipt=self.capability(),
                                 accepted_original_operation_receipt=review)

    def test_downstream_requires_distinct_linked_checkpoint(self):
        with self.assertRaisesRegex(ValueError,"without accepted original review"):
            self.blocked(verified_modality_receipt=self.capability(),
                         next_milestone_receipt=self.advanced())
        for change in (
            {"prior_accepted_receipt_sha256":"f"*64},
            {"source_sha256":"f"*64},
            {"status":"PLAN_CREATED_NOT_EXECUTED"},
            {"checkpoint_sha256":"not-a-sha"},
        ):
            with self.subTest(change=change):
                downstream={**self.advanced(),**change}
                with self.assertRaisesRegex(ValueError,"no linked real checkpoint"):
                    self.blocked(
                        verified_modality_receipt=self.capability(),
                        accepted_original_operation_receipt=self.source_review(),
                        next_milestone_receipt=downstream)

    def test_only_all_three_evidence_layers_can_classify_forward(self):
        # Synthetic fixtures exercise state ordering ONLY, not provider proof.
        result=self.blocked(
            verified_modality_receipt=self.capability(),
            accepted_original_operation_receipt=self.source_review(),
            next_milestone_receipt=self.advanced())
        self.assertEqual(result["status"],"NEXT_MILESTONE_ADVANCED")
        self.assertTrue(result["original_operation_recovered"])
        self.assertTrue(result["next_milestone_advanced"])
        self.assertFalse(result["scientific_approval_fabricated"])

    def test_contract_is_versioned_and_requires_real_source_acceptance(self):
        text=(Path(__file__).resolve().parents[1]/"docs"/
              "auto_cont_dev_prompt_v6.1.md").read_text(encoding="utf8")
        self.assertIn("**Version:** 6.1",text)
        self.assertIn("## 14. Critical-Path Recovery Proof",text)
        self.assertIn("ORIGINAL_OPERATION_RECOVERED",text)
        self.assertIn("NEXT_MILESTONE_ADVANCED",text)
        self.assertIn("two distinct synthetic PDFs",text)
        self.assertIn("the real originally failed operation",text.lower())


if __name__=="__main__":
    unittest.main()
