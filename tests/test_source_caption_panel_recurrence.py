"""Known recurrence: normal source->slide figure mapping misses compact (a)/(b)/(c) panels.

The automatic route must reject whole-image semantic approval even when
the figure is narrower than the old 2.5:1 aspect threshold. No model, TTS
or source mutation is used by this test.
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

import pymupdf
from PIL import Image

from selenium_pipeline.scene_candidate_authoring import draft, visible_multi_panel_labels
from selenium_pipeline.element_plan_autodraft import propose
from selenium_pipeline.rich_element_mapping_checkpoint import (
    MAPPING_DETECTOR_REVISION, ElementMappingCheckpointBlocked,
    require_automatic_mapping_or_checkpoint,
)
from selenium_pipeline.rich_element_model_alignment import (
    RichMappingError, request_for_slide, assess_response,
)


class SourceCaptionPanelRecurrence(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.original = self.root / "source" / "6.4"
        self.original.mkdir(parents=True)
        self.reviews = self.root / "independent_reviews"
        self.reviews.mkdir()
        self.source = self.original / "source.pdf"
        self.slides = self.original / "slides.pdf"
        self.script = self.original / "script.txt"
        self._make_pdf(panel_caption=True)

    def _make_pdf(self, *, panel_caption: bool):
        with pymupdf.open() as book:
            page = book.new_page(width=400, height=450)
            page.insert_text((50, 85),
                             "The source figure shows three panels for a sphere in oil.")
            book.save(self.source)
        with pymupdf.open() as doc:
            pg = doc.new_page(width=400, height=450)
            caption = ("(a) Forces on falling sphere; (b) velocity arrows; "
                       "(c) approach to terminal speed." if panel_caption else
                       "Forces on a falling sphere in oil.")
            pg.insert_textbox(pymupdf.Rect(43, 63, 358, 126),
                              caption, fontsize=11)
            im = Image.new("RGB", (160, 110), "white")
            stream = io.BytesIO()
            im.save(stream, format="PNG")
            # 260/150 = 1.73: the older width/height > 2.5 gate misses it.
            pg.insert_image(pymupdf.Rect(50, 165, 310, 315),
                            stream=stream.getvalue())
            doc.save(self.slides)
        self.script.write_text(
            "**Slide 1 [20 sec]:\nThese diagrams explain the falling sphere.",
            encoding="utf8")

    def test_detector_requires_two_explicit_panel_labels(self):
        self.assertEqual(visible_multi_panel_labels(
            ["single label (a) is not a montage"]), [])
        self.assertEqual(visible_multi_panel_labels(
            ["(a) force, (b) speed, (c) time"]), ["a", "b", "c"])
        self.assertEqual(visible_multi_panel_labels(
            ["A paragraph with variables a and b"]), [])

    def test_normal_scene_and_narration_draft_propagate_panel_guard(self):
        s = draft(self.source, self.slides)
        images = [t for t in s["slides"][0]["targets"]
                  if t["type"] in ("image_whole", "inline_image_whole")]
        self.assertEqual(len(images), 1)
        self.assertTrue(images[0]["suspected_multipart"])
        self.assertEqual(images[0]["visible_caption_subpanel_labels_unverified"],
                         ["a", "b", "c"])
        p = propose(source_pdf=self.source, slides_pdf=self.slides,
                    script_txt=self.script)
        self.assertTrue(p["slides"][0]["figure_panel_review_required"])
        figure = next(t for t in p["slides"][0]["auto_candidate_targets"]
                      if t["kind"] == "image_whole")
        self.assertTrue(figure["panel_identity_review_required"])
        self.assertFalse(figure["source_evidence_verified"])

    def test_one_image_without_subpanel_labels_is_not_mislabeled(self):
        self._make_pdf(panel_caption=False)
        s = draft(self.source, self.slides)
        img = next(t for t in s["slides"][0]["targets"]
                   if t["type"] == "image_whole")
        self.assertFalse(img["suspected_multipart"])
        self.assertEqual(img["visible_caption_subpanel_labels_unverified"], [])

    def test_normal_checkpoint_and_ai_request_cannot_bypass_panel_guard(self):
        original = [p.read_bytes() for p in
                    (self.source, self.slides, self.script)]
        with self.assertRaises(ElementMappingCheckpointBlocked):
            require_automatic_mapping_or_checkpoint(
                source=self.source, slides=self.slides, script=self.script,
                checkpoint_root=self.reviews)
        checkpoints = list(self.reviews.glob("rich_element_map_*"))
        self.assertEqual(len(checkpoints), 1)
        cache = checkpoints[0]
        receipt = json.loads((cache / "mapping_checkpoint.json").read_text("utf8"))
        self.assertEqual(receipt["mapping_detector_revision"],
                         MAPPING_DETECTOR_REVISION)
        req = request_for_slide(source_folder=self.original,
                                checkpoint=cache, slide_number=1)
        figure = next(t for t in req["visible_targets"]
                      if t["kind"] == "image_whole")
        self.assertTrue(figure["figure_panel_review_required"])
        response = {
            "slide": 1, "request_sha256": req["request_sha256"],
            "associations": [{
                "utterance_id": req["original_utterances"][0]["utterance_id"],
                "target_id": figure["target_id"], "source_page": 1,
                "source_quote": "The source figure shows three panels for a sphere in oil.",
                "reason": "Figure is illustrated on source page",
                "needs_review": False,
            }],
        }
        audited = assess_response(
            source_folder=self.original, checkpoint=cache,
            slide_number=1, proposed=response)
        entry = audited["entries"][0]
        self.assertIn(
            "composite_figure_panel_identity_requires_independent_review",
            entry["remaining_independent_scientific_review_reasons"])
        self.assertFalse(audited["paid_tts_authorized"])
        self.assertFalse(audited["student_publication_authorized"])
        self.assertEqual(original, [p.read_bytes() for p in
                         (self.source, self.slides, self.script)])

    def test_old_detector_checkpoint_is_not_accepted_for_model_mapping(self):
        with self.assertRaises(ElementMappingCheckpointBlocked):
            require_automatic_mapping_or_checkpoint(
                source=self.source, slides=self.slides, script=self.script,
                checkpoint_root=self.reviews)
        cache = next(self.reviews.glob("rich_element_map_*"))
        path = cache / "mapping_checkpoint.json"
        receipt = json.loads(path.read_text("utf8"))
        receipt["mapping_detector_revision"] = 1
        path.write_text(json.dumps(receipt), encoding="utf8")
        with self.assertRaises((ElementMappingCheckpointBlocked, RichMappingError)):
            request_for_slide(source_folder=self.original,
                              checkpoint=cache, slide_number=1)


if __name__ == "__main__":
    unittest.main()
