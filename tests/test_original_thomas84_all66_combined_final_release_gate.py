import tempfile,unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_all66_combined_final_release_gate import (
 STATUS,combined_gate)
class All66FinalGate(unittest.TestCase):
 def test_relevant_source_element_not_same_as_perfect_acoustic_word_proof(self):
  self.assertIn("THREE_QA_CHECKS",STATUS)
 def test_absent_source_fail_closed(self):
  with tempfile.TemporaryDirectory() as t:
   b=Path(t)
   with self.assertRaises((ValueError,FileNotFoundError)):
    combined_gate(original=b/"orig",corrected_source=b/"pair",
      source_review=b/"review.json",domain_evidence=b/"domain.json",
      slide11_voice=b/"voice.json",original16_ASR=b/"asr16.json",
      slide4_five_source=b/"five.json",slide4_five_ASR=b/"fiveasr.json",
      new8_audio=b/"new",new8_ASR=b/"newasr.json",new17_ASR=b/"new17.json",
      independent_final_video=b/"media.json",out=b/"out.json")
   self.assertFalse((b/"out.json").exists())
if __name__=="__main__":unittest.main()
