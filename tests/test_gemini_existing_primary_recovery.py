"""Finite on-flight recovery of only a previously authenticated primary profile."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from selenium_pipeline.gemini_existing_primary_recovery import (
    recover_existing_primary_debug_session as recover,
)


class PrimaryExistingProfileRecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "persisted_primary"
        self.root.mkdir()
        (self.root / "Local State").write_text("existing-state")
        (self.root / "Default").mkdir()
        self.profile = patch("selenium_pipeline.launch_gemini.profile_root",
                             return_value=self.root)
        self.profile.start()
        self.addCleanup(self.profile.stop)

    def test_registered_existing_profile_may_reopen_same_identity_only(self):
        opened = []
        def open_same():
            opened.append(1)
            return 9222, self.root
        with patch("selenium_pipeline.launch_gemini.ready",
                   side_effect=[False, True]), patch(
                   "selenium_pipeline.launch_gemini.launch",
                   side_effect=open_same):
            self.assertTrue(recover(9222))
        self.assertEqual(len(opened), 1)

    def test_already_running_primary_needs_no_restart(self):
        with patch("selenium_pipeline.launch_gemini.ready",
                   return_value=True), patch(
                   "selenium_pipeline.launch_gemini.launch",
                   side_effect=AssertionError("not needed")):
            self.assertTrue(recover(9222))

    def test_no_relaunch_of_an_alternate_user_or_other_debug_port(self):
        with patch("selenium_pipeline.launch_gemini.ready",
                   side_effect=AssertionError("unknown port")), patch(
                   "selenium_pipeline.launch_gemini.launch",
                   side_effect=AssertionError("not authorized")):
            for port in (9225, 9223, 9226, "9222", True):
                with self.subTest(port=port):
                    self.assertFalse(recover(port))

    def test_missing_initialized_primary_never_launches(self):
        (self.root / "Local State").unlink()
        with patch("selenium_pipeline.launch_gemini.ready",
                   return_value=False), patch(
                   "selenium_pipeline.launch_gemini.launch",
                   side_effect=AssertionError("never create fresh")):
            self.assertFalse(recover(9222))

    def test_absent_default_profile_never_launches(self):
        (self.root / "Default").rmdir()
        with patch("selenium_pipeline.launch_gemini.ready",
                   return_value=False), patch(
                   "selenium_pipeline.launch_gemini.launch",
                   side_effect=AssertionError("never create fresh")):
            self.assertFalse(recover(9222))

    def test_retired_registry_fails_closed_before_chrome(self):
        with patch("selenium_pipeline.launch_gemini.ready",
                   return_value=False), patch(
                   "selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None), patch(
                   "selenium_pipeline.launch_gemini.launch",
                   side_effect=AssertionError("registry disabled")):
            self.assertFalse(recover(9222))

    def test_relaunch_wrong_profile_does_not_count_as_recovered(self):
        with patch("selenium_pipeline.launch_gemini.ready",
                   side_effect=[False, True]), patch(
                   "selenium_pipeline.launch_gemini.launch",
                   return_value=(9222, Path("wrong"))):
            self.assertFalse(recover(9222))

    def test_race_relaunch_started_but_port_does_not_return(self):
        with patch("selenium_pipeline.launch_gemini.ready",
                   return_value=False), patch(
                   "selenium_pipeline.launch_gemini.launch",
                   return_value=(9222, self.root)):
            self.assertFalse(recover(9222))

    def test_launcher_failure_is_safe_boundary_without_repeated_spawn(self):
        calls = []
        def fail():
            calls.append(1)
            raise OSError("cannot open Chrome")
        with patch("selenium_pipeline.launch_gemini.ready",
                   return_value=False), patch(
                   "selenium_pipeline.launch_gemini.launch", side_effect=fail):
            self.assertFalse(recover(9222))
        self.assertEqual(len(calls), 1)

    def test_symlinked_profile_state_is_not_trusted(self):
        target = self.root / "existing-state.txt"
        target.write_text("existing state")
        (self.root / "Local State").unlink()
        try:
            (self.root / "Local State").symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("No symlink capability")
        with patch("selenium_pipeline.launch_gemini.ready",
                   return_value=False), patch(
                   "selenium_pipeline.launch_gemini.launch",
                   side_effect=AssertionError("symlinked state")):
            self.assertFalse(recover(9222))
