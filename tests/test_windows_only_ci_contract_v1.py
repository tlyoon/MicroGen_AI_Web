"""Enforce Windows-only CI and development contract without OS-specific test dependencies."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CONTRACT = ROOT / "docs" / "MicroGen_Windows_Only_Development_Regression_Contract_20261125.md"

class WindowsOnlyDevelopmentRegressionContractTests(unittest.TestCase):
    def _workflow_texts(self):
        files = sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")])
        self.assertGreaterEqual(len(files), 2)
        return {p.name: p.read_text(encoding="utf8") for p in files}

    def test_every_hosted_ci_job_runs_on_windows(self):
        for name, source in self._workflow_texts().items():
            runners = re.findall(r"^\s+runs-on:\s*(.+)$", source, re.M)
            with self.subTest(workflow=name):
                self.assertTrue(runners, "CI workflow must declare a runner")
                self.assertTrue(all(x.strip() == "windows-latest" for x in runners),
                                "Only windows-latest is supported")
                self.assertNotIn("ubuntu-latest", source)
                self.assertNotIn("macos-latest", source)
                self.assertNotIn("matrix.os", source)
                self.assertNotRegex(source, r"(?m)^\s+os:\s*\[")

    def test_reliability_keeps_historical_and_full_qa(self):
        s = self._workflow_texts()["microgen-reliability-tests.yml"]
        self.assertEqual(s.count("runs-on: windows-latest"), 2)
        self.assertIn("Full offline suite (Windows, Python 3.12)", s)
        self.assertIn("python -m pytest -q tests selenium_pipeline/tests", s)
        for required in (
            "tests.test_browser_port_lock", "tests.test_stage3_fault_injection",
            "tests.test_narration_retry_feedback", "tests.test_figure_mapping_source_only_prompt",
            "tests.test_spoken_math_review", "tests.test_video_ffmpeg_assembly",
            "selenium_pipeline/runner.py", "selenium_pipeline/storyboard_cli.py",
        ):
            with self.subTest(test=required):
                self.assertIn(required, s)
        self.assertEqual(s.count("shell: pwsh"), 2)
        self.assertIn("run: >-", s)
        self.assertNotIn("sudo ", s)
        self.assertNotIn("shell: bash", s)
        self.assertNotRegex(s, r"(?m)^\s*.+\\\s*$")

    def test_publication_integrity_suite_remains_windows(self):
        s = self._workflow_texts()["source-adjacent-output-tests.yml"]
        self.assertEqual(s.count("runs-on: windows-latest"), 1)
        for required in (
            "test_source_adjacent_publication.py",
            "test_video_ffmpeg_assembly.py",
            "python -m py_compile",
            "selenium_pipeline/output_paths.py",
        ):
            self.assertIn(required, s)

    def test_authoritative_contract_preserves_windows_qa(self):
        self.assertTrue(CONTRACT.is_file())
        c = CONTRACT.read_text(encoding="utf8")
        self.assertIn("Windows is the only supported execution", c)
        self.assertIn("Linux regression suites are not required", c)
        self.assertIn("not a relaxation of test coverage", c)
        self.assertIn("previously established Windows production-specific criteria", c)
        for p in (ROOT/"README.md",
                  ROOT/"selenium_pipeline"/"README.md",
                  ROOT/"docs"/"G3_CONTINUOUS_RECOVERY_FORWARD_CONTRACT_20261124.md"):
            self.assertIn("MicroGen_Windows_Only_Development_Regression_Contract_20261125.md",
                          p.read_text(encoding="utf8"))

if __name__ == "__main__":
    unittest.main()
