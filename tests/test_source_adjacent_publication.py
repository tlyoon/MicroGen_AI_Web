"""Source-root and output-publication regression tests (no Gemini required)."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.runner import REPO, Settings, main
from selenium_pipeline.output_paths import resolve_source_root
from microgen_batch import build_parser, prepare_stage, publish, numbered_files
from unittest.mock import patch

from selenium_pipeline.output_paths import (
    assert_writable_directory,
    publish_stage_outputs,
    verify_source_tree,
)


class SourceAdjacentPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source_dir = self.root / "22" / "22.3"
        self.source_dir.mkdir(parents=True)
        self.source = self.source_dir / "source.pdf"
        self.source.write_bytes(b"%PDF-1.7\nsource")
        self.work = self.source_dir / ".microgen_work"
        self.work.mkdir()

    def test_default_workspace_is_inside_source_subchapter(self):
        setting = Settings(source_root=self.root, work_root=None, subchapter="22.3")
        self.assertEqual(setting.source(), self.source)
        self.assertEqual(setting.directory(), self.source_dir / ".microgen_work")
        custom = Settings(source_root=self.root, work_root=self.root / "scratch", subchapter="22.3")
        self.assertEqual(custom.directory(), self.root / "scratch" / "22" / "22.3")

    def test_cli_uses_separate_explicit_source_root(self):
        with patch.dict(os.environ, {"MICROGEN_SOURCE_ROOT": ""}):
            with patch("selenium_pipeline.runner.execute") as mocked:
                self.assertEqual(main(["--source-root", str(self.root), "--subchapter", "22.3", "--dry-run"]), 0)
                setting = mocked.call_args.args[0]
                self.assertEqual(setting.source_root, self.root.resolve())
                self.assertIsNone(setting.work_root)
                self.assertTrue(setting.dry_run)

    def test_cli_accepts_env_source_root(self):
        with patch.dict(os.environ, {"MICROGEN_SOURCE_ROOT": str(self.root)}):
            with patch("selenium_pipeline.runner.execute") as mocked:
                self.assertEqual(main(["--subchapter", "22.3", "--dry-run"]), 0)
                self.assertEqual(mocked.call_args.args[0].source_root, self.root.resolve())

    def test_missing_source_root_fails_instead_of_using_repo(self):
        with patch.dict(os.environ, {"MICROGEN_SOURCE_ROOT": ""}):
            with self.assertRaises(SystemExit) as raised:
                main(["--subchapter", "22.3", "--dry-run"])
            self.assertEqual(raised.exception.code, 2)

    def test_source_root_is_distinct_from_code_root(self):
        with self.assertRaises(ValueError):
            resolve_source_root(REPO, code_root=REPO)
        with self.assertRaises(ValueError):
            resolve_source_root("https://drive.google.com/example", code_root=REPO)

    def test_nested_source_directory_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_source_root(REPO / "tests", code_root=REPO)
        with self.assertRaises(ValueError):
            resolve_source_root(REPO.parent, code_root=REPO)

    def test_explicit_source_root_overrides_env(self):
        with patch.dict(os.environ, {"MICROGEN_SOURCE_ROOT": str(REPO)}):
            root = resolve_source_root(self.root, code_root=REPO)
            self.assertEqual(root, self.root.resolve())

    def test_batch_parser_supports_independent_roots_without_work_root(self):
        args = build_parser().parse_args(["--source-root", str(self.root), "--targets", "22.3"])
        self.assertEqual(args.source_root, self.root)
        self.assertIsNone(args.work_root)

    def test_batch_stages_in_hidden_source_subfolder(self):
        separate_code_root = REPO
        stage, checkpoint, cp_path = prepare_stage(
            separate_code_root, self.root, None, "22.3", 0, "test"
        )
        self.assertEqual(stage, self.source_dir / ".microgen_batch_work")
        self.assertTrue(cp_path.exists())
        self.assertTrue((stage / "source.pdf").exists())

    def test_batch_publishes_audio_and_individual_slide_pdfs(self):
        (self.work / "slides.pdf").write_bytes(b"PDF")
        (self.work / "slides.tex").write_text("latex", encoding="utf-8")
        (self.work / "script.txt").write_text("narration", encoding="utf-8")
        (self.work / "slide1.wav").write_bytes(b"RIFF" + b"x" * 40)
        (self.work / "slide1.pdf").write_bytes(b"%PDF")
        (self.work / "slides.mp4").write_bytes(b"video")
        (self.work / "microgen_batch.log").write_text("log", encoding="utf-8")
        publish(self.work, self.source_dir)
        self.assertTrue((self.source_dir / "slide1.wav").exists())
        self.assertTrue((self.source_dir / "slide1.pdf").exists())
        self.assertTrue((self.source_dir / "slides.mp4").exists())
        self.assertTrue((self.source_dir / "microgen_batch.log").exists())
        self.assertEqual(len(numbered_files(self.source_dir, "wav")), 1)
        self.assertEqual(self.source.read_bytes(), b"%PDF-1.7\nsource")

    def test_root_and_subchapter_are_writable(self):
        verify_source_tree(self.root, self.source)
        self.assertFalse(list(self.root.glob(".microgen_write_probe_*")))
        self.assertFalse(list(self.source_dir.glob(".microgen_write_probe_*")))

    def test_missing_root_is_not_created(self):
        with self.assertRaises(NotADirectoryError):
            assert_writable_directory(self.root / "missing")

    def test_source_must_be_within_root(self):
        other_root = self.root / "other"
        other_root.mkdir()
        with self.assertRaises(ValueError):
            verify_source_tree(other_root, self.source)

    def test_slides_publish_beside_pdf_not_inside_workspace_only(self):
        (self.work / "slides.tex").write_text("slides", encoding="utf-8")
        (self.work / "slides.pdf").write_bytes(b"%PDF-1.7 slides")
        (self.work / "microgen_slides.log").write_text("OK", encoding="utf-8")
        (self.work / ".selenium_pipeline_state.json").write_text("{}", encoding="utf-8")
        (self.work / "selenium.py").write_text("DO NOT PUBLISH", encoding="utf-8")
        published = publish_stage_outputs(self.work, self.source, "slides")
        self.assertIn(self.source_dir / "slides.pdf", published)
        self.assertEqual((self.source_dir / "slides.pdf").read_bytes(), b"%PDF-1.7 slides")
        self.assertFalse((self.source_dir / "selenium.py").exists())
        self.assertEqual(self.source.read_bytes(), b"%PDF-1.7\nsource")

    def test_wav_video_and_slide_pdfs_publish(self):
        (self.work / "slide1.wav").write_bytes(b"RIFF" + b"x" * 40)
        (self.work / "slide1.tmp.wav").write_bytes(b"bad")
        (self.work / "slide1.pdf").write_bytes(b"pdf")
        (self.work / "slides.mp4").write_bytes(b"mp4")
        publish_stage_outputs(self.work, self.source, "tts")
        publish_stage_outputs(self.work, self.source, "video")
        self.assertTrue((self.source_dir / "slide1.wav").exists())
        self.assertTrue((self.source_dir / "slide1.pdf").exists())
        self.assertTrue((self.source_dir / "slides.mp4").exists())
        self.assertFalse((self.source_dir / "slide1.tmp.wav").exists())

    def test_failed_stage_diagnostics_do_not_overwrite_good_media(self):
        (self.source_dir / "slides.pdf").write_bytes(b"good")
        (self.work / "slides.pdf").write_bytes(b"bad")
        (self.work / "microgen_slides.log").write_text("failure", encoding="utf-8")
        publish_stage_outputs(self.work, self.source, "slides", diagnostics_only=True)
        self.assertEqual((self.source_dir / "slides.pdf").read_bytes(), b"good")
        self.assertTrue((self.source_dir / "microgen_slides.log").exists())


if __name__ == "__main__":
    unittest.main()
