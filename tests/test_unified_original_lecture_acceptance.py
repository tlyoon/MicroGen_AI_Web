import tempfile,unittest
from pathlib import Path
from selenium_pipeline.unified_original_lecture_acceptance import inspect_original_multimedia_acceptance
from test_original_math_audio_release_ledger import ReleaseBlockers

class CompleteReadiness(unittest.TestCase):
 def test_unreviewed_original_remains_release_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   original,q=ReleaseBlockers().setup(d)
   x=inspect_original_multimedia_acceptance(
       original_folder=original,queue_root=q)
   self.assertEqual(x["original_utterances"],1)
   self.assertEqual(x["independent_math_agreements"],0)
   self.assertIn("INDEPENDENT_SOURCE_MATH_REVIEW",x["blocking_stages"])
   self.assertIn("NO_VERIFIED_ORIGINAL_MULTIPART_ELEMENT_VIDEO",x["blocking_stages"])
   self.assertFalse(x["student_publication_authorized"])
 def test_fake_encoded_candidate_still_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   original,q=ReleaseBlockers().setup(d)
   candidate=Path(d)/"candidate";candidate.mkdir()
   (candidate/"source.pdf").write_bytes((original/"source.pdf").read_bytes())
   x=inspect_original_multimedia_acceptance(
       original_folder=original,queue_root=q,candidate=candidate)
   self.assertIn("UNVERIFIED_MP4_AUDIO_PIXEL_OR_DURATION",x["blocking_stages"])
   self.assertFalse(x["source_bound_decoded_audio_pixels_and_duration_verified"])
 def test_unrelated_source_candidate_not_promoted(self):
  with tempfile.TemporaryDirectory() as d:
   original,q=ReleaseBlockers().setup(d)
   c=Path(d)/"candidate";c.mkdir()
   (c/"source.pdf").write_text("unrelated")
   x=inspect_original_multimedia_acceptance(
       original_folder=original,queue_root=q,candidate=c)
   self.assertIn("CANDIDATE_ORIGINAL_SOURCE_IDENTITY_MISMATCH",x["blocking_stages"])
 def test_original_text_drift_cannot_be_masked_by_receipts(self):
  with tempfile.TemporaryDirectory() as d:
   original,q=ReleaseBlockers().setup(d)
   (original/"script.txt").write_text("fabricated")
   with self.assertRaises(Exception):
    inspect_original_multimedia_acceptance(original_folder=original,queue_root=q)
