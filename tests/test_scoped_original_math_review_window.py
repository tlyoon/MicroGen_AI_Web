import hashlib,json,tempfile,unittest
from pathlib import Path
from selenium_pipeline.scoped_original_math_review_window import (
    create_window,inspect_window,historical_evidence,
    dispatch_single_approved_window_tick)

CONSENT="USER_APPROVED_NEW_ORIGINAL_REVIEW_20261023_proceed"

def original_fixture(root):
    root=Path(root);original=root/"original";original.mkdir()
    for name in ("source.pdf","slides.pdf","script.txt"):
        (original/name).write_bytes(("immutable-"+name).encode())
    q=root/"queue";q.mkdir()
    hashes={name:hashlib.sha256((original/name).read_bytes()).hexdigest()
            for name in ("source.pdf","slides.pdf","script.txt")}
    (q/"queue.json").write_text(json.dumps({
       "status":"IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
       "student_publication_authorized":False,"original_source_folder":str(original),
       "expected_utterances":1,
       "slide_jobs":[{"slide":1,"utterance_count":1,
           "original_source_sha256":hashes["source.pdf"],
           "original_slides_sha256":hashes["slides.pdf"],
           "original_script_sha256":hashes["script.txt"]}]}))
    (q/"slide_001_initial_review.json").write_text('{"valid_first_review":true}')
    for n in range(1,4):
        (q/f"slide_001_independent_challenge_attempt_{n:02d}.json").write_text(json.dumps({
          "status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED",
          "slide":1,"attempt":n,"mode":"INDEPENDENT_CHALLENGE",
          "academically_approved":False}))
    return original,q

class ScopedAcademicWindow(unittest.TestCase):
 def test_new_explicitly_approved_scope_preserves_old_history(self):
  with tempfile.TemporaryDirectory() as d:
   folder,q=original_fixture(d)
   before=historical_evidence(queue_root=q,original_folder=folder)
   window=Path(d)/"new20261023"
   status=create_window(original_folder=folder,queue_root=q,
       window_root=window,approval_reference=CONSENT,now=1000)
   self.assertEqual(status["original_attempts_preserved"],3)
   self.assertEqual(status["new_confirmed_submissions"],0)
   self.assertEqual(historical_evidence(queue_root=q,original_folder=folder),before)
   read=inspect_window(window_root=window,now=1000)
   self.assertFalse(read["eligible_for_single_authorized_dispatch"])
   self.assertTrue(read["checkpoint_due_without_probe"])
   self.assertEqual(read["new_window_confirmed_submissions"],0)
 def test_unhealthy_or_stale_gemini_canary_blocks_retries(self):
  with tempfile.TemporaryDirectory() as d:
   folder,q=original_fixture(d);w=Path(d)/"new"
   create_window(original_folder=folder,queue_root=q,
       window_root=w,approval_reference=CONSENT,now=1000)
   for recent,status in ((990,"FAILED"),(-1000,"COMPLETE_STRUCTURED_TEXT_ONLY_RESPONSE")):
    (w/"source_transport_health.json").write_text(json.dumps({
      "status":status,"same_owned_gemini_session":True,
      "model_stopped_generating":True,"exact_expected_json":True,
      "prompt_characters":1500,"completed_unix_utc":recent,
      "verified_response_sha256":"a"*64}))
    self.assertFalse(inspect_window(window_root=w,now=1000)
                     ["eligible_for_single_authorized_dispatch"])
   response=w/"source_transport_health.response.json"
   response.write_text('{"probe":"microgen_source_transport_ok"}')
   record=json.loads((w/"source_transport_health.json").read_text())
   record["completed_unix_utc"]=990
   record["verified_response_sha256"]=hashlib.sha256(response.read_bytes()).hexdigest()
   (w/"source_transport_health.json").write_text(json.dumps(record))
   self.assertTrue(inspect_window(window_root=w,now=1000)
                   ["eligible_for_single_authorized_dispatch"])
 def test_no_probe_disallows_any_approved_scope_dispatch(self):
  with tempfile.TemporaryDirectory() as d:
   f,q=original_fixture(d);w=Path(d)/"new"
   create_window(original_folder=f,queue_root=q,window_root=w,
                 approval_reference=CONSENT,now=1000)
   called=[]
   out=dispatch_single_approved_window_tick(
       window_root=w,send_once=lambda:called.append(1),now=1000)
   self.assertFalse(out["model_request_sent"])
   self.assertEqual(called,[])
 def test_verified_same_owned_probe_allows_one_claim_only(self):
  with tempfile.TemporaryDirectory() as d:
   f,q=original_fixture(d);w=Path(d)/"new"
   create_window(original_folder=f,queue_root=q,window_root=w,
                 approval_reference=CONSENT,now=1000)
   response=w/"source_transport_health.response.json"
   response.write_text('{"probe":"microgen_source_transport_ok"}')
   (w/"source_transport_health.json").write_text(json.dumps({
        "status":"COMPLETE_STRUCTURED_TEXT_ONLY_RESPONSE",
        "same_owned_gemini_session":True,"model_stopped_generating":True,
        "exact_expected_json":True,"prompt_characters":1300,
        "completed_unix_utc":990,
        "verified_response_sha256":hashlib.sha256(response.read_bytes()).hexdigest()}))
   sent=[]
   def callback():
    sent.append(True)
    return {"outcome":"CONFIRMED_SUBMITTED",
           "user_turn_created":True,"composer_cleared":True}
   a=dispatch_single_approved_window_tick(window_root=w,send_once=callback,now=1000)
   self.assertTrue(a["model_request_sent"])
   b=dispatch_single_approved_window_tick(window_root=w,send_once=callback,now=1000)
   self.assertFalse(b["model_request_sent"])
   self.assertEqual(len(sent),1)
 def test_no_approval_or_duplicate_window_refused(self):
  with tempfile.TemporaryDirectory() as d:
   f,q=original_fixture(d);w=Path(d)/"new"
   with self.assertRaises(ValueError):
    create_window(original_folder=f,queue_root=q,window_root=w,
                  approval_reference="automatic_override",now=1000)
   create_window(original_folder=f,queue_root=q,window_root=w,
                 approval_reference=CONSENT,now=1000)
   with self.assertRaises(ValueError):
    create_window(original_folder=f,queue_root=q,window_root=w,
                  approval_reference=CONSENT,now=1000)
 def test_historical_receipt_tamper_blocks_all_new_dispatch(self):
  with tempfile.TemporaryDirectory() as d:
   f,q=original_fixture(d);w=Path(d)/"new"
   create_window(original_folder=f,queue_root=q,window_root=w,
                 approval_reference=CONSENT,now=1000)
   (q/"slide_001_independent_challenge_attempt_03.json").write_text(
       '{"status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED","slide":1,"attempt":3,"mode":"INDEPENDENT_CHALLENGE","other":"tampered"}')
   with self.assertRaises(ValueError):inspect_window(window_root=w,now=1001)
 def test_original_sha_change_blocks_resume(self):
  with tempfile.TemporaryDirectory() as d:
   f,q=original_fixture(d);w=Path(d)/"new"
   create_window(original_folder=f,queue_root=q,window_root=w,
                 approval_reference=CONSENT,now=1000)
   (f/"script.txt").write_text("changed")
   with self.assertRaises(ValueError):inspect_window(window_root=w,now=1001)
 def test_unexhausted_scope_cannot_open_second_window(self):
  with tempfile.TemporaryDirectory() as d:
   f,q=original_fixture(d);w=Path(d)/"new"
   (q/"slide_001_independent_challenge_attempt_03.json").unlink()
   with self.assertRaises(ValueError):
    create_window(original_folder=f,queue_root=q,window_root=w,
                  approval_reference=CONSENT,now=1000)
