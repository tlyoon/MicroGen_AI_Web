"""Conservative real-PDF speech-vs-notation ranking: no semantic approval."""
import unittest
from selenium_pipeline.element_plan_autodraft import (
    _exact_spoken_math_operator_hint,stable_recommendations)


def target(text, *, kind="text_block", id="s011.text.003"):
    return {"draft_element_id":id,"kind":kind,"visible_text":text,
            "anchor":{"type":"text_block","index":0}}


class ExactSpokenOperatorHintsTests(unittest.TestCase):
    def test_literal_plus_equals_matches_only_identical_operands_and_result(self):
        speech=" So, n plus m equals one."
        good=target("n + m = 1\nand\nm = 2")
        self.assertGreater(_exact_spoken_math_operator_hint(
            speech,good["visible_text"]),0.8)
        ranked=stable_recommendations(speech,[good])
        self.assertEqual([x["draft_element_id"] for x in ranked],
                         ["s011.text.003"])
        self.assertGreaterEqual(ranked[0]["overlap_hint"],0.9)
        for wrong in ("n + m = 2","m + n = 1","n + 2 = 1",
                      "n + m = 11","n = m + 1"):
            with self.subTest(wrong=wrong):
                self.assertEqual(
                    _exact_spoken_math_operator_hint(speech,wrong),0.0)

    def test_proportional_to_exact_variables_and_exponent(self):
        speech=(" Bringing it all together, we conclude that position x "
                "is proportional to acceleration a times time t squared.")
        good=target("Conclusion: x ∝at2",id="s008.text.009")
        matches=stable_recommendations(speech,[good])
        self.assertTrue(matches)
        self.assertEqual(matches[0]["draft_element_id"],"s008.text.009")
        self.assertGreaterEqual(matches[0]["overlap_hint"],0.9)
        for wrong in ("Conclusion x ∝ at3","Conclusion y ∝ at2",
                      "Conclusion x ∝ bt2", "Conclusion x ∝ ta2",
                      "Conclusion x = at2"):
            with self.subTest(wrong=wrong):
                self.assertEqual(
                    _exact_spoken_math_operator_hint(speech,wrong),0.0)

    def test_literal_unit_ratio_does_not_conflate_squared_denominators(self):
        phrase=(" One factor of time cancels in the denominator, "
                "leaving us with length divided by time on the right side.")
        good=target("Because both sides yield L/T, the expression is correct",
                    id="s009.text.010")
        self.assertGreater(_exact_spoken_math_operator_hint(
            phrase,good["visible_text"]),0.6)
        self.assertEqual(stable_recommendations(
            phrase,[good])[0]["draft_element_id"],"s009.text.010")
        squared="The dimension is length divided by time squared."
        for wrong in ("Result L/T²","Result L/T2","Result L/T^2"):
            with self.subTest(wrong=wrong):
                self.assertEqual(
                    _exact_spoken_math_operator_hint(squared,wrong),0)

    def test_unobserved_fraction_geometry_not_manufactured(self):
        speech=" The number one half is dimensionless."
        self.assertEqual(_exact_spoken_math_operator_hint(
            speech,"Proposed equation: x = 1"),0)
        self.assertEqual(_exact_spoken_math_operator_hint(
            speech,"2at2"),0)
        self.assertEqual(stable_recommendations(
            speech,[target("Proposed equation x = 1"),
                    target("2at2",id="s006.text.004")]),[])

    def test_semantic_paraphrase_without_literal_match_remains_unranked(self):
        speech=" You cannot add a length to a time."
        self.assertEqual(_exact_spoken_math_operator_hint(
            speech,"Quantities can be added or subtracted only if they "
                   "have the same dimensions."),0)

    def test_no_image_or_panel_without_existing_visual_authority(self):
        speech=" So, n plus m equals one."
        self.assertEqual(stable_recommendations(
            speech,[target("n + m = 1",kind="image_whole")]),[])

    def test_retired_or_unknown_recovery_registry_removes_only_new_hint(self):
        from unittest.mock import patch
        speech="So, n plus m equals one."
        expected=target("n + m = 1")
        self.assertTrue(stable_recommendations(speech,[expected]))
        for mock_value in (None, "RETIRED_UNVERIFIED_FIX"):
            with self.subTest(mock_value=mock_value):
                with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                           return_value=mock_value):
                    self.assertEqual(stable_recommendations(
                        speech,[expected]),[])
        self.assertEqual(stable_recommendations(
            "Dimensions must match",[target("Dimensions must match")])[0][
                "draft_element_id"],"s011.text.003")

    def test_existing_trig_mismatch_still_excluded(self):
        speech="The sine of theta is positive."
        results=stable_recommendations(
            speech,[target("cos theta = 1")])
        self.assertEqual(results,[])

    def test_ordinary_lexical_candidate_remains_available(self):
        speech="Dimensions must match across both sides."
        good=target("Dimensions must match")
        self.assertTrue(stable_recommendations(speech,[good]))


if __name__=="__main__":
    unittest.main()
