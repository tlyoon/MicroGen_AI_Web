"""Synthetic regressions for restoring SHA-pinned original lecture input."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.recover_pinned_original_thomas_corpus import (
    inspect_candidate, resolve_original,
)


class RecoverySelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "Thomas_calculus_13ed" / "8"
        self.counts = {"8.4": 1, "8.5": 1, "8.6": 1}
        self.pins = {}
        for sec in self.counts:
            d = self.root / sec
            d.mkdir(parents=True)
            src = ("real textbook " + sec).encode("utf-8")
            pdf = ("real author pdf " + sec).encode("utf-8")
            (d / "source.pdf").write_bytes(src)
            (d / "slides.pdf").write_bytes(pdf)
            (d / "slides.tex").write_text(r"\begin{frame}A\end{frame}",
                                         encoding="utf-8")
            (d / "script.txt").write_text("original narration", encoding="utf-8")
            (d / "slide1.wav").write_bytes(b"R" * 64)
            self.pins[sec] = (hashlib.sha256(src).hexdigest(),
                              hashlib.sha256(pdf).hexdigest())

    def test_selects_only_matching_preserved_snapshot(self):
        found, details, attempts = resolve_original([Path(self.temp.name)],
            pins=self.pins, counts=self.counts)
        self.assertEqual(found, self.root)
        self.assertEqual(len(details), 3)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(details["8.5"]["original_slide_count"], 1)
        self.assertIn("slide1.wav", details["8.6"]["original_wav_sha256"])

    def test_regenerated_slide_fails_even_when_publisher_is_unchanged(self):
        (self.root / "8.5" / "slides.pdf").write_bytes(b"regenerated")
        got, why = inspect_candidate(self.root, pins=self.pins,
                                     counts=self.counts)
        self.assertIsNone(got)
        self.assertIn("8.5: publisher/author hash mismatch", why)
        with self.assertRaisesRegex(RuntimeError, "PINNED_ORIGINAL_41_SOURCE_NOT_FOUND"):
            resolve_original([Path(self.temp.name)], pins=self.pins,
                             counts=self.counts)

    def test_rejects_missing_original_wav(self):
        (self.root / "8.6" / "slide1.wav").unlink()
        got, why = inspect_candidate(self.root, pins=self.pins,
                                     counts=self.counts)
        self.assertIsNone(got)
        self.assertIn("8.6: missing or linked original input", why)

    def test_rejects_wrong_frame_count_without_modifying_source(self):
        target = self.root / "8.4" / "slides.tex"
        target.write_text(r"\begin{frame}A\end{frame}" * 2, encoding="utf-8")
        before = target.read_bytes()
        got, why = inspect_candidate(self.root, pins=self.pins,
                                     counts=self.counts)
        self.assertIsNone(got)
        self.assertIn("frames 2, expected 1", why)
        self.assertEqual(target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
