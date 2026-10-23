import unittest
from unittest.mock import patch
from subprocess import CompletedProcess
from selenium_pipeline.ffmpeg_fps_mode_compat import (
    fps_mode_flags,FfmpegSyncOptionError)
class VideoSyncVersion(unittest.TestCase):
    def test_legacy_v4_uses_documented_vsync(self):
        with patch("selenium_pipeline.ffmpeg_fps_mode_compat.subprocess.run",
                   return_value=CompletedProcess([],0,
                      "ffmpeg version 4.0.2 Copyright\n","")):
            self.assertEqual(fps_mode_flags("ffmpeg","vfr"),["-vsync","vfr"])
            self.assertEqual(fps_mode_flags("ffmpeg","cfr"),["-vsync","cfr"])
    def test_modern_version_uses_fps_mode(self):
        with patch("selenium_pipeline.ffmpeg_fps_mode_compat.subprocess.run",
                   return_value=CompletedProcess([],0,
                        "ffmpeg version n7.1.1 Copyright\n","")):
            self.assertEqual(fps_mode_flags("ffmpeg","vfr"),["-fps_mode","vfr"])
    def test_no_unknown_or_failed_encoder_assumption(self):
        for reply in ("", "ffmpeg version N-12345\n","ffmpeg version 2.8\n"):
            with patch("selenium_pipeline.ffmpeg_fps_mode_compat.subprocess.run",
                       return_value=CompletedProcess([],0,reply,"")):
                with self.assertRaises(FfmpegSyncOptionError):
                    fps_mode_flags("ffmpeg","vfr")
        with self.assertRaises(FfmpegSyncOptionError):fps_mode_flags("ffmpeg","x")
