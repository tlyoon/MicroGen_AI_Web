import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.runner import Settings, blocks, job_source, check_valid, execute, archive_existing_outputs


class PipelineTests(unittest.TestCase):
    def test_parse_reference_script(self):
        example = "**Slide 1 [10 sec]:\nTitle**\n\n**Slide 2 [40 sec]:\nPhysics explanation.**"
        self.assertEqual(blocks(example), [(1, "Title"), (2, "Physics explanation.")])

    def test_reject_missing_block(self):
        with self.assertRaises(ValueError):
            blocks("**Slide 1 [10 sec]:\nA**\n\n**Slide 3 [20 sec]:\nC**")

    def test_validate_source_subchapter(self):
        self.assertEqual(job_source(Path("Serway"), "22.1"), Path("Serway/22/22.1/source.pdf"))
        with self.assertRaises(ValueError):
            job_source(Path("Serway"), "../../sensitive")

    def test_dry_run_does_not_touch_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "root"
            source = root / "22" / "22.1"
            source.mkdir(parents=True)
            (source / "source.pdf").write_bytes(b"%PDF placeholder for dry-run only")
            workspace = Path(td) / "work"
            folder = execute(Settings(root, workspace, "22.1", dry_run=True))
            self.assertEqual(folder, workspace / "22" / "22.1")
            self.assertFalse(folder.exists())

    def test_pro_attestation_required_before_work(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "root"
            folder = root / "22" / "22.1"
            folder.mkdir(parents=True)
            (folder / "source.pdf").write_bytes(b"%PDF stub")
            dest = Path(td) / "working"
            with self.assertRaisesRegex(RuntimeError, "manually select Gemini Pro"):
                execute(Settings(root, dest, "22.1"))
            self.assertFalse(dest.exists())

    def test_regeneration_preserves_previous_slide_files(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / "slides.tex").write_text("prior LaTeX", encoding="utf-8")
            (folder / "slides.pdf").write_bytes(b"previous deck")
            archive_existing_outputs("slides", folder)
            self.assertFalse((folder / "slides.tex").exists())
            self.assertFalse((folder / "slides.pdf").exists())
            archived = list((folder / ".history").rglob("slides.tex"))
            self.assertEqual(len(archived), 1)
            self.assertEqual(archived[0].read_text(encoding="utf-8"), "prior LaTeX")

    def test_missing_artifacts_fail_validation(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            self.assertFalse(check_valid("slides", folder))
            self.assertFalse(check_valid("narration", folder))
            self.assertFalse(check_valid("tts", folder))
            self.assertFalse(check_valid("video", folder))


if __name__ == "__main__":
    unittest.main()
