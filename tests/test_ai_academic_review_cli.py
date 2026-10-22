import json,tempfile,unittest
from pathlib import Path
from selenium_pipeline.ai_academic_review_cli import import_prior_source_verified_pass
from selenium_pipeline.ai_academic_review_queue import prepare_resumable_review
from selenium_pipeline.ai_academic_web_review import build_review_job,validate_model_review
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_original_packet_evidence_audit import fixture
from test_ai_academic_web_review import response
class PriorImport(unittest.TestCase):
 def test_real_original_source_evidence_import_and_duplicate_rejection(self):
  import wave
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);folder=root/"src";fixture(folder)
   (folder/"script.txt").write_text("**Slide 1 [1 sec]:\nA visible equation**\n")
   with wave.open(str(folder/"slide1.wav"),"wb") as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b"\x01\x02"*24000)
   queue=root/"q";prepare_resumable_review(folder=folder,output_root=queue,slide_numbers=[1])
   job=build_review_job(folder=folder,slide_numbers=[1]);unit=job["slides"][0]["utterances"][0]
   proposal=response();proposal["rows"][0]["spoken_sha256"]=unit["spoken_sha256"]
   proposal["rows"][0]["target_id"]=job["slides"][0]["visual_targets"][0]["id"]
   prior=root/"prior.json"
   actual=validate_model_review(folder=folder,job=job,response=proposal,mode="INITIAL_REVIEW")
   prior.write_text(json.dumps(actual))
   got=import_prior_source_verified_pass(queue_root=queue,folder=folder,slide=1,prior=prior)
   self.assertEqual(got["utterances"],1)
   with self.assertRaises(FigureIdentityReviewRequired):
    import_prior_source_verified_pass(queue_root=queue,folder=folder,slide=1,prior=prior)
 def test_forged_source_quote_rejected(self):
  import wave
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);folder=root/"src";fixture(folder)
   (folder/"script.txt").write_text("**Slide 1 [1 sec]:\nA visible equation**\n")
   with wave.open(str(folder/"slide1.wav"),"wb") as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b"\x01\x02"*24000)
   queue=root/"q";prepare_resumable_review(folder=folder,output_root=queue,slide_numbers=[1])
   job=build_review_job(folder=folder,slide_numbers=[1]);unit=job["slides"][0]["utterances"][0]
   proposal=response();proposal["rows"][0]["spoken_sha256"]=unit["spoken_sha256"]
   proposal["rows"][0]["target_id"]=job["slides"][0]["visual_targets"][0]["id"]
   validated=validate_model_review(folder=folder,job=job,response=proposal,mode="INITIAL_REVIEW")
   validated["rows"][0]["verbatim_source_quote"]="Fabricated fictional textbook"
   prior=root/"prior.json";prior.write_text(json.dumps(validated))
   with self.assertRaises(FigureIdentityReviewRequired):
    import_prior_source_verified_pass(queue_root=queue,folder=folder,slide=1,prior=prior)
