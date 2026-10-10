import unittest

from selenium_pipeline.vendor_template_v2.script_tts_risk import (
    analyze_script_text,
    collect_tts_risks,
)


class ScriptTTSRiskTests(unittest.TestCase):
    def test_single_letter_period_is_warning_for_acoustic_qa(self):
        findings = collect_tts_risks(
            "The constant c. determines the value.",
            slide=2,
        )
        self.assertTrue(
            any(
                item["kind"] == "dotted_single_letter"
                and item["text"] == "c."
                and item["severity"] == "warning"
                for item in findings
            )
        )
        self.assertFalse(any(item["severity"] == "blocking" for item in findings))

    def test_isolated_y_is_warning_for_acoustic_qa(self):
        findings = collect_tts_risks("The force points along Y", slide=4)
        self.assertTrue(
            any(
                item["severity"] == "warning"
                and item["text"] == "Y"
                for item in findings
            )
        )
        self.assertFalse(any(item["severity"] == "blocking" for item in findings))

    def test_sentence_ending_r_is_warning_not_blocking(self):
        findings = collect_tts_risks("The radial distance is r.", slide=4)
        self.assertTrue(
            any(
                item["kind"] == "dotted_single_letter"
                and item["text"] == "r."
                and item["severity"] == "warning"
                for item in findings
            )
        )
        self.assertFalse(any(item["severity"] == "blocking" for item in findings))

    def test_explicit_y_axis_is_not_blocking(self):
        findings = collect_tts_risks("The force points along the y-axis.", slide=4)
        self.assertFalse(any(item["severity"] == "blocking" for item in findings))

    def test_contextual_charge_letter_is_warning_not_blocking(self):
        findings = collect_tts_risks("The force on charge A is to the left.", slide=4)
        self.assertTrue(
            any(
                item["kind"] == "contextual_letter"
                and item["text"] == "A"
                and item["severity"] == "warning"
                for item in findings
            )
        )
        self.assertFalse(any(item["severity"] == "blocking" for item in findings))

    def test_explicit_capital_letter_a_is_warning_not_blocking(self):
        findings = collect_tts_risks(
            "The cap area capital A cancels from both sides.",
            slide=16,
        )
        self.assertTrue(
            any(
                item["kind"] == "contextual_letter"
                and item["text"] == "A"
                and item["severity"] == "warning"
                for item in findings
            )
        )
        self.assertFalse(any(item["severity"] == "blocking" for item in findings))

    def test_mid_sentence_capital_a_article_is_blocking(self):
        findings = collect_tts_risks("We use A torsion balance here.", slide=3)
        self.assertTrue(
            any(
                item["kind"] == "ambiguous_capital_a"
                and item["text"] == "A"
                and item["severity"] == "blocking"
                for item in findings
            )
        )

    def test_slide_one_exact_title_risk_is_warning_only(self):
        report = analyze_script_text(
            "**Slide 1 [5 sec]:\nY c. title**\n\n"
            "**Slide 2 [20 sec]:\nThe y-axis is vertical.**"
        )
        self.assertEqual(report["summary"]["blocking"], 0)
        self.assertGreaterEqual(report["summary"]["warnings"], 1)


if __name__ == "__main__":
    unittest.main()
