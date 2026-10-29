import unittest,tempfile,hashlib,wave
from pathlib import Path
from selenium_pipeline.ai_reviewed_audio_qa import prepare_original_ai_tts_jobs,inspect_genuine_tts_wav_deliveries
from selenium_pipeline.incremental_chunk_tts_requests import DEFAULT_MODEL,DEFAULT_VOICE
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_ai_academic_web_review import job
class ElementAudioReview(unittest.TestCase):
 def test_actual_original_spoken_text_is_passed_through_without_billing(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/"src";j=job(root)
   c={"status":"AI_DOUBLE_PASS_SOURCE_WITNESSED_ELEMENT_REVIEW",
      "source_sha256":j["source_sha256"],"slides_sha256":j["slides_sha256"],
      "script_sha256":j["script_sha256"],"original_utterance_count":1,
      "items":[{"utterance_id":"s001.utterance.001","spoken_sha256":"f"*64,
               "ai_double_pass_source_witnessed":True,"target_id":"s001.text.001",
               "target_bbox_pdf_pt":[20,15,100,33]}]}
   r=prepare_original_ai_tts_jobs(folder=root,job=j,consensus=c)
   self.assertEqual(r["jobs"][0]["spoken_text"],"A visible equation.")
   self.assertEqual(r["provider_requests_performed"],0)
 def test_real_pcm_receipt_qa_flags_actual_clipping(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=root/"src";source.mkdir()
   wav=root/"audio.wav"
   with wave.open(str(wav),"wb") as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000)
    w.writeframes(b"\xff\x7f"*12000)
   j={"job_id":"s001.utterance.001","spoken_text_sha256":"a"*64}
   jobs={"status":"AI_SOURCE_WITNESSED_ELEMENT_AUDIO_JOBS_NON_BILLED",
         "model":DEFAULT_MODEL,"voice":DEFAULT_VOICE,"jobs":[j]}
   r={"job_id":j["job_id"],"spoken_text_sha256":j["spoken_text_sha256"],
      "model":DEFAULT_MODEL,"voice":DEFAULT_VOICE,
      "provider_receipt_present":True,"execution_id":"provider-observed-123",
      "pcm_wav_path":str(wav),"wav_sha256":hashlib.sha256(wav.read_bytes()).hexdigest()}
   out=inspect_genuine_tts_wav_deliveries(folder=source,jobs=jobs,receipts=[r])
   self.assertEqual(out["status"],"ELEMENT_PCM_NEEDS_REPAIR")
   r["wav_sha256"]="0"*64
   with self.assertRaises(FigureIdentityReviewRequired):
    inspect_genuine_tts_wav_deliveries(folder=source,jobs=jobs,receipts=[r])
