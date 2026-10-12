"""Real-media and offline regression coverage for FFmpeg stage recovery."""
from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from selenium_pipeline import runner, video_ffmpeg


class VideoRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def write_wav(self, slide: int, seconds: int):
        with wave.open(str(self.folder / f"slide{slide}.wav"), "wb") as sound:
            sound.setnchannels(1)
            sound.setsampwidth(2)
            sound.setframerate(44100)
            sound.writeframes(b"\0\0" * (44100 * seconds))

    def test_input_hash_and_profile_invalidate_cache(self):
        pdf = self.folder / "slide1.pdf"
        pdf.write_bytes(b"%PDF first")
        self.write_wav(1, 2)
        wav = self.folder / "slide1.wav"
        baseline = video_ffmpeg._segment_signature(pdf, wav, 2.0, 2, 1280, 720)
        self.assertEqual(baseline, video_ffmpeg._segment_signature(
            pdf, wav, 2.0, 2, 1280, 720))
        self.assertNotEqual(baseline, video_ffmpeg._segment_signature(
            pdf, wav, 2.0, 24, 1280, 720))
        pdf.write_bytes(b"%PDF changed")
        self.assertNotEqual(baseline, video_ffmpeg._segment_signature(
            pdf, wav, 2.0, 2, 1280, 720))
        self.write_wav(1, 3)
        self.assertNotEqual(baseline, video_ffmpeg._segment_signature(
            pdf, wav, 3.0, 2, 1280, 720))

    def test_cache_is_local_and_stable(self):
        root = self.folder / "local_cache"
        with patch.dict(os.environ, {"MICROGEN_VIDEO_CACHE_ROOT": str(root)}):
            a = video_ffmpeg._video_cache(self.folder / "subchapter")
            b = video_ffmpeg._video_cache(self.folder / "subchapter")
            via_alias = video_ffmpeg._video_cache(self.folder / "subchapter" / ".." / "subchapter")
            other = video_ffmpeg._video_cache(self.folder / "another")
        self.assertEqual(a, b)
        self.assertEqual(a, via_alias, "Equivalent Windows canonical paths must share recovery cache")
        self.assertNotEqual(a, other)
        self.assertTrue(a.is_relative_to(root))

    def test_process_tree_termination_is_scoped_to_video(self):
        process = SimpleNamespace(pid=19673, poll=lambda: None, wait=lambda timeout: 0)
        with patch.object(runner, "os", SimpleNamespace(name="nt")), \
             patch.object(runner.subprocess, "run") as taskkill:
            runner._terminate_child(process, whole_tree=True)
        command = taskkill.call_args.args[0]
        self.assertEqual(command, ["taskkill", "/PID", "19673", "/T", "/F"])

    def test_actual_mp4_resume_and_preservation(self):
        try:
            import fitz
            video_ffmpeg.ffmpeg_executable()
        except (ImportError, FileNotFoundError):
            self.skipTest("Real media test requires PyMuPDF and imageio-ffmpeg")
        # Source content is synthetic and temporary, never a production lecture.
        for number, duration in ((1, 2), (2, 3)):
            pdf = fitz.open()
            page = pdf.new_page(width=640, height=360)
            page.insert_text((25, 85), f"MicroGen slide {number}", fontsize=24)
            pdf.save(str(self.folder / f"slide{number}.pdf"))
            pdf.close()
            self.write_wav(number, duration)

        with patch.dict(os.environ, {"MICROGEN_VIDEO_CACHE_ROOT": str(self.folder / "cache")}):
            original_run = video_ffmpeg.run_ffmpeg

            def inject_interruption(exe, args, *, step):
                if step == "slide 2":
                    raise RuntimeError("injected interruption")
                return original_run(exe, args, step=step)

            with patch.object(video_ffmpeg, "run_ffmpeg", side_effect=inject_interruption):
                with self.assertRaisesRegex(RuntimeError, "injected interruption"):
                    video_ffmpeg.assemble(self.folder)
            cache = video_ffmpeg._video_cache(self.folder)
            self.assertTrue((cache / "segment0001.mp4").is_file())
            self.assertFalse((self.folder / "slides.mp4").exists())

            with patch.object(video_ffmpeg, "run_ffmpeg", wraps=original_run) as watched:
                dest = video_ffmpeg.assemble(self.folder)
                self.assertEqual([call.kwargs["step"] for call in watched.call_args_list],
                                 ["slide 2", "concat"])
            self.assertFalse(cache.exists())
            video_ffmpeg.validate_video(video_ffmpeg.ffmpeg_executable(), dest, 5)
            former_sha = hashlib.sha256(dest.read_bytes()).hexdigest()

            self.write_wav(2, 4)  # invalidate only the changed media input
            video_ffmpeg.assemble(self.folder)
            video_ffmpeg.validate_video(video_ffmpeg.ffmpeg_executable(), dest, 6)
            archived = list((self.folder / ".history").rglob("slides.mp4"))
            self.assertEqual(len(archived), 1)
            self.assertEqual(hashlib.sha256(archived[0].read_bytes()).hexdigest(), former_sha)


if __name__ == "__main__":
    unittest.main()
