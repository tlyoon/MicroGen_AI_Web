"""Real native Windows subprocess timeout/UTF-8 tests: no provider or browser."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.windows_bounded_stage_process import (
    run_bounded, WindowsStageRecoveryError,
)


class WindowsBoundedStageProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_real_unicode_output_is_raw_without_cp1252_read_thread(self):
        out = self.root / "unicode_stdout.log"
        result = run_bounded(
            command=[sys.executable, "-c",
                     "import sys;sys.stdout.write('pi=\\u03c0 integral=\\u222b\\n')"],
            cwd=self.root, log_path=out, timeout_seconds=15)
        self.assertEqual(result.returncode, 0)
        self.assertIn("π", out.read_text(encoding="utf8"))
        self.assertIn("∫", out.read_text(encoding="utf8"))

    def test_actual_sleeping_child_is_killed_on_bounded_timeout(self):
        out = self.root / "timed_out_stdout.log"
        with self.assertRaises(subprocess.TimeoutExpired):
            run_bounded(
                command=[sys.executable, "-c",
                         "import time;print('stage started', flush=True);time.sleep(12)"],
                cwd=self.root, log_path=out, timeout_seconds=0.6)
        self.assertTrue(out.is_file())
        self.assertIn(b"stage started", out.read_bytes())

    def test_existing_log_is_not_overwritten_or_stage_started(self):
        out = self.root / "already_exists.log"
        out.write_text("accepted history", encoding="utf8")
        with self.assertRaises(WindowsStageRecoveryError):
            run_bounded(command=[sys.executable, "-c", "print('run')"],
                        cwd=self.root, log_path=out, timeout_seconds=5)
        self.assertEqual(out.read_text(encoding="utf8"), "accepted history")

    def test_invalid_deadline_is_rejected_pre_execution(self):
        with self.assertRaises(WindowsStageRecoveryError):
            run_bounded(command=[sys.executable, "-c", "print('run')"],
                        cwd=self.root, log_path=self.root / "no.log",
                        timeout_seconds=-1)
        self.assertFalse((self.root / "no.log").exists())


if __name__ == "__main__":
    unittest.main()
