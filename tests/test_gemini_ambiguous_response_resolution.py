import tempfile,unittest
from pathlib import Path
from selenium_pipeline import gemini_review_backoff_checkpoint as b
from selenium_pipeline.gemini_ambiguous_response_resolution import assess_unresolved_owned_reply
from test_gemini_review_backoff_checkpoint import make_paths
class Reconciliation(unittest.TestCase):
 def setup(self,d):
  f,cp=make_paths(d);b.initialize(checkpoint=cp,original_folder=f,job_id="slide_diag",now=0)
  token=b.claim_due(checkpoint=cp,original_folder=f,now=0)
  b.submitted(checkpoint=cp,original_folder=f,claim=token,user_turn_created=True,composer_cleared=True)
  b.ambiguous(checkpoint=cp,original_folder=f,claim=token)
  return f,cp
 def test_no_resume_without_identical_owned_browser_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   f,cp=self.setup(d);p=Path(d)/"reply.json";p.write_text('{"candidate":"text"}')
   s=assess_unresolved_owned_reply(checkpoint=cp,original_folder=f,receipt=p,
                                  owned_session_proven=False,completed_in_owned_tab=True)
   self.assertEqual(s["status"],"UNKNOWN_OUTCOME_RECONCILIATION_REQUIRED")
 def test_owned_complete_json_still_needs_math_validation(self):
  with tempfile.TemporaryDirectory() as d:
   f,cp=self.setup(d);p=Path(d)/"reply.json";p.write_text('{"candidate":"text"}')
   s=assess_unresolved_owned_reply(checkpoint=cp,original_folder=f,receipt=p,
                                  owned_session_proven=True,completed_in_owned_tab=True)
   self.assertFalse(s["mathematically_verified"])
   self.assertFalse(s["auto_retry_authorized"])
 def test_bad_json_does_not_claim_completion(self):
  with tempfile.TemporaryDirectory() as d:
   f,cp=self.setup(d);p=Path(d)/"reply.json";p.write_text("{")
   s=assess_unresolved_owned_reply(checkpoint=cp,original_folder=f,receipt=p,
                                  owned_session_proven=True,completed_in_owned_tab=True)
   self.assertEqual(s["status"],"INCOMPLETE_UNTRUSTED_REPLY")
