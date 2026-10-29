import unittest,tempfile,pathlib
from unittest.mock import patch
from selenium_pipeline.batch_element_sync_acceptance import audit
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
class BatchElementAcceptanceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=pathlib.Path(self.tmp.name)
 def test_no_source_fails_closed_and_does_not_create_originals(self):
  r=audit(root=self.root,names=("8.4","8.5","8.6"))
  self.assertEqual(r["production_accepted_subchapter_count"],0)
  self.assertTrue(all(x["status"]=="SOURCE_OR_SCRIPT_MISSING" for x in r["items"]))
  self.assertFalse((self.root/"8.4").exists())
 def test_path_traversal_rejected(self):
  with self.assertRaises(FigureIdentityReviewRequired):
   audit(root=self.root,names=("../8.4",))
 def test_preview_can_never_promote_to_student_publication(self):
  folder=self.root/"8.4";folder.mkdir()
  for f in ("source.pdf","slides.pdf","script.txt"):(folder/f).write_text("stub")
  with patch("selenium_pipeline.batch_element_sync_acceptance.inspect_original_slide_wav_plan",
      return_value={"original_wav_count":1,"total_original_wav_duration_s":10.,
      "proposed_parts":[{"slide_start":1,"slide_end":1,"original_wav_duration_sum_s":10.}]}),patch(
      "selenium_pipeline.batch_element_sync_acceptance.tts_preflight",
      return_value={"status":"BLOCKED","element_mapping_prerequisite_passed":False}),patch(
      "selenium_pipeline.batch_element_sync_acceptance.verify_full_staged_element_coverage",
      return_value={"all_events_encoded_pixel_recheck_count":3,
        "total_provisional_highlight_events":3,"status":"REVIEW_ONLY"}):
   stage=self.root/"stage";stage.mkdir()
   data=audit(root=self.root,names=("8.4",),staged={"8.4":stage})
  self.assertEqual(data["staged_preview_subchapter_count"],1)
  self.assertEqual(data["production_accepted_subchapter_count"],0)
  self.assertFalse(data["student_publication_authorized"])
