"""Cross-pass approved-original math consensus never forges human approval."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.scoped_original_math_consensus import (
    reconcile_approved_original_math_window)
from selenium_pipeline.scoped_original_math_review_window import create_window
from selenium_pipeline.gemini_review_backoff_checkpoint import (
    claim_due,submitted,captured_unreviewed)
from test_scoped_original_math_review_window import original_fixture,CONSENT


def setup_case(folder):
    f,q=original_fixture(folder)
    w=Path(folder)/"window"
    create_window(original_folder=f,queue_root=q,window_root=w,
                  approval_reference=CONSENT,now=1000)
    saved=w/"slide_001_newwindow_independent_challenge_captured.json"
    saved.write_text(json.dumps({"status":"SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS",
        "mode":"INDEPENDENT_CHALLENGE","review_count":1,
        "student_publication_authorized":False}))
    cp=w/"separate_window_checkpoint.json"
    token=claim_due(checkpoint=cp,original_folder=f,now=1000)
    submitted(checkpoint=cp,original_folder=f,claim=token,
              user_turn_created=True,composer_cleared=True,now=1000)
    captured_unreviewed(checkpoint=cp,original_folder=f,claim=token,
                        response_receipt=saved,now=1000)
    return f,q,w,saved


def rows(explanation="An independently explained source witness with a distinct mathematical rationale.",
         target="s001.text.001",page=1):
    return [{
        "utterance_id":"s001.utterance.001",
        "spoken_sha256":"a"*64,
        "target_id":target,
        "source_page":page,
        "verdict":"SUPPORTED",
        "exact_textbook_quote_verified":True,
        "text_target_pdf_bbox_pt":[1.,2.,3.,4.],
        "math_explanation":explanation,
    }]


def fake_job():
    return {"slides":[{"utterances":[{
        "id":"s001.utterance.001","spoken_sha256":"a"*64}]}]}


def baseline(accepted=None):
    return {"original_utterances":1,"accepted_ai_evidence":accepted or []}


def execute_mocked(w,*,second=None,original_base=None):
    first=rows("The original textbook section heading matches this slide exactly.")
    next_pass=second if second is not None else rows()
    with (
        patch("selenium_pipeline.scoped_original_math_consensus.build_review_job",
              return_value=fake_job()),
        patch("selenium_pipeline.scoped_original_math_consensus."
              "_independently_check_saved_pass",side_effect=[first,next_pass]),
        patch("selenium_pipeline.scoped_original_math_consensus."
              "reconcile_actual_review_queue",return_value=original_base or baseline()),
    ):
        return reconcile_approved_original_math_window(window_root=w)


class OriginalMathConsensus(unittest.TestCase):
    def test_two_independent_source_witnesses_count_one_but_no_publish(self):
        with tempfile.TemporaryDirectory() as d:
            _,q,w,_=setup_case(d)
            before={p.name:p.read_bytes() for p in q.iterdir()}
            report=execute_mocked(w)
            self.assertEqual(report["combined_independent_source_witnessed_ai_agreements"],1)
            self.assertEqual(report["combined_math_pending_or_disputed"],0)
            self.assertFalse(report["AI_consensus_is_formal_mathematical_proof"])
            self.assertFalse(report["genuine_Kore_TTS_authorized"])
            self.assertFalse(report["student_publication_authorized"])
            self.assertEqual(before,{p.name:p.read_bytes() for p in q.iterdir()})

    def test_missing_captured_source_review_refused(self):
        with tempfile.TemporaryDirectory() as d:
            f,q=original_fixture(d)
            w=Path(d)/"window"
            create_window(original_folder=f,queue_root=q,window_root=w,
                          approval_reference=CONSENT,now=1000)
            with self.assertRaises(ValueError):
                execute_mocked(w)

    def test_tampered_external_response_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            _,_,w,saved=setup_case(d)
            saved.write_text(saved.read_text()+" altered")
            with self.assertRaises(ValueError):
                execute_mocked(w)

    def test_identical_reasoning_does_not_prove_independence(self):
        with tempfile.TemporaryDirectory() as d:
            _,_,w,_=setup_case(d)
            same=rows("The original textbook section heading matches this slide exactly.")
            report=execute_mocked(w,second=same)
            self.assertEqual(report["combined_independent_source_witnessed_ai_agreements"],0)
            self.assertEqual(report["combined_math_pending_or_disputed"],1)

    def test_mismatched_target_or_physical_page_remains_unresolved(self):
        with tempfile.TemporaryDirectory() as d:
            _,_,w,_=setup_case(d)
            report=execute_mocked(w,second=rows(target="s001.other"))
            self.assertEqual(report["approved_separate_window_ai_agreements"],0)
            report=execute_mocked(w,second=rows(page=2))
            self.assertEqual(report["approved_separate_window_ai_agreements"],0)

    def test_existing_queue_agreement_cannot_be_double_counted(self):
        with tempfile.TemporaryDirectory() as d:
            _,_,w,_=setup_case(d)
            with self.assertRaises(ValueError):
                execute_mocked(w,original_base=baseline([
                    {"utterance_id":"s001.utterance.001"}]))

    def test_drift_to_original_source_blocks_all_approval(self):
        with tempfile.TemporaryDirectory() as d:
            f,_,w,_=setup_case(d)
            (f/"source.pdf").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                execute_mocked(w)


if __name__=="__main__":
    unittest.main()
