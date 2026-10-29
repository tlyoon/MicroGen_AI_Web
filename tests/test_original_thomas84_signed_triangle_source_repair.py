import tempfile,unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_signed_triangle_source_repair import (
 signed_geometry_proof,repair_signed_triangle,CORRECTED_SPOKEN,CORRECTED_TEX)
class SignedReferenceMathCorrection(unittest.TestCase):
 def test_negative_x_requires_unsigned_geometry(self):
  p=signed_geometry_proof()
  self.assertTrue(p["physical_side_length_must_be_abs_x"])
  self.assertIn("|x|",CORRECTED_TEX)
 def test_repaired_script_distinguishes_signed_tangent(self):
  self.assertIn("absolute value of x",CORRECTED_SPOKEN)
  self.assertIn("retains the sign",CORRECTED_SPOKEN)
 def test_missing_original_prevents_false_completion(self):
  with tempfile.TemporaryDirectory() as t:
   b=Path(t)
   with self.assertRaises((ValueError,FileNotFoundError)):
    repair_signed_triangle(original=b/"source",prior_pair=b/"prior",
       full_semantic=b/"audit.json",out=b/"new")
   self.assertFalse((b/"new").exists())
if __name__=="__main__":unittest.main()
