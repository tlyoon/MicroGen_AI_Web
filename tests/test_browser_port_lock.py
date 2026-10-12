"""Offline browser exclusivity tests (local OS file locks, no Drive)."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.runner import Settings, execute
from selenium_pipeline.three_pc_worker import LocalInstanceLock


class BrowserPortLockTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_second_simultaneous_owner_cannot_take_same_browser_lock(self):
        locks = self.root / "local_browser_locks"
        with LocalInstanceLock("gemini_port_9222", locks):
            with self.assertRaisesRegex(RuntimeError, "already active"):
                with LocalInstanceLock("gemini_port_9222", locks):
                    self.fail("duplicate lock acquired")

    def test_different_browser_ports_have_independent_locks(self):
        locks = self.root / "local_browser_locks"
        with LocalInstanceLock("gemini_port_9222", locks):
            with LocalInstanceLock("gemini_port_9223", locks):
                pass

    def test_chrome_stage_uses_lock(self):
        s = Settings(source_root=self.root, work_root=None, subchapter="8.1",
                     from_stage="narration", through_stage="narration")
        with patch("selenium_pipeline.runner._execute_unlocked", return_value=self.root):
            with patch("selenium_pipeline.three_pc_worker.LocalInstanceLock") as lock:
                execute(s)
                self.assertEqual(lock.call_count, 1)
                self.assertEqual(lock.call_args.args[0], "gemini_port_9222")

    def test_nonbrowser_and_dry_run_do_not_lock(self):
        for settings in (
            Settings(source_root=self.root, work_root=None, subchapter="8.1",
                     from_stage="tts", through_stage="video"),
            Settings(source_root=self.root, work_root=None, subchapter="8.1", dry_run=True),
        ):
            with patch("selenium_pipeline.runner._execute_unlocked", return_value=self.root):
                with patch("selenium_pipeline.three_pc_worker.LocalInstanceLock") as lock:
                    execute(settings)
                    lock.assert_not_called()
