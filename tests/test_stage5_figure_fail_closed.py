"""Failed Gemini figure mapping must block downstream slide/narration claims."""
import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "selenium_pipeline" / "vendor_template_v2" / "map_and_rename_selenium_v8.py"


class FigureMappingFailClosedTests(unittest.TestCase):
    def setUp(self):
        self.tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

    def test_invalid_mapping_raises_instead_of_returning_empty_success(self):
        fn = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "map_and_rename_single_step")
        blocks = [n for n in ast.walk(fn) if isinstance(n, ast.Raise)]
        self.assertTrue(any("Unverified figure mapping" in ast.unparse(n) for n in blocks))

    def test_page_errors_abort_entire_mapping_stage(self):
        fn = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "run_mapping")
        handlers = [n for n in ast.walk(fn) if isinstance(n, ast.ExceptHandler)]
        raise_handlers = [n for n in handlers if
                          any(isinstance(s, ast.Raise) and
                              "Figure mapping halted" in ast.unparse(s)
                              for s in n.body)]
        self.assertEqual(len(raise_handlers), 1)
        self.assertFalse(any(isinstance(s, ast.Continue) for s in raise_handlers[0].body))

    def test_all_completed_log_is_after_page_loop(self):
        fn = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "run_mapping")
        self.assertIn("All selected figure mappings completed with no exceptions", ast.unparse(fn))


if __name__ == "__main__":
    unittest.main()
