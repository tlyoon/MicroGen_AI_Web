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


class ActualNormalFigureWorkerReconciliation(unittest.TestCase):
    """Execute the vendor's REAL stage function on offline, isolated source data."""

    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.page = self.root / "page_1.png"
        self.page.write_bytes(b"original page image fixture")
        self.crops = self.root / "crops"
        self.crops.mkdir()
        (self.crops / "fig_2.png").write_bytes(b"original crop two")
        (self.crops / "fig_4.png").write_bytes(b"original crop four")

    def worker(self, model_reply, calls):
        import json
        import os
        import shutil
        import subprocess
        import sys
        import time
        from types import SimpleNamespace
        tree = ast.parse(VENDOR.read_text(encoding="utf8"))
        needed = {"parse_mapping_lines", "reconcile_surplus_duplicate_mappings",
                  "map_and_rename_single_step"}
        found = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in needed]
        self.assertEqual({node.name for node in found}, needed)
        future = ast.ImportFrom(module="__future__",
                                names=[ast.alias(name="annotations")], level=0)
        module = ast.fix_missing_locations(
            ast.Module(body=[future, *found], type_ignores=[]))
        def owned_model_response(*args, **kwargs):
            calls.append("one_old_response")
            return model_reply
        scope = {
            "Path": Path, "List": list, "Tuple": tuple, "Optional": object,
            "re": re, "json": json, "os": os, "shutil": shutil,
            "subprocess": subprocess, "sys": sys, "time": time,
            "CFG": SimpleNamespace(root=self.root),
            "_ts_now": time.perf_counter,
            "natural_sort_key": lambda name: name,
            "log": lambda *args, **kwargs: None,
            "log_timing": lambda *args, **kwargs: None,
            "clean_model_text": lambda raw: raw,
            "_page_text_lower": lambda driver: "",
            "_looks_like_gemini_failure_text": lambda text: False,
            "_send_prompt_and_capture_mapping_text": owned_model_response,
        }
        exec(compile(module, str(VENDOR), "exec"), scope)
        class FakeClient:
            driver = None
            def open_clean_gemini_chat(self):
                pass
            def upload_files(self, paths):
                self.uploads = [p.name for p in paths]
        return scope["map_and_rename_single_step"], FakeClient()

    def test_original_surplus_reply_uses_one_capture_and_writes_two_exact_source_crops(self):
        import hashlib
        import json
        calls = []
        work, client = self.worker(RESPONSE, calls)
        mapping_path, mapped = work(client, self.page, self.crops, wait_cap=60,
                                    backend_override="selenium", single_attempt=True)
        self.assertEqual(calls, ["one_old_response"])
        self.assertEqual(client.uploads,
                         ["page_1.png", "fig_2.png", "fig_4.png"])
        self.assertEqual([p.name for p in mapped],
                         ["Figure 7.5.png", "Figure 7.6.png"])
        self.assertEqual((self.crops / "Figure 7.5.png").read_bytes(),
                         (self.crops / "fig_2.png").read_bytes())
        self.assertEqual((self.crops / "Figure 7.6.png").read_bytes(),
                         (self.crops / "fig_4.png").read_bytes())
        self.assertEqual(len(mapping_path.read_text().strip().splitlines()), 2)
        untrusted = self.root / "page_1_surplus_mapping_untrusted.txt"
        evidence = json.loads(
            (self.root / "page_1_surplus_mapping_evidence.json").read_text())
        self.assertEqual(untrusted.read_text().strip(), RESPONSE)
        self.assertEqual(evidence["original_model_response_sha256"],
                         hashlib.sha256(untrusted.read_bytes()).hexdigest())
        self.assertEqual(evidence["original_parsed_lines"], 3)
        self.assertEqual(evidence["structurally_resolved_lines"], 2)
        self.assertEqual(evidence["page_image_sha256"],
                         hashlib.sha256(self.page.read_bytes()).hexdigest())
        self.assertFalse(evidence["new_provider_requests_for_reconciliation"])
        self.assertFalse(evidence["independent_figure_caption_semantics_verified"])
        self.assertFalse(evidence["student_publication_authorized"])

    def test_conflicting_surplus_reply_stops_without_publishing_any_mapping(self):
        calls = []
        response = (RESPONSE.replace(
            'fig_4.fig_2_75e426.png : "Figure 7.5" : Figure 7.5.png',
            'fig_4.png : "Figure 7.5" : Figure 7.5.png'))
        work, client = self.worker(response, calls)
        with self.assertRaisesRegex(RuntimeError, "Unverified figure mapping"):
            work(client, self.page, self.crops, wait_cap=60,
                 backend_override="selenium", single_attempt=True)
        self.assertEqual(calls, ["one_old_response"])
        self.assertFalse((self.crops / "Figure 7.5.png").exists())
        self.assertFalse((self.crops / "Figure 7.6.png").exists())
        self.assertFalse((self.root / "page_1_surplus_mapping_evidence.json").exists())
        self.assertEqual((self.crops / "fig_2.png").read_bytes(),
                         b"original crop two")


if __name__ == "__main__":
    unittest.main()
