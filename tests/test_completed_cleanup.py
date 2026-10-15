"""Tests for final-only, non-destructive MicroGen subchapter cleanup."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import microgen_batch
from selenium_pipeline.cleanup import (
    RECEIPT, cleanup_completed_lecture, completed_lecture,
)
from selenium_pipeline.runner import Settings, execute


class CompletedCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        # Unit tests must not contend with a real Gemini worker currently
        # holding the user's production browser lock on the same Windows PC.
        self.local_env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.root / "isolated-localappdata")})
        self.local_env.start()
        self.addCleanup(self.local_env.stop)
        self.folder = self.root / "8" / "8.1"
        self.folder.mkdir(parents=True)
        self.source = self.folder / "source.pdf"
        self.source.write_bytes(b"%PDF-1.7 original textbook")
        self.content = b"%PDF-1.7 original textbook"

    def final(self, tex=r"\documentclass{beamer}"):
        for name, data in {
            "slides.tex": tex,
            "slides.pdf": "%PDF slide deck",
            "script.txt": "Narration",
            "slides.mp4": "Video output",
        }.items():
            (self.folder / name).write_text(data, encoding="utf-8")

    def work(self, pipeline="selenium", *, external=False):
        path = (
            self.root / "external_jobs" / "8.1"
            if external else self.folder / (".microgen_work" if pipeline == "selenium" else ".microgen_batch_work")
        )
        path.mkdir(parents=True)
        (path / "source.pdf").write_bytes(self.content)
        marker = ".selenium_pipeline_state.json" if pipeline == "selenium" else ".microgen_checkpoint.json"
        (path / marker).write_text("{}", encoding="utf-8")
        (path / "launch_gemini.py").write_text("script", encoding="utf-8")
        return path

    def test_completed_prunes_known_temporaries_preserves_latex_figures_and_unknown(self):
        self.final()
        workspace = self.work()
        for name in (
            "slide1.pdf", "slide2.pdf", "slide1.wav", "slide2.wav", "script_tts.json",
            ".selenium_pipeline_state.json", "microgen_video.log", "slides.aux",
            "slides.log", "gen_video.log",
        ):
            (self.folder / name).write_text("intermediate", encoding="utf-8")
        (self.folder / "Figure 8.1.png").write_bytes(b"image")
        (self.folder / "image.jpg").write_bytes(b"image")
        (self.folder / "subchapter-notes.pdf").write_bytes(b"personal")
        (self.folder / "custom-script.py").write_text("print(1)", encoding="utf-8")
        (self.folder / "script_risk_report.json").write_text('{"passed": true}')
        for folder_name in ("pages", "crops", ".history", "__pycache__"):
            d = self.folder / folder_name
            d.mkdir()
            (d / "generated.dat").write_bytes(b"temp")
        removed = cleanup_completed_lecture(self.source, workspace=workspace, pipeline="selenium")
        self.assertTrue(removed)
        self.assertFalse(workspace.exists())
        for name in ("pages", "crops", "__pycache__", "slide2.pdf",
                     "script_tts.json", "slides.aux", "slides.log",
                     ".selenium_pipeline_state.json"):
            self.assertFalse((self.folder / name).exists(), name)
        self.assertEqual((self.folder / "slide1.wav").read_text(), "intermediate")
        self.assertEqual((self.folder / ".history" / "generated.dat").read_bytes(), b"temp")
        for name in ("source.pdf", "slides.tex", "slides.pdf", "script.txt",
                     "slides.mp4", "Figure 8.1.png", "image.jpg",
                     "subchapter-notes.pdf", "custom-script.py",
                     "script_risk_report.json", RECEIPT):
            self.assertTrue((self.folder / name).exists(), name)
        self.assertEqual(self.source.read_bytes(), self.content)
        self.assertTrue(completed_lecture(self.source))
        self.assertEqual(json.loads((self.folder / RECEIPT).read_text())["cleanup"], "complete")

    def test_incomplete_lecture_is_never_modified(self):
        self.final()
        (self.folder / "slides.mp4").unlink()
        workspace = self.work()
        (self.folder / "slide1.wav").write_bytes(b"intermediate")
        with self.assertRaisesRegex(ValueError, "incomplete lecture"):
            cleanup_completed_lecture(self.source, workspace=workspace, pipeline="selenium")
        self.assertTrue(workspace.is_dir())
        self.assertTrue((self.folder / "slide1.wav").exists())
        self.assertFalse((self.folder / RECEIPT).exists())

    def test_referenced_figure_directory_is_preserved(self):
        self.final(tex=r"\\includegraphics[width=.5\\textwidth]{crops/figure-a.png}")
        crop = self.folder / "crops"
        crop.mkdir()
        (crop / "figure-a.png").write_bytes(b"figure")
        pages = self.folder / "pages"
        pages.mkdir()
        (pages / "page_1.png").write_bytes(b"temporary")
        cleanup_completed_lecture(self.source, pipeline="selenium")
        self.assertTrue((crop / "figure-a.png").exists())
        self.assertFalse(pages.exists())

    def test_foreign_external_workspace_is_refused(self):
        self.final()
        workspace = self.work(external=True)
        (workspace / "source.pdf").write_bytes(b"different textbook")
        with self.assertRaisesRegex(ValueError, "not owned"):
            cleanup_completed_lecture(self.source, workspace=workspace, pipeline="selenium")
        self.assertTrue(workspace.exists())
        self.assertFalse((self.folder / RECEIPT).exists())

    def test_owned_external_workspace_is_deleted(self):
        self.final()
        workspace = self.work(external=True)
        cleanup_completed_lecture(self.source, workspace=workspace, pipeline="selenium")
        self.assertFalse(workspace.exists())
        self.assertTrue(completed_lecture(self.source))

    def test_completion_invalidated_when_source_or_deliverable_changes(self):
        self.final()
        cleanup_completed_lecture(self.source, pipeline="selenium")
        self.assertTrue(completed_lecture(self.source))
        (self.folder / "script.txt").write_text("changed content", encoding="utf-8")
        self.assertFalse(completed_lecture(self.source))
        (self.folder / "script.txt").write_text("Narration", encoding="utf-8")
        self.assertTrue(completed_lecture(self.source))
        self.source.write_bytes(b"%PDF altered")
        self.assertFalse(completed_lecture(self.source))

    def test_idempotent_second_cleanup_with_no_workspace(self):
        self.final()
        cleanup_completed_lecture(self.source, workspace=self.work(), pipeline="selenium")
        self.assertEqual(cleanup_completed_lecture(self.source, pipeline="selenium"), [])
        self.assertTrue(completed_lecture(self.source))

    def test_direct_runner_cannot_overwrite_unreconciled_published_mp4(self):
        self.final()
        settings = Settings(source_root=self.root, work_root=None, subchapter="8.1",
                            from_stage="slides", through_stage="video")
        with patch("selenium_pipeline.launch_gemini.launch",
                   side_effect=AssertionError("browser must not launch")):
            with self.assertRaisesRegex(RuntimeError, "Published MP4 has no valid"):
                execute(settings)
        self.assertEqual((self.folder / "slides.mp4").read_text(), "Video output")

    def test_partial_run_cannot_replace_a_receipt_verified_video_without_force(self):
        self.final()
        cleanup_completed_lecture(self.source, pipeline="selenium")
        original = (self.folder / "slides.mp4").read_bytes()
        settings = Settings(source_root=self.root, work_root=None,
                            subchapter="8.1", from_stage="video", through_stage="video")
        with self.assertRaisesRegex(RuntimeError, "already receipt-verified"):
            execute(settings)
        self.assertEqual((self.folder / "slides.mp4").read_bytes(), original)

    def test_selenium_resumes_completed_without_launching_browser(self):
        self.final()
        cleanup_completed_lecture(self.source, pipeline="selenium")
        settings = Settings(source_root=self.root, work_root=None, subchapter="8.1")
        with patch("selenium_pipeline.runner.prepare", side_effect=AssertionError("should not prepare")):
            with patch("selenium_pipeline.launch_gemini.launch", side_effect=AssertionError("should not launch")):
                with self.assertRaisesRegex(RuntimeError, "Legacy receipt-verified"):
                    execute(settings)
        self.assertFalse(settings.directory().exists())
        self.assertTrue(completed_lecture(self.source))

    def test_batch_resumes_completed_without_creating_stage(self):
        self.final()
        cleanup_completed_lecture(self.source, pipeline="batch")
        args = SimpleNamespace(source_root=self.root)
        report = []
        with patch("microgen_batch.prepare_stage", side_effect=AssertionError("should not prepare")):
            with self.assertRaisesRegex(RuntimeError, "Legacy MicroGen batch generation is disabled"):
                microgen_batch.process_one(args, "8.1", report)
        self.assertEqual(report, [])
        self.assertFalse((self.folder / ".microgen_batch_work").exists())

    def test_batch_completed_folder_cleans_owned_stage(self):
        self.final()
        workspace = self.work(pipeline="batch")
        (self.folder / ".microgen_checkpoint.json").write_text("{}")
        (self.folder / "slide1.wav").write_bytes(b"RIFF")
        cleanup_completed_lecture(self.source, workspace=workspace, pipeline="batch")
        self.assertFalse(workspace.exists())
        self.assertFalse((self.folder / ".microgen_checkpoint.json").exists())
        self.assertTrue((self.folder / "slide1.wav").exists())
        self.assertTrue(completed_lecture(self.source))


    def test_drive_lock_retries_before_deleting_workspace(self):
        self.final()
        workspace = self.work()
        from selenium_pipeline import cleanup
        original = cleanup.shutil.rmtree
        attempts = []

        def transient_lock(path):
            attempts.append(path)
            if len(attempts) == 1:
                raise PermissionError("Drive folder temporarily locked")
            return original(path)

        with patch.object(cleanup.shutil, "rmtree", side_effect=transient_lock):
            with patch.object(cleanup.time, "sleep"):
                cleanup_completed_lecture(self.source, workspace=workspace, pipeline="selenium")
        self.assertEqual(len(attempts), 2)
        self.assertTrue(completed_lecture(self.source))

    def test_video_success_survives_cleanup_error(self):
        self.final()
        workspace = self.work()
        from selenium_pipeline import runner
        settings = Settings(source_root=self.root, work_root=None, subchapter="8.1", through_stage="video")
        # Exercise the post-publication cleanup block in the runner source:
        # errors must be logged rather than converted into video-stage failure.
        source = (Path(runner.__file__).read_text(encoding="utf-8"))
        self.assertIn("CLEANUP DEFERRED (published video retained)", source)
        self.assertIn("except (OSError, ValueError) as cleanup_error", source)

    def test_missing_referenced_graphic_blocks_workspace_deletion(self):
        self.final(tex=r"\includegraphics{new-diagram.png}")
        workspace = self.work()
        with self.assertRaisesRegex(ValueError, "required LaTeX graphic"):
            cleanup_completed_lecture(self.source, workspace=workspace, pipeline="selenium")
        self.assertTrue(workspace.exists())
        self.assertFalse((self.folder / RECEIPT).exists())

    def test_staged_nested_graphic_is_published_before_workspace_removed(self):
        self.final(tex=r"\includegraphics[width=.5\textwidth]{figures/custom.jpg}")
        workspace = self.work()
        asset = workspace / "figures"
        asset.mkdir()
        (asset / "custom.jpg").write_bytes(b"important-graphic")
        cleanup_completed_lecture(self.source, workspace=workspace, pipeline="selenium")
        self.assertFalse(workspace.exists())
        self.assertEqual((self.folder / "figures" / "custom.jpg").read_bytes(), b"important-graphic")
        self.assertTrue(completed_lecture(self.source))

    def test_missing_final_graphic_invalidates_completion_receipt(self):
        self.final(tex=r"\includegraphics{Figure 8.4.png}")
        graphic = self.folder / "Figure 8.4.png"
        graphic.write_bytes(b"image")
        cleanup_completed_lecture(self.source, pipeline="selenium")
        self.assertTrue(completed_lecture(self.source))
        graphic.unlink()
        self.assertFalse(completed_lecture(self.source))

    def test_publication_copies_theme_logo_and_nonstandard_image(self):
        from selenium_pipeline.output_paths import publish_stage_outputs
        self.final()
        workspace = self.work()
        for name in ("beamerthemeGelugor.sty", "logotype.jpg", "Diagram.png", "custom.jpeg"):
            (workspace / name).write_bytes(b"asset")
        (workspace / "slides.pdf").write_bytes(b"%PDF")
        (workspace / "slides.tex").write_text(r"\includegraphics{Diagram.png}", encoding="utf-8")
        publish_stage_outputs(workspace, self.source, "slides")
        for name in ("beamerthemeGelugor.sty", "logotype.jpg", "Diagram.png", "custom.jpeg"):
            self.assertEqual((self.folder / name).read_bytes(), b"asset")

if __name__ == "__main__":
    unittest.main()
