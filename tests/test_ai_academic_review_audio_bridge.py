import tempfile,unittest,wave
from pathlib import Path
from selenium_pipeline.ai_academic_review_audio_bridge import prepare_real_source_ai_kore_jobs
from selenium_pipeline.ai_academic_review_queue import prepare_resumable_review
from test_original_packet_evidence_audit import fixture
class SourceAIRenderHandoff(unittest.TestCase):
 def setup(self,t):
  folder=Path(t)/"src";fixture(folder)
  (folder/"script.txt").write_text("**Slide 1 [1 sec]:\nA visible equation**\n")
  with wave.open(str(folder/"slide1.wav"),"wb") as w:
   w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b"\x01\x02"*24000)
  q=Path(t)/"queue";prepare_resumable_review(folder=folder,output_root=q,slide_numbers=[1])
  return folder,q
 def test_zero_ai_agreement_cannot_create_billed_tts(self):
  with tempfile.TemporaryDirectory() as t:
   f,q=self.setup(t)
   r=prepare_real_source_ai_kore_jobs(folder=f,queue_root=q)
   self.assertEqual(r["AI_source_agreed_segments"],0)
   self.assertEqual(r["unresolved_source_segments"],1)
   self.assertFalse(r["paid_TTS_request_made"])
 def test_no_external_overwrite_original_folder(self):
  from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
  with tempfile.TemporaryDirectory() as t:
   f,q=self.setup(t)
   with self.assertRaises(FigureIdentityReviewRequired):
    prepare_real_source_ai_kore_jobs(folder=f,queue_root=q,destination=f/"job.json")
