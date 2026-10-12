"""Offline regressions for targeted narration retry feedback."""

import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "selenium_pipeline/vendor_template_v2/gen_script_selenium_v15.py"


def _retry_function():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "retry_instruction")
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["retry_instruction"]


class NarrationRetryFeedbackTests(unittest.TestCase):
    def test_first_attempt_unchanged(self):
        self.assertEqual(_retry_function()("base", []), "base")

    def test_targeted_feedback_and_fail_closed(self):
        result = _retry_function()("base", ["Slide 14: ambiguous_capital_a"] * 2)
        self.assertEqual(result.count("Slide 14: ambiguous_capital_a"), 1)
        self.assertIn("COMPLETE script", result)
        self.assertIn("never guess", result)
        self.assertIn("speech-safety", result)

    def test_feedback_bounded(self):
        result = _retry_function()("base", ["x" * 1000] * 30)
        self.assertLess(len(result), 1100)

    def test_rejected_output_is_archived_before_retry(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("OUT_SCRIPT.replace(archive)", text)
        self.assertIn("refusing destructive retry", text)
        self.assertIn("retry_instruction(instruction, last_warnings)", text)


if __name__ == "__main__":
    unittest.main()
