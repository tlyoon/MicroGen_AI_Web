"""Portable dependency doctor launcher never weakens readiness gates."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from selenium_pipeline import runtime_doctor


class RuntimeDoctorTests(unittest.TestCase):
    def test_explicit_python_beats_config(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            active=p/"selected_python.exe"
            active.write_bytes(b"test")
            (p/".env").write_text("MICROGEN_PIPELINE_PYTHON=not-the-correct-one\n")
            resolved=runtime_doctor.select_runner_python({
                "MICROVID_CONFIG_DIR":str(p),
                "MICROGEN_PIPELINE_PYTHON":str(active),
            },current_python="defaultpython")
            self.assertEqual(resolved,str(active))

    def test_reads_only_relevant_config_key_without_exposing_secrets(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            active=p/"dedicated python.exe"
            active.write_bytes(b"x")
            (p/".env").write_text(
                "GEMINI_API_KEY=not-for-output\n"
                f'MICROGEN_PIPELINE_PYTHON="{active}"\n',encoding="utf8")
            selected=runtime_doctor.select_runner_python(
                {"MICROVID_CONFIG_DIR":td},current_python="python-current")
            self.assertEqual(selected,str(active))

    def test_first_existing_config_is_authoritative(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            (p/".env").write_text("UNRELATED=value\n",encoding="utf8")
            local=p/"Microvid"
            local.mkdir()
            (local/".env").write_text("MICROGEN_PIPELINE_PYTHON=unsafe-other-env\n")
            result=runtime_doctor.select_runner_python({
                "MICROVID_CONFIG_DIR":td, "LOCALAPPDATA":td},
                current_python="currentpython")
            self.assertEqual(result,"currentpython")

    def test_conflicting_duplicate_python_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/".env").write_text(
                "MICROGEN_PIPELINE_PYTHON=a\nMICROGEN_PIPELINE_PYTHON=b\n")
            with self.assertRaisesRegex(runtime_doctor.RuntimeDoctorError,
                                        "Conflicting"):
                runtime_doctor.select_runner_python(
                    {"MICROVID_CONFIG_DIR":td},current_python="python")

    def test_missing_explicit_python_fails_not_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(runtime_doctor.RuntimeDoctorError,
                                        "unavailable"):
                runtime_doctor.select_runner_python(
                    {"MICROGEN_PIPELINE_PYTHON":str(Path(td)/"missing.exe")},
                    current_python="python")

    def test_no_configuration_uses_current_python(self):
        self.assertEqual(runtime_doctor.select_runner_python({}, "currentpy"),
                         "currentpy")

    def test_doctor_propagates_failed_status(self):
        with patch.object(runtime_doctor, "select_runner_python",
                          return_value="chosen.exe"), patch.object(
                            runtime_doctor.subprocess, "run",
                            return_value=SimpleNamespace(returncode=2)) as run:
            self.assertEqual(runtime_doctor.main([]),2)
            args=run.call_args.args[0]
            self.assertEqual(args,["chosen.exe","-m",
                                  "selenium_pipeline.runner","--doctor"])

    def test_refuses_generation_arguments(self):
        with self.assertRaisesRegex(runtime_doctor.RuntimeDoctorError,
                                    "no generation"):
            runtime_doctor.main(["--subchapter","22.3"])


if __name__=="__main__":
    unittest.main()
