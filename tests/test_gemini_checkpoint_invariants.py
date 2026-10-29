import json,tempfile,unittest
from selenium_pipeline import gemini_review_backoff_checkpoint as b
from test_gemini_review_backoff_checkpoint import make_paths
class StateInvariants(unittest.TestCase):
 def test_spoofed_ready_with_active_claim_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   src,cp=make_paths(d);b.initialize(checkpoint=cp,original_folder=src,job_id="slide_diag")
   j=json.loads(cp.read_text());j["active_claim"]="a"*32;cp.write_text(json.dumps(j))
   with self.assertRaises(ValueError):b.claim_due(checkpoint=cp,original_folder=src)
 def test_fake_scheduled_inflight_and_forged_history_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   src,cp=make_paths(d);b.initialize(checkpoint=cp,original_folder=src,job_id="slide_diag")
   token=b.claim_due(checkpoint=cp,original_folder=src,now=100000000000)
   self.assertIsNotNone(token)
   j=json.loads(cp.read_text());j["next_due_unix_utc"]=1;cp.write_text(json.dumps(j))
   with self.assertRaises(ValueError):b.inspect(checkpoint=cp,original_folder=src)
 def test_source_bound_normal_progress_remains_valid(self):
  with tempfile.TemporaryDirectory() as d:
   src,cp=make_paths(d);b.initialize(checkpoint=cp,original_folder=src,job_id="slide_diag",now=100)
   token=b.claim_due(checkpoint=cp,original_folder=src,now=100)
   b.submitted(checkpoint=cp,original_folder=src,claim=token,user_turn_created=True,composer_cleared=True)
   x=b.inspect(checkpoint=cp,original_folder=src)
   self.assertEqual(x["status"],"IN_FLIGHT")
