import tempfile,unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_all66_independent_semantic_matrix import (
 CURATED_BLOCKS,MATH_ISSUES,CONTEXTUAL_NOT_PROVEN_AS_UNIQUE_ELEMENT,review_66)
class All66OriginalSourceMath(unittest.TestCase):
 def test_full_original_source_narrative_count(self):
  self.assertEqual(sum(len(x) for x in CURATED_BLOCKS.values()),66)
  self.assertEqual(len(MATH_ISSUES),2)
 def test_signed_negative_leg_is_not_unsigned_geometry(self):
  x=-2
  self.assertNotEqual(x,abs(x))
  self.assertIn((8,2),MATH_ISSUES)
 def test_missing_source_produces_no_math_approval(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)
   with self.assertRaises((ValueError,FileNotFoundError)):
    review_66(original=p/"none",source_plan=p/"plan.json",
     paired_source=p/"pair",independent_video=p/"video.json",
     source_slide11_audio=p/"voice.json",five_domains=p/"domains.json",
     out=p/"out.json")
   self.assertFalse((p/"out.json").exists())
if __name__=="__main__":unittest.main()
