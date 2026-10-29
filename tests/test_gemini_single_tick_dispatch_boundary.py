import tempfile,unittest
from pathlib import Path
from selenium_pipeline.gemini_single_tick_dispatch_boundary import one_authorized_tick
from selenium_pipeline import gemini_review_backoff_checkpoint as b
from test_gemini_review_backoff_checkpoint import make_paths
class SingleTick(unittest.TestCase):
 def setup(self,d):
  f,cp=make_paths(d);b.initialize(checkpoint=cp,original_folder=f,job_id="slide_diag",now=10)
  return f,cp
 def test_one_confirmed_send_and_no_second_due_send(self):
  with tempfile.TemporaryDirectory() as d:
   f,cp=self.setup(d);count=[]
   def send():
    count.append(1);return {"outcome":"CONFIRMED_SUBMITTED",
       "user_turn_created":True,"composer_cleared":True}
   a=one_authorized_tick(checkpoint=cp,original_folder=f,send_once=send,now=10)
   self.assertEqual(a["status"],"IN_FLIGHT")
   one_authorized_tick(checkpoint=cp,original_folder=f,send_once=send,now=10)
   self.assertEqual(len(count),1)
 def test_transport_timeout_never_triggers_resubmission(self):
  with tempfile.TemporaryDirectory() as d:
   f,cp=self.setup(d)
   x=one_authorized_tick(checkpoint=cp,original_folder=f,
       send_once=lambda:1/0,now=10)
   self.assertEqual(x["status"],"AMBIGUOUS_TRANSPORT_EXCEPTION")
   self.assertEqual(b.inspect(checkpoint=cp,original_folder=f)["status"],"RECONCILIATION_REQUIRED")
 def test_proven_unsent_counts_separately(self):
  with tempfile.TemporaryDirectory() as d:
   f,cp=self.setup(d)
   x=one_authorized_tick(checkpoint=cp,original_folder=f,
       send_once=lambda:{"outcome":"VERIFIED_UNSENT",
              "user_turn_created":False,"composer_cleared":False},now=10)
   self.assertEqual(x["status"],"WAITING")
   self.assertEqual(b.inspect(checkpoint=cp,original_folder=f)["confirmed_submissions"],0)
