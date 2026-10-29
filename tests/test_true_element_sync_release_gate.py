import unittest
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline.true_element_sync_release_gate import inspect
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
class ReleaseGateTests(unittest.TestCase):
 def fake(self):
  return {"source_sha256":"a","slides_sha256":"b",
          "script_sha256":"c","original_utterance_count":71}
 def test_pilot_is_not_real_speech_aligned_video(self):
  with patch("selenium_pipeline.true_element_sync_release_gate.build",return_value=self.fake()):
   out=inspect(source=Path("source"),slides=Path("slides"),script=Path("script"))
  self.assertFalse(out["provisional_slide_wav_timing_is_element_alignment"])
  self.assertFalse(out["encoded_production_candidate_exists"])
  self.assertFalse(out["student_publication_authorized"])
 def test_partial_audio_promotion_is_invalid(self):
  with patch("selenium_pipeline.true_element_sync_release_gate.build",return_value=self.fake()):
   with self.assertRaises(FigureIdentityReviewRequired):
    inspect(source=Path("source"),slides=Path("slides"),script=Path("script"),
            authored=Path("authored"))
 def test_original_placeholder_review_cannot_make_audio_provenance(self):
  with patch("selenium_pipeline.true_element_sync_release_gate.build",return_value=self.fake()):
   with self.assertRaises(FigureIdentityReviewRequired):
    inspect(source=Path("source"),slides=Path("slides"),script=Path("script"),
            authored=Path("missing_authored"),audio=Path("missing_wavs"),
            review=Path("missing_review"),destination=Path("somewhere"))
