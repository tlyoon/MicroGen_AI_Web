"""Executable G2 multi-stage forward-and-repair contract, actual disk journal."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.g2_forward_recovery_engine import run, _json_file, _new_json


class G2ForwardRecoveryEngineTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.folder=self.root/"source_tree"/"1"/"1.3"
        self.queue=self.root/"g2_academic_review"
        self.work=self.root/"work"
        for p in (self.folder,self.queue,self.work):
            p.mkdir(parents=True,exist_ok=True)
        for name in ("source.pdf","slides.pdf","script.txt"):
            (self.folder/name).write_text("GENUINE SOURCE SHA "+name,encoding="utf8")
        self.hashes={name:file_sha256(self.folder/name)
                     for name in ("source.pdf","slides.pdf","script.txt")}
        self.original_hashes=self.hashes.copy()
        self.selection={
            "status":"ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY",
            "action":"FRESH_FIRST_ATTEMPT",
            "next_slide":5,
            "next_mode":"INITIAL_REVIEW",
        }
        self.events=[]
        self.mock_a=patch(
            "selenium_pipeline.g2_forward_recovery_engine._source_lock",
            side_effect=lambda *args:self.verify_original())
        self.mock_b=patch(
            "selenium_pipeline.ai_academic_review_queue.select_next_safe_review",
            side_effect=lambda **kw:self.selection.copy())
        self.mock_a.start();self.mock_b.start()
        self.addCleanup(self.mock_a.stop)
        self.addCleanup(self.mock_b.stop)

    def verify_original(self):
        actual={name:file_sha256(self.folder/name)
                for name in ("source.pdf","slides.pdf","script.txt")}
        if actual!=self.original_hashes:
            raise ValueError("Original queue SHA-bound files changed")
        return actual.copy()

    def invoke(self,*,execute=False,max_cycles=8,supervisor=None,
               synthetic_pdf_probe=None,offline_auditor=None):
        return run(folder=self.folder,queue_root=self.queue,
                   work_root=self.work,execute=execute,
                   max_cycles=max_cycles,supervisor=supervisor,
                   synthetic_pdf_probe=synthetic_pdf_probe,
                   offline_auditor=offline_auditor,
                   health_family="pro",auto_media=True)

    def report(self,status,*,attempt=None,health=None,agreed=4,pending=81):
        return {
            "schema_version":1,
            "status":status,
            "original_source_sha256":self.hashes["source.pdf"],
            "original_slides_sha256":self.hashes["slides.pdf"],
            "original_script_sha256":self.hashes["script.txt"],
            "two_pass_ai_source_agreed_segments":agreed,
            "pending_or_disputed_segments":pending,
            "expected_original_utterances":agreed+pending,
            "next_safe_academic_action":self.selection.copy(),
            "bounded_review_attempt":attempt,
            "provider_health":health,
            "new_paid_tts_dispatched":False,
            "real_mp4_encoded_this_cycle":False,
        }

    def test_v6_unknown_action_does_not_dispatch_or_claim_source_send(self):
        self.selection["action"]="UNREGISTERED_RISKY_PROVIDER_RETRY"
        def forbidden(**kw):
            self.fail("An unclassified recovery may not call the supervisor")
        with self.assertRaisesRegex(Exception,"Unknown source-review recovery action"):
            self.invoke(execute=True,supervisor=forbidden)
        home=self.work/"g2_forward_recovery_v1"
        self.assertFalse(list(home.rglob("*.intent.json")))

    def test_consumed_pdf_probe_does_not_create_another_stage_on_restart(self):
        self.selection={
            "status":"DEFERRED_SYNTHETIC_PDF_CAPABILITY_EXHAUSTED_NO_RESEND",
            "unattempted_candidate_slide":12,
            "unattributed_prior_slides":[10,11],
            "last_capability_status":"DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED",
            "new_model_requests":False,
        }
        def never_supervisor(**kw):
            self.fail("Consumed synthetic probe cannot dispatch a new request")
        def never_probe(**kw):
            self.fail("Consumed synthetic probe may not be resent")
        def audited(**kw):
            self.events.append(kw)
            self.assertEqual(kw["next_slide"],12)
            return {"status":"G2_OFFLINE_READINESS_COMPLETED_NO_GEMINI_SEND",
                    "original_utterance_count":85,
                    "original_two_pass_accepted":20,
                    "new_model_requests":0,"scientific_approval":False,
                    "student_publication_authorized":False}
        output=self.invoke(execute=True,max_cycles=8,
            supervisor=never_supervisor,synthetic_pdf_probe=never_probe,
            offline_auditor=audited)
        self.assertEqual(len(self.events),1)
        self.assertEqual(output["last_stage"][
            "independent_offline_source_readiness"]["status"],
            "G2_OFFLINE_READINESS_COMPLETED_NO_GEMINI_SEND")
        self.assertEqual(output["critical_path_recovery_proof"]["status"],
                         "BLOCKED_EXTERNAL_DEPENDENCY")
        self.assertFalse(output["critical_path_recovery_proof"][
            "original_operation_recovered"])
        self.assertTrue(output["critical_path_recovery_proof"][
            "supporting_work_completed"])
        self.assertEqual(output["status"],
                         "G2_FORWARD_STOPPED_AT_VERIFIED_ELIGIBILITY_BOUNDARY")
        self.assertEqual(output["stage_cycles_this_invocation"],[])
        self.assertEqual(output["last_stage"]["unattempted_candidate_slide"],12)
        self.assertEqual(list(Path(output["journal"]).glob("*.intent.json")),[])

    def test_offline_dependency_never_grants_provider_send_or_science(self):
        self.selection={
            "status":"DEFERRED_SYNTHETIC_PDF_CAPABILITY_EXHAUSTED_NO_RESEND",
            "unattempted_candidate_slide":12,
        }
        for promoted in (
            {"new_model_requests":1, "scientific_approval":False,
             "student_publication_authorized":False},
            {"new_model_requests":0, "scientific_approval":True,
             "student_publication_authorized":False},
            {"new_model_requests":0, "scientific_approval":False,
             "student_publication_authorized":True},
        ):
            with self.subTest(promoted=promoted):
                def malicious(**kw):
                    return {"status":"G2_OFFLINE_READINESS_COMPLETED_NO_GEMINI_SEND",
                            **promoted}
                with self.assertRaisesRegex(ValueError,
                                            "cannot authorize model replay"):
                    self.invoke(execute=True,offline_auditor=malicious,
                                supervisor=lambda **kw:self.fail(
                                    "No scientific Send may occur"))
                home=self.work/"g2_forward_recovery_v1"
                self.assertFalse(list(home.rglob("*.intent.json")))

    def test_synthetic_dual_pdf_capability_proof_advances_to_fresh_source(self):
        self.selection={
            "status":"DEFERRED_REPEATED_UNATTRIBUTED_BROWSER_SEND",
            "required_recovery_action":"SYNTHETIC_DUAL_PDF_CAPABILITY_PROBE",
            "unattributed_prior_slides":[10,11],
            "unattempted_candidate_slide":12,
            "new_model_requests":False,
        }
        sends=[]
        def pdf_probe(**kw):
            sends.append(kw)
            self.selection={
                "status":"ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY",
                "action":"FRESH_FIRST_ATTEMPT",
                "next_slide":12,"next_mode":"INITIAL_REVIEW",
                "original_source_pdf_health_proven":True,
            }
            return {
                "status":"DUAL_SYNTHETIC_PDF_RESPONSE_VERIFIED",
                "incident_sha256":"a"*64,
                "new_source_review_send_allowed":True,
                "new_provider_requests":1,
            }
        def supervisor(**kw):
            self.events.append(kw)
            self.assertEqual(self.selection["next_slide"],12)
            return self.report("G2_PROVIDER_HEALTH_DEFERRED_NO_NEW_SOURCE_SEND",
                               health={"new_source_review_send_allowed":False})
        science={
            "status":"INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE",
            "accepted_ai_evidence":[{"id":str(i)} for i in range(20)],
            "pending_or_disputed":65,"original_utterances":85}
        with patch(
            "selenium_pipeline.ai_academic_review_consensus.reconcile_actual_review_queue",
            return_value=science):
            result=self.invoke(execute=True,max_cycles=2,
                supervisor=supervisor,synthetic_pdf_probe=pdf_probe)
        self.assertEqual(len(sends),1)
        self.assertEqual(len(self.events),1)
        self.assertEqual(result["stage_cycles_this_invocation"][0]["action"],
                         "CONTINUE")
        self.assertEqual(result["stage_cycles_this_invocation"][1]["action"],
                         "HALT")
        home=Path(result["journal"])
        first=_json_file(home/"0001.intent.json")
        receipt=_json_file(home/"0001.result.json")
        self.assertEqual(first["stage_classification"],
                         "SOURCE_REVIEW_MODALITY_CAPABILITY_PROBE")
        self.assertEqual(first["original_unsafe_claim_slides"],[10,11])
        self.assertEqual(first["recovery_mechanism"],
                         "OWNED_TWO_SYNTHETIC_PDF_SOURCE_MODALITY_TEST_ONCE_ONLY")
        self.assertEqual(receipt["actual_report"][
            "two_pass_ai_source_agreed_segments"],20)
        self.assertFalse(receipt["actual_report"]["academic_science_approved"])
        self.assertFalse(receipt["actual_report"]["new_paid_tts_dispatched"])

    def test_synthetic_pdf_probe_failure_is_persisted_and_never_sends_source(self):
        self.selection={
            "status":"DEFERRED_REPEATED_UNATTRIBUTED_BROWSER_SEND",
            "required_recovery_action":"SYNTHETIC_DUAL_PDF_CAPABILITY_PROBE",
            "unattributed_prior_slides":[10,11],
            "unattempted_candidate_slide":12}
        calls=[]
        def fail(**kw):
            calls.append(kw)
            return {"status":"DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED",
                    "new_source_review_send_allowed":False,
                    "new_provider_requests":1}
        def never_supervisor(**kw):
            self.fail("Cannot begin science review after failed PDF canary")
        science={
            "status":"INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE",
            "accepted_ai_evidence":[],"pending_or_disputed":85,
            "original_utterances":85}
        with patch(
            "selenium_pipeline.ai_academic_review_consensus.reconcile_actual_review_queue",
            return_value=science):
            output=self.invoke(execute=True,max_cycles=8,
                supervisor=never_supervisor,synthetic_pdf_probe=fail)
        self.assertEqual(len(calls),1)
        self.assertEqual(len(output["stage_cycles_this_invocation"]),1)
        self.assertEqual(output["stage_cycles_this_invocation"][0]["action"],
                         "HALT")
        receipt=_json_file(Path(output["journal"])/"0001.result.json")
        self.assertEqual(receipt["actual_report"]["status"],
                         "G2_SYNTHETIC_PDF_CAPABILITY_DEFERRED")
        self.assertFalse(receipt["actual_report"]["provider_health"][
            "new_source_review_send_allowed"])

    def test_completed_recovery_triggers_next_stage_without_new_user_prompt(self):
        def dispatch(**kwargs):
            self.events.append(kwargs)
            self.assertTrue(kwargs["execute"])
            self.assertEqual(kwargs["max_units"],1)
            count=len(self.events)
            if count==1:
                self.selection={**self.selection,"next_slide":6}
                return self.report("G2_ACADEMIC_QA_INCOMPLETE_REVIEW_OR_SOURCE_REPAIR",
                    attempt={
                        "status":"BOUNDED_REVIEW_LIMIT_REACHED",
                        "completed":[{"slide":5,"receipt_sha256":"f"*64}],
                    })
            return self.report("G2_PROVIDER_HEALTH_DEFERRED_NO_NEW_SOURCE_SEND",
                               health={"new_source_review_send_allowed":False})
        result=self.invoke(execute=True,supervisor=dispatch)
        self.assertEqual(len(self.events),2)
        self.assertEqual(result["status"],
                         "G2_FORWARD_STOPPED_AT_VERIFIED_ELIGIBILITY_BOUNDARY")
        self.assertEqual([x["ordinal"] for x in result["stage_cycles_this_invocation"]],
                         [1,2])
        self.assertEqual(result["stage_cycles_this_invocation"][0]["action"],
                         "CONTINUE")
        self.assertEqual(result["stage_cycles_this_invocation"][1]["action"],
                         "HALT")
        home=Path(result["journal"])
        self.assertEqual(len(list(home.glob("*.result.json"))),2)
        a=_json_file(home/"0001.result.json")
        b=_json_file(home/"0002.intent.json")
        self.assertEqual(b["prior_result_sha256"],
                         file_sha256(home/"0001.result.json"))
        self.assertFalse(result["next_scheduled_task_created"])

    def test_immediately_advances_local_no_send_reconciliation(self):
        self.selection["action"]="RECONCILE_PRIOR_RESPONSE_NO_SEND"
        def dispatch(**kw):
            self.events.append(1)
            if len(self.events)==1:
                self.selection={**self.selection,
                                "action":"FRESH_FIRST_ATTEMPT","next_slide":6}
                return self.report("G2_ACADEMIC_QA_INCOMPLETE_REVIEW_OR_SOURCE_REPAIR",
                    attempt={
                        "status":"BOUNDED_REVIEW_LIMIT_REACHED",
                        "completed":[{"slide":5,"receipt_sha256":"f"*64}],
                    })
            return self.report("G2_PROVIDER_HEALTH_DEFERRED_NO_NEW_SOURCE_SEND")
        result=self.invoke(execute=True,supervisor=dispatch)
        self.assertEqual(len(self.events),2)
        one=_json_file(Path(result["journal"])/"0001.intent.json")
        self.assertEqual(one["recovery_mechanism"],
                         "SHA_LOCKED_SOURCE_CITATION_DOWNGRADE_AND_LOCAL_REPLY_RECONCILIATION")

    def test_new_wrapped_saved_reply_recovers_and_advances_without_prompt(self):
        self.selection["action"]="RECOVER_WRAPPED_SAVED_REPLY_NO_SEND"
        def dispatch(**kw):
            self.events.append(kw)
            if len(self.events)==1:
                self.selection={**self.selection,
                                "next_slide":7,
                                "action":"RECOVER_WRAPPED_SAVED_REPLY_NO_SEND"}
                return self.report("G2_ACADEMIC_QA_INCOMPLETE_REVIEW_OR_SOURCE_REPAIR",
                    attempt={"status":"BOUNDED_REVIEW_LIMIT_REACHED",
                             "completed":[{"slide":5,"receipt_sha256":"f"*64}]})
            return self.report("G2_PROVIDER_HEALTH_DEFERRED_NO_NEW_SOURCE_SEND")
        out=self.invoke(execute=True,supervisor=dispatch)
        self.assertEqual(len(self.events),2)
        self.assertEqual(out["stage_cycles_this_invocation"][0]["action"],
                         "CONTINUE")
        self.assertEqual(out["stage_cycles_this_invocation"][1]["action"],
                         "HALT")
        home=Path(out["journal"])
        intent=_json_file(home/"0001.intent.json")
        self.assertEqual(intent["recovery_mechanism"],
                         "EXACT_OWNED_JSON_ENVELOPE_AND_DOWNGRADE_ONLY_SOURCE_RECONCILIATION")
        self.assertTrue(intent["never_resend_ambiguous_claim"])

    def test_quarantined_saved_reply_advances_next_unattempted_slide(self):
        """A genuinely rejected saved reply may not halt unrelated science."""
        self.selection["action"]="RECONCILE_PRIOR_RESPONSE_NO_SEND"
        def dispatch(**kwargs):
            self.events.append(kwargs)
            if len(self.events)==1:
                self.assertEqual(self.selection["next_slide"],5)
                self.selection={**self.selection,"next_slide":6,
                                "action":"FRESH_FIRST_ATTEMPT",
                                "blocked_other_slides":[{
                                    "slide":5,
                                    "reason":"SOURCE_REVIEW_QUARANTINED_INVALID_SAVED_REPLY",
                                    "original_request_replay_authorized":False}]}
                return self.report("G2_ACADEMIC_QA_INCOMPLETE_REVIEW_OR_SOURCE_REPAIR",
                    attempt={"status":"BOUNDED_REVIEW_STOPPED_AFTER_UNACCEPTED_UNIT",
                             "completed":[]})
            self.assertEqual(self.selection["next_slide"],6)
            return self.report("G2_PROVIDER_HEALTH_DEFERRED_NO_NEW_SOURCE_SEND",
                               health={"new_source_review_send_allowed":False})
        result=self.invoke(execute=True,supervisor=dispatch)
        self.assertEqual(len(self.events),2)
        stages=result["stage_cycles_this_invocation"]
        self.assertEqual(stages[0]["action"],"CONTINUE")
        self.assertEqual(stages[0]["classification"],
                         "NEXT_ELIGIBLE_SLIDE_REQUIRES_PROVIDER_HEALTH")
        self.assertEqual(stages[1]["action"],"HALT")
        self.assertFalse(result["G2_claimed_complete"])

    def test_rerun_verifies_existing_chain_and_never_overwrites(self):
        def dispatch(**kw):
            return self.report("G2_PROVIDER_HEALTH_DEFERRED_NO_NEW_SOURCE_SEND")
        first=self.invoke(execute=True,supervisor=dispatch)
        home=Path(first["journal"])
        old=home.joinpath("0001.result.json").read_bytes()
        second=self.invoke(execute=True,supervisor=dispatch)
        self.assertEqual(old,home.joinpath("0001.result.json").read_bytes())
        self.assertEqual(len(list(home.glob("*.intent.json"))),2)
        self.assertEqual(len(list(home.glob("*.result.json"))),2)
        self.assertEqual(second["stage_cycles_this_invocation"][0]["ordinal"],2)

    def test_tampered_old_receipt_prevents_next_any_provider_call(self):
        report=self.invoke(execute=True,supervisor=lambda **kw:
            self.report("G2_PROVIDER_HEALTH_DEFERRED_NO_NEW_SOURCE_SEND"))
        home=Path(report["journal"])
        result=home/"0001.result.json"
        obj=_json_file(result)
        obj["intent_sha256"]="z"*64
        result.write_text(json.dumps(obj))
        def never(**kw):
            self.fail("No stage may run with tampered history")
        with self.assertRaises(ValueError):
            self.invoke(execute=True,supervisor=never)

    def test_crash_orphan_intent_is_source_reinspected_without_dispatch(self):
        def dispatch(**kw):
            self.assertTrue(kw["execute"])
            result=self.report("G2_PROVIDER_HEALTH_DEFERRED_NO_NEW_SOURCE_SEND")
            return result
        initial=self.invoke(execute=True,supervisor=dispatch)
        home=Path(initial["journal"])
        previous=file_sha256(home/"0001.result.json")
        orphan={
            "schema_version":1,"original_source_folder":str(self.folder),
            "original_review_queue":str(self.queue),
            "original_source_sha256":self.hashes["source.pdf"],
            "original_slides_sha256":self.hashes["slides.pdf"],
            "original_script_sha256":self.hashes["script.txt"],
            "prior_result_sha256":previous,
            "stage_classification":"SOURCE_CITED_ACADEMIC_REVIEW",
        }
        _new_json(home/"0002.intent.json",orphan)
        seen=[]
        def inspect(**kwargs):
            seen.append(kwargs["execute"])
            return self.report("G2_ACADEMIC_QA_INCOMPLETE_REVIEW_OR_SOURCE_REPAIR")
        result=self.invoke(execute=False,supervisor=inspect)
        self.assertEqual(seen,[False,False])
        repaired=_json_file(home/"0002.result.json")
        self.assertEqual(repaired["status"],
                         "CRASHED_STAGE_SOURCE_REINSPECTED_NO_PROVIDER_REPLAY")
        self.assertFalse(repaired["source_request_retried"])
        self.assertEqual(result["recovered_cycles"],2)

    def test_finite_budget_persists_exact_maximum_without_infinite_loop(self):
        def dispatch(**kw):
            self.events.append(kw)
            self.selection={**self.selection,"next_slide":5+len(self.events)}
            return self.report("G2_ACADEMIC_QA_INCOMPLETE_REVIEW_OR_SOURCE_REPAIR",
                attempt={"status":"BOUNDED_REVIEW_LIMIT_REACHED",
                         "completed":[{"slide":5+len(self.events),
                                       "receipt_sha256":"f"*64}]})
        result=self.invoke(execute=True,max_cycles=3,supervisor=dispatch)
        self.assertEqual(result["status"],
                         "G2_FINITE_FORWARD_BUDGET_REACHED_CHECKPOINT_PRESERVED")
        self.assertEqual(len(self.events),3)
        self.assertEqual(len(list(Path(result["journal"]).glob("*.result.json"))),3)

    def test_normal_windows_launcher_always_uses_recovery_chain_no_scheduler(self):
        root=Path(__file__).resolve().parents[1]
        code=(root/"operations"/"g2_serway13_autonomous_cycle.ps1").read_text(
            encoding="utf8")
        workflow=(root/".github"/"workflows"/"microgen-reliability-tests.yml").read_text(
            encoding="utf8")
        self.assertIn("selenium_pipeline.g2_forward_recovery_engine",code)
        self.assertIn("--max-cycles",code)
        self.assertIn("tests.test_g2_forward_recovery_engine",workflow)
        self.assertNotIn("Register-ScheduledTask",code)
        self.assertNotIn("schtasks",code)

    def test_rejects_unbounded_budget_and_changed_source(self):
        with self.assertRaises(ValueError):
            self.invoke(execute=True,max_cycles=33)
        prior=self.invoke(execute=True,supervisor=lambda **kw:
            self.report("G2_PROVIDER_HEALTH_DEFERRED_NO_NEW_SOURCE_SEND"))
        (self.folder/"source.pdf").write_bytes(b"tampered original source")
        with self.assertRaises(ValueError):
            self.invoke(execute=True,supervisor=lambda **kw:
                self.fail("No future request after original source SHA changes"))


if __name__=="__main__":
    unittest.main()
