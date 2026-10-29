import tempfile,unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_signed_triangle_single_kore_tts import generate,MODEL
class OneSingleVoiceMath(unittest.TestCase):
 def test_primary_model_approved(self):
  self.assertEqual(MODEL,"gemini-3.8-flash-lite-tts")
 def test_no_source_never_dispatches(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)
   with self.assertRaises((ValueError,FileNotFoundError)):
    generate(original=p/"original",corrected_source=p/"paired",
             out=p/"tts",dispatch_single_routine_tts=True)
   self.assertFalse((p/"tts").exists())
if __name__=="__main__":unittest.main()
