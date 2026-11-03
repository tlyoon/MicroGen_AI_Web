"""Windows offline recovery for real figure-rich, paraphrased lecture narration.

Uses actual synthetic source/slide PDFs and real candidate extraction.
No source originals, Gemini, paid TTS, FFmpeg or publication are touched.
"""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from selenium_pipeline.rich_element_mapping_checkpoint import (
    ElementMappingCheckpointBlocked,
    require_automatic_mapping_or_checkpoint,
)
from selenium_pipeline.full_pipeline_video_handoff import complete_from_published


class RichElementMappingCheckpointTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.temp = Path(t.name)
        self.lecture = self.temp / "publisher" / "8" / "8.4"
        self.lecture.mkdir(parents=True)
        self.checkpoint = self.temp / "independent_windows_mapping_cache"
        self.checkpoint.mkdir()
        self.source = self.lecture / "source.pdf"
        self.slides = self.lecture / "slides.pdf"
        self.script = self.lecture / "script.txt"
        with pymupdf.open() as book:
            page = book.new_page()
            page.insert_text((60, 90),
                "Integration by substitution replaces variables to simplify integrals.")
            book.save(self.source)
        with pymupdf.open() as deck:
            page = deck.new_page()
            page.insert_text((60, 110),
                "Integration by substitution replaces variables.")
            # Actual mathematical/diagram vector content, not a fake text-only slide.
            page.draw_rect(pymupdf.Rect(85, 180, 210, 260))
            page.draw_line((95, 250), (195, 190))
            deck.save(self.slides)
        self.script.write_text(
            "**Slide 1 [10 sec]:\nWe introduce substitution as a way to simplify integrals.",
            encoding="utf8")

    def preflight(self):
        return require_automatic_mapping_or_checkpoint(
            source=self.source, slides=self.slides, script=self.script,
            checkpoint_root=self.checkpoint)

    def stored(self):
        files=list(self.checkpoint.glob("rich_element_map_*/mapping_checkpoint.json"))
        self.assertEqual(len(files),1)
        return files[0].parent

    def test_real_illustrated_explanatory_slide_is_checkpointed_for_entire_deck(self):
        originals=[p.read_bytes() for p in (self.source,self.slides,self.script)]
        with self.assertRaisesRegex(ElementMappingCheckpointBlocked,
                                    "Full-deck mapping checkpoint"):
            self.preflight()
        cache=self.stored()
        receipt=json.loads((cache/"mapping_checkpoint.json").read_text("utf8"))
        self.assertEqual(receipt["status"],
                         "SOURCEBOUND_RICH_ELEMENT_MAPPING_REVIEW_REQUIRED")
        self.assertEqual(receipt["slide_count"],1)
        self.assertGreaterEqual(receipt["slides_with_graphics"],1)
        self.assertFalse(receipt["paid_tts_authorized"])
        self.assertFalse(receipt["student_publication_authorized"])
        self.assertTrue((cache/"element_mapping_worklist.md").is_file())
        self.assertEqual([p.read_bytes() for p in
                          (self.source,self.slides,self.script)],originals)

    def test_repeat_unresolved_original_hash_reuses_worklist_without_new_source_scan(self):
        with self.assertRaises(ElementMappingCheckpointBlocked):
            self.preflight()
        cache=self.stored()
        original=(cache/"mapping_checkpoint.json").read_bytes()
        with patch("selenium_pipeline.automatic_element_narration.inspect_text_only",
                   side_effect=AssertionError("Do not re-analyze same source")), \
             patch("selenium_pipeline.visual_element_mapping_readiness.inspect_all",
                   side_effect=AssertionError("Do not recompute accepted source report")), \
             patch("selenium_pipeline.element_plan_autodraft.propose",
                   side_effect=AssertionError("Do not repeat original full-deck draft")):
            with self.assertRaisesRegex(ElementMappingCheckpointBlocked,
                                        "reused immutable complete-deck"):
                self.preflight()
        self.assertEqual((cache/"mapping_checkpoint.json").read_bytes(),original)

    def test_mutated_previously_checkpointed_report_fails_closed(self):
        with self.assertRaises(ElementMappingCheckpointBlocked):
            self.preflight()
        cache=self.stored()
        (cache/"element_mapping_candidates.json").write_text(
            '{"status":"APPROVED_FOR_PAID_TTS"}',encoding="utf8")
        with self.assertRaisesRegex(ElementMappingCheckpointBlocked,
                                    "modified"):
            self.preflight()

    def test_changing_script_requires_separate_new_source_bound_report(self):
        with self.assertRaises(ElementMappingCheckpointBlocked):
            self.preflight()
        old=self.stored()
        self.script.write_text(self.script.read_text("utf8")+
                               " Then evaluate the integral.",
                               encoding="utf8")
        with self.assertRaises(ElementMappingCheckpointBlocked):
            self.preflight()
        self.assertEqual(len(list(self.checkpoint.glob("rich_element_map_*"))),2)
        self.assertTrue((old/"mapping_checkpoint.json").is_file())

    def test_exact_simple_source_text_can_still_use_existing_paid_approval_path(self):
        line="This original source text provides reliable evidence for substitution."
        with pymupdf.open() as d:
            d.new_page().insert_text((60,90),line)
            d.save(self.temp/"clean_source.pdf")
        with pymupdf.open() as d:
            d.new_page().insert_text((60,90),line)
            d.save(self.temp/"clean_slides.pdf")
        self.source.write_bytes((self.temp/"clean_source.pdf").read_bytes())
        self.slides.write_bytes((self.temp/"clean_slides.pdf").read_bytes())
        self.script.write_text("**Slide 1 [10 sec]:\n"+line,encoding="utf8")
        result=self.preflight()
        self.assertEqual(result["status"],"EXACT_TEXT_SOURCE_MAPPING_CAN_PROCEED")
        self.assertFalse(result["paid_tts_authorized_by_this_preflight"])
        self.assertEqual(list(self.checkpoint.iterdir()),[])

    def test_actual_video_handoff_stops_figure_rich_source_before_any_paid_synthesis(self):
        with patch.dict("os.environ",{"LOCALAPPDATA":str(self.temp)}):
            with patch("selenium_pipeline.runner.check_valid",return_value=False), \
                 patch("selenium_pipeline.automatic_element_audio_stage.produce_element_audio",
                       side_effect=AssertionError("Never synthesize an unmapped graphic")) as paid, \
                 patch("selenium_pipeline.sourcebound_production_video.render_and_install_prepared",
                       side_effect=AssertionError("Never render unverified elements")) as video:
                with self.assertRaises(ElementMappingCheckpointBlocked):
                    complete_from_published(source=self.source)
        paid.assert_not_called()
        video.assert_not_called()
        self.assertFalse((self.lecture/"element_wav").exists())
        self.assertFalse((self.lecture/"lecture_completion.json").exists())


if __name__ == "__main__":
    unittest.main()
