import unittest,tempfile,json
from pathlib import Path
from selenium_pipeline.ai_academic_review_queue import prepare_resumable_review,execute_one_review,summarize_queue
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_original_packet_evidence_audit import fixture
from test_ai_academic_web_review import response
from unittest.mock import patch
from selenium_pipeline.ai_academic_web_review import build_review_job
class ReviewQueue(unittest.TestCase):
 def setup(self,t):
  root=Path(t);folder=root/"src";fixture(folder)
  (folder/"script.txt").write_text("**Slide 1 [1 sec]:\nA visible equation**\n")
  import wave
  with wave.open(str(folder/"slide1.wav"),"wb") as w:
   w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b"\x00\x02"*24000)
  queue=root/"reviews";prepare_resumable_review(folder=folder,output_root=queue,slide_numbers=[1])
  return folder,queue
 def test_failure_quarantine_then_explicit_second_attempt(self):
  with tempfile.TemporaryDirectory() as t:
   folder,queue=self.setup(t)
   failure=execute_one_review(queue_root=queue,folder=folder,slide=1,
      mode="INITIAL_REVIEW",transport=lambda p,f:"Gemini said: Can't fulfill request")
   self.assertEqual(failure["status"],"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED")
   j=build_review_job(folder=folder,slide_numbers=[1])
   model=response();model["rows"][0]["utterance_id"]=j["slides"][0]["utterances"][0]["id"]
   model["rows"][0]["spoken_sha256"]=j["slides"][0]["utterances"][0]["spoken_sha256"]
   model["rows"][0]["target_id"]=j["slides"][0]["visual_targets"][0]["id"]
   ok=execute_one_review(queue_root=queue,folder=folder,slide=1,
      mode="INITIAL_REVIEW",attempt=2,transport=lambda p,f:json.dumps(model))
   self.assertEqual(ok["status"],"GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED")
   with self.assertRaises(FigureIdentityReviewRequired):
    execute_one_review(queue_root=queue,folder=folder,slide=1,mode="INITIAL_REVIEW",
                       attempt=3,transport=lambda p,f:json.dumps(model))
 def test_no_challenge_without_initial_and_original_hash_drift(self):
  with tempfile.TemporaryDirectory() as t:
   folder,queue=self.setup(t)
   with self.assertRaises(FigureIdentityReviewRequired):
    execute_one_review(queue_root=queue,folder=folder,slide=1,
         mode="INDEPENDENT_CHALLENGE",transport=lambda p,f:"{}")
   (folder/"script.txt").write_text("changed")
   with self.assertRaises(FigureIdentityReviewRequired):
    execute_one_review(queue_root=queue,folder=folder,slide=1,
         mode="INITIAL_REVIEW",transport=lambda p,f:"{}")
