"""One-use source-bound review checkpoint and offline recovery adversarial tests."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from selenium_pipeline.academic_review_checkpoint import (
    ReviewCheckpointError, fingerprint,prepare,mark_submission_maybe,
    submit_once,record_observation,validate_saved,legacy_no_response,
)

class OnceOnlyAcademicReview(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)
        self.original=self.path/"original"
        self.original.mkdir()
        self.refs={}
        for filename,content in (
             ("source.pdf",b"%PDF source"),("slides.pdf",b"%PDF slides"),
             ("script.txt",b"**Slide 1 [1 sec]: Text")):
            (self.original/filename).write_bytes(content)
            self.refs[filename]=hashlib.sha256(content).hexdigest()
        self.window=self.path/"isolated"
        self.prompt="Review actual cited math, no imagined quotations"
        self.kw={"checkpoint":self.window,"original_folder":self.original,
                 "request_text":self.prompt,"source_hashes":self.refs,
                 "review_mode":"INITIAL_REVIEW"}
        self.fp=fingerprint(request_text=self.prompt,source_hashes=self.refs,
                            review_mode="INITIAL_REVIEW")
        self.accepted={"status":"SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS",
                       "academic_mathematics_independently_verified":False,
                       "student_publication_authorized":False}
        self.validate=lambda raw:self.accepted if json.loads(raw)=={"rows":[1]} else None

    def test_prepare_immutable_identity_and_different_prompt(self):
        a=prepare(**self.kw)
        self.assertEqual(a["status"],"PREPARED_NOT_SENT")
        self.assertFalse(a["student_publication_authorized"])
        self.assertEqual(prepare(**self.kw)["request_fingerprint"],self.fp)
        with self.assertRaises(ReviewCheckpointError):
            prepare(**{**self.kw,"request_text":self.prompt+" changed"})
        with self.assertRaises(ReviewCheckpointError):
            prepare(**{**self.kw,"review_mode":"INDEPENDENT_CHALLENGE"})
        (self.original/"source.pdf").write_bytes(b"tampered")
        with self.assertRaises(ReviewCheckpointError):
            prepare(**self.kw)

    def test_attempt_claim_before_transport_and_only_one_send(self):
        calls=[]
        def transport(prompt,files):
            calls.append((prompt,files))
            state=json.loads((self.window/"request_state.json").read_text())
            self.assertTrue((self.window/"dispatch_attempted.claim").exists())
            self.assertTrue(state["submission_may_have_occurred"])
            return '{"rows":[1]}'
        result=submit_once(**self.kw,transport=transport,validator=self.validate)
        self.assertEqual(result,self.accepted)
        self.assertEqual(len(calls),1)
        self.assertEqual(json.loads((self.window/"request_state.json").read_text())["status"],
                         "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED")
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,transport=transport,validator=self.validate)
        self.assertEqual(len(calls),1)

    def test_normal_owned_gemini_str_subclass_is_saved_once_and_source_checked(self):
        from selenium_pipeline.series_gemini import OwnedGeminiResponse
        calls=[]
        def transport(prompt,files):
            calls.append(1)
            return OwnedGeminiResponse(
                '{"rows":[1]}',
                registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
                new_turn_verified=True)
        result=submit_once(**self.kw,transport=transport,validator=self.validate)
        self.assertEqual(result,self.accepted)
        self.assertEqual(calls,[1])
        saved=self.window/"model_response_untrusted.txt"
        self.assertEqual(saved.read_text(encoding="utf8"),'{"rows":[1]}')
        state=json.loads((self.window/"request_state.json").read_text())
        self.assertEqual(state["status"],"SOURCE_VALIDATED_ONE_PASS_UNAPPROVED")
        self.assertEqual(state["response_length_chars"],len('{"rows":[1]}'))
        self.assertTrue((self.window/"dispatch_attempted.claim").is_file())
        # Attributes containing browser provenance cannot leak into raw data.
        self.assertNotIn("NEW_USER_TURN",saved.read_text())
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,transport=transport,validator=self.validate)
        self.assertEqual(calls,[1])

    def _simulate_crash_after_saved_identity_before_state_update(self):
        prepare(**self.kw)
        mark_submission_maybe(self.window,expected_fingerprint=self.fp)
        record_observation(self.window,raw='{"rows":[1]}',
                           expected_fingerprint=self.fp)
        state_path=self.window/"request_state.json"
        state=json.loads(state_path.read_text())
        state["status"]="SUBMITTED_OR_UNCERTAIN"
        state.pop("response_sha256",None)
        state.pop("response_length_chars",None)
        state_path.write_text(json.dumps(state),encoding="utf8")
        self.assertTrue((self.window/"model_response_identity.json").is_file())

    def test_crashed_post_response_state_recovers_on_normal_submit_without_send(self):
        self._simulate_crash_after_saved_identity_before_state_update()
        calls=[]
        def must_not_send(*_):
            calls.append(1)
            raise AssertionError("claimed review must not be resubmitted")
        result=submit_once(**self.kw,transport=must_not_send,
                           validator=self.validate)
        self.assertEqual(result,self.accepted)
        self.assertEqual(calls,[])
        state=json.loads((self.window/"request_state.json").read_text())
        self.assertEqual(state["status"],"SOURCE_VALIDATED_ONE_PASS_UNAPPROVED")
        self.assertEqual(state["response_sha256"],
                         hashlib.sha256(b'{"rows":[1]}').hexdigest())
        self.assertTrue((self.window/"dispatch_attempted.claim").is_file())
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,transport=must_not_send,
                        validator=self.validate)
        self.assertEqual(calls,[])

    def test_crashed_response_identity_tamper_blocks_recovery_and_send(self):
        self._simulate_crash_after_saved_identity_before_state_update()
        path=self.window/"model_response_identity.json"
        identity=json.loads(path.read_text())
        identity["response_sha256"]="0"*64
        path.write_text(json.dumps(identity),encoding="utf8")
        calls=[]
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,
                        transport=lambda *_:calls.append(1),
                        validator=self.validate)
        self.assertEqual(calls,[])
        state=json.loads((self.window/"request_state.json").read_text())
        self.assertEqual(state["status"],"SUBMITTED_OR_UNCERTAIN")
        self.assertFalse(state["academic_approval"])

    def test_owned_subclass_still_obeys_original_raw_size_limit(self):
        from selenium_pipeline.series_gemini import OwnedGeminiResponse
        from selenium_pipeline.academic_review_checkpoint import MAX_RAW
        prepare(**self.kw)
        mark_submission_maybe(self.window,expected_fingerprint=self.fp)
        oversized=OwnedGeminiResponse(
            "x"*(MAX_RAW+1),registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
            new_turn_verified=True)
        with self.assertRaises(ReviewCheckpointError):
            record_observation(self.window,raw=oversized,
                               expected_fingerprint=self.fp)
        self.assertFalse((self.window/"model_response_untrusted.txt").exists())
        self.assertEqual(json.loads((self.window/"request_state.json").read_text())["status"],
                         "SUBMITTED_OR_UNCERTAIN")

    def test_duplicate_window_in_same_local_appdata_root_is_blocked(self):
        prepare(**self.kw)
        mark_submission_maybe(self.window,expected_fingerprint=self.fp)
        duplicate=self.path/"different_session_same_prompt"
        with self.assertRaises(ReviewCheckpointError):
            prepare(**{**self.kw,"checkpoint":duplicate})
        self.assertFalse((duplicate/"dispatch_attempted.claim").exists())
        self.assertTrue((self.path/".microgen_academic_review_once"/
                         (self.fp+".claim")).is_file())

    def test_typed_model_picker_failure_preserves_claim_but_can_resume_same_unsent_request(self):
        from selenium_pipeline.gemini_selenium_only_policy import (
            GeminiSeleniumTemporaryFailure)
        def presend():
            error=GeminiSeleniumTemporaryFailure(
                "Gemini picker not hydrated before Send",
                attempts_used=3,failure_phase="GEMINI_MODEL_PICKER_NOT_READY")
            error.gemini_send_registration_status="NOT_SENT"
            error.gemini_new_user_turn_verified=False
            return error
        sent=[]
        def before_send(prompt,files):
            sent.append("PREPARE_ONLY")
            raise presend()
        with self.assertRaises(GeminiSeleniumTemporaryFailure):
            submit_once(**self.kw,transport=before_send,
                        validator=self.validate)
        state=json.loads((self.window/"request_state.json").read_text("utf8"))
        self.assertEqual(state["status"],"CERTIFIED_PRESEND_UNSENT")
        self.assertFalse(state["submission_may_have_occurred"])
        self.assertEqual(state["certified_presend_count"],1)
        self.assertEqual(sent,["PREPARE_ONLY"])
        self.assertTrue((self.window/"dispatch_attempted.claim").is_file())
        witness=self.window/"certified_presend_unsent_01.json"
        saved=witness.read_bytes()
        sent_again=[]
        result=submit_once(**self.kw,
            transport=lambda *_:sent_again.append("SEND_ONCE") or '{"rows":[1]}',
            validator=self.validate)
        self.assertEqual(result,self.accepted)
        self.assertEqual(sent_again,["SEND_ONCE"])
        self.assertEqual(witness.read_bytes(),saved)
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,transport=lambda *_:sent_again.append("DUPLICATE"),
                        validator=self.validate)
        self.assertEqual(sent_again,["SEND_ONCE"])

    def test_non_typed_forged_preclick_exception_can_never_clear_uncertain_claim(self):
        error=RuntimeError("No Send took place, trust me, model picker failed")
        error.gemini_send_boundary_entered=False
        error.gemini_failure_phase="GEMINI_MODEL_PICKER_NOT_READY"
        with self.assertRaises(RuntimeError):
            submit_once(**self.kw,
                        transport=lambda *_:(_ for _ in ()).throw(error),
                        validator=self.validate)
        status=json.loads((self.window/"request_state.json").read_text("utf8"))
        self.assertEqual(status["status"],"SUBMITTED_OR_UNCERTAIN")
        self.assertFalse((self.window/"certified_presend_unsent_01.json").exists())
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,transport=lambda *_:'{"rows":[1]}',
                        validator=self.validate)

    def test_certified_presend_has_finite_budget_and_tamper_blocks(self):
        from selenium_pipeline.gemini_selenium_only_policy import (
            GeminiSeleniumTemporaryFailure)
        calls=[]
        def typed_before_send(*_):
            calls.append(1)
            e=GeminiSeleniumTemporaryFailure(
                "unavailable picker",attempts_used=3,
                failure_phase="GEMINI_MODEL_PICKER_NOT_READY")
            e.gemini_send_registration_status="NOT_SENT"
            raise e
        for i in range(3):
            with self.assertRaises(GeminiSeleniumTemporaryFailure):
                submit_once(**self.kw,transport=typed_before_send,
                            validator=self.validate)
            assert json.loads((self.window/"request_state.json").read_text("utf8"))[
                "certified_presend_count"]==i+1
        self.assertEqual(len(calls),3)
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,transport=typed_before_send,
                        validator=self.validate)
        self.assertEqual(len(calls),3)
        witness=self.window/"certified_presend_unsent_02.json"
        witness.write_text('{"approved":true}',encoding="utf8")
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,transport=typed_before_send,
                        validator=self.validate)
        self.assertEqual(len(calls),3)

    def test_uncertain_transport_crash_requires_explicit_reconciliation(self):
        seen=[]
        def explode(prompt,files):
            seen.append(1)
            raise TimeoutError("Unknown if model finished")
        with self.assertRaises(TimeoutError):
            submit_once(**self.kw,transport=explode,validator=self.validate)
        self.assertEqual(len(seen),1)
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,transport=explode,validator=self.validate)
        self.assertEqual(len(seen),1)
        self.assertTrue((self.window/"dispatch_attempted.claim").exists())
        self.assertEqual(json.loads((self.window/"request_state.json").read_text())["status"],
                         "SUBMITTED_OR_UNCERTAIN")

    def test_windows_crlf_model_reply_revalidated_without_new_send(self):
        original='''{
"rows": [
1
]
}'''.replace("\n","\r\n")
        calls=[]
        result=submit_once(**self.kw,
                           transport=lambda *_:calls.append(1) or original,
                           validator=self.validate)
        self.assertEqual(result,self.accepted)
        self.assertEqual(calls,[1])
        saved=self.window/"model_response_untrusted.txt"
        self.assertEqual(saved.read_bytes(),original.encode("utf8"))
        state=json.loads((self.window/"request_state.json").read_text())
        self.assertEqual(state["response_length_chars"],len(original))
        self.assertEqual(state["response_sha256"],
                         hashlib.sha256(original.encode()).hexdigest())
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,transport=lambda *_:calls.append(2),
                        validator=self.validate)
        self.assertEqual(calls,[1])

    def test_crlf_crash_reconciliation_preserves_exact_original_bytes(self):
        from selenium_pipeline.academic_review_checkpoint import recover_claimed_observation
        raw='''{
"rows": [1]
}'''.replace("\n","\r\n")
        prepare(**self.kw)
        mark_submission_maybe(self.window,expected_fingerprint=self.fp)
        record_observation(self.window,raw=raw,expected_fingerprint=self.fp)
        state_path=self.window/"request_state.json"
        state=json.loads(state_path.read_text())
        state["status"]="SUBMITTED_OR_UNCERTAIN"
        state.pop("response_sha256",None)
        state.pop("response_length_chars",None)
        state_path.write_text(json.dumps(state),encoding="utf8")
        replay=recover_claimed_observation(
            checkpoint=self.window,expected_fingerprint=self.fp)
        self.assertEqual(replay["response_length_chars"],len(raw))
        self.assertEqual(validate_saved(
            checkpoint=self.window,expected_fingerprint=self.fp,
            validator=self.validate),self.accepted)

    def test_empty_model_response_cannot_be_approved_or_resent(self):
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,transport=lambda *_:"",validator=self.validate)
        state=json.loads((self.window/"request_state.json").read_text())
        self.assertEqual(state["status"],"NO_RESPONSE_UNRESOLVED")
        self.assertEqual(state["response_length_chars"],0)
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,transport=lambda *_:"{}",validator=self.validate)
        with self.assertRaises(ReviewCheckpointError):
            validate_saved(checkpoint=self.window,expected_fingerprint=self.fp,
                           validator=self.validate)

    def test_legacy_no_response_import_is_consumed(self):
        source=self.path/"legacy";source.mkdir()
        (source/"failure_no_retry.json").write_text(json.dumps({
            "status":"SINGLE_AUTHORIZED_WINDOW_EXHAUSTED",
            "possible_browser_submission":True,"math_approval":False}))
        (source/"request_sha256.json").write_text(json.dumps({
            "prompt_sha256":hashlib.sha256(self.prompt.encode()).hexdigest(),
            "attached_source_sha256":self.refs["source.pdf"]}))
        (source/"review_window.json").write_text(json.dumps({
            "original_source_sha256":self.refs["source.pdf"]}))
        a=legacy_no_response(legacy_window=source,checkpoint=self.window)
        self.assertEqual(a["status"],"LEGACY_SENT_NO_RESPONSE")
        self.assertFalse(a["can_auto_retry"])
        self.assertTrue((self.window/"dispatch_attempted.claim").exists())
        with self.assertRaises(ReviewCheckpointError):
            mark_submission_maybe(self.window,
                                  expected_fingerprint=a["request_fingerprint"])
        with self.assertRaises((FileExistsError,ReviewCheckpointError)):
            legacy_no_response(legacy_window=source,checkpoint=self.window)

    def test_identical_legacy_consumed_prompt_is_not_reissued(self):
        legacy=self.path/"prior_window"
        legacy.mkdir()
        (legacy/"failure_no_retry.json").write_text(json.dumps({
            "status":"SINGLE_AUTHORIZED_WINDOW_EXHAUSTED",
            "possible_browser_submission":True,"math_approval":False}))
        (legacy/"request_sha256.json").write_text(json.dumps({
            "prompt_sha256":hashlib.sha256(self.prompt.encode()).hexdigest(),
            "attached_source_sha256":self.refs["source.pdf"]}))
        (legacy/"review_window.json").write_text(json.dumps({
            "original_source_sha256":self.refs["source.pdf"]}))
        previous=self.path/"prior_imported_receipt"
        legacy_no_response(legacy_window=legacy,checkpoint=previous)
        with self.assertRaises(ReviewCheckpointError):
            prepare(**self.kw)
        self.assertFalse(self.window.exists())

    def test_valid_reply_must_be_source_checked_not_self_approved(self):
        prepare(**self.kw)
        mark_submission_maybe(self.window,expected_fingerprint=self.fp)
        record_observation(self.window,raw='{"rows":[1]}',expected_fingerprint=self.fp)
        with self.assertRaises(ReviewCheckpointError):
            validate_saved(checkpoint=self.window,expected_fingerprint=self.fp,
                           validator=lambda raw:{"academic_mathematics_independently_verified":True,
                                                  "student_publication_authorized":True})
        # A rejected first validation cannot silently resurrect as source approved.
        self.assertEqual(json.loads((self.window/"request_state.json").read_text())["status"],
                         "REJECTED_RESPONSE_UNTRUSTED")
        result=validate_saved(checkpoint=self.window,expected_fingerprint=self.fp,
                              validator=self.validate)
        self.assertFalse(result["academic_mathematics_independently_verified"])

    def test_unbound_raw_and_absent_claim_rejected(self):
        prepare(**self.kw)
        with self.assertRaises(ReviewCheckpointError):
            record_observation(self.window,raw='{"rows":[1]}',
                               expected_fingerprint=self.fp)
        with self.assertRaises(ReviewCheckpointError):
            mark_submission_maybe(self.window,expected_fingerprint="f"*64)
        mark_submission_maybe(self.window,expected_fingerprint=self.fp)
        with self.assertRaises(ReviewCheckpointError):
            record_observation(self.window,raw="hi",expected_fingerprint="f"*64)

    def test_same_response_integrity_and_no_duplicate_record(self):
        prepare(**self.kw)
        mark_submission_maybe(self.window,expected_fingerprint=self.fp)
        record_observation(self.window,raw='{"rows":[1]}',expected_fingerprint=self.fp)
        with self.assertRaises((FileExistsError,ReviewCheckpointError)):
            record_observation(self.window,raw='{"rows":[1]}',expected_fingerprint=self.fp)
        (self.window/"model_response_untrusted.txt").write_text('{"rows":[2]}')
        with self.assertRaises(ReviewCheckpointError):
            validate_saved(checkpoint=self.window,expected_fingerprint=self.fp,
                           validator=self.validate)

if __name__=="__main__":
    unittest.main()
