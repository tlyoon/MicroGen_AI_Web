"""Real isolated Python subprocess must import the checked-out shared pipeline."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from selenium_pipeline.runner import REPO, source_locked_worker_pythonpath


class IsolatedVendorPythonPathTests(unittest.TestCase):
    def test_anchored_root_is_first_and_prior_paths_are_preserved_once(self):
        original = {"PYTHONPATH": os.pathsep.join((str(REPO), "C:\\vendor_a",
                                                  "C:\\vendor_b"))}
        selected = source_locked_worker_pythonpath(original)
        parts = selected.split(os.pathsep)
        self.assertEqual(Path(parts[0]).resolve(), REPO.resolve())
        self.assertEqual(sum(Path(part) == REPO for part in parts), 1)
        self.assertEqual(parts[1:], ["C:\\vendor_a", "C:\\vendor_b"])
        self.assertEqual(original["PYTHONPATH"].count("vendor_a"), 1)

    def test_invalid_source_root_is_never_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                source_locked_worker_pythonpath({}, Path(tmp))

    def test_real_subprocess_imports_from_isolated_job_folder_no_sends(self):
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONPATH"] = source_locked_worker_pythonpath(env)
        env["PYTHONNOUSERSITE"] = "1"
        code = (
            "import pathlib; "
            "import selenium_pipeline.figure_crop_source_provenance as m; "
            "print('WORKER_PACKAGE_IMPORT_OK'); "
            "assert pathlib.Path(m.__file__).resolve().is_relative_to("
            f"pathlib.Path({str(REPO)!r}).resolve())"
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=tmp, env=env, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=40, check=False)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("WORKER_PACKAGE_IMPORT_OK", result.stdout)

    def test_production_runner_uses_path_for_stage_subprocess_env(self):
        script = (REPO / "selenium_pipeline" / "runner.py").read_text(
            encoding="utf8")
        self.assertIn('"PYTHONPATH": source_locked_worker_pythonpath(env, REPO)', script)
        self.assertIn('run_cmd([stage_python, script], folder, log_file, env)', script)


if __name__ == "__main__":
    unittest.main()
