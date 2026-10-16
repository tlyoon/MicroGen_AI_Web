"""Fail-closed academic/voice listening review matrix offline tests."""
import json,tempfile,hashlib,unittest
from pathlib import Path
from selenium_pipeline.speech_review_matrix import build,sha

def save(p,d):p.write_text(json.dumps(d),encoding="utf8")

class SpeechReviewMatrixTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  root=Path(self.tmp.name)
  self.plan=root/"plan.json"
  self.asr=root/"asr";self.asr.mkdir()
  self.audio=root/"audio";self.audio.mkdir()
  self.csv=root/"report.csv";self.json=root/"report.json"
  self.wav=self.audio/"n1.wav";self.wav.write_bytes(b"real speech bytes")
  self.spoken="This is a defined trigonometric substitution."
  data={"status":"author_specified_unapproved_element_narration","parts":[{
    "slides":[{"slide":13,"elements":[
    {"wav":"n1.wav","spoken_text":self.spoken},
    {"wav":"n2.wav","spoken_text":"This word sequence is pending recognition."}]}]}]}
  save(self.plan,data)
  (self.audio/"n2.wav").write_bytes(b"another speech byte sample")
  self.model="gemini-3.1-flash-lite"
  save(self.asr/"asr_job.json",{"plan_sha256":sha(self.plan),"model":self.model,
     "clips":["n1.wav","n2.wav"]})
  self.record={
     "wav":"n1.wav","wav_sha256":sha(self.wav),
     "reference_sha256":hashlib.sha256(self.spoken.encode("utf8")).hexdigest(),
     "transcript":self.spoken,
     "transcript_sha256":hashlib.sha256(self.spoken.encode("utf8")).hexdigest(),
     "asr_model":self.model,
     "metrics":{"wer":0.0,"machine_asr_consistent":True}}
  save(self.asr/"n1.wav.asr.json",self.record)
 def do(self):
  return build(plan=self.plan,asr=self.asr,audio=self.audio,
     out_csv=self.csv,out_json=self.json)
 def test_incomplete_review_keeps_all_approval_flags_false(self):
  report=self.do()
  self.assertEqual((report["consistent_not_certified"],report["flagged"],report["pending"]),(1,0,1))
  self.assertFalse(report["production_approved"])
  self.assertFalse(report["human_listening_approved"])
  contents=self.csv.read_text(encoding="utf-8-sig")
  self.assertIn("n2.wav",contents)
  self.assertIn("pending_independent_asr",contents)
 def test_asr_mismatch_explicitly_flagged(self):
  self.record["metrics"]={"wer":0.5,"machine_asr_consistent":False}
  save(self.asr/"n1.wav.asr.json",self.record)
  result=self.do()
  self.assertEqual(result["flagged"],1)
  self.assertEqual(result["flagged_clip_ids"],["n1.wav"])
 def test_tampered_transcript_hash_fails_without_output(self):
  self.record["transcript"]="different words"
  save(self.asr/"n1.wav.asr.json",self.record)
  with self.assertRaisesRegex(ValueError,"Stale/changed"):
   self.do()
  self.assertFalse(self.csv.exists())
 def test_refuse_destination_overwrite(self):
  self.csv.write_text("historical")
  with self.assertRaisesRegex(ValueError,"new"):
   self.do()
  self.assertEqual(self.csv.read_text(),"historical")
if __name__=="__main__":unittest.main()
