"""Offline end-to-end PDF/WAV -> H.264/AAC and safe failure smoke.

Run: python -m tests.acceptance_media_smoke
Creates temporary synthetic slides/audio only, never edits source PDFs.
"""
from __future__ import annotations
import hashlib
import math
import struct
import tempfile
import wave
from pathlib import Path

import pymupdf
from selenium_pipeline.video_ffmpeg import assemble, check_inputs, ffmpeg_executable, validate_video


def make_audio(path: Path, seconds: float = 0.8):
    rate = 16000
    count = int(rate * seconds)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        payload = b"".join(struct.pack("<h", round(4000 * math.sin(2*math.pi*220*i/rate)))
                           for i in range(count))
        out.writeframes(payload)


def main():
    with tempfile.TemporaryDirectory(prefix="microgen_acceptance_") as temp:
        root = Path(temp)
        with pymupdf.open() as combined:
            for number in (1, 2):
                page = combined.new_page()
                page.insert_text((75, 90), f"Physics teaching slide {number}")
            for idx in range(2):
                with pymupdf.open() as one:
                    one.insert_pdf(combined, from_page=idx, to_page=idx)
                    one.save(root / f"slide{idx+1}.pdf")
        for idx in (1, 2):
            make_audio(root / f"slide{idx}.wav")
        (root / ".microgen_static_review_sandbox").write_text(
            "SYNTHETIC TEST ONLY", encoding="utf-8")
        before = {n: hashlib.sha256((root/n).read_bytes()).hexdigest()
                  for n in ("slide1.wav", "slide2.wav")}
        result = assemble(root, output="REVIEW_ONLY_static_slides.mp4",
                          _offline_test_only=True, width=640, height=360, fps=12)
        validate_video(ffmpeg_executable(), result, 1.6)
        assert result.is_file() and result.stat().st_size > 2048
        assert before == {n: hashlib.sha256((root/n).read_bytes()).hexdigest()
                          for n in before}
        # Inject an absent narration segment: original video must survive.
        original = hashlib.sha256(result.read_bytes()).hexdigest()
        (root / "slide2.wav").unlink()
        try:
            check_inputs(root)
        except ValueError:
            pass
        else:
            raise AssertionError("Missing WAV unexpectedly passed validation")
        assert hashlib.sha256(result.read_bytes()).hexdigest() == original
        print("MEDIA_ACCEPTANCE_PASS 2 slide pairs, decodable video+audio, "
              "missing-WAV fail-closed and output preserved", flush=True)


if __name__ == "__main__":
    main()
