"""Cross-PC regressions for local PDF splitting, media input staging, and cleanup."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline import cleanup, slide_pdf_split, video_ffmpeg


class PortableMediaSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_split_slides_uses_local_scratch_and_keeps_original(self):
        try:
            from PyPDF2 import PdfWriter
        except ImportError:
            from pypdf import PdfWriter
        deck = self.root / "slides.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=640, height=360)
        writer.add_blank_page(width=640, height=360)
        with deck.open("wb") as stream:
            writer.write(stream)
        original = slide_pdf_split.sha256(deck)
        self.assertEqual(slide_pdf_split.split_slides(self.root), 2)
        self.assertEqual(slide_pdf_split.sha256(deck), original)
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            from pypdf import PdfReader
        for i in (1, 2):
            with (self.root / f"slide{i}.pdf").open("rb") as stream:
                self.assertEqual(len(PdfReader(stream).pages), 1)
        first_hash = slide_pdf_split.sha256(self.root / "slide1.pdf")
        self.assertEqual(slide_pdf_split.split_slides(self.root), 2)
        self.assertEqual(slide_pdf_split.sha256(self.root / "slide1.pdf"), first_hash)

    def test_bad_pdf_preserves_previous_slide(self):
        (self.root / "slides.pdf").write_bytes(b"not a pdf" * 20)
        existing = self.root / "slide1.pdf"
        existing.write_bytes(b"previous verified slide")
        with self.assertRaises(Exception):
            slide_pdf_split.split_slides(self.root)
        self.assertEqual(existing.read_bytes(), b"previous verified slide")

    def test_media_staging_verifies_input_hash(self):
        source = self.root / "remote.wav"
        source.write_bytes(b"preserved audio bytes")
        target = self.root / "cache" / "input.wav"
        target.parent.mkdir()
        digest = video_ffmpeg._sha256(source)
        self.assertEqual(video_ffmpeg._verified_local_input(source, target, digest), target)
        self.assertEqual(target.read_bytes(), source.read_bytes())
        source.write_bytes(b"changed audio")
        with self.assertRaisesRegex(RuntimeError, "changed during local staging"):
            video_ffmpeg._verified_local_input(source, target, digest)
        self.assertEqual(target.read_bytes(), b"preserved audio bytes")

    def test_busy_google_drive_workspace_is_deferred_not_failed(self):
        course = self.root / "3" / "3.2"
        course.mkdir(parents=True)
        original = course / "source.pdf"
        original.write_bytes(b"%PDF-1.7 original textbook")
        for name in ("slides.tex", "slides.pdf", "script.txt", "slides.mp4"):
            (course / name).write_bytes(b"verified " + name.encode())
        stage = course / ".microgen_work"
        stage.mkdir()
        (stage / "source.pdf").write_bytes(original.read_bytes())
        (stage / ".selenium_pipeline_state.json").write_text("{}")
        busy = OSError("directory not empty")
        busy.winerror = 145
        with patch.object(cleanup, "_safe_remove", side_effect=busy):
            removed = cleanup.cleanup_completed_lecture(
                original, workspace=stage, pipeline="selenium")
        self.assertEqual(removed, [])
        receipt = json.loads((course / cleanup.RECEIPT).read_text())
        self.assertEqual(receipt["cleanup"], "deferred")
        self.assertTrue(receipt["cleanup_deferred"])
        self.assertTrue(cleanup.completed_lecture(original))
        self.assertTrue((course / "slides.mp4").exists())
        self.assertTrue(stage.exists())


if __name__ == "__main__":
    unittest.main()
