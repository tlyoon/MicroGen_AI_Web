"""Windows full original-source academic/multimedia gate.

Tests real PyMuPDF publisher/author PDF inputs and frozen source-mapping
evidence, never TTS, model UI, FFmpeg or an arbitrary approval marker.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pymupdf

from selenium_pipeline.rich_element_mapping_checkpoint import (
    require_automatic_mapping_or_checkpoint,ElementMappingCheckpointBlocked)
from selenium_pipeline.rich_element_safe_prose_fallback import stage_section
from selenium_pipeline.rich_unresolved_model_queue import prepare_queue
from selenium_pipeline.original_source_e2e_acceptance import (
    inspect_source_e2e,execute_prepared,SourceReleaseBlocked)


class OriginalE2EExecutionGateTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.original=self.root/"original"/"8"/"8.4"
        self.original.mkdir(parents=True)
        self.source=self.original/"source.pdf"
        self.slides=self.original/"slides.pdf"
        self.script=self.original/"script.txt"
        self.prose="The experiment provides evidence for the observed physical process."
        self.second="The measurement confirms the predicted qualitative behavior."
        with pymupdf.open() as d:
            page=d.new_page()
            page.insert_text((60,90),self.prose)
            page.insert_text((60,130),self.second)
            d.save(self.source)
        with pymupdf.open() as d:
            page=d.new_page()
            page.insert_text((60,90),self.prose)
            page.insert_text((60,130),self.second)
            page.draw_line((70,195),(180,215))
            d.save(self.slides)
        self.script.write_text(
            "**Slide 1 [12sec]:\n"+self.prose+" "+self.second,
            encoding="utf8")
        self.immutable=[p.read_bytes() for p in
                        (self.source,self.slides,self.script)]
        c=self.root/"mapping"
        c.mkdir()
        with self.assertRaises(ElementMappingCheckpointBlocked):
            require_automatic_mapping_or_checkpoint(
                source=self.source,slides=self.slides,script=self.script,
                checkpoint_root=c)
        self.ck=next(c.glob("rich_element_map_*"))
        self.fallback=self.root/"accepted_prose"
        stage_section(source_folder=self.original,checkpoint=self.ck,
                      destination=self.fallback)
        self.queue=self.root/"unresolved_queue"
        prepare_queue(source_folder=self.original,checkpoint=self.ck,
                      fallback_dir=self.fallback,destination=self.queue)

    def inspect(self,**kwargs):
        return inspect_source_e2e(lecture=self.original,
            checkpoint=self.ck,fallback_dir=self.fallback,
            queue_dir=self.queue,**kwargs)

    def test_no_response_does_not_mean_all_lecture_semantics_passed(self):
        r=self.inspect()
        self.assertEqual(r["status"],
                         "BLOCKED_UNRESOLVED_SOURCE_VISUAL_NARRATION")
        self.assertFalse(r["full_semantic_source_review_ready"])
        self.assertFalse(r["execution_allowed_without_new_paid_or_model_calls"])
        self.assertFalse(r["dry_run_proves_entire_lecture_ready"])
        self.assertFalse(r["new_model_or_tts_calls"])
        self.assertFalse(r["student_publication_authorized"])

    def test_prose_only_complete_response_still_requires_real_element_audio(self):
        r=self.inspect(model_responses=self.fallback)
        self.assertEqual(r["unresolved_source_element_mappings"],0)
        self.assertTrue(r["full_semantic_source_review_ready"])
        self.assertEqual(r["status"],"SOURCE_MAPPING_VERIFIED_ELEMENT_PCM_REQUIRED")
        with patch("selenium_pipeline.full_pipeline_video_handoff.complete_from_published",
                   side_effect=AssertionError("No PCM, no rendering")) as video:
            with self.assertRaisesRegex(SourceReleaseBlocked,
                                        "not ready"):
                execute_prepared(lecture=self.original,
                    checkpoint=self.ck,fallback_dir=self.fallback,
                    queue_dir=self.queue,model_responses=self.fallback)
        video.assert_not_called()

    def test_existing_real_element_audio_may_use_only_the_verified_renderer(self):
        for name in ("element_narration_plan.json","element_tts_manifest.json"):
            (self.original/name).write_text("{}",encoding="utf8")
        (self.original/"element_wav").mkdir()
        with patch("selenium_pipeline.full_pipeline_video_handoff.complete_from_published",
                return_value={
                    "status":"INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO",
                    "part_count":1,
                    "student_publication_authorized":False}) as video:
            result=execute_prepared(lecture=self.original,checkpoint=self.ck,
                fallback_dir=self.fallback,queue_dir=self.queue,
                model_responses=self.fallback)
        self.assertEqual(result["status"],
                         "ORIGINAL_SOURCE_STRICT_MULTIPART_TECHNICAL_PASS")
        video.assert_called_once_with(source=self.source,
                                      require_slide_tts_qa=False)
        self.assertEqual(self.immutable,[p.read_bytes() for p in
                             (self.source,self.slides,self.script)])
        self.assertFalse(result["student_publication_authorized"])

    def test_accepted_multipart_is_reused_without_recomputing_all_stages(self):
        with patch("selenium_pipeline.sourcebound_completion_guard.inspect_sourcebound_completion",
             return_value={"status":"ALREADY_COMPLETED_SOURCEBOUND_MULTIPART",
                           "part_count":2}):
            r=inspect_source_e2e(lecture=self.original)
        self.assertEqual(r["status"],
                         "REUSED_PHYSICALLY_VERIFIED_MULTIPART_TECHNICAL_ONLY")
        self.assertEqual(r["part_count"],2)
        self.assertFalse(r["all_seven_stages_recomputed"])

    def test_partial_element_audio_is_protected_not_regenerated(self):
        (self.original/"element_narration_plan.json").write_text("{}")
        with self.assertRaisesRegex(SourceReleaseBlocked,"Partial recorded"):
            self.inspect(model_responses=self.fallback)
        self.assertFalse((self.original/"element_wav").exists())

    def test_physical_original_source_change_invalidates_earlier_receipt(self):
        self.source.write_bytes(b"publisher source was changed")
        with self.assertRaises((ValueError,SourceReleaseBlocked)):
            self.inspect(model_responses=self.fallback)

    def test_wrong_publisher_version_is_rejected_before_any_render(self):
        with self.assertRaisesRegex(SourceReleaseBlocked,"Wrong publisher"):
            self.inspect(expected_publisher_sha256="f"*64)


if __name__=="__main__":
    unittest.main()
