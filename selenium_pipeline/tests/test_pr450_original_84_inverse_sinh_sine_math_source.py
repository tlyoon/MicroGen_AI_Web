"""Original §8.4 source Example2/3 exact calculus and domain bounds."""
import importlib.util
import unittest
from selenium_pipeline.original_thomas84_two_examples_source_math_equivalence import (
    STATUS,CLAUSES,check_exact_math,
)

class OriginalInverseSinhSineExamples(unittest.TestCase):
    def test_original_11_12_13_author_math_source_clauses(self):
        self.assertEqual(sorted(CLAUSES),[11,12,13])
        self.assertEqual(sum(map(len,CLAUSES.values())),13)
        self.assertIn("Figure 8.5.png",CLAUSES[13])
        self.assertIn("NONPRODUCTION",STATUS)

    @unittest.skipUnless(importlib.util.find_spec("sympy"),"SymPy unavailable")
    def test_exact_source_inverse_sinh_and_sine_primitive(self):
        result=check_exact_math()
        self.assertTrue(result["inverse_hyperbolic_log_formula_same_derivative_and_zero_constant"])
        self.assertTrue(result["sine_substitution_jacobian_and_positive_cos_branch_exact"])
        self.assertTrue(result["publisher_example3_final_radical_integral_exact_derivative"])
        self.assertFalse(result["whole_original_41_slide_math_and_figure_labels_accepted"])

    @unittest.skipUnless(importlib.util.find_spec("sympy"),"SymPy unavailable")
    def test_wrong_sign_in_final_radical_integral_is_detectable(self):
        import sympy as s
        x=s.symbols("x",real=True)
        wrong=s.Rational(9,2)*s.asin(x/3)+x*s.sqrt(9-x*x)/2
        difference=s.simplify(s.diff(wrong,x)-x*x/s.sqrt(9-x*x))
        self.assertNotEqual(difference,0)
        self.assertNotEqual(s.simplify(difference.subs(x,1)),0)

    @unittest.skipUnless(importlib.util.find_spec("sympy"),"SymPy unavailable")
    def test_cosine_positive_branch_must_not_be_extended(self):
        import sympy as s
        positive=s.simplify(s.sqrt(9*s.cos(s.pi/3)**2)-3*s.cos(s.pi/3))
        invalid=s.simplify(s.sqrt(9*s.cos(2*s.pi/3)**2)-3*s.cos(2*s.pi/3))
        self.assertEqual(positive,0)
        self.assertNotEqual(invalid,0)

if __name__=="__main__":
    unittest.main()
