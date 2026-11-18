"""Enrolled Account B-only no-Send, no-credential Chrome restoration."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from selenium_pipeline.gemini_existing_alternate_recovery import (
    recover_existing_alternate_debug_session as recover)


class EnrolledAlternateRecoveryTests(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)/"AccountB"
        self.root.mkdir()
        (self.root/"Local State").write_text("existing-state")
        (self.root/"Default").mkdir()
        p=patch("selenium_pipeline.launch_gemini.profile_root",
                side_effect=lambda label:self.root if label=="AccountB" else
                    self.fail("Unknown alternate profile requested"))
        p.start()
        self.addCleanup(p.stop)

    def test_one_registered_presend_reopen_only_existing_authorized_account(self):
        calls=[]
        def opened(label,*,port,existing_profile_only):
            calls.append((label,port,existing_profile_only))
            return 9225,self.root
        with patch("selenium_pipeline.launch_gemini.ready",
                   return_value=False),patch(
                   "selenium_pipeline.gemini_existing_alternate_recovery.enrolled_alternate_port_owned",
                   return_value=True),patch(
                   "selenium_pipeline.launch_gemini.launch",
                   side_effect=opened):
            self.assertTrue(recover(9225))
        self.assertEqual(calls,[("AccountB",9225,True)])

    def test_live_session_does_not_spawn_another(self):
        with patch("selenium_pipeline.launch_gemini.ready",return_value=True),patch(
                "selenium_pipeline.gemini_existing_alternate_recovery.enrolled_alternate_port_owned",
                return_value=True),patch(
                "selenium_pipeline.launch_gemini.launch",
                side_effect=AssertionError("No Chrome launch")):
            self.assertTrue(recover(9225))

    def test_wrong_chrome_process_must_not_count_as_enrolled(self):
        from selenium_pipeline.gemini_existing_alternate_recovery import (
            enrolled_alternate_port_owned)
        from types import SimpleNamespace
        wrong=SimpleNamespace(info={"name":"chrome.exe","cmdline":[
            "chrome.exe","--remote-debugging-port=9225",
            "--user-data-dir=C:\\Temp\\unrelated-profile"]})
        good=SimpleNamespace(info={"name":"chrome.exe","cmdline":[
            "chrome.exe","--remote-debugging-port=9225",
            "--user-data-dir="+str(self.root)]})
        from unittest.mock import patch as mock_patch
        fake=SimpleNamespace(NoSuchProcess=LookupError,
                             AccessDenied=PermissionError,
                             process_iter=lambda attrs:[wrong])
        # No CI dependency on psutil: simulate the OS process inventory,
        # while production Dell-115 requires a real installed psutil.
        with mock_patch("selenium_pipeline.launch_gemini.ready",
                        return_value=True),mock_patch.dict(
                        "sys.modules",{"psutil":fake}):
            self.assertFalse(enrolled_alternate_port_owned())
            self.assertFalse(recover(9225))
        # Exercise both the literal launcher --user-data-dir argument and
        # its normalized Windows junction alias (CI temp directories can
        # resolve differently from their raw paths).
        canonical=SimpleNamespace(info={"name":"chrome.exe","cmdline":[
            "chrome.exe","--remote-debugging-port=9225",
            "--user-data-dir="+str(self.root.resolve())]})
        for candidate in (good,canonical):
            with self.subTest(candidate=candidate),mock_patch(
                    "selenium_pipeline.launch_gemini.ready",
                    return_value=True),mock_patch.dict(
                    "sys.modules",{"psutil":fake}):
                fake.process_iter=lambda attrs:[wrong,candidate]
                self.assertTrue(enrolled_alternate_port_owned())
                self.assertTrue(recover(9225))

    def test_raw_chrome_argument_survives_a_different_resolved_junction_alias(self):
        from types import SimpleNamespace
        from selenium_pipeline.gemini_existing_alternate_recovery import (
            enrolled_alternate_port_owned)
        fake_proc=SimpleNamespace(info={"name":"chrome.exe","cmdline":[
            "chrome.exe","--remote-debugging-port=9225",
            "--user-data-dir="+str(self.root)]})
        fake=SimpleNamespace(NoSuchProcess=LookupError,
                             AccessDenied=PermissionError,
                             process_iter=lambda attrs:[fake_proc])
        # The real Chrome launch passes the raw enrolled path, while
        # canonicalization of an NTFS junction may return a different alias.
        with patch("selenium_pipeline.launch_gemini.ready",
                   return_value=True),patch.dict(
                   "sys.modules",{"psutil":fake}),patch.object(
                   Path,"resolve",return_value=Path(str(self.root)+"-canonical")):
            self.assertTrue(enrolled_alternate_port_owned())

    def test_invalid_ports_never_even_check_profile(self):
        for port in (9222,9223,9226,"9225",True,None):
            with self.subTest(port=port),patch(
                    "selenium_pipeline.launch_gemini.ready",
                    side_effect=AssertionError("Never check port")):
                self.assertFalse(recover(port))

    def test_missing_profile_identity_never_launches_or_creates_account(self):
        (self.root/"Local State").unlink()
        with patch("selenium_pipeline.launch_gemini.ready",return_value=False),patch(
                "selenium_pipeline.launch_gemini.launch",
                side_effect=AssertionError("No unauthorized profile creation")):
            self.assertFalse(recover(9225))
        self.assertFalse((self.root/"Local State").exists())

    def test_missing_default_directory_denies_launch(self):
        (self.root/"Default").rmdir()
        with patch("selenium_pipeline.launch_gemini.ready",return_value=False),patch(
                "selenium_pipeline.launch_gemini.launch",
                side_effect=AssertionError("No launch")):
            self.assertFalse(recover(9225))

    def test_retired_registry_no_browser_side_effect(self):
        with patch("selenium_pipeline.launch_gemini.ready",return_value=False),patch(
                "selenium_pipeline.recovery_registry.lookup_mechanism",
                return_value=None),patch(
                "selenium_pipeline.launch_gemini.launch",
                side_effect=AssertionError("No launch")):
            self.assertFalse(recover(9225))

    def test_wrong_return_port_or_identity_never_qualifies(self):
        with patch("selenium_pipeline.launch_gemini.ready",return_value=False),patch(
                   "selenium_pipeline.gemini_existing_alternate_recovery.enrolled_alternate_port_owned",
                   return_value=True),patch(
                   "selenium_pipeline.launch_gemini.launch",
                   return_value=(9222,self.root)):
            self.assertFalse(recover(9225))
        with patch("selenium_pipeline.launch_gemini.ready",return_value=False),patch(
                   "selenium_pipeline.gemini_existing_alternate_recovery.enrolled_alternate_port_owned",
                   return_value=True),patch(
                   "selenium_pipeline.launch_gemini.launch",
                   return_value=(9225,Path("different"))):
            self.assertFalse(recover(9225))

    def test_relaunch_that_never_binds_port_still_fails(self):
        with patch("selenium_pipeline.launch_gemini.ready",return_value=False),patch(
                   "selenium_pipeline.gemini_existing_alternate_recovery.enrolled_alternate_port_owned",
                   return_value=False),patch(
                   "selenium_pipeline.launch_gemini.launch",
                   return_value=(9225,self.root)):
            self.assertFalse(recover(9225))

    def test_existing_only_launcher_rejects_unenrolled_state_before_spawn(self):
        from selenium_pipeline.launch_gemini import launch
        with patch("selenium_pipeline.launch_gemini.profile_root",
                   return_value=self.root),patch(
                   "selenium_pipeline.launch_gemini.ready",
                   return_value=False),patch(
                   "selenium_pipeline.launch_gemini.chrome_exe",
                   side_effect=AssertionError("Must check enrollment first")):
            (self.root/"Local State").unlink()
            with self.assertRaisesRegex(ValueError,"Enrolled Chrome profile"):
                launch("AccountB",port=9225,existing_profile_only=True)

    def test_symlinked_chrome_state_not_accepted(self):
        target=self.root/"existing-state"
        target.write_text("marker")
        (self.root/"Local State").unlink()
        try:
            (self.root/"Local State").symlink_to(target)
        except (OSError,NotImplementedError):
            self.skipTest("No symlink rights in current Windows session")
        with patch("selenium_pipeline.launch_gemini.ready",return_value=False),patch(
                "selenium_pipeline.launch_gemini.launch",
                side_effect=AssertionError("No launch")):
            self.assertFalse(recover(9225))


if __name__=="__main__":
    unittest.main()
