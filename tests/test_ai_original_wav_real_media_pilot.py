import tempfile,unittest,math,wave
from pathlib import Path
from selenium_pipeline.ai_original_wav_real_media_pilot import render_original_single_utterance_review
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.ai_academic_web_review import build_review_job,validate_model_review
from test_original_packet_evidence_audit import fixture
class RealWavPilot(unittest.TestCase):
 def test_actual_pcm_encoded_and_independently_decoded_not_production(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);folder=root/"source";fixture(folder)
   import pymupdf
   with pymupdf.open() as doc:
    page=doc.new_page(width=362.835,height=272.126)
    page.insert_text((20,30),"A visible equation")
    doc.save(folder/"odd_slides.pdf")
   (folder/"slides.pdf").write_bytes((folder/"odd_slides.pdf").read_bytes())
   (folder/"script.txt").write_text("**Slide 1 [1 sec]:\nA visible equation**\n",encoding="utf8")
   import numpy as np
   pcm=(14000*np.sin(2*np.pi*440*np.arange(24000)/24000)).astype("<i2")
   with wave.open(str(folder/"slide1.wav"),"wb") as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(pcm.tobytes())
   job=build_review_job(folder=folder,slide_numbers=[1])
   for j in job["slides"][0]["utterances"]:
    self.assertTrue(j["spoken_text"])
   from selenium_pipeline.ai_academic_web_review import validate_model_review
   u=job["slides"][0]["utterances"][0];target=job["slides"][0]["visual_targets"][0]
   m={"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
      "rows":[{"utterance_id":u["id"],"spoken_sha256":u["spoken_sha256"],
               "target_id":target["id"],"source_page":1,
               "verbatim_source_quote":"A visible equation","verdict":"SUPPORTED",
               "math_explanation":"The original slide shows the exact original textbook words as a visible element."}]}
   a=validate_model_review(folder=folder,job=job,response=m,mode="INITIAL_REVIEW")
   out=render_original_single_utterance_review(folder=folder,job=job,
        ai_first_pass=a,destination=root/"pilot")
   self.assertLess(out["actual_encoded_duration_s"],600)
   self.assertTrue(out["decoded_original_audio_spectrum_verified"])
   self.assertFalse(out["student_publication_authorized"])
 def test_not_runnable_without_genuine_one_to_one_mapping(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);folder=root/"source";fixture(folder)
   (folder/"script.txt").write_text("**Slide 1 [1 sec]:\nA visible equation**\n",encoding="utf8")
   import numpy as np
   pcm=(14000*np.sin(2*np.pi*440*np.arange(24000)/24000)).astype("<i2")
   with wave.open(str(folder/"slide1.wav"),"wb") as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(pcm.tobytes())
   job=build_review_job(folder=folder,slide_numbers=[1])
   with self.assertRaises(FigureIdentityReviewRequired):
    render_original_single_utterance_review(folder=folder,job=job,
       ai_first_pass={},destination=root/"pilot")
