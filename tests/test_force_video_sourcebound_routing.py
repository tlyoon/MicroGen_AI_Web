"""No CLI force or video-only restart may use a static-slide renderer.

True Windows runner dispatch tests, no network, Gemini, TTS, paid requests or
publisher file modifications. Sourcebound multipart evidence is still required.
"""
from __future__ import annotations
import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from selenium_pipeline import runner


class VideoOnlyForcedPathSafetyTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        self.source_root=self.root/"original"
        self.source=self.source_root/"8"/"8.4"/"source.pdf"
        self.source.parent.mkdir(parents=True)
        with pymupdf.open() as doc:
            doc.new_page()
            doc.save(self.source)

    def setting(self,forced):
        return runner.Settings(
            source_root=self.source_root,work_root=self.root/"staging",
            subchapter="8.4",from_stage="video",through_stage="video",
            force_from=forced)

    def test_force_video_still_uses_same_sourcebound_multipart_producer(self):
        settings=self.setting("video")
        with patch("selenium_pipeline.runner.check_valid",return_value=False), \
             patch("selenium_pipeline.full_pipeline_video_handoff.complete_from_published",
                return_value={"status":"INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO",
                              "part_count":2,"student_publication_authorized":False}) as bridge, \
             patch("selenium_pipeline.runner.run_cmd",
                   side_effect=AssertionError("Old static video command prohibited")) as run, \
             patch("selenium_pipeline.launch_gemini.launch",
                   side_effect=AssertionError("No Chrome for sourcebound video only")):
            result=runner._execute_unlocked(settings)
        self.assertEqual(result,settings.directory())
        bridge.assert_called_once_with(source=self.source,
                                      require_slide_tts_qa=False)
        run.assert_not_called()
        self.assertFalse((self.source.parent/"slides.mp4").exists())

    def test_force_video_with_accepted_media_does_not_regenerate(self):
        settings=self.setting("video")
        with patch("selenium_pipeline.runner.check_valid",return_value=True), \
             patch("selenium_pipeline.full_pipeline_video_handoff.complete_from_published",
                   side_effect=AssertionError("Accepted media must not rerender")) as bridge:
            self.assertEqual(runner._execute_unlocked(settings),
                             settings.directory())
        bridge.assert_not_called()

    def test_unrelated_force_stage_cannot_enter_video_only_static_backend(self):
        settings=self.setting("figures")
        with patch("selenium_pipeline.runner.run_cmd",
                   side_effect=AssertionError("Never launch old ffmpeg")) as run:
            with self.assertRaisesRegex(ValueError,
                                        "Video-only force-from"):
                runner._execute_unlocked(settings)
        run.assert_not_called()

    def test_legacy_video_ffmpeg_is_absent_from_main_stage_dispatch(self):
        source=inspect.getsource(runner._execute_unlocked)
        self.assertNotIn('str(REPO / "selenium_pipeline" / "video_ffmpeg.py")',
                         source)
        self.assertNotIn('str(REPO / "selenium_pipeline" / "slide_pdf_split.py")',
                         source)
        self.assertIn("Legacy static-slide video backend is prohibited",source)
        self.assertIn('if s.from_stage == "video" and s.through_stage == "video":',
                      source)


if __name__=="__main__":
    unittest.main()
