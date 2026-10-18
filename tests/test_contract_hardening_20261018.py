"""Fail-closed cross-entrypoint preservation and governance regression checks.

Synthetic, non-billable, no real source PDF/media. Every test starts from
a separate disposable directory and may not publish a student artifact.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline import video_ffmpeg


ROOT = Path(__file__).resolve().parents[1]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class EntrypointContractTests(unittest.TestCase):
    def test_legacy_direct_script_cannot_replace_existing_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            historical = folder / "slides.mp4"
            payload = b"HISTORICAL_MP4_DO_NOT_REPLACE" * 50
            historical.write_bytes(payload)
            (folder / "source.pdf").write_bytes(b"%PDF-1.4\noriginal source")
            scripts = (
                ROOT / "gen_video_v22.py",
                ROOT / "gen_video_fr_png_v2.py",
                ROOT / "selenium_pipeline/vendor_template_v2/gen_video.py",
            )
            for script in scripts:
                with self.subTest(script=script.name):
                    result = subprocess.run(
                        [sys.executable, str(script)],
                        cwd=folder, capture_output=True, text=True, timeout=20
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("disabled", result.stderr.lower())
                    self.assertEqual(sha(historical.read_bytes()), sha(payload))
                    self.assertFalse(list(folder.glob("slide*.pdf")))
                    self.assertEqual(len(list(folder.iterdir())), 2)

    def test_standalone_normal_api_refuses_before_read_or_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            original = folder / "slides.mp4"
            original.write_bytes(b"untouchable")
            with patch.object(video_ffmpeg, "check_inputs",
                              side_effect=AssertionError("must not read input")):
                with patch.object(video_ffmpeg, "_video_cache",
                                  side_effect=AssertionError("must not create cache")):
                    with self.assertRaisesRegex(RuntimeError, "disabled"):
                        video_ffmpeg.assemble(folder)
            self.assertEqual(original.read_bytes(), b"untouchable")
            self.assertEqual(set(p.name for p in folder.iterdir()), {"slides.mp4"})

    def test_cli_cannot_publish_even_with_custom_output_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            original = folder / "slides.mp4"
            original.write_bytes(b"protected")
            with patch.object(sys, "argv",
                              ["video_ffmpeg", "--folder", str(folder),
                               "--output", "alternative.mp4"]):
                self.assertEqual(video_ffmpeg.main(), 1)
            self.assertEqual(original.read_bytes(), b"protected")
            self.assertFalse((folder / "alternative.mp4").exists())

    def test_review_sandbox_requires_marker_no_source_and_new_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            output = "REVIEW_ONLY_static_slides.mp4"
            with self.assertRaisesRegex(ValueError, "sandbox"):
                video_ffmpeg.assemble(folder, output=output, _offline_test_only=True)
            (folder / ".microgen_static_review_sandbox").touch()
            with self.assertRaisesRegex(ValueError, "Only REVIEW_ONLY"):
                video_ffmpeg.assemble(folder, output="slides.mp4", _offline_test_only=True)
            (folder / "source.pdf").write_bytes(b"%PDF-1.4\nprotected")
            with self.assertRaisesRegex(ValueError, "sandbox"):
                video_ffmpeg.assemble(folder, output=output, _offline_test_only=True)
            (folder / "source.pdf").unlink()
            saved = folder / output
            saved.write_bytes(b"EXISTING REVIEW CANNOT CHANGE")
            with self.assertRaises(FileExistsError):
                video_ffmpeg.assemble(folder, output=output, _offline_test_only=True)
            self.assertEqual(saved.read_bytes(), b"EXISTING REVIEW CANNOT CHANGE")

    def test_canonical_duration_policy_and_schema_are_identical(self):
        from selenium_pipeline.production_video_contract import MAX_PART_DURATION_SECONDS
        from selenium_pipeline.tts_duration_preflight import calculate
        import inspect
        self.assertEqual(MAX_PART_DURATION_SECONDS, 600)
        self.assertEqual(inspect.signature(calculate).parameters["limit_seconds"].default, 600)
        schema = json.loads((ROOT / "schemas/lesson_plan.schema.json").read_text(encoding="utf-8"))
        upper = schema["properties"]["parts"]["items"]["properties"]["estimated_duration_s"]["properties"]["max"]
        self.assertEqual(upper["exclusiveMaximum"], 600)

    def test_supersession_index_present(self):
        policy = ROOT / "docs/EFFECTIVE_CONTRACT_AND_SUPERSESSION_20261018.md"
        self.assertTrue(policy.is_file())
        text = policy.read_text(encoding="utf-8")
        self.assertIn("strictly less than 600", text)
        self.assertIn("Gemini Flash-Lite", text)
        self.assertIn("HP, Dell-115 and Yoga6", text)
        self.assertIn("No Whisper", text)


if __name__ == "__main__":
    unittest.main()
