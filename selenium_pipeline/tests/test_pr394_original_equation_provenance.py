"""Original equation chain witnesses reject changed math, even at endpoints."""
import unittest
from selenium_pipeline.original_thomas84_equation_provenance import canonical,match_line

TAN="a2 + x2 = a2 + a2 tan2 u = a2(1 + tan2 u) = a2 sec2 u."
SIN="a2 - x2 = a2 - a2 sin2 u = a2(1 - sin2 u) = a2 cos2 u."
SEC="x2 - a2 = a2 sec2 u - a2 = a2(sec2 u - 1) = a2 tan2 u."

class TestOriginalSourceEquationCorrespondence(unittest.TestCase):
    def test_full_chain_with_greek_variable_rename_matches(self):
        self.assertEqual(len(match_line(
            "a2 + x2 = a2 + a2 tan2 θ = a2(1 + tan2 θ) = a2 sec2 θ",
            [[TAN]],slide=5)),1)
    def test_first_and_last_equations_matched_on_one_source_chain(self):
        self.assertEqual(len(match_line(
            "x2 −a2 = a2 tan2 θ.",[[TAN,SEC]],slide=4)),1)
        self.assertEqual(len(match_line(
            "a2 −x2 = a2 cos2 θ.",[[SIN]],slide=4)),1)
    def test_middle_operator_corruption_rejected_on_full_chain(self):
        self.assertFalse(match_line(
            "a2+x2=a2+a2tan2θ=a2(1-tan2θ)=a2sec2θ",
            [[TAN]],slide=5))
    def test_endpoint_function_and_sign_corruption_rejected(self):
        self.assertFalse(match_line("a2+x2=a2cos2θ",[[TAN]],slide=4))
        self.assertFalse(match_line("a2-x2=a2sec2θ",[[SIN]],slide=4))
        self.assertFalse(match_line("x2+a2=a2tan2θ",[[SEC]],slide=4))
    def test_theta_and_u_normalization_only_preserves_operators(self):
        self.assertEqual(canonical(" 9 − x2 = 9 cos2 θ."),
                         canonical("9 - x2 = 9 cos2 u"))
        self.assertNotEqual(canonical("9-x2=9cos2u"),
                            canonical("9-x2=9sin2u"))
    def test_substitution_source_text_does_not_prove_unrelated_equation(self):
        self.assertFalse(match_line("x = a cot θ",[[TAN,SIN,SEC]],slide=3))
        self.assertEqual(len(match_line("x = a sec θ",
                         [["The original substitution is x = a sec u."]],
                         slide=3)),1)

if __name__=="__main__":
    unittest.main()
