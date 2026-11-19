"""Synthetic two-PDF Gemini recovery: source-safe proof, no replay or false science."""
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from selenium_pipeline.academic_dual_pdf_capability import (
    ROOT, _expected, _exact, _values, probe_once, qualifying_proof)
from selenium_pipeline.series_gemini import OwnedGeminiResponse

SHA = "a" * 64
NOW = 1800000000.0


class DualPdfCapabilityTests(TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.queue = self.root / "original_queue"
        self.queue.mkdir()
        self.sends = []
        self.seed(10, "b" * 64, NOW - 100)
        self.seed(11, "c" * 64, NOW - 50)

    def seed(self, slide, fingerprint, moment):
        cp = self.queue / f"slide_{slide:03d}_initial_review_attempt_01_request"
        cp.mkdir()
        (cp / "request_state.json").write_text(json.dumps({
            "source_sha256": SHA, "request_fingerprint": fingerprint,
            "status": "SUBMITTED_OR_UNCERTAIN",
            "submission_may_have_occurred": True, "can_auto_retry": False,
            "student_publication_authorized": False}))
        (cp / "dispatch_attempted.claim").write_text(fingerprint)
        os.utime(cp / "request_state.json", (moment, moment))
        return cp

    def good_transport(self, prompt, files):
        self.sends.append((prompt, files))
        self.assertEqual([p.name for p in files],
                         ["SyntheticA.pdf", "SyntheticB.pdf"])
        self.assertNotIn("source.pdf", " ".join(p.name for p in files))
        self.assertNotIn("slide", " ".join(p.name for p in files))
        nonce = re.search(r'\{"probe":"([0-9a-f]{18})"', prompt)[1]
        from fitz import open as read_pdf
        tokens=[]
        for file in files:
            doc=read_pdf(str(file))
            self.assertEqual(doc.page_count,1)
            text=doc[0].get_text()
            marker=re.search(r"PDF_CODE: ([0-9A-F]{18})",text)
            self.assertIsNotNone(marker)
            tokens.append(marker[1])
        self.assertNotIn(tokens[0],prompt)
        self.assertNotIn(tokens[1],prompt)
        return OwnedGeminiResponse(
            json.dumps({"probe":nonce,"a":tokens[0],"b":tokens[1]}),
            registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
            new_turn_verified=True)

    def probe(self, slides=None, moment=NOW, family="pro", transport=None):
        return probe_once(
            queue_root=self.queue,checkpoint_parent=self.root,
            source_sha=SHA,prior_slides=slides or [10,11],
            family=family,now=moment,
            transport=self.good_transport if transport is None else transport)

    def evidence(self, slides=None, moment=NOW + 60, family="pro"):
        return qualifying_proof(
            queue_root=self.queue, checkpoint_parent=self.root,
            source_sha=SHA,prior_slides=slides or [10,11],
            family=family,now=moment)

    def production_probe(self, family="flash"):
        return probe_once(
            queue_root=self.queue, checkpoint_parent=self.root,
            source_sha=SHA, prior_slides=[10, 11], family=family,
            now=NOW, transport=None)

    def test_live_absent_flash_blocks_before_any_synthetic_claim(self):
        from selenium_pipeline.academic_gemini_presend_preflight import (
            AcademicGeminiPreSendBlocked)
        with patch(
                "selenium_pipeline.academic_gemini_presend_preflight.select_ready_existing_session",
                side_effect=AcademicGeminiPreSendBlocked(
                    "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE")) as owned:
            result = self.production_probe(family="flash")
        self.assertEqual(result["status"],
                         "V1_SYNTHETIC_PDF_PRESEND_UNAVAILABLE_NO_CLAIM")
        self.assertEqual(result["failure_phase"],
                         "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE")
        self.assertFalse(result["new_source_review_send_allowed"])
        self.assertEqual(result["new_provider_requests"],0)
        self.assertEqual(owned.call_args.kwargs,dict(
            primary_port=9222,allow_active_alternate=False))
        self.assertFalse((self.root/ROOT).exists())
        self.assertEqual(self.sends,[])

    def test_wrong_model_or_alternate_proof_cannot_burn_claim(self):
        result={"verified_port":9225,"model_family":"flash",
                "thinking_level":"medium","gemini_requests_submitted":0,
                "files_uploaded":0,"model_prompt_typed":False,
                "student_publication_authorized":False,"G2_approved":False}
        with patch(
                "selenium_pipeline.academic_gemini_presend_preflight.select_ready_existing_session",
                return_value=result):
            blocked=self.production_probe("flash")
        self.assertEqual(blocked["failure_phase"],"PRESEND_EVIDENCE_MISMATCH")
        self.assertFalse((self.root/ROOT).exists())
        # Pro family proof cannot count for a claimed Flash-family diagnostic.
        result.update(verified_port=9222,model_family="pro")
        with patch(
                "selenium_pipeline.academic_gemini_presend_preflight.select_ready_existing_session",
                return_value=result):
            blocked=self.production_probe("flash")
        self.assertEqual(blocked["new_provider_requests"],0)
        self.assertFalse((self.root/ROOT).exists())

    def test_real_pro_verified_preflight_then_one_owned_synthetic_transport(self):
        verified={"verified_port":9222,"model_family":"pro",
                  "thinking_level":"medium","gemini_requests_submitted":0,
                  "files_uploaded":0,"model_prompt_typed":False,
                  "student_publication_authorized":False,
                  "G2_approved":False}
        with patch(
                "selenium_pipeline.academic_gemini_presend_preflight.select_ready_existing_session",
                return_value=verified) as owned:
            with patch("selenium_pipeline.series_gemini._browser_request",
                       side_effect=lambda prompt, files, **kwargs:
                           self.good_transport(prompt, files)) as browser:
                first=self.production_probe("pro")
                second=self.production_probe("pro")
        self.assertEqual(first["status"],"DUAL_SYNTHETIC_PDF_RESPONSE_VERIFIED")
        self.assertEqual(first["new_provider_requests"],1)
        self.assertEqual(second["new_provider_requests"],0)
        self.assertTrue(second["new_source_review_send_allowed"])
        self.assertEqual(browser.call_count,1)
        self.assertEqual(owned.call_count,1)
        self.assertEqual(len(list((self.root/ROOT).rglob("claim.json"))),1)
        self.assertEqual(len(self.sends),1)

    def test_disabled_preclaim_registry_never_calls_model_or_send(self):
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with patch(
                "selenium_pipeline.academic_gemini_presend_preflight.select_ready_existing_session"
            ) as inspector:
                with self.assertRaisesRegex(
                        ValueError,"pre-claim recovery disabled"):
                    self.production_probe("flash")
                inspector.assert_not_called()
        self.assertFalse((self.root/ROOT).exists())

    def test_preflight_generic_exception_cannot_consume_claim(self):
        with patch(
                "selenium_pipeline.academic_gemini_presend_preflight.select_ready_existing_session",
                side_effect=RuntimeError("unsafe arbitrary browser page content")):
            result=self.production_probe("flash")
        self.assertEqual(result["failure_phase"],"PRESEND_VERIFICATION_FAILED")
        self.assertNotIn("browser page",str(result))
        self.assertFalse((self.root/ROOT).exists())

    def test_real_pdf_tokens_prove_both_attachments_without_source(self):
        answer=self.probe()
        self.assertEqual(answer["status"],
                         "DUAL_SYNTHETIC_PDF_RESPONSE_VERIFIED")
        self.assertTrue(answer["new_source_review_send_allowed"])
        self.assertEqual(answer["new_provider_requests"],1)
        self.assertEqual(len(self.sends),1)
        proof=self.evidence()
        self.assertEqual(proof["incident_sha256"],answer["incident_sha256"])
        self.assertFalse(proof["original_source_uploaded"])
        self.assertFalse(proof["academic_approval"])
        self.assertFalse(proof["paid_operations_authorized"])
        self.assertEqual(len(list((self.root/ROOT).rglob("claim.json"))),1)

    def test_restart_reuses_proof_and_never_sends_again(self):
        self.probe()
        again=self.probe(moment=NOW+30)
        self.assertEqual(len(self.sends),1)
        self.assertEqual(again["new_provider_requests"],0)
        self.assertTrue(again["new_source_review_send_allowed"])

    def test_nonce_only_reply_is_not_source_capability_proof(self):
        def no_pdf_read(prompt, files):
            self.sends.append((prompt, files))
            token=re.search(r'\{"probe":"([0-9a-f]{18})"',prompt)[1]
            return OwnedGeminiResponse(
                json.dumps({"probe":token,"a":"not-read","b":"not-read"}),
                registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
                new_turn_verified=True)
        bad=self.probe(transport=no_pdf_read)
        self.assertEqual(bad["status"],
                         "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED")
        self.assertFalse(bad["new_source_review_send_allowed"])
        self.assertIsNone(self.evidence())
        self.assertEqual(self.probe(moment=NOW+30)["new_provider_requests"],0)
        self.assertEqual(len(self.sends),1)

    def test_an_ordinary_str_without_owned_response_is_never_proof(self):
        def fake(prompt, files):
            self.sends.append((prompt, files))
            real=self.good_transport(prompt, files)
            return str(real)
        out=self.probe(transport=fake)
        self.assertFalse(out["new_source_review_send_allowed"])
        self.assertIsNone(self.evidence())

    def test_crash_after_claim_never_retries_synthetic_request(self):
        self.probe()
        saved=next((self.root/ROOT).rglob("result.json"))
        saved.unlink()
        old=len(self.sends)
        self.assertIsNone(self.evidence())
        prior=self.probe(moment=NOW+100)
        self.assertEqual(prior["status"],
                         "PRIOR_SYNTHETIC_PDF_SEND_UNCERTAIN_NO_RESEND")
        self.assertEqual(prior["new_provider_requests"],0)
        self.assertEqual(len(self.sends),old)

    def test_consumed_failed_probe_exposes_durable_no_resend_state(self):
        from selenium_pipeline.academic_dual_pdf_capability import existing_outcome
        def no_response(prompt, files):
            self.sends.append((prompt, files))
            raise TimeoutError("No attributable Gemini owned model response")
        initial=self.probe(transport=no_response)
        self.assertFalse(initial["new_source_review_send_allowed"])
        saved=existing_outcome(
            queue_root=self.queue,checkpoint_parent=self.root,
            source_sha=SHA,prior_slides=[10,11],family="pro",now=NOW+100)
        self.assertEqual(saved["status"],
                         "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED")
        self.assertEqual(saved["new_provider_requests"],0)
        self.assertFalse(saved["new_source_review_send_allowed"])
        self.assertEqual(len(self.sends),1)

    def test_daily_budget_blocks_new_incident_without_unbounded_retries(self):
        self.probe()
        self.seed(12,"d"*64,NOW+20)
        blocked=self.probe(slides=[11,12],moment=NOW+40)
        self.assertEqual(blocked["status"],
                         "SYNTHETIC_PDF_DAILY_BUDGET_EXHAUSTED")
        self.assertFalse(blocked["new_source_review_send_allowed"])
        self.assertEqual(blocked["new_provider_requests"],0)
        self.assertEqual(len(self.sends),1)

    def test_newer_source_failure_cannot_reuse_old_proof(self):
        self.probe()
        self.seed(12,"d"*64,NOW+20)
        self.assertIsNone(self.evidence(slides=[11,12],moment=NOW+60))
        self.assertIsNotNone(self.evidence(slides=[10,11],moment=NOW+60))

    def test_corrupt_result_or_wrong_family_fails_closed(self):
        self.probe()
        self.assertIsNone(self.evidence(family="flash"))
        result=next((self.root/ROOT).rglob("result.json"))
        receipt=json.loads(result.read_text())
        receipt["model_response_json"]["a"]="forged"
        result.write_text(json.dumps(receipt))
        with self.assertRaises(ValueError):
            self.evidence()

    def test_tampered_original_request_blocks_probe_even_with_old_reply(self):
        cp=self.queue/"slide_011_initial_review_attempt_01_request"
        (cp/"dispatch_attempted.claim").write_text("e"*64)
        with self.assertRaises(ValueError):
            self.probe()

    def test_duplicate_json_not_accepted(self):
        expected={"probe":"n","a":"A","b":"B"}
        self.assertFalse(_exact(
            '{"probe":"n","a":"A","a":"A","b":"B"}',expected))
        self.assertTrue(_exact('{"probe":"n","a":"A","b":"B"}',expected))

    def test_no_source_or_textbook_material_in_generated_attachments(self):
        self.probe()
        for path in (self.root/ROOT).rglob("Synthetic*.pdf"):
            raw=path.read_bytes()
            self.assertNotIn(b"Serway",raw)
            self.assertNotIn(b"tlyoon",raw)
            self.assertNotIn(b"source.pdf",raw)
        self.assertEqual(len(self.sends),1)
