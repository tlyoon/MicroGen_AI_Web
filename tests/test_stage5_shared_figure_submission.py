"""Figure mapping must reuse the proven shared Gemini submission verifier.

A text-bearing Send button alone is not evidence that Google Gemini accepted
the multimodal prompt. The figure mapper used to depend on a Windows-specific
pywinauto/pywin32 Enter fallback, which failed on HP. The slide/narration path
already has a bounded browser-verified send gate.
"""
from __future__ import annotations
import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "selenium_pipeline" / "vendor_template_v2" / "map_and_rename_selenium_v8.py"


class SharedFigureSubmissionTests(unittest.TestCase):
    def test_figure_send_uses_shared_confirmation(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        fun = next(x for x in tree.body if isinstance(x, ast.FunctionDef)
                   and x.name == "_send_prompt_and_capture_mapping_text")
        calls = [x for x in ast.walk(fun) if isinstance(x, ast.Call)]
        shared = [x for x in calls if isinstance(x.func, ast.Attribute)
                  and isinstance(x.func.value, ast.Name)
                  and x.func.value.id == "client"
                  and x.func.attr == "click_send_with_fallbacks"]
        self.assertEqual(len(shared), 1)
        self.assertTrue(any(kw.arg == "retries" and isinstance(kw.value, ast.Constant)
                            and kw.value.value == 1 for kw in shared[0].keywords))
        self.assertFalse(any(isinstance(x.func, ast.Name)
                             and x.func.id == "click_safe_send_button" for x in calls),
                         "live figure send must not use broken win32api fallback")

    def test_shared_submission_is_required_before_capture(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        fun = next(x for x in tree.body if isinstance(x, ast.FunctionDef)
                   and x.name == "_send_prompt_and_capture_mapping_text")
        txt = ast.unparse(fun)
        self.assertIn("if not send_ok:", txt)
        self.assertIn("Prompt could not be reliably submitted to Gemini.", txt)
        self.assertIn("if clicked:", txt)
        self.assertIn("send_ok = True", txt)


if __name__ == "__main__":
    unittest.main()
