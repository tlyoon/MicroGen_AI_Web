"""Regression checks for portable MicroGen workers and permanent Flash defaults."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.three_pc_worker import (
    LocalInstanceLock,
    assigned_jobs,
    run_stage,
    validate_manifest,
)


class PortableWorkerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for key in ("8.1", "8.3", "9.2"):
            folder = self.root / key.split(".")[0] / key
            folder.mkdir(parents=True)
            (folder / "source.pdf").write_bytes(b"%PDF-1.4\n")
        self.control = self.root / ".microgen_coordination" / "run1"
        self.control.mkdir(parents=True)
        self.manifest = self.control / "assignments.json"

    def _manifest(self, mapping):
        self.manifest.write_text(
            json.dumps({
                "dataset_id": "serway-example",
                "assignments": {"Workstation-42": [8], "Node_2": [9]},
                "source_roots": mapping,
            }), encoding="utf-8"
        )

    def test_arbitrary_worker_name_with_local_path_mapping(self):
        self._manifest({
            "Workstation-42": str(self.root),
            "Node_2": str(self.root),
        })
        validate_manifest(self.manifest, "Workstation-42", [8], root=self.root)
        validate_manifest(self.manifest, "Node_2", [9], root=self.root)
        self.assertEqual(assigned_jobs(self.root, [8]), ["8.1", "8.3"])

    def test_pilot_manifest_limits_one_subchapter_without_mutating_others(self):
        from selenium_pipeline.three_pc_worker import main
        self._manifest({
            "Workstation-42": str(self.root),
            "Node_2": str(self.root),
        })
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["targets"] = {"Workstation-42": ["8.1"], "Node_2": ["9.2"]}
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(main([
            "--source-root", str(self.root), "--run-id", "run1",
            "--worker", "Workstation-42", "--chapters", "8",
            "--subchapters", "8.1", "--dry-run",
        ]), 0)
        with self.assertRaisesRegex(ValueError, "must match manifest.targets"):
            main([
                "--source-root", str(self.root), "--run-id", "run1",
                "--worker", "Workstation-42", "--chapters", "8",
                "--subchapters", "8.3", "--dry-run",
            ])

    def test_wrong_source_root_fails_closed(self):
        self._manifest({
            "Workstation-42": str(self.root / "not-our-source"),
            "Node_2": str(self.root),
        })
        with self.assertRaisesRegex(ValueError, "source root differs"):
            validate_manifest(self.manifest, "Workstation-42", [8], root=self.root)

    def test_missing_worker_and_overlap_fail_closed(self):
        self._manifest({"Workstation-42": str(self.root)})
        with self.assertRaisesRegex(ValueError, "missing source root"):
            validate_manifest(self.manifest, "Node_2", [9], root=self.root)
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["assignments"]["Node_2"] = [8]
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "two owners"):
            validate_manifest(self.manifest, "Workstation-42", [8], root=self.root)

    def test_local_lock_prevents_same_worker_duplicate(self):
        locks = self.root / "locks"
        with LocalInstanceLock("Workstation-42", locks):
            with self.assertRaises(RuntimeError):
                with LocalInstanceLock("Workstation-42", locks):
                    pass
        with LocalInstanceLock("Workstation-42", locks):
            pass

    def test_idle_watchdog_stops_only_spawned_test_stage(self):
        actual_popen = subprocess.Popen

        def silent_stage(*_args, **_kwargs):
            if _args and _args[0] and str(_args[0][0]).lower() == "taskkill":
                return actual_popen(*_args, **_kwargs)
            return actual_popen(
                [sys.executable, "-u", "-c", "import time; time.sleep(60)"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                errors="replace", start_new_session=(os.name != "nt")
            )

        with patch("selenium_pipeline.three_pc_worker.subprocess.Popen",
                   side_effect=silent_stage):
            ok, reason = run_stage(
                self.root, "8.1", "figures", 9222,
                self.root / "stage.log", self.root / "lane",
                idle_seconds=0.6, hard_seconds=8,
            )
        self.assertFalse(ok)
        self.assertIn("stalled", reason)


class FlashDefaultTests(unittest.TestCase):
    def test_production_phase_does_not_change_flash_model(self):
        env = dict(os.environ)
        env["MICROGEN_MODEL_PHASE"] = "production"
        env.pop("MICROGEN_GEMINI_UI_MODE", None)
        env.pop("MICROGEN_LLM_MODEL", None)
        code = (
            "from selenium_pipeline import runner; "
            "from selenium_pipeline.gemini_model import configured_ui_mode; "
            "assert runner.MODEL_PHASE == 'production'; "
            "assert runner.ACTIVE_LLM_MODEL == 'gemini-3.8-flash'; "
            "assert runner.DEFAULT_CAPTION_MODEL == runner.DEFAULT_SLIDE_MODEL "
            "== runner.DEFAULT_NARRATION_MODEL == 'gemini-3.8-flash'; "
            "assert runner.PRODUCTION_LLM_MODEL == 'gemini-3.8-flash'; "
            "assert configured_ui_mode() == 'flash'"
        )
        run = subprocess.run(
            [sys.executable, "-c", code],
            env=env, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
