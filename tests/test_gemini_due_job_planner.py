import tempfile,unittest
from pathlib import Path
from selenium_pipeline.gemini_due_job_planner import plan_due_retry_jobs
from selenium_pipeline import gemini_review_backoff_checkpoint as b
from test_gemini_review_backoff_checkpoint import make_paths
class DuePlanner(unittest.TestCase):
 def test_selects_one_due_job_without_claiming(self):
  with tempfile.TemporaryDirectory() as d:
   f,cp=make_paths(d);b.initialize(checkpoint=cp,original_folder=f,job_id="slide_diagnostic",now=10)
   out=plan_due_retry_jobs(items=[(cp,f)],now=10)
   self.assertEqual(out["ready_count"],1)
   self.assertFalse(out["model_request_sent"])
   self.assertEqual(b.inspect(checkpoint=cp,original_folder=f)["status"],"READY")
 def test_no_due_job_before_cooldown(self):
  with tempfile.TemporaryDirectory() as d:
   f,cp=make_paths(d);b.initialize(checkpoint=cp,original_folder=f,job_id="slide_diagnostic",now=100)
   self.assertEqual(plan_due_retry_jobs(items=[(cp,f)],now=90)["ready_count"],0)
 def test_duplicate_job_or_more_than_one_send_per_tick_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   f,cp=make_paths(d);b.initialize(checkpoint=cp,original_folder=f,job_id="slide_diagnostic")
   with self.assertRaises(ValueError):plan_due_retry_jobs(items=[(cp,f),(cp,f)],now=1e10)
   with self.assertRaises(ValueError):plan_due_retry_jobs(items=[(cp,f)],now=1e10,budget=2)
