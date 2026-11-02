"""Regression: decoded encoded-frame batch must use repository's existing FFmpeg version policy."""
from __future__ import annotations
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from selenium_pipeline.encoded_highlight_pixels import (
    _decode_selected, EncodedPixelQAError,
)
from selenium_pipeline.ffmpeg_fps_mode_compat import fps_mode_flags
from selenium_pipeline.highlight_video_preview import ffmpeg_path


class IndexedEncodedFrameCompatibility(unittest.TestCase):
    def test_existing_version_helper_is_reused_not_a_second_implementation(self):
        import inspect
        import selenium_pipeline.encoded_highlight_pixels as decoder
        source = inspect.getsource(decoder._decode_selected)
        self.assertIn('fps_mode_flags(exe,"vfr")', source)
        self.assertNotIn('"-vsync","0"', source)

    def test_actual_windows_ffmpeg_batch_select_returns_exact_order(self):
        ffmpeg = ffmpeg_path()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for i,color in enumerate(((245,22,22),(22,245,22),(22,22,245))):
                Image.new("RGB",(64,64),color).save(root/f"source_{i:03d}.png")
            movie = root/"source_test.mp4"
            cmd=[ffmpeg,"-hide_banner","-loglevel","error",
                 "-framerate","1","-i",str(root/"source_%03d.png"),
                 "-pix_fmt","yuv420p","-c:v","libx264",str(movie)]
            completed=subprocess.run(cmd,capture_output=True,text=True,timeout=45)
            self.assertEqual(completed.returncode,0,completed.stderr)
            with tempfile.TemporaryDirectory() as output:
                selected=_decode_selected(movie,[2,0],output_dir=Path(output),exe=ffmpeg)
                self.assertEqual(sorted(selected),[0,2])
                self.assertEqual(len(list(Path(output).glob("selected_*.png"))),2)
                with Image.open(selected[0]) as a, Image.open(selected[2]) as b:
                    pix_a=a.convert("RGB").getpixel((32,32))
                    pix_b=b.convert("RGB").getpixel((32,32))
                    self.assertGreater(pix_a[0],200)
                    self.assertLess(pix_a[1],60)
                    self.assertGreater(pix_b[2],200)
                    self.assertLess(pix_b[0],60)
                self.assertEqual(len(fps_mode_flags(ffmpeg,"vfr")),2)

    def test_invalid_frame_indices_never_run_ffmpeg(self):
        with patch("selenium_pipeline.encoded_highlight_pixels.subprocess.run",
                   side_effect=AssertionError("must not call decoder")):
            for x in ([],[-1],[True],[1.5]):
                with self.subTest(indices=x), tempfile.TemporaryDirectory() as p:
                    with self.assertRaises(EncodedPixelQAError):
                        _decode_selected(Path(p)/"nonexistent.mp4",x,
                                         output_dir=Path(p),exe="ffmpeg")


if __name__=="__main__":
    unittest.main()
