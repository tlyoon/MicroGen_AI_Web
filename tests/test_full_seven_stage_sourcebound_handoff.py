"""Real main-runner-to-multipart integration; no paid provider or external browser."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from selenium_pipeline import runner
from selenium_pipeline.full_pipeline_video_handoff import (
    VideoHandoffBlocked, complete_from_published,
)
from selenium_pipeline.runner_stage_artifact_evidence import build_stage_evidence

class CompliantFullVideoHandoffTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base=Path(tmp.name)
        self.source_root=base/"publisher"
        self.work_root=base/"workspace"
        self.source=self.source_root/"8"/"8.4"/"source.pdf"
        self.source.parent.mkdir(parents=True)
        with pymupdf.open() as d:
            d.new_page()
            d.save(self.source)
        with pymupdf.open() as d:
            d.new_page()
            d.save(self.source.parent/"slides.pdf")
        (self.source.parent/"slides.tex").write_text(
            "\\begin{document}\\end{document}",encoding="utf8")
        (self.source.parent/"script.txt").write_text("**Slide 1 [30s]:\n\nSource verified.\n",
                                                    encoding="utf8")
        self.setting=runner.Settings(
            source_root=self.source_root,work_root=self.work_root,
            subchapter="8.4",from_stage="tts_qa",through_stage="video",
            tts_provider="gemini")
        self.workspace=self.setting.directory()
        self.workspace.mkdir(parents=True)
        (self.workspace/"source.pdf").write_bytes(self.source.read_bytes())
        (self.workspace/"slides.pdf").write_bytes(
            (self.source.parent/"slides.pdf").read_bytes())
        (self.workspace/"script.txt").write_bytes(
            (self.source.parent/"script.txt").read_bytes())
        (self.workspace/"slide1.wav").write_bytes(b"RIFF"+b"PCM"*60)
        (self.workspace/"tts_fidelity_report.json").write_text(
            '{"status":"accepted"}',encoding="utf8")
        (self.workspace/"tts_fidelity_report.md").write_text(
            "Independently accepted voice",encoding="utf8")
        self.signature=runner.digest(self.source)
        self.qa_model=(f"{self.setting.tts_qa_model}:"
                       f"threshold={self.setting.tts_qa_threshold:.3f}:v1")
        self.state={
            "source_sha256":self.signature,
            "completed":{"tts_qa":{
                "model":self.qa_model,
                "artifact_evidence":build_stage_evidence(
                    self.workspace,"tts_qa",self.signature),
            }},
        }
        (self.workspace/".selenium_pipeline_state.json").write_text(
            json.dumps(self.state),encoding="utf8")

    def test_one_command_full_pipeline_dry_run_admits_compliant_video_stage(self):
        setting=runner.Settings(source_root=self.source_root,
            work_root=self.work_root,subchapter="8.4",dry_run=True,
            from_stage="figures",through_stage="video")
        with patch("selenium_pipeline.launch_gemini.launch",
                   side_effect=AssertionError("dry-run must not open Gemini")) as browser:
            self.assertEqual(runner._execute_unlocked(setting),setting.directory())
        browser.assert_not_called()

    def test_main_runner_hands_cached_original_audio_to_compliant_video_only(self):
        with patch("selenium_pipeline.runner.check_valid",return_value=True):
            with patch("selenium_pipeline.inverse_trig_principal_domain_guard.enforce"),\
                 patch("selenium_pipeline.figure_audit.enforce_graphics"),\
                 patch("selenium_pipeline.source_numbered_example_coverage.require_coverage"):
                with patch("selenium_pipeline.runner.run_cmd",
                           side_effect=AssertionError("No legacy FFmpeg or paid command")) as run:
                    with patch("selenium_pipeline.full_pipeline_video_handoff.complete_from_published",
                          return_value={"status":"INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO",
                              "part_count":1,
                              "new_generation_performed":True,
                              "student_publication_authorized":False}) as bridge:
                        result=runner._execute_unlocked(self.setting)
        self.assertEqual(result,self.workspace)
        bridge.assert_called_once_with(source=self.source,require_slide_tts_qa=True)
        run.assert_not_called()
        self.assertFalse((self.source.parent/"slides.mp4").exists())
        saved=json.loads((self.workspace/".selenium_pipeline_state.json").read_text("utf8"))
        self.assertEqual(saved["completed"]["video"]["technical_install_status"],
                         "INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO")
        self.assertFalse(saved["completed"]["video"]["student_publication_authorized"])

    def test_complete_existing_multipart_never_reencodes_or_calls_element_tts(self):
        with patch("selenium_pipeline.runner.check_valid",
                   side_effect=lambda stage,folder: stage=="video"):
            with patch("selenium_pipeline.automatic_element_audio_stage.produce_element_audio",
                       side_effect=AssertionError("No repeated TTS")) as tts:
                with patch("selenium_pipeline.sourcebound_production_video.render_and_install_prepared",
                           side_effect=AssertionError("No repeated FFmpeg")) as video:
                    result=complete_from_published(source=self.source,
                                                   require_slide_tts_qa=True)
        self.assertFalse(result["new_generation_performed"])
        tts.assert_not_called()
        video.assert_not_called()

    def test_partial_sourcebound_audio_does_not_trigger_billable_retry(self):
        (self.source.parent/"element_narration_plan.json").write_text("{}",encoding="utf8")
        with patch("selenium_pipeline.runner.check_valid",return_value=False):
            with patch("selenium_pipeline.automatic_element_audio_stage.produce_element_audio",
                       side_effect=AssertionError("No paid redo")) as tts:
                with self.assertRaisesRegex(VideoHandoffBlocked,"Partial original"):
                    complete_from_published(source=self.source)
        tts.assert_not_called()

    def test_existing_legacy_video_is_protected(self):
        (self.source.parent/"slides.mp4").write_bytes(b"published historic MP4")
        with patch("selenium_pipeline.runner.check_valid",return_value=False):
            with self.assertRaisesRegex(VideoHandoffBlocked,"protected"):
                complete_from_published(source=self.source)
        self.assertEqual((self.source.parent/"slides.mp4").read_bytes(),
                         b"published historic MP4")

    def test_full_handoff_requires_original_passed_tts_qa_before_synthesis(self):
        with patch("selenium_pipeline.runner.check_valid",return_value=False):
            with patch("selenium_pipeline.automatic_element_audio_stage.produce_element_audio",
                       side_effect=AssertionError("No paid generation")) as synth:
                with self.assertRaisesRegex(VideoHandoffBlocked,"pronunciation QA"):
                    complete_from_published(source=self.source,require_slide_tts_qa=True)
        synth.assert_not_called()

    def test_successful_full_handoff_uses_existing_verified_sourcebound_renderer(self):
        def fake_generate(*,source,slides,script,local_work_root):
            for name in ("element_narration_plan.json",
                         "element_tts_manifest.json"):
                (source.parent/name).write_text("{}",encoding="utf8")
            (source.parent/"element_wav").mkdir()
        flag={"rendered":False}
        def valid(stage,folder):
            return flag["rendered"] if stage=="video" else True
        def render(**kwargs):
            self.assertEqual(kwargs["source"],self.source)
            self.assertEqual(kwargs["slides"],self.source.parent/"slides.pdf")
            self.assertTrue(kwargs["authored"].is_file())
            flag["rendered"]=True
            return {"status":"INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO",
                    "part_count":2}
        with patch("selenium_pipeline.runner.check_valid",side_effect=valid),\
             patch("selenium_pipeline.slide_narration_sync.verify"),\
             patch("selenium_pipeline.source_numbered_example_coverage.require_coverage"),\
             patch("selenium_pipeline.automatic_element_audio_stage.produce_element_audio",
                   side_effect=fake_generate) as make,\
             patch("selenium_pipeline.sourcebound_production_video.render_and_install_prepared",
                   side_effect=render) as render_call:
            result=complete_from_published(source=self.source,
                                           require_slide_tts_qa=True)
        make.assert_called_once()
        render_call.assert_called_once()
        self.assertTrue(result["new_generation_performed"])
        self.assertEqual(result["part_count"],2)
        self.assertFalse(result["student_publication_authorized"])

if __name__ == "__main__":
    unittest.main()
