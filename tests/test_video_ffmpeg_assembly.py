"""Fast media-assembly regression tests; do not require FFmpeg or Gemini."""
from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path

from selenium_pipeline import runner
from selenium_pipeline.video_ffmpeg import check_inputs, assemble


class VideoAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def pair(self, n: int, frames: int = 44100):
        (self.root / f"slide{n}.pdf").write_bytes(b"%PDF demo")
        with wave.open(str(self.root / f"slide{n}.wav"), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(44100)
            wav.writeframes(b"\0\0" * frames)

    def test_complete_pairs_have_correct_order_and_duration(self):
        self.pair(2)
        self.pair(1, frames=88200)
        rows = check_inputs(self.root)
        self.assertEqual([n for n, _, _, _ in rows], [1, 2])
        self.assertAlmostEqual(sum(row[3] for row in rows), 3.0)

    def test_missing_wav_aborts_before_touching_mp4(self):
        self.pair(1)
        (self.root / "slide1.wav").unlink()
        current = self.root / "slides.mp4"
        current.write_bytes(b"existing-valid-video")
        with self.assertRaises(ValueError):
            check_inputs(self.root)
        self.assertEqual(current.read_bytes(), b"existing-valid-video")

    def test_noncontiguous_slide_pairs_abort(self):
        self.pair(1)
        self.pair(3)
        with self.assertRaises(ValueError):
            check_inputs(self.root)

    def test_old_moviepy_script_no_longer_invoked(self):
        self.assertEqual(runner.SCRIPTS["video"], ("slice_pdf.py",))

    def test_bad_output_name_rejected(self):
        self.pair(1)
        with self.assertRaises(ValueError):
            assemble(self.root, output="../unsafe.mp4")


if __name__ == "__main__":
    unittest.main()
