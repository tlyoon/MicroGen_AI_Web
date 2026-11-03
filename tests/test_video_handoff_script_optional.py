"""Protect source-grounded existing element-WAV jobs without a slide script.

Only a *previously complete* source-bound original element plan and manifest
may proceed without a separate script.txt. Any new TTS generation or a
full seven-stage handoff still requires the actual published narration script.
No real model, TTS, video or publisher material is used in these tests.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.full_pipeline_video_handoff import (
    VideoHandoffBlocked, complete_from_published,
)


class ExistingSourceboundVideoWithoutSlideScriptTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.lecture = self.root / "8" / "8.4"
        self.lecture.mkdir(parents=True)
        self.source = self.lecture / "source.pdf"
        self.source.write_bytes(b"%PDF-1.4 original publisher fixture")
        (self.lecture / "slides.pdf").write_bytes(b"%PDF-1.4 original authored")
        self.assertFalse((self.lecture / "script.txt").exists())

    def _existing_elements(self):
        (self.lecture / "element_narration_plan.json").write_text(
            '{"status":"author_specified_unapproved_element_narration"}',
            encoding="utf8")
        (self.lecture / "element_tts_manifest.json").write_text(
            '{"status":"verified_source_bound_element_audio"}',
            encoding="utf8")
        (self.lecture / "element_wav").mkdir()

    def test_complete_preexisting_sourcebound_element_audio_does_not_require_script(self):
        self._existing_elements()
        state = {"rendered": False}
        def valid(stage, folder):
            self.assertEqual(stage, "video")
            self.assertEqual(folder, self.lecture)
            return state["rendered"]
        def render(**kwargs):
            self.assertEqual(kwargs["source"], self.source)
            self.assertEqual(kwargs["slides"], self.lecture / "slides.pdf")
            self.assertEqual(kwargs["authored"], self.lecture /
                             "element_narration_plan.json")
            self.assertEqual(kwargs["audio"], self.lecture / "element_wav")
            state["rendered"] = True
            return {"status": "INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO",
                    "part_count": 2}
        with patch("selenium_pipeline.runner.check_valid", side_effect=valid), \
             patch("selenium_pipeline.automatic_element_audio_stage.produce_element_audio",
                   side_effect=AssertionError("Existing audio must not be regenerated")) as synth, \
             patch("selenium_pipeline.sourcebound_production_video.render_and_install_prepared",
                   side_effect=render) as video:
            result = complete_from_published(source=self.source)
        self.assertEqual(result["status"],
                         "INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO")
        self.assertEqual(result["part_count"], 2)
        self.assertFalse(result["student_publication_authorized"])
        synth.assert_not_called()
        video.assert_called_once()
        self.assertFalse((self.lecture / "script.txt").exists())

    def test_no_existing_element_inputs_requires_original_script_before_paid_tts(self):
        with patch("selenium_pipeline.runner.check_valid", return_value=False), \
             patch("selenium_pipeline.automatic_element_audio_stage.produce_element_audio",
                   side_effect=AssertionError("Must not synthesize without source script")) as synth:
            with self.assertRaisesRegex(VideoHandoffBlocked, "script.txt"):
                complete_from_published(source=self.source)
        synth.assert_not_called()
        self.assertFalse((self.lecture / "element_wav").exists())

    def test_full_seven_stage_requires_script_even_if_element_plan_exists(self):
        self._existing_elements()
        with patch("selenium_pipeline.runner.check_valid", return_value=False), \
             patch("selenium_pipeline.automatic_element_audio_stage.produce_element_audio",
                   side_effect=AssertionError("Must not synthesize")) as synth:
            with self.assertRaisesRegex(VideoHandoffBlocked, "script.txt"):
                complete_from_published(source=self.source,
                                        require_slide_tts_qa=True)
        synth.assert_not_called()

    def test_partial_element_provenance_without_script_is_not_rebuilt(self):
        (self.lecture / "element_narration_plan.json").write_text("{}")
        with patch("selenium_pipeline.runner.check_valid", return_value=False), \
             patch("selenium_pipeline.automatic_element_audio_stage.produce_element_audio",
                   side_effect=AssertionError("Must not replace partial evidence")) as synth:
            with self.assertRaisesRegex(VideoHandoffBlocked, "Partial original"):
                complete_from_published(source=self.source)
        synth.assert_not_called()


if __name__ == "__main__":
    unittest.main()
