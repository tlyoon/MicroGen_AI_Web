import json,tempfile,unittest,wave
from pathlib import Path
from selenium_pipeline.ai_compact_original_challenge import (
 write_bounded_challenge_evidence,execute_compact_original_challenge)
from selenium_pipeline.ai_academic_review_queue import prepare_resumable_review
from selenium_pipeline.ai_academic_web_review import build_review_job,validate_model_review
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_original_packet_evidence_audit import fixture
from test_ai_academic_web_review import response
class TextExcerptReview(unittest.TestCase):
 def setup(self,t):
  root=Path(t);folder=root/"src";fixture(folder)
  (folder/"script.txt").write_text("**Slide 1 [1 sec]:\nA visible equation**\n")
  with wave.open(str(folder/"slide1.wav"),"wb") as w:
   w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b"\x03\x04"*24000)
  q=root/"q";prepare_resumable_review(folder=folder,output_root=q,slide_numbers=[1])
  j=build_review_job(folder=folder,slide_numbers=[1])
  u=j["slides"][0]["utterances"][0];proposal=response()
  proposal["rows"][0]["spoken_sha256"]=u["spoken_sha256"]
  proposal["rows"][0]["target_id"]=j["slides"][0]["visual_targets"][0]["id"]
  p=validate_model_review(folder=folder,job=j,response=proposal,mode="INITIAL_REVIEW")
  (q/"slide_001_initial_review.json").write_text(json.dumps(p))
  return root,folder,q,j,proposal
 def test_original_pdf_excerpt_allows_separately_validated_textual_challenge(self):
  with tempfile.TemporaryDirectory() as t:
   root,folder,q,j,proposal=self.setup(t)
   proposal["rows"][0]["math_explanation"]="This independent source check confirms the original equation is visible and worded accurately."
   report=execute_compact_original_challenge(queue_root=q,folder=folder,slide=1,
       attempt=1,excerpt=root/"source_excerpt.txt",
       transport=lambda prompt,files:json.dumps(proposal))
   self.assertEqual(report["status"],"GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED")
   self.assertTrue((root/"source_excerpt.txt").is_file())
   self.assertFalse(report["figure_math_semantics_without_visual_qa_verified"])
 def test_no_prior_first_pass_or_source_drift_fails_closed(self):
  with tempfile.TemporaryDirectory() as t:
   root,folder,q,j,proposal=self.setup(t)
   (q/"slide_001_initial_review.json").unlink()
   with self.assertRaises(FigureIdentityReviewRequired):
    write_bounded_challenge_evidence(queue_root=q,folder=folder,
        slide=1,output=root/"excerpt.txt")
