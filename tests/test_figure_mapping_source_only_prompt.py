"""Regression: caption mapping must not solicit web knowledge or split panels."""
from pathlib import Path
import ast
import unittest

FILE=(Path(__file__).resolve().parents[1]
      /"selenium_pipeline"/"vendor_template_v2"/"map_and_rename_selenium_v8.py")


class FigureMappingPromptTests(unittest.TestCase):
    def test_prompt_declares_attachments_only_no_web(self):
        text=FILE.read_text(encoding="utf-8")
        self.assertIn("LOCAL VISUAL-TRANSCRIPTION TASK only",text)
        self.assertIn("Do NOT search the web or use outside",text)
        self.assertIn("sole evidence",text)
        self.assertIn("invented caption/figure numbers",text)

    def test_multi_panel_crop_not_silently_simplified(self):
        text=FILE.read_text(encoding="utf-8")
        self.assertIn("multiple panels (a), (b), (c)",text)
        self.assertIn("partial-panel figure",text)

    def test_ambiguous_mapping_fails_closed(self):
        text=FILE.read_text(encoding="utf-8")
        self.assertIn("MAPPING_REVIEW_REQUIRED",text)
        self.assertIn("Otherwise return exactly one line per crop",text)
        self.assertIn("exact_count = len(parsed) == len(fig_files)",text)
        self.assertIn("if exact_count and not explicit_error:",text)

    def test_vendor_source_syntax(self):
        ast.parse(FILE.read_text(encoding="utf-8"))


if __name__=="__main__":
    unittest.main()
