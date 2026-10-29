import unittest,tempfile
from pathlib import Path
from selenium_pipeline.ai_dual_review_geometry import reconcile_dual_ai_reviews
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_original_packet_evidence_audit import fixture
from test_ai_academic_web_review import job,response
from selenium_pipeline.ai_academic_web_review import validate_model_review
class DualReview(unittest.TestCase):
    def test_independent_ai_reviews_agree_but_not_claim_formal_proof(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/"source";j=job(f)
            a=validate_model_review(folder=f,job=j,response=response(),mode="INITIAL_REVIEW")
            b_obj=response()
            b_obj["rows"][0]["math_explanation"]="This separately assessed source expression has a consistent original visible definition."
            b=validate_model_review(folder=f,job=j,response=b_obj,mode="INDEPENDENT_CHALLENGE")
            r=reconcile_dual_ai_reviews(folder=f,job=j,initial=a,challenge=b,
                                        distinct_review_sessions=True)
            self.assertEqual(r["ai_two_pass_agreement_count"],1)
            self.assertFalse(r["ai_consensus_is_formal_proof"])
    def test_reused_review_or_no_separate_session_cannot_approve(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/"source";j=job(f)
            a=validate_model_review(folder=f,job=j,response=response(),mode="INITIAL_REVIEW")
            b=validate_model_review(folder=f,job=j,response=response(),mode="INDEPENDENT_CHALLENGE")
            r=reconcile_dual_ai_reviews(folder=f,job=j,initial=a,challenge=b,
                                        distinct_review_sessions=True)
            self.assertEqual(r["unresolved_or_disputed_count"],1)
            with self.assertRaises(FigureIdentityReviewRequired):
                reconcile_dual_ai_reviews(folder=f,job=j,initial=a,challenge=b,
                                          distinct_review_sessions=False)
