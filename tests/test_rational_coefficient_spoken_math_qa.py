"""Original-source rational-function narration: coefficient A is a named
parameter, not an ambiguous English article; never relax truly unsafe x=0
cancellations. All examples are synthetic and use no provider calls.
"""
import unittest
from selenium_pipeline.vendor_template_v2.script_tts_risk import analyze_script_text
from selenium_pipeline.automatic_math_semantic_qa import inspect_math_semantics

def fake(body):
    return "**Slide 1 [5 sec]:\nIntroduction.\n**Slide 2 [20 sec]:\n"+body

class RationalNarrationQA(unittest.TestCase):
    def kinds(self,body):
        return [(x["kind"],x["severity"]) for x in
            analyze_script_text(fake(body))["findings"]]
    def math_kinds(self,body):
        return [x["rule"] for x in inspect_math_semantics(fake(body))["findings"]]
    def test_named_undetermined_coefficient_a_is_not_blocked(self):
        s="We solve for the undetermined coefficient A and constant B."
        self.assertNotIn(("ambiguous_capital_a","blocking"),self.kinds(s))
    def test_for_a_and_b_after_coefficient_context_is_not_blocked(self):
        s=("Matching corresponding powers of x determines the coefficients "
           "so that we solve for A and B.")
        self.assertNotIn(("ambiguous_capital_a","blocking"),self.kinds(s))
    def test_real_unknown_context_for_a_remains_blocking(self):
        self.assertIn(("ambiguous_capital_a","blocking"),
                      self.kinds("Our argument treats A rational function differently."))
    def test_passive_fraction_with_nonzero_factor_is_not_false_cancellation(self):
        s=("We write the undetermined coefficient A divided by x plus two, "
           "with x not equal to negative two.")
        self.assertNotIn("division_by_possible_zero",self.math_kinds(s))
    def test_genuine_division_by_unrestricted_x_remains_blocking(self):
        self.assertIn("division_by_possible_zero",
                      self.math_kinds("We divide both sides by x to obtain the result."))
    def test_cancel_x_requires_nonzero_guard(self):
        self.assertIn("division_by_possible_zero",
                      self.math_kinds("We cancel the x factor in the numerator."))

if __name__=="__main__": unittest.main()
