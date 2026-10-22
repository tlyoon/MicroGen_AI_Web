import json,tempfile,unittest,wave
from pathlib import Path
from selenium_pipeline.ai_academic_review_consensus import reconcile_actual_review_queue
from selenium_pipeline.ai_academic_review_queue import prepare_resumable_review
from selenium_pipeline.ai_academic_web_review import build_review_job,validate_model_review
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_original_packet_evidence_audit import fixture
from test_ai_academic_web_review import response
class IndependentReconciliation(unittest.TestCase):
 def setup(self,t):
  root=Path(t);source=root/"original";fixture(source)
  (source/"script.txt").write_text("**Slide 1 [1 sec]:\nA visible equation**\n")
  with wave.open(str(source/"slide1.wav"),"wb") as w:
   w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b"\x03\x04"*24000)
  queue=root/"review";prepare_resumable_review(folder=source,output_root=queue,slide_numbers=[1])
  job=build_review_job(folder=source,slide_numbers=[1])
  u=job["slides"][0]["utterances"][0]
  a=response()
  a["rows"][0]["spoken_sha256"]=u["spoken_sha256"]
  a["rows"][0]["target_id"]=job["slides"][0]["visual_targets"][0]["id"]
  p=validate_model_review(folder=source,job=job,response=a,mode="INITIAL_REVIEW")
  (queue/"slide_001_initial_review.json").write_text(json.dumps(p))
  return source,queue,job,a
 def test_real_original_pdf_differing_valid_quotes_both_count_as_evidence(self):
  with tempfile.TemporaryDirectory() as t:
   folder,queue,job,reply=self.setup(t)
   reply["rows"][0]["verbatim_source_quote"]="visible equation"
   reply["rows"][0]["math_explanation"]="An independent examination finds these actual source words and the original equation match."
   b=validate_model_review(folder=folder,job=job,response=reply,mode="INDEPENDENT_CHALLENGE")
   (queue/"slide_001_independent_challenge.json").write_text(json.dumps(b))
   r=reconcile_actual_review_queue(queue_root=queue,folder=folder)
   self.assertEqual(r["agreed_source_witnessed_segments"],1)
   self.assertEqual(r["pending_or_disputed"],0)
   self.assertFalse(r["AI_consensus_is_formal_math_proof"])
 def test_unverified_challenge_cannot_approve(self):
  with tempfile.TemporaryDirectory() as t:
   folder,queue,job,reply=self.setup(t)
   r=reconcile_actual_review_queue(queue_root=queue,folder=folder)
   self.assertEqual(r["pending_or_disputed"],1)
   bad=json.loads((queue/"slide_001_initial_review.json").read_text())
   bad["mode"]="INDEPENDENT_CHALLENGE"
   bad["rows"][0]["verbatim_source_quote"]="Fabricated literature"
   (queue/"slide_001_independent_challenge.json").write_text(json.dumps(bad))
   with self.assertRaises(FigureIdentityReviewRequired):
    reconcile_actual_review_queue(queue_root=queue,folder=folder)
