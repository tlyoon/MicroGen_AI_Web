"""Stage 3: controlled fault injection for historical MicroGen incident classes.

All fixtures use temporary directories and synthetic data.  No Gemini calls,
Google Drive writes, or production worker changes are permitted.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from selenium_pipeline import video_ffmpeg
from selenium_pipeline.cleanup import _final_hashes, _sha256, _write_receipt, completed_lecture
from selenium_pipeline.reliability_audit import inspect_campaign
from selenium_pipeline.runner import run_cmd, valid
from selenium_pipeline.three_pc_worker import validate_manifest


class FaultInjectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.folder = self.root / "8" / "8.1"
        self.folder.mkdir(parents=True)
        self.source = self.folder / "source.pdf"
        self.source.write_bytes(b"synthetic textbook for test only")

    def _final_outputs(self):
        for name in ("slides.tex", "slides.pdf", "script.txt", "slides.mp4"):
            (self.folder / name).write_bytes((name + " synthetic").encode())
        _write_receipt(self.source, {
            "source_sha256": _sha256(self.source),
            "final_sha256": _final_hashes(self.folder),
        })

    def test_source_drift_fails_closed_and_preserves_outputs(self):
        self._final_outputs()
        old = (self.folder / "slides.mp4").read_bytes()
        self.assertTrue(completed_lecture(self.source))
        self.source.write_bytes(b"changed textbook")
        self.assertFalse(completed_lecture(self.source))
        self.assertEqual((self.folder / "slides.mp4").read_bytes(), old)

    def test_corrupt_receipt_does_not_certify_video(self):
        self._final_outputs()
        (self.folder / ".microgen_completion.json").write_text('{"source_sha256":"fake"}')
        self.assertFalse(completed_lecture(self.source))
        self.assertEqual(
            inspect_campaign(self.root, expected_count=1)["categories"]["published_requires_reconciliation"], 1
        )

    def test_read_only_campaign_audit_does_not_modify_files(self):
        self._final_outputs()
        before = {x.name: (x.stat().st_mtime_ns, hashlib.sha256(x.read_bytes()).hexdigest())
                  for x in self.folder.iterdir() if x.is_file()}
        report = inspect_campaign(self.root, expected_count=1)
        after = {x.name: (x.stat().st_mtime_ns, hashlib.sha256(x.read_bytes()).hexdigest())
                 for x in self.folder.iterdir() if x.is_file()}
        self.assertTrue(report["all_verified_complete"])
        self.assertEqual(before, after)

    def test_missing_graphic_makes_receipt_untrusted(self):
        self._final_outputs()
        (self.folder / "slides.tex").write_text(r"\includegraphics{Figure10_4.png}")
        self.assertFalse(completed_lecture(self.source))
        self.assertEqual(
            inspect_campaign(self.root, expected_count=1)["jobs"][0]["latex_graphics"], "blocked"
        )

    def test_strict_tts_qa_rejects_pending_review_even_with_zero_blockers(self):
        report = {
            "threshold_percent": 99.0,
            "summary": {"slides": 2, "passed": 2, "review": 1,
                        "blocking_failures": 0, "minimum_fidelity_percent": 100.0},
        }
        (self.folder / "tts_fidelity_report.json").write_text(json.dumps(report))
        (self.folder / "tts_fidelity_report.md").write_text("synthetic QA")
        with patch("selenium_pipeline.runner.slide_pages", return_value=2):
            self.assertFalse(valid("tts_qa", self.folder))

    def test_ffmpeg_probe_rejects_missing_audio(self):
        mp4 = self.folder / "candidate.mp4"
        mp4.write_bytes(b"0" * 4096)
        fake = SimpleNamespace(stderr="Duration: 00:00:04.00\nVideo: h264\n", stdout="")
        with patch.object(video_ffmpeg.subprocess, "run", return_value=fake):
            with self.assertRaisesRegex(RuntimeError, "lacks decodable video or audio"):
                video_ffmpeg.validate_video("ffmpeg", mp4, 4.0)

    def test_ffmpeg_probe_rejects_truncated_media(self):
        mp4 = self.folder / "candidate.mp4"
        mp4.write_bytes(b"0" * 4096)
        fake = SimpleNamespace(stderr="Duration: 00:00:01.00\nVideo: h264\nAudio: aac", stdout="")
        with patch.object(video_ffmpeg.subprocess, "run", return_value=fake):
            with self.assertRaisesRegex(RuntimeError, "unexpectedly short"):
                video_ffmpeg.validate_video("ffmpeg", mp4, 5.0)

    def test_worker_manifest_rejects_duplicate_pc_ownership(self):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({
            "source_root": str(self.root),
            "assignments": {"hp": [8, 9], "dell": [9, 10], "yoga6": [11]},
        }))
        with self.assertRaisesRegex(ValueError, "two owners"):
            validate_manifest(manifest, "hp", [8, 9], root=self.root)

    def test_stage_timeout_preserves_log_without_hanging_child(self):
        log = self.root / "stage.log"
        command = [sys.executable, "-u", "-c",
                   "import time;print('started',flush=True);time.sleep(30)"]
        with self.assertRaisesRegex(TimeoutError, "Stage timed out"):
            run_cmd(command, self.root, log, dict(os.environ), timeout_s=0.6,
                    kill_tree_on_timeout=True)
        self.assertIn("started", log.read_text(encoding="utf-8"))

    def test_ffmpeg_progress_messages_not_equivalent_to_finished_output(self):
        # A process can emit indefinite duplicated frames, without making
        # media progress. The watchdog must not accept those as progress.
        raw_popen = subprocess.Popen
        script = (
            "import time\n"
            "print('frame=1',flush=True)\n"
            "for i in range(40):\n"
            " print('frame=1',flush=True);time.sleep(0.25)\n"
        )

        def mock_start(_cmd, **kwargs):
            return raw_popen([sys.executable, "-u", "-c", script], **kwargs)

        with patch.dict(os.environ, {
            "MICROGEN_FFMPEG_TIMEOUT_SECONDS": "20",
            "MICROGEN_FFMPEG_STALL_SECONDS": "5",
        }):
            with patch.object(video_ffmpeg.subprocess, "Popen", side_effect=mock_start):
                with self.assertRaisesRegex(TimeoutError, "no media progress"):
                    video_ffmpeg.run_ffmpeg("unused", [], step="synthetic-frozen")


if __name__ == "__main__":
    unittest.main()
