"""One authorized original academic source challenge, never instant approval."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.scoped_original_math_review_capture import (
    capture_one_scoped_source_challenge)
from selenium_pipeline.scoped_original_math_review_window import (
    create_window, inspect_window)
from test_scoped_original_math_review_window import original_fixture, CONSENT


def setup_scope(folder, *, healthy=True):
    original,q=original_fixture(folder)
    w=Path(folder)/"newwindow"
    create_window(original_folder=original,queue_root=q,window_root=w,
                  approval_reference=CONSENT,now=1000)
    if healthy:
        response=w/"source_transport_health.response.json"
        response.write_text('{"probe":"microgen_source_transport_ok"}')
        (w/"source_transport_health.json").write_text(json.dumps({
            "status":"COMPLETE_STRUCTURED_TEXT_ONLY_RESPONSE",
            "same_owned_gemini_session":True,
            "model_stopped_generating":True,
            "exact_expected_json":True,
            "prompt_characters":1400,
            "completed_unix_utc":990,
            "verified_response_sha256":hashlib.sha256(response.read_bytes()).hexdigest(),
        }))
    return original,q,w


def reviewed():
    return {
        "status":"SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS",
        "mode":"INDEPENDENT_CHALLENGE",
        "rows":[{"utterance_id":"S001E01","verdict":"UNRESOLVED",
                 "math_explanation":"Missing independent diagram witness in original book."}],
        "review_count":1,
        "academic_mathematics_independently_verified":False,
        "student_publication_authorized":False,
    }


class RealWindowCapture(unittest.TestCase):
    def test_missing_verified_transport_cannot_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            _,_,w=setup_scope(d,healthy=False)
            got=capture_one_scoped_source_challenge(window_root=w,now=1000)
            self.assertFalse(got["model_request_sent"])
            self.assertFalse((w/"slide_001_newwindow_independent_challenge_captured.json").exists())

    def test_verified_original_source_review_is_captured_without_math_approval(self):
        with tempfile.TemporaryDirectory() as d:
            original,q,w=setup_scope(d)
            before={p.name:p.read_bytes() for p in q.iterdir()}
            calls=[]
            with (
                patch("selenium_pipeline.scoped_original_math_review_capture._check_queue",
                      return_value={"utterance_count":1}),
                patch("selenium_pipeline.scoped_original_math_review_capture.build_review_job",
                      return_value={"utterance_count":1}),
                patch("selenium_pipeline.scoped_original_math_review_capture."
                      "_independently_check_saved_pass",return_value=[]),
                patch("selenium_pipeline.scoped_original_math_review_capture.run_web_review",
                      side_effect=lambda **kw:(calls.append(1),reviewed())[1]),
            ):
                done=capture_one_scoped_source_challenge(window_root=w,now=1000)
            self.assertEqual(done["status"],"RESPONSE_CAPTURED_UNVERIFIED")
            self.assertTrue(done["model_request_sent"])
            self.assertEqual(calls,[1])
            self.assertFalse(done["independent_mathematics_agreed"])
            self.assertEqual(inspect_window(window_root=w,now=1000)
                             ["new_window_confirmed_submissions"],1)
            self.assertFalse(inspect_window(window_root=w,now=1000)
                             ["eligible_for_single_authorized_dispatch"])
            self.assertEqual(
                json.loads((w/"slide_001_newwindow_independent_challenge_captured.json")
                           .read_text())["status"],
                "SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS")
            self.assertEqual(before,{p.name:p.read_bytes() for p in q.iterdir()})

    def test_failure_before_response_cannot_be_retried_blindly(self):
        with tempfile.TemporaryDirectory() as d:
            _,_,w=setup_scope(d)
            with (
                patch("selenium_pipeline.scoped_original_math_review_capture._check_queue",
                      return_value={"utterance_count":1}),
                patch("selenium_pipeline.scoped_original_math_review_capture.build_review_job",
                      return_value={"utterance_count":1}),
                patch("selenium_pipeline.scoped_original_math_review_capture.run_web_review",
                      side_effect=RuntimeError("uncertain provider after Send")),
            ):
                result=capture_one_scoped_source_challenge(window_root=w,now=1000)
            self.assertEqual(result["status"],"AMBIGUOUS_TRANSPORT_EXCEPTION")
            self.assertFalse(inspect_window(window_root=w,now=1000)
                             ["eligible_for_single_authorized_dispatch"])
            self.assertTrue(inspect_window(window_root=w,now=1000)
                            ["requires_reconciliation"])

    def test_old_original_history_drift_refuses_new_review(self):
        with tempfile.TemporaryDirectory() as d:
            _,q,w=setup_scope(d)
            (q/"slide_001_independent_challenge_attempt_03.json").write_text(
                '{"forged":true}')
            with self.assertRaises(ValueError):
                capture_one_scoped_source_challenge(window_root=w,now=1000)


if __name__=="__main__":
    unittest.main()
