import tempfile,unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_signed_triangle_full_mp4_independent_audit import (
 second_pass,STATUS)
class BothOriginalMathVideoAudit(unittest.TestCase):
 def test_source_audit_release_separate(self):
  self.assertIn("PHYSICAL_PASS",STATUS)
 def test_missing_video_fails_safely(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)
   with self.assertRaises((ValueError,FileNotFoundError)):
    second_pass(original=p/"orig",paired=p/"paired",kore=p/"audio",
      final_video_receipt=p/"final.json",prior_video_receipt=p/"old.json",
      out=p/"out.json")
   self.assertFalse((p/"out.json").exists())
if __name__=="__main__":unittest.main()
