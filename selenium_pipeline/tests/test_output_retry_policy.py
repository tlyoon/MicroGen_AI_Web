import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAPPER = ROOT / "vendor_template_v2" / "map_and_rename_selenium_v8.py"
NARRATION = ROOT / "vendor_template_v2" / "gen_script_selenium_v15.py"


def load_failure_detector():
    tree = ast.parse(MAPPER.read_text(encoding="utf-8"))
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "GEMINI_FAILURE_MARKERS" in names:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "_looks_like_gemini_failure_text":
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    ns = {"re": re}
    exec(compile(module, str(MAPPER), "exec"), ns)
    return ns["_looks_like_gemini_failure_text"]


class GeminiOutputRetryPolicyTests(unittest.TestCase):
    def test_known_gemini_error_text_is_rejected(self):
        detector = load_failure_detector()
        self.assertTrue(detector("I encountered an error doing what you asked. Could you try again?"))
        self.assertTrue(detector("Something went wrong. Please try again."))
        self.assertFalse(detector('fig_1.png : "Figure 22.4" : Figure 22.4.png'))

    def test_mapping_retries_default_to_three_identical_submissions(self):
        source = MAPPER.read_text(encoding="utf-8")
        self.assertIn('GEMINI_OUTPUT_ATTEMPTS", "3"', source)
        self.assertIn("resubmitting the SAME request", source)
        self.assertIn("len(parsed) == len(fig_files)", source)

    def test_page_stall_retries_default_to_three(self):
        source = MAPPER.read_text(encoding="utf-8")
        self.assertIn('GEMINI_PAGE_ATTEMPTS", "3"', source)

    def test_mapping_stall_window_does_not_preempt_normal_slow_response(self):
        source = MAPPER.read_text(encoding="utf-8")
        self.assertIn('GEMINI_MAPPING_STALL_SECONDS", "90"', source)

    def test_narration_defaults_to_three_total_attempts(self):
        source = NARRATION.read_text(encoding="utf-8")
        self.assertIn('RETRY_COUNT = int(os.environ.get("RETRY_COUNT", "2"))', source)
        self.assertIn("attempts = RETRY_COUNT + 1", source)


if __name__ == "__main__":
    unittest.main()
