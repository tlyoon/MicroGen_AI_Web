"""Regression tests for existing-lecture image audit and safe retrofit planning."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import fitz

from selenium_pipeline.retrofit_image_repair import (
    audit, balanced_groups, chapter_audit, patch_files, publish, stage_rebuild,
)


class PartitionTests(unittest.TestCase):
    def test_two_balanced_parts_with_slides_under_six_hundred_seconds(self):
        durations = [51.0] * 15
        ranges = balanced_groups(durations)
        self.assertEqual(ranges[0][0], 1)
        self.assertEqual(ranges[-1][1], 15)
        self.assertEqual(len(ranges), 2)
        self.assertEqual([i for a, b in ranges for i in range(a, b + 1)],
                         list(range(1, 16)))
        self.assertTrue(all(sum(durations[a - 1:b]) <= 585 for a, b in ranges))

    def test_three_parts_for_long_lecture(self):
        durations = [60.0] * 25
        ranges = balanced_groups(durations)
        self.assertEqual(len(ranges), 3)
        self.assertTrue(all(sum(durations[a - 1:b]) <= 585 for a, b in ranges))

    def test_no_speech_raises(self):
        for bad in ([], [1.0, 0.0], [-1.0], [600.0]):
            with self.subTest(durations=bad):
                with self.assertRaises(ValueError):
                    balanced_groups(bad)

    def test_single_short_video_supported(self):
        self.assertEqual(balanced_groups([20.0, 30.0]), [(1, 2)])


class PatchSafetyTests(unittest.TestCase):
    def test_source_pdf_cannot_be_supplied_as_patch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "slides.tex").write_text("patched", encoding="utf8")
            (root / "source.pdf").write_bytes(b"not-authorized")
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                patch_files(root)

    def test_modified_script_requires_full_pipeline(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "slides.tex").write_text("patched")
            (root / "script.txt").write_text("changed audio")
            with self.assertRaises(ValueError):
                patch_files(root)

    def test_figure_patch_is_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "slides.tex").write_text("new image")
            (root / "Figure_8_1.png").write_bytes(b"png bytes")
            self.assertEqual({p.name for p in patch_files(root)},
                             {"slides.tex", "Figure_8_1.png"})

    def test_missing_latex_patch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "fig.png").write_bytes(b"data")
            with self.assertRaises(ValueError):
                patch_files(root)


class HistoricPackageAuditTests(unittest.TestCase):
    def _fake_folder(self, folder: Path, figure: bool = True) -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        src = fitz.open()
        p = src.new_page()
        p.insert_text((50, 70), "Figure 8.1 Energy transfer diagram")
        src.save(folder / "source.pdf")
        src.close()
        slides = fitz.open()
        s = slides.new_page()
        s.insert_text((50, 70), "Energy transfer mechanisms")
        slides.save(folder / "slides.pdf")
        slides.close()
        (folder / "slides.tex").write_text(
            "\\documentclass{beamer}\\n\\begin{document}"
            "\\begin{frame}Energy transfer\\end{frame}\\end{document}",
            encoding="utf8",
        )
        if figure:
            (folder / "Figure_8_1.png").write_bytes(b"known image asset")
        return folder

    def test_missing_latex_inclusion_is_review_not_automatic_pass(self):
        with tempfile.TemporaryDirectory() as d:
            f = self._fake_folder(Path(d) / "8.1")
            original = (f / "source.pdf").read_bytes()
            report = audit(f)
            self.assertEqual(report["result"], "REVIEW_REQUIRED")
            self.assertIn("source_figures_but_no_slide_graphics_review_required",
                          report["review_flags"])
            self.assertEqual(original, (f / "source.pdf").read_bytes())

    def test_natural_order_and_ignores_problems(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "8"
            self._fake_folder(root / "8.10", figure=False)
            self._fake_folder(root / "8.2", figure=False)
            (root / "problems").mkdir()
            self.assertEqual([x["subtopic"] for x in chapter_audit(root)],
                             ["8.2", "8.10"])


class FailClosedPublishTests(unittest.TestCase):
    def test_concurrent_source_change_prevents_publication(self):
        with tempfile.TemporaryDirectory() as d:
            original = Path(d) / "8.1"
            work = Path(d) / "stage"
            original.mkdir()
            work.mkdir()
            (original / "source.pdf").write_bytes(b"already modified")
            values = {
                "subtopic": "8.1",
                "source_folder": str(original.resolve()),
                "status": "STAGED_ACCEPTED",
                "original_checksums": {
                    "source.pdf": hashlib.sha256(b"earlier source").hexdigest()
                },
                "files": [],
                "stage_checksums": {},
            }
            (work / "retrofit_state.json").write_text(json.dumps(values))
            with self.assertRaisesRegex(RuntimeError, "Concurrent modification"):
                publish(original, work)
            self.assertEqual((original / "source.pdf").read_bytes(),
                             b"already modified")


if __name__ == "__main__":
    unittest.main()
