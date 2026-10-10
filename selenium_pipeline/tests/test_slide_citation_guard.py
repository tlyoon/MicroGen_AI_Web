import ast
import re
import unittest
from pathlib import Path
from typing import List


ROOT = Path(__file__).resolve().parents[1]
SLIDES = ROOT / "vendor_template_v2" / "gen_slides_selenium_v11.py"
PROMPT = ROOT / "vendor_template_v2" / "gen_slides_prompt_v23.txt"


def load_citation_guard():
    tree = ast.parse(SLIDES.read_text(encoding="utf-8"))
    wanted_assignments = {
        "SAFE_CITATION_ARTIFACT_RE",
        "CITATION_ARTIFACT_PATTERNS",
    }
    wanted_functions = {
        "strip_unmistakable_citation_artifacts",
        "find_citation_artifacts",
    }
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & wanted_assignments:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected.append(node)
    ns = {"re": re, "List": List}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(SLIDES), "exec"), ns)
    return ns


class SlideCitationGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guard = load_citation_guard()

    def test_unmistakable_cite_tags_are_removed(self):
        clean, removed = self.guard["strip_unmistakable_citation_artifacts"](
            r"Zero resistance. [cite: 1] High-Tc ceramics. [cite: 1, 2]"
        )
        self.assertEqual(clean, "Zero resistance.  High-Tc ceramics. ")
        self.assertEqual(removed, ["[cite: 1]", "[cite: 1, 2]"])

    def test_legitimate_square_bracket_physics_is_preserved(self):
        original = r"The normalized coordinate lies in [0, 1] and M=[1,0;0,1]."
        clean, removed = self.guard["strip_unmistakable_citation_artifacts"](original)
        self.assertEqual(clean, original)
        self.assertEqual(removed, [])

    def test_detector_catches_source_tracking_variants(self):
        find = self.guard["find_citation_artifacts"]
        text = (
            r"A [citation: 3] B [source: 4] C 【1】 "
            r"D turn0search1 E \cite{smith2026}"
        )
        found = find(text)
        self.assertTrue(any("[citation: 3]" == x for x in found))
        self.assertTrue(any("[source: 4]" == x for x in found))
        self.assertTrue(any("【1】" == x for x in found))
        self.assertTrue(any("turn0search1" == x for x in found))
        self.assertTrue(any(r"\cite{smith2026}" == x for x in found))

    def test_prompt_explicitly_prohibits_citation_leakage(self):
        prompt = PROMPT.read_text(encoding="utf-8")
        self.assertIn("NEVER expose source-tracking metadata", prompt)
        self.assertIn("[cite: 1, 2]", prompt)
        self.assertIn(r"LaTeX \cite{...}", prompt)

    def test_release_gate_scans_latex_and_rendered_pdf(self):
        source = SLIDES.read_text(encoding="utf-8")
        self.assertIn("citation/source-tracking artifact(s) remain in LaTeX", source)
        self.assertIn("citation/source-tracking artifact(s) visible in compiled PDF", source)
        self.assertIn("Final slide deck passed citation/source-tracking artifact gate.", source)


if __name__ == "__main__":
    unittest.main()
