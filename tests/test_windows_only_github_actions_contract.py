"""Permanent Windows-only GitHub Actions contract without extra dependencies.

Protects the deployment decision: only Windows runners (GitHub and Dell-115).
Historical Unix code and logs may exist, but cannot become CI requirements.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class WindowsOnlyGitHubActionsContract(unittest.TestCase):
    def workflow_sources(self):
        found=sorted((*WORKFLOWS.glob("*.yml"),*WORKFLOWS.glob("*.yaml")))
        self.assertEqual(
            {p.name for p in found},
            {"microgen-reliability-tests.yml","source-adjacent-output-tests.yml"},
            "New GitHub workflows require explicit Windows-only contract review")
        return {p.name:p.read_text(encoding="utf8") for p in found}

    def test_all_ci_runners_are_explicitly_windows_latest(self):
        for filename,source in self.workflow_sources().items():
            with self.subTest(filename=filename):
                runner_lines=re.findall(r"(?m)^\s*runs-on:\s*(.+?)\s*$",source)
                self.assertTrue(runner_lines)
                self.assertTrue(all(x=="windows-latest" for x in runner_lines))
                self.assertNotRegex(source,r"(?i)ubuntu|linux|macos|matrix\.os|shell:\s*bash")
                self.assertNotRegex(source,r"(?m)^\s*(?:apt-get|sudo|chmod)\s")

    def test_main_ci_retains_two_distinct_windows_jobs(self):
        source=self.workflow_sources()["microgen-reliability-tests.yml"]
        self.assertRegex(source,r"(?m)^  offline-regressions:\s*$")
        self.assertRegex(source,r"(?m)^  full-regressions:\s*$")
        self.assertEqual(len(re.findall(r"(?m)^    runs-on:",source)),2)
        self.assertIn("Full offline suite (Windows, Python 3.12)",source)
        self.assertIn("python -m pytest -q tests selenium_pipeline/tests",source)
        self.assertIn("python-version: '3.12'",source)

    def test_fast_suite_retains_complete_unittest_and_syntax_coverage(self):
        src=self.workflow_sources()["microgen-reliability-tests.yml"]
        self.assertIn("shell: pwsh",src)
        self.assertIn("python -m unittest -v @regressionModules",src)
        self.assertIn("python -m py_compile @pythonEntrypoints",src)
        modules=re.findall(r'^            "(tests\.test_[A-Za-z0-9_]+)"$',src,re.M)
        entrypoints=re.findall(r'^            "(selenium_pipeline/[^"]+\.py)"$',src,re.M)
        self.assertGreaterEqual(len(modules),46)
        self.assertGreaterEqual(len(entrypoints),40)
        self.assertEqual(len(modules),len(set(modules)))
        for required in (
            "tests.test_stage3_fault_injection",
            "tests.test_video_ffmpeg_assembly",
            "tests.test_production_video_contract",
            "tests.test_tts_duration_preflight",
            "tests.test_gemini_send_recovery",
            "tests.test_gemini_response_recovery",
            "tests.test_windows_only_github_actions_contract",
            "tests.test_original_slide4_figure_highlight_candidates",
            "tests.test_original_slide4_five_visual_candidates",
            "tests.test_original_slide4_audio_eligibility",
            "tests.test_original_slide4_audio_five_visual_integration",
            "tests.test_original_slide4_external_pcm_receipt_gate",
            "tests.test_original_slide4_untimed_highlight_preview",
        ):
            self.assertIn(required,modules)
        self.assertNotIn("python -m unittest -v \\",src)
        self.assertNotIn("python -m py_compile \\",src)

    def test_publication_workflow_still_runs_source_adjacent_safety(self):
        src=self.workflow_sources()["source-adjacent-output-tests.yml"]
        self.assertEqual(len(re.findall(r"(?m)^    runs-on:",src)),1)
        self.assertIn("test_source_adjacent_publication.py",src)
        self.assertIn("test_video_ffmpeg_assembly.py",src)
        self.assertIn("python -m py_compile",src)

    def test_main_workflow_runs_for_contract_regressions(self):
        src=self.workflow_sources()["microgen-reliability-tests.yml"]
        self.assertIn("- 'tests/**'",src)
        self.assertIn("- '.github/workflows/**'",src)
        self.assertIn("- 'docs/**'",src)


if __name__=="__main__":
    unittest.main()
