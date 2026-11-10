"""Offline fault injection: duplicate Gemini figure rows must never trigger a resend."""
import ast
from pathlib import Path
import re
import unittest

VENDOR = (Path(__file__).resolve().parents[1] /
          "selenium_pipeline" / "vendor_template_v2" /
          "map_and_rename_selenium_v8.py")


def shared_reconciler():
    """Compile exactly the pure function shipped in the normal vendor worker."""
    tree = ast.parse(VENDOR.read_text(encoding="utf8"))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == "reconcile_surplus_duplicate_mappings"]
    assert len(functions) == 1
    scope = {"List": list, "Tuple": tuple, "Path": Path, "re": re}
    exec(compile(ast.Module(body=functions, type_ignores=[]),
                 str(VENDOR), "exec"), scope)
    return scope[functions[0].name]


CROPS = [Path("fig_2.png"), Path("fig_4.png")]
RESPONSE = (
    'fig_2.png : "Figure 7.5" : Figure 7.5.png\n'
    'fig_4.fig_2_75e426.png : "Figure 7.5" : Figure 7.5.png\n'
    'fig_4_75e426.png : "Figure 7.6" : Figure 7.6.png'
)
EXPECTED = [
    ("fig_2.png", "Figure 7.5", "Figure 7.5.png"),
    ("fig_4_75e426.png", "Figure 7.6", "Figure 7.6.png"),
]


class FigureMappingSurplusRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reconcile = staticmethod(shared_reconciler())

    def test_actual_immutable_three_rows_for_two_crops_structurally_deduplicate(self):
        rows = [("fig_2.png", "Figure 7.5", "Figure 7.5.png"),
                ("fig_4.fig_2_75e426.png", "Figure 7.5", "Figure 7.5.png"),
                ("fig_4_75e426.png", "Figure 7.6", "Figure 7.6.png")]
        copy = rows[:]
        result, yes = self.reconcile(rows, CROPS)
        self.assertTrue(yes)
        self.assertEqual(result, EXPECTED)
        self.assertEqual(rows, copy)  # Original untrusted response untouched.

    def assert_unresolved(self, rows, crops=CROPS):
        unchanged = rows[:]
        result, reconciled = self.reconcile(rows, crops)
        self.assertFalse(reconciled)
        self.assertEqual(result, unchanged)

    def test_model_changes_second_figure_label_conflicts(self):
        self.assert_unresolved([
            ("fig_2.png", "Figure 7.5", "Figure 7.5.png"),
            ("fig_4_abcabc.png", "Figure 7.7", "Figure 7.7.png"),
            ("fig_4.png", "Figure 7.6", "Figure 7.6.png")])

    def test_same_caption_with_different_output_names_is_not_duplicate(self):
        self.assert_unresolved([
            ("fig_2.png", "Figure 7.5", "Figure 7.5.png"),
            ("fig_4_75e426.png", "Figure 7.5", "Figure 7.5 copy.png"),
            ("fig_4.png", "Figure 7.6", "Figure 7.6.png")])

    def test_different_captions_with_same_output_name_is_not_duplicate(self):
        self.assert_unresolved([
            ("fig_2.png", "Figure 7.5", "Figure 7.5.png"),
            ("fig_4_75e426.png", "Figure 7.6", "Figure 7.5.png"),
            ("fig_4.png", "Figure 7.6", "Figure 7.6.png")])

    def test_other_exact_crop_name_cannot_be_discarded_as_duplicate(self):
        self.assert_unresolved([
            ("fig_2.png", "Figure 7.5", "Figure 7.5.png"),
            ("fig_4.png", "Figure 7.5", "Figure 7.5.png"),
            ("fig_4_75e426.png", "Figure 7.6", "Figure 7.6.png")])

    def test_reversed_crop_order_does_not_get_assigned_by_position(self):
        self.assert_unresolved([
            ("fig_4.png", "Figure 7.6", "Figure 7.6.png"),
            ("fig_4_75e426.png", "Figure 7.6", "Figure 7.6.png"),
            ("fig_2.png", "Figure 7.5", "Figure 7.5.png")])

    def test_missing_crop_identity_cannot_be_inferred_from_caption(self):
        self.assert_unresolved([
            ("fig_2.png", "Figure 7.5", "Figure 7.5.png"),
            ("fig_2_abcabc.png", "Figure 7.5", "Figure 7.5.png"),
            ("unrelated.png", "Figure 7.6", "Figure 7.6.png")])

    def test_non_hex_alias_and_target_caption_mismatch_rejected(self):
        self.assert_unresolved([
            ("fig_2.png", "Figure 7.5", "Figure 7.5.png"),
            ("fig_2_abcabc.png", "Figure 7.5", "Figure 7.5.png"),
            ("fig_4_arbitrary.png", "Figure 7.6", "Figure 7.6.png")])
        self.assert_unresolved([
            ("fig_2.png", "Figure 7.5", "Figure 7.4.png"),
            ("fig_2_abcabc.png", "Figure 7.5", "Figure 7.4.png"),
            ("fig_4_75e426.png", "Figure 7.6", "Figure 7.6.png")])

    def test_genuinely_identical_captions_for_two_crops_not_auto_collapsed(self):
        self.assert_unresolved([
            ("fig_2.png", "Figure 7.5", "Figure 7.5.png"),
            ("fig_2_abcabc.png", "Figure 7.5", "Figure 7.5.png"),
            ("fig_4.png", "Figure 7.5", "Figure 7.5.png")])

    def test_too_many_or_too_few_rows_unchanged(self):
        same = [("fig_2.png", "Figure 7.5", "Figure 7.5.png")]
        self.assert_unresolved(same)
        excess = [EXPECTED[0]] * 4 + [EXPECTED[1]]
        self.assert_unresolved(excess)
        self.assert_unresolved([EXPECTED[0]] * 2, [Path("fig_2.png")])

    def test_normal_worker_wires_reconcile_before_exact_count_and_retains_raw(self):
        source = VENDOR.read_text(encoding="utf8")
        self.assertIn("reconcile_surplus_duplicate_mappings(\n", source)
        self.assertLess(
            source.index("deduped, proven_duplicate = reconcile_surplus_duplicate_mappings("),
            source.index("exact_count = len(parsed) == len(fig_files)"))
        self.assertIn("_surplus_mapping_untrusted.txt", source)
        self.assertIn("validate_and_prepare_mappings(resolved_triples)", source)
        self.assertIn("if len(parsed) != len(fig_files) or _looks_like_gemini_failure_text(txt)", source)


if __name__ == "__main__":
    unittest.main()
