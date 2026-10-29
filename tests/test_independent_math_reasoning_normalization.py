import unittest,tempfile,json
from pathlib import Path
from selenium_pipeline.ai_academic_review_consensus import (
    _canonical_academic_rationale,reconcile_actual_review_queue)
from selenium_pipeline.ai_academic_web_review import validate_model_review
from test_ai_academic_review_consensus import IndependentReconciliation
class DistinctReasoning(unittest.TestCase):
 def test_formatting_is_not_independent_explanation(self):
    self.assertEqual(_canonical_academic_rationale("Integral OF    X"),
                     _canonical_academic_rationale(" integral  of x  "))
 def test_reworded_case_only_math_does_not_create_false_agreement(self):
    with tempfile.TemporaryDirectory() as t:
        f,q,j,response=IndependentReconciliation().setup(t)
        prev=json.loads((q/"slide_001_initial_review.json").read_text())
        reason=prev["rows"][0]["math_explanation"]
        response["rows"][0]["math_explanation"]="   "+reason.upper().replace(" ","   ")+"   "
        response["rows"][0]["spoken_sha256"]=j["slides"][0]["utterances"][0]["spoken_sha256"]
        response["rows"][0]["target_id"]=j["slides"][0]["visual_targets"][0]["id"]
        second=validate_model_review(folder=f,job=j,response=response,mode="INDEPENDENT_CHALLENGE")
        (q/"slide_001_independent_challenge.json").write_text(json.dumps(second))
        audit=reconcile_actual_review_queue(queue_root=q,folder=f)
        self.assertEqual(audit["agreed_source_witnessed_segments"],0)
        self.assertEqual(audit["pending_or_disputed"],1)
