import unittest
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline.element_tts_safe_handoff import preflight
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
class GuardedTTSHandoffTests(unittest.TestCase):
 def test_ambiguity_blocks_even_if_paid_provider_is_available(self):
  with patch("selenium_pipeline.element_tts_safe_handoff.build",return_value={
        "source_sha256":"a","slides_sha256":"b","script_sha256":"c",
        "original_utterance_count":71}),patch(
         "selenium_pipeline.element_tts_safe_handoff.inspect_text_only",
         side_effect=ValueError("unverified figure")):
   r=preflight(source=Path("a"),slides=Path("b"),script=Path("c"))
  self.assertFalse(r["element_mapping_prerequisite_passed"])
  self.assertFalse(r["paid_tts_execution_authorized"])
  self.assertFalse(r["video_publishing_authorized"])
 def test_no_selection_pair_is_invalid(self):
  with patch("selenium_pipeline.element_tts_safe_handoff.build",return_value={
       "source_sha256":"a","slides_sha256":"b","script_sha256":"c",
       "original_utterance_count":1}):
   with self.assertRaises(FigureIdentityReviewRequired):
    preflight(source=Path("a"),slides=Path("b"),script=Path("c"),draft=Path("draft"))
 def test_forged_approvals_do_not_make_paid_call(self):
  with patch("selenium_pipeline.element_tts_safe_handoff.build",return_value={
      "source_sha256":"a","slides_sha256":"b","script_sha256":"c",
      "original_utterance_count":1}),patch(
      "selenium_pipeline.element_tts_safe_handoff.inspect_text_only",
      side_effect=ValueError("source bad")),patch(
      "selenium_pipeline.element_tts_safe_handoff.promoted",
      return_value={"status":"reviewed_element_tts_request_unapproved",
       "tts_model":"gemini-3.8-flash-tts","tts_voice":"different",
       "source_sha256":"a","slides_sha256":"b","script_sha256":"c"}):
   r=preflight(source=Path("a"),slides=Path("b"),script=Path("c"),
               draft=Path("draft"),selection=Path("selection"))
  self.assertFalse(r["element_mapping_prerequisite_passed"])
  self.assertFalse(r["paid_tts_execution_authorized"])
