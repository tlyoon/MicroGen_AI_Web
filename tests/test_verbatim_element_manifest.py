import unittest,tempfile,pathlib
from unittest.mock import patch
from selenium_pipeline.verbatim_element_manifest import build,validate
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
class ManifestSecurityTests(unittest.TestCase):
 def test_complete_exact_text_and_fail_closed_status(self):
  from selenium_pipeline import verbatim_element_manifest as m
  draft={"source_sha256":"s","slides_sha256":"l","script_sha256":"x",
    "utterance_count":1,"slides":[{"slide_number":1,
      "original_script_block_sha256":"h","figure_panel_review_required":False,
      "verbatim_slide_narration":"an equation",
      "proposed_utterances":[{"proposal_id":"s001.utterance.001",
        "verbatim_script_fragment":"an equation"}]}]}
  stric={"source_sha256":"s","slides_sha256":"l","script_sha256":"x",
        "slides":[{"slide":1,"utterances":[{"utterance_id":"s001.utterance.001",
             "exact_verbatim_script_fragment":"an equation",
             "candidate_visual_id":None,"unique_source_pdf_page":None,
             "text_appearance_supported":False}]}]}
  with patch.object(m,"classify",return_value=stric),patch.object(m,"propose",return_value=draft),patch.object(m,"_sha",side_effect=["s","l","x","s","l","x"]):
   report=m.build(source=pathlib.Path("source"),slides=pathlib.Path("slides"),script=pathlib.Path("script"))
  self.assertEqual(report["unresolved_utterance_count"],1)
  self.assertFalse(report["element_tts_batch_allowed"])
  self.assertFalse(report["student_publication_authorized"])
  self.assertEqual(report["slides"][0]["utterances"][0]["verbatim_script_fragment"],"an equation")
 def test_edited_promoted_manifest_fails_immutable_validation(self):
  with patch("selenium_pipeline.verbatim_element_manifest.build",return_value={"status":"REVIEW_REQUIRED","student_publication_authorized":False}):
   with self.assertRaises(FigureIdentityReviewRequired):
    validate(source=pathlib.Path("a"),slides=pathlib.Path("b"),script=pathlib.Path("c"),
             receipt={"status":"REVIEW_REQUIRED","student_publication_authorized":True})
