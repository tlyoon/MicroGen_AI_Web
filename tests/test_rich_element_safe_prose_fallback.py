"""Zero-provider generic real PDF prose fallback, with strict math/figure holds."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from selenium_pipeline.rich_element_mapping_checkpoint import (
    ElementMappingCheckpointBlocked,require_automatic_mapping_or_checkpoint)
from selenium_pipeline.rich_element_model_alignment import request_for_slide
from selenium_pipeline.rich_element_safe_prose_fallback import (
    overlap,propose_safe_text_slide,stage_section)
from selenium_pipeline.rich_element_selection_compiler import compile_selection
from selenium_pipeline.element_plan_review_bridge import promoted


class IndependentSafeProseFallbackTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.folder=self.root/"publisher"/"22"/"22.1"
        self.folder.mkdir(parents=True)
        self.source=self.folder/"source.pdf"
        self.slides=self.folder/"slides.pdf"
        self.script=self.folder/"script.txt"
        self.text=(
            "The experiment provides evidence for the observed physical process.",
            "The measurement confirms the predicted qualitative behavior.",
        )
        with pymupdf.open() as pdf:
            p=pdf.new_page()
            for i,line in enumerate(self.text):p.insert_text((60,90+i*30),line)
            pdf.save(self.source)
        with pymupdf.open() as pdf:
            p=pdf.new_page()
            for i,line in enumerate(self.text):p.insert_text((60,90+i*30),line)
            p.draw_line((80,180),(260,192))
            pdf.save(self.slides)
        self.script.write_text(
            "**Slide 1 [15s]:\n"+" ".join(self.text),encoding="utf8")
        self.cache_root=self.root/"cache"
        self.cache_root.mkdir()
        with self.assertRaises(ElementMappingCheckpointBlocked):
            require_automatic_mapping_or_checkpoint(
                source=self.source,slides=self.slides,script=self.script,
                checkpoint_root=self.cache_root)
        found=list(self.cache_root.glob("rich_element_map_*"))
        self.assertEqual(len(found),1)
        self.checkpoint=found[0]
        self.destination=self.root/"safe_response"

    def test_safe_original_prose_is_auto_accepted_without_any_provider_call(self):
        before={x.name:x.read_bytes() for x in (self.source,self.slides,self.script)}
        with patch("selenium_pipeline.series_gemini._browser_request",
                   side_effect=AssertionError("No LLM allowed")), \
             patch("selenium_pipeline.tts._gemini_say_with_watchdog",
                   side_effect=AssertionError("No TTS allowed")):
            report=stage_section(source_folder=self.folder,
                  checkpoint=self.checkpoint,destination=self.destination)
        self.assertEqual(report["original_utterances"],2)
        self.assertEqual(report["machine_verified_safe_prose_links"],2)
        self.assertEqual(report["unresolved_original_math_figure_or_ambiguous_utterances"],0)
        self.assertFalse(report["model_provider_invoked"])
        self.assertFalse(report["paid_tts_authorized"])
        self.assertEqual(before,
                         {x.name:x.read_bytes() for x in
                          (self.source,self.slides,self.script)})
        compiler=compile_selection(source_folder=self.folder,
          checkpoint=self.checkpoint,responses=self.destination,
          tts_model="gemini-3.8-flash-lite-tts",tts_voice="Kore")
        self.assertTrue(compiler["machine_technical_processing_ready"])
        selection=self.root/"accepted_technical_selection.json"
        selection.write_text(json.dumps(compiler),encoding="utf8")
        prepared=promoted(source=self.source,slides=self.slides,
                script=self.script,draft_path=self.checkpoint/
                "element_mapping_candidates.json",selection=selection,
                prepare_tts=True)
        self.assertEqual(prepared["status"],"reviewed_element_tts_request_unapproved")
        self.assertFalse(prepared["api_execution_authorized"])

    def test_competing_visual_targets_remain_unassigned(self):
        request=request_for_slide(source_folder=self.folder,
             checkpoint=self.checkpoint,slide_number=1)
        request["visible_targets"].append(
            dict(request["visible_targets"][0],target_id="s001.text.999"))
        response=propose_safe_text_slide(request)
        self.assertIsNone(response["associations"][0]["target_id"])
        self.assertTrue(response["associations"][0]["needs_review"])

    def test_named_math_and_figure_mentions_never_accepted_by_lexical_overlap(self):
        request=request_for_slide(source_folder=self.folder,
            checkpoint=self.checkpoint,slide_number=1)
        for spoken in ("The tangent theta equals the original expression.",
                       "The graph illustrates the observed physical process.",
                       "The integral equals the sum of two squared expressions."):
            request["original_utterances"][0]["verbatim_text"]=spoken
            answer=propose_safe_text_slide(request)
            self.assertIsNone(answer["associations"][0]["target_id"])

    def test_changed_original_author_source_cannot_reuse_previously_accepted_request(self):
        self.source.write_bytes(b"changed publisher original PDF")
        with self.assertRaises(ValueError):
            stage_section(source_folder=self.folder,
                 checkpoint=self.checkpoint,destination=self.destination)
        self.assertFalse(self.destination.exists())

    def test_duplicate_or_existing_output_directory_never_overwritten(self):
        stage_section(source_folder=self.folder,
            checkpoint=self.checkpoint,destination=self.destination)
        protected=(self.destination/"slide_001.json").read_bytes()
        with self.assertRaises(ValueError):
            stage_section(source_folder=self.folder,
                checkpoint=self.checkpoint,destination=self.destination)
        self.assertEqual((self.destination/"slide_001.json").read_bytes(),protected)

    def test_generic_overlap_is_bounded_and_zero_for_no_source_terms(self):
        self.assertEqual(overlap("the and or","the of and"),0.)
        self.assertEqual(overlap(self.text[0],self.text[0]),1.)
        self.assertLess(overlap(self.text[0],self.text[1]),.9)


if __name__=="__main__":
    unittest.main()
