"""TTS lint regression: explicitly defined area A remains a warning, not a blocker."""
import unittest
from selenium_pipeline.vendor_template_v2.script_tts_risk import (
    analyze_script_text, CAPITAL_A_DEFINITION)


def report(*bodies):
    return analyze_script_text("\n".join(
        f"**Slide {i} [25 sec]:**\n{body}\n"
        for i,body in enumerate(bodies, start=1)))


class ScientificCapitalARiskTests(unittest.TestCase):
    def test_explicit_same_slide_area_a_allows_later_formula_usage(self):
        result=report("Introduction.",
            "The cross-sectional area A is perpendicular to the flow. "
            "We divide mass by A to find this expression.")
        self.assertEqual(result["summary"]["blocking"],0)
        self.assertTrue(any(x["text"]=="A" and x["severity"]=="warning"
                            for x in result["findings"]))

    def test_defined_area_a_remains_in_scope_across_later_slides(self):
        result=report(
            "Introduction.",
            "The cross-sectional area A represents the projected area.",
            "Drag is proportional to speed squared and divided by A.",
            "The final expression contains rho times A.")
        self.assertEqual(result["summary"]["blocking"],0)

    def test_an_undefined_mid_sentence_capital_a_still_blocks(self):
        result=report("Introduction.",
            "This is A simple statement with unexplained capitalization.")
        self.assertGreater(result["summary"]["blocking"],0)
        self.assertTrue(any(x["kind"]=="ambiguous_capital_a"
                            and x["severity"]=="blocking"
                            for x in result["findings"]))

    def test_lowercase_article_does_not_declare_symbol(self):
        self.assertIsNone(CAPITAL_A_DEFINITION.search("the area a is positive"))
        result=report("Introduction.",
            "The area a is a phrase. We divide by A something.")
        self.assertGreater(result["summary"]["blocking"],0)

if __name__ == "__main__":
    unittest.main()
