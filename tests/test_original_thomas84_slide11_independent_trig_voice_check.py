"""True sine/cosine swaps fail; safely split 'co sign' is not a swap."""
import unittest,tempfile
from pathlib import Path
from selenium_pipeline.tts_flexible_pronunciation_contract import evaluate_tts_soundalike
from selenium_pipeline.original_thomas84_new_kore_offline_audio_qa import screen_speech
from selenium_pipeline.original_thomas84_slide11_independent_trig_voice_check import check_original_11
class Slide11ActualTrigSpeech(unittest.TestCase):
 def test_observed_split_cosine_orthography_matches_mathematics(self):
  reference="Using the identity sine two u equals two sine u cosine u resolves this."
  heard="using the identity sign to you equals to sign you co sign you resolves this"
  x=screen_speech(reference,heard)
  self.assertTrue(x["phonetic_soundalike_screen_pass"])
  self.assertFalse(x["targeted_audible_check_required"])
 def test_actual_opposite_trig_function_still_blocks(self):
  x=evaluate_tts_soundalike("Sine and cosine u.","Cosine and sine u.")
  self.assertFalse(x["tts_qa_soundalike_pass"])
  self.assertIn("EXPLICIT_TRIGONOMETRIC_FUNCTION_CHANGED",x["critical_errors"])
 def test_real_source_needed(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)
   with self.assertRaises((ValueError,FileNotFoundError)):
    check_original_11(original=p/"original",asr_provenance=p/"asr.json",
       model_dir=p/"model",packages_dir=p/"packages",out=p/"out.json")
   self.assertFalse((p/"out.json").exists())
if __name__=="__main__":unittest.main()
