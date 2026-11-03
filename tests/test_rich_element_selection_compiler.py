"""The general AI-source bridge must be executable by the existing TTS
preparation workflow only when every original prose mapping is independently
verified, with mathematical and figure cases fail-closed.

No paid Gemini/TTS/ffmpeg calls.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.rich_element_mapping_checkpoint import (
    ElementMappingCheckpointBlocked,require_automatic_mapping_or_checkpoint)
from selenium_pipeline.rich_element_model_alignment import request_for_slide
from selenium_pipeline.rich_element_selection_compiler import (
    compile_selection,verify_machine_selection)
from selenium_pipeline.element_plan_review_bridge import (
    promoted,PlanPromotionError)


class ModelSourceVerifiedTechnicalSelectionTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        root=Path(t.name)
        self.original=root/"publisher"/"22"/"22.1"
        self.original.mkdir(parents=True)
        self.out=root/"outside_source_results"
        self.out.mkdir()
        self.source=self.original/"source.pdf"
        self.slides=self.original/"slides.pdf"
        self.script=self.original/"script.txt"
        self.checkpoint=root/"checkpoint"
        self.checkpoint.mkdir()
        self.responses=root/"gemini_response_quarantine"
        self.responses.mkdir()
        self.text=[
            "The experiment provides evidence for the observed physical process.",
            "The measurement confirms the predicted qualitative behavior."
        ]
        with pymupdf.open() as d:
            p=d.new_page()
            p.insert_text((50,90),self.text[0])
            p.insert_text((50,130),self.text[1])
            d.save(self.source)
        with pymupdf.open() as d:
            p=d.new_page()
            p.insert_text((50,90),self.text[0])
            p.insert_text((50,130),self.text[1])
            p.draw_line((80,160),(250,170))  # not text-only
            d.save(self.slides)
        self.script.write_text(
            "**Slide 1 [15sec]:\n"+self.text[0]+" "+self.text[1],
            encoding="utf8")
        with self.assertRaises(ElementMappingCheckpointBlocked):
            require_automatic_mapping_or_checkpoint(
                source=self.source,slides=self.slides,script=self.script,
                checkpoint_root=self.checkpoint)
        folder=list(self.checkpoint.glob("rich_element_map_*"))
        self.assertEqual(len(folder),1)
        self.checkpoint=folder[0]
        req=request_for_slide(source_folder=self.original,
                              checkpoint=self.checkpoint,slide_number=1)
        self.req=req
        self.assertEqual(len(req["original_utterances"]),2)
        self.assertEqual(len(req["visible_targets"]),2)

    def response(self):
        return {
            "slide":1,
            "request_sha256":self.req["request_sha256"],
            "associations":[{
                "utterance_id":u["utterance_id"],
                "target_id":t["target_id"],
                "source_page":1,
                "source_quote":self.text[i],
                "reason":"Source quote and actual authored visible prose agree.",
                "needs_review":False,
            } for i,(u,t) in enumerate(zip(
                self.req["original_utterances"],self.req["visible_targets"]))],
        }

    def save_response(self, response=None):
        path=self.responses/"slide_001.json"
        path.write_text(json.dumps(response or self.response()),encoding="utf8")
        return path

    def compile(self):
        return compile_selection(source_folder=self.original,
            checkpoint=self.checkpoint,responses=self.responses,
            tts_model="gemini-3.8-flash-lite-tts",tts_voice="Kore")

    def test_two_source_and_author_verified_prose_elements_prepare_without_paid_tts(self):
        self.save_response()
        report=self.compile()
        self.assertEqual(report["status"],"REVIEWED_SELECTION_FOR_PROCESSING")
        self.assertEqual(report["source_anchored_technical_text_utterances"],2)
        self.assertFalse(report["academic_approval"])
        self.assertFalse(report["student_publication"])
        self.assertEqual(len(report["slides"][0]["elements"]),2)
        selection=self.out/"technical_model_selection.json"
        selection.write_text(json.dumps(report),encoding="utf8")
        prepared=promoted(source=self.source,slides=self.slides,
            script=self.script,draft_path=self.checkpoint/
            "element_mapping_candidates.json",selection=selection,
            prepare_tts=True)
        self.assertEqual(prepared["status"],
                         "reviewed_element_tts_request_unapproved")
        self.assertFalse(prepared["api_execution_authorized"])
        self.assertFalse(prepared["academic_approval"])
        self.assertFalse(prepared["student_publication"])
        self.assertEqual(len(prepared["parts"]),1)
        self.assertEqual(len(prepared["parts"][0]["slides"][0]["elements"]),2)

    def test_mutated_source_or_model_response_fails_at_actual_tts_promotion(self):
        self.save_response()
        report=self.compile()
        path=self.out/"machine_selection.json"
        path.write_text(json.dumps(report),encoding="utf8")
        self.save_response({"slide":1,"request_sha256":"bad","associations":[]})
        with self.assertRaises(ValueError):
            promoted(source=self.source,slides=self.slides,script=self.script,
                 draft_path=self.checkpoint/"element_mapping_candidates.json",
                 selection=path,prepare_tts=True)

    def test_incomplete_response_is_review_only_not_a_paid_TTS_request(self):
        model=self.response()
        model["associations"][0].update(target_id=None,source_page=None,
                                         source_quote=None,needs_review=True)
        self.save_response(model)
        selection=self.compile()
        self.assertEqual(selection["status"],"REVIEW_SELECTION_INCOMPLETE")
        self.assertFalse(selection["machine_technical_processing_ready"])
        self.assertGreaterEqual(len(selection["remaining_technical_review_items"]),1)
        path=self.out/"incomplete_selection.json"
        path.write_text(json.dumps(selection),encoding="utf8")
        with self.assertRaises((PlanPromotionError,ValueError)):
            promoted(source=self.source,slides=self.slides,script=self.script,
                draft_path=self.checkpoint/"element_mapping_candidates.json",
                selection=path,prepare_tts=True)

    def test_missing_response_file_fails_to_promote_while_preserving_original(self):
        selection=self.compile()
        self.assertEqual(selection["status"],"REVIEW_SELECTION_INCOMPLETE")
        self.assertEqual(selection["model_processed_utterances"],0)
        self.assertFalse(selection["student_publication"])
        self.assertEqual(selection["source_anchored_technical_text_utterances"],0)

    def test_extra_unknown_model_response_file_is_rejected(self):
        self.save_response()
        (self.responses/"slide_999.json").write_text("{}",encoding="utf8")
        with self.assertRaisesRegex(ValueError,"Unknown or unsafe"):
            self.compile()


if __name__=="__main__":
    unittest.main()
