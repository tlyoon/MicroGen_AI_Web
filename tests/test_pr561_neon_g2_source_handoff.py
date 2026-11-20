"""Source-bearing original G2 Neon/High receipt is immutable and not a Pro replay."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from selenium_pipeline.academic_review_checkpoint import (
    ReviewCheckpointError,submit_once,_load,
    NEON_MODEL_WITNESS_NAME,record_observation,fingerprint,
    prepare,mark_submission_maybe,validate_saved,recover_claimed_observation,
)
from selenium_pipeline.series_gemini import OwnedGeminiResponse

REG="NEW_USER_TURN_AND_COMPOSER_CLEARED"


class NeonOriginalSourceWitnessTests(TestCase):
    def setUp(self):
        t=TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.home=Path(t.name)
        self.src=self.home/"protected_source";self.src.mkdir()
        self.hashes={}
        for name,content in {
            "source.pdf":b"%PDF-1.4 science source",
            "slides.pdf":b"%PDF-1.4 parsed slides",
            "script.txt":b"**Slide 1 [1s]: science line",
        }.items():
            (self.src/name).write_bytes(content)
            self.hashes[name]=hashlib.sha256(content).hexdigest()
        self.slot=self.home/"claimed_slide_012_initial_review"
        self.kw={
            "checkpoint":self.slot,"original_folder":self.src,
            "request_text":"cite actual Serway scientific source",
            "source_hashes":self.hashes,"review_mode":"INITIAL_REVIEW",
        }
        self.fp=fingerprint(
            request_text=self.kw["request_text"],
            source_hashes=self.hashes,review_mode="INITIAL_REVIEW")
        self.validation={
            "status":"SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS",
            "academic_mathematics_independently_verified":False,
            "student_publication_authorized":False,
        }
        self.validate=lambda raw:(self.validation
               if json.loads(raw)=={"rows":[1]} else None)

    def response(self, model="neon",effort="high", registered=True):
        return OwnedGeminiResponse(
            '{"rows":[1]}',registration_status=REG,
            new_turn_verified=registered,
            verified_model_family=model,verified_thinking_level=effort)

    def test_one_verified_neon_high_source_reply_is_only_one_pass(self):
        calls=[]
        def one_send(*_):
            calls.append("one")
            self.assertTrue((self.slot/"dispatch_attempted.claim").is_file())
            return self.response()
        actual=submit_once(**self.kw,transport=one_send,
                           validator=self.validate,
                           required_model_family="neon")
        self.assertEqual(actual,self.validation)
        self.assertEqual(calls,["one"])
        witness=json.loads((self.slot/NEON_MODEL_WITNESS_NAME).read_text())
        self.assertEqual(witness["selected_model_family"],"neon")
        self.assertEqual(witness["checked_thinking_level"],"high")
        self.assertEqual(witness["request_fingerprint"],self.fp)
        self.assertFalse(witness["academic_approval"])
        self.assertEqual(_load(self.slot)["status"],
                         "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED")
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,transport=one_send,
                        validator=self.validate,required_model_family="neon")
        self.assertEqual(calls,["one"])

    def test_wrong_model_no_source_promotion_and_no_resend(self):
        for family,effort in (("pro","high"),("neon","medium")):
            with self.subTest(family=family,effort=effort):
                # New request fingerprint and protected original per case.
                t=TemporaryDirectory();self.addCleanup(t.cleanup)
                slot=Path(t.name)/"claimed"
                calls=[]
                def wrong(*_):
                    calls.append(1)
                    return self.response(model=family,effort=effort)
                with self.assertRaises(ReviewCheckpointError):
                    submit_once(**{**self.kw,"checkpoint":slot},
                                transport=wrong,validator=self.validate,
                                required_model_family="neon")
                self.assertEqual(calls,[1])
                self.assertEqual(_load(slot)["status"],"SUBMITTED_OR_UNCERTAIN")
                self.assertFalse((slot/"model_response_untrusted.txt").exists())
                self.assertFalse((slot/NEON_MODEL_WITNESS_NAME).exists())
                with self.assertRaises(ReviewCheckpointError):
                    submit_once(**{**self.kw,"checkpoint":slot},
                                transport=wrong,validator=self.validate,
                                required_model_family="neon")
                self.assertEqual(calls,[1])

    def test_raw_text_without_owned_new_turn_cannot_pass_source_gate(self):
        calls=[]
        def unowned(*_):
            calls.append(1);return '{"rows":[1]}'
        with self.assertRaises(ReviewCheckpointError):
            submit_once(**self.kw,transport=unowned,
                        validator=self.validate,required_model_family="neon")
        self.assertEqual(_load(self.slot)["status"],"SUBMITTED_OR_UNCERTAIN")
        self.assertEqual(calls,[1])
        self.assertFalse((self.slot/"model_response_untrusted.txt").exists())

    def test_response_witness_tamper_cannot_be_revalidated(self):
        submit_once(**self.kw,transport=lambda *_:self.response(),
                    validator=self.validate,required_model_family="neon")
        witness_path=self.slot/NEON_MODEL_WITNESS_NAME
        witness=json.loads(witness_path.read_text())
        witness["checked_thinking_level"]="medium"
        witness_path.write_text(json.dumps(witness))
        with self.assertRaises(ReviewCheckpointError):
            validate_saved(checkpoint=self.slot,
                           expected_fingerprint=self.fp,
                           validator=self.validate,required_model_family="neon")

    def test_source_reply_modified_after_witness_cannot_be_revalidated(self):
        submit_once(**self.kw,transport=lambda *_:self.response(),
                    validator=self.validate,required_model_family="neon")
        witness_path=self.slot/NEON_MODEL_WITNESS_NAME
        witness=json.loads(witness_path.read_text())
        witness["response_sha256"]="0"*64
        witness_path.write_text(json.dumps(witness))
        with self.assertRaises(ReviewCheckpointError):
            validate_saved(checkpoint=self.slot,
                           expected_fingerprint=self.fp,
                           validator=self.validate,required_model_family="neon")

    def test_crash_after_model_response_before_status_never_resends(self):
        submit_once(**self.kw,transport=lambda *_:self.response(),
                    validator=self.validate,required_model_family="neon")
        original=(self.slot/NEON_MODEL_WITNESS_NAME).read_bytes()
        state_path=self.slot/"request_state.json"
        state=json.loads(state_path.read_text())
        state["status"]="SUBMITTED_OR_UNCERTAIN"
        state.pop("response_sha256",None)
        state.pop("response_length_chars",None)
        state_path.write_text(json.dumps(state))
        calls=[]
        result=submit_once(**self.kw,
                           transport=lambda *_:calls.append(1),
                           validator=self.validate,
                           required_model_family="neon")
        self.assertEqual(result,self.validation)
        self.assertEqual(calls,[])
        self.assertEqual((self.slot/NEON_MODEL_WITNESS_NAME).read_bytes(),original)

    def test_ambient_flash_cannot_override_source_qualified_neon_high(self):
        import os
        from unittest.mock import patch
        from selenium_pipeline.ai_academic_web_review import _academic_browser_request
        with patch.dict(os.environ,{
                "MICROGEN_GEMINI_UI_MODE":"flash",
                "MICROGEN_GEMINI_THINKING_LEVEL":"medium",
                "MICROGEN_ACTIVE_GENERATION_STAGE":"figures"},clear=False):
            observed=[]
            def model_call(*args,**kwargs):
                observed.append((os.getenv("MICROGEN_GEMINI_UI_MODE"),
                                 os.getenv("MICROGEN_GEMINI_THINKING_LEVEL")))
                return "ONLY_DIAGNOSTIC_TRANSPORT"
            with patch("selenium_pipeline.ai_academic_web_review._browser_request",
                       side_effect=model_call) as send:
                result=_academic_browser_request(
                    "source-specific review",[self.src/"source.pdf"],
                    chrome_port=9222,wait_cap_s=90,
                    required_runtime_family="neon")
                self.assertEqual(result,"ONLY_DIAGNOSTIC_TRANSPORT")
                self.assertEqual(send.call_args.kwargs["expected_runtime_family"],
                                 "neon")
                self.assertEqual(send.call_args.kwargs["expected_thinking_level"],
                                 "high")
                self.assertEqual(send.call_args.kwargs["port"],9222)
                self.assertEqual(observed,[("pro","high")])
                self.assertEqual(os.getenv("MICROGEN_GEMINI_UI_MODE"),"flash")
                self.assertEqual(os.getenv("MICROGEN_GEMINI_THINKING_LEVEL"),"medium")
            self.assertEqual(os.getenv("MICROGEN_GEMINI_UI_MODE"),"flash")
            self.assertEqual(os.getenv("MICROGEN_GEMINI_THINKING_LEVEL"),"medium")

    def test_historical_pro_response_no_new_witness_required(self):
        result=submit_once(**self.kw,
                           transport=lambda *_:'{"rows":[1]}',
                           validator=self.validate)
        self.assertEqual(result,self.validation)
        self.assertFalse((self.slot/NEON_MODEL_WITNESS_NAME).exists())
        with self.assertRaises(ReviewCheckpointError):
            validate_saved(checkpoint=self.slot,
                           expected_fingerprint=self.fp,validator=self.validate,
                           required_model_family="neon")


if __name__=="__main__":
    import unittest
    unittest.main()
