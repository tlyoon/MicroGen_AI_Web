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

    def test_duplicate_window_in_same_local_appdata_root_is_blocked(self):
        prepare(**self.kw)
        mark_submission_maybe(self.window,expected_fingerprint=self.fp)
        duplicate=self.path/"different_session_same_prompt"
        prepare(**{**self.kw,"checkpoint":duplicate})
        with self.assertRaises(FileExistsError):
            mark_submission_maybe(duplicate,expected_fingerprint=self.fp)
        self.assertFalse((duplicate/"dispatch_attempted.claim").exists())
        self.assertTrue((self.path/".microgen_academic_review_once"/
                         (self.fp+".claim")).is_file())

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
