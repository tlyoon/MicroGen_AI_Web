"""Native Windows sourcebound completion reuse and bad-media fail-closed tests.

Synthetic receipts test runner control flow; actual physical FFmpeg/media
acceptance is still enforced independently by production_video_contract.
No expensive generation, historic publisher files or student publication.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from selenium_pipeline.sourcebound_completion_guard import (
    SourceboundCompletionBlocked, inspect_sourcebound_completion,
)
from selenium_pipeline import runner


class SourceboundCompletionGuardTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.publisher=self.root/"publisher"
        self.lecture=self.publisher/"8"/"8.4"
        self.lecture.mkdir(parents=True)
        self.source=self.lecture/"source.pdf"
        with pymupdf.open() as d:
            d.new_page()
            d.save(self.source)
        self.setting=runner.Settings(
            source_root=self.publisher,work_root=self.root/"work",
            subchapter="8.4",from_stage="figures",through_stage="video")
        self.manifest=self.lecture/"lecture_completion.json"

    def _make_completion(self,*,parts=2):
        for index in range(1,parts+1):
            (self.lecture/f"part_{index:02d}").mkdir()
        self.manifest.write_text(json.dumps({
            "schema_version":1,
            "status":"accepted_synchronized_series",
            "origin":"independent_fresh_decoded_pixel_reverification",
            "acceptance_scope":"technical_only",
            "human_academic_review_verified":False,
            "student_published":False,
            "parts":[{"part_id":f"part_{i:02d}"} for i in range(1,parts+1)],
        }),encoding="utf8")

    def test_absence_of_multipart_series_does_not_fake_a_completion(self):
        record=inspect_sourcebound_completion(self.source)
        self.assertEqual(record["status"],"NO_SOURCEBOUND_COMPLETION")
        self.assertFalse(record["student_publication_authorized"])

    def test_verified_original_multipart_is_reused_without_legacy_mp4(self):
        self._make_completion()
        with patch("selenium_pipeline.production_video_contract.verify_series",
                return_value={"status":"accepted_synchronized_series",
                  "student_publication_permitted":False,
                  "parts":[{"part_id":"part_01"},{"part_id":"part_02"}]}) as proof:
            accepted=inspect_sourcebound_completion(self.source)
        self.assertEqual(accepted["status"],
                         "ALREADY_COMPLETED_SOURCEBOUND_MULTIPART")
        self.assertEqual(accepted["part_count"],2)
        self.assertFalse((self.lecture/"slides.mp4").exists())
        proof.assert_called_once()

    def test_main_full_run_halts_early_for_accepted_multipart(self):
        self._make_completion(parts=1)
        def accepted(source):
            self.assertEqual(source,self.source)
            return {"status":"ALREADY_COMPLETED_SOURCEBOUND_MULTIPART",
                    "part_count":1}
        with patch("selenium_pipeline.sourcebound_completion_guard.inspect_sourcebound_completion",
                   side_effect=accepted) as inspect, \
             patch("selenium_pipeline.runner.run_cmd",
                   side_effect=AssertionError("Do not redo any generation")), \
             patch("selenium_pipeline.launch_gemini.launch",
                   side_effect=AssertionError("Do not open Gemini")), \
             patch("selenium_pipeline.automatic_element_audio_stage.produce_element_audio",
                   side_effect=AssertionError("Do not bill repeat TTS")):
            returned=runner._execute_unlocked(self.setting)
        self.assertEqual(returned,self.setting.directory())
        inspect.assert_called_once()
        self.assertFalse((self.lecture/"slides.mp4").exists())

    def test_partial_part_tree_without_completion_blocks_before_gemini(self):
        (self.lecture/"part_01").mkdir()
        with self.assertRaisesRegex(SourceboundCompletionBlocked,
                                    "Partial sourcebound"):
            runner._execute_unlocked(self.setting)
        self.assertFalse((self.lecture/"slides.mp4").exists())
        self.assertFalse(self.setting.directory().exists())

    def test_extra_unknown_part_dir_blocks_even_if_receipt_claims_complete(self):
        self._make_completion(parts=1)
        (self.lecture/"part_02").mkdir()
        with patch("selenium_pipeline.production_video_contract.verify_series",
                   side_effect=AssertionError("Must reject before FFmpeg")) as verify:
            with self.assertRaisesRegex(SourceboundCompletionBlocked,
                                        "differ"):
                inspect_sourcebound_completion(self.source)
        verify.assert_not_called()

    def test_forged_publication_flag_cannot_be_a_technical_pass(self):
        self._make_completion(parts=1)
        value=json.loads(self.manifest.read_text("utf8"))
        value["student_published"]=True
        self.manifest.write_text(json.dumps(value),encoding="utf8")
        with self.assertRaisesRegex(SourceboundCompletionBlocked,
                                    "technical-only"):
            inspect_sourcebound_completion(self.source)

    def test_tampered_original_source_or_media_is_not_rebuilt(self):
        self._make_completion(parts=1)
        from selenium_pipeline.production_video_contract import VideoContractError
        with patch("selenium_pipeline.production_video_contract.verify_series",
                   side_effect=VideoContractError("source SHA changed")):
            with self.assertRaisesRegex(SourceboundCompletionBlocked,
                                        "failed physical"):
                inspect_sourcebound_completion(self.source)


if __name__=="__main__":
    unittest.main()
