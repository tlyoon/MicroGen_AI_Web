"""Never install anything during automated tests; verify fail-closed choices."""
import unittest
from unittest.mock import Mock

from selenium_pipeline.windows_install_smoke import inspect, REQUIRED_IMPORTS


class WindowsInstallSmokeTests(unittest.TestCase):
    def test_correct_imports_and_external_tools_can_certify_worker_only(self):
        report = inspect(import_module=lambda name: object(),
                         pip_checker=lambda: True,
                         tools=lambda cmd: "C:/tools/" + cmd,
                         platform="win32",
                         prefix="C:/users/user/AppData/Local/venv",
                         base_prefix="C:/python")
        self.assertEqual(report["status"], "WINDOWS_ISOLATED_WORKER_INSTALL_PASS")
        self.assertFalse(report["sourcebound_full_lecture_production_certified"])
        self.assertFalse(report["model_or_paid_tts_called"])
        self.assertFalse(report["student_publication_authorized"])
        self.assertEqual(len(report["import_checks"]), len(REQUIRED_IMPORTS))

    def test_import_failure_does_not_certify_install(self):
        def imports(name):
            if name == "google.genai":
                raise ImportError("credential=NEVER_LEAK")
            return object()
        report = inspect(import_module=imports, pip_checker=lambda: True,
                         tools=lambda name: "fake",
                         platform="win32", prefix="C:/venv", base_prefix="C:/base")
        self.assertEqual(report["import_checks"]["google.genai"], "ImportError")
        self.assertNotIn("NEVER_LEAK", str(report))
        self.assertEqual(report["status"], "WINDOWS_WORKER_INSTALL_INCOMPLETE")

    def test_not_isolated_or_wrong_platform_fails(self):
        report = inspect(import_module=lambda name: object(),
                         pip_checker=lambda: True, tools=lambda name: "fake",
                         platform="win32", prefix="C:/base", base_prefix="C:/base")
        self.assertEqual(report["status"], "WINDOWS_WORKER_INSTALL_INCOMPLETE")
        self.assertFalse(report["isolated_virtual_environment"])
        other = inspect(import_module=lambda name: object(),
                         pip_checker=lambda: True, tools=lambda name: "fake",
                         platform="linux", prefix="C:/venv", base_prefix="C:/base")
        self.assertEqual(other["status"], "WINDOWS_WORKER_INSTALL_INCOMPLETE")

    def test_missing_external_executable_or_pip_conflict_blocks(self):
        report = inspect(import_module=lambda name: object(),
                         pip_checker=lambda: False,
                         tools=lambda name: None if name == "pdflatex" else "ffmpeg",
                         platform="win32", prefix="C:/venv", base_prefix="C:/base")
        self.assertFalse(report["pip_dependency_check_pass"])
        self.assertFalse(report["external_tools"]["pdflatex"])
        self.assertEqual(report["status"], "WINDOWS_WORKER_INSTALL_INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
