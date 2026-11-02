"""Source-locked exact textbook Example2/Reduction/Example4 regression."""
import importlib.util
import unittest
from selenium_pipeline.original_thomas86_three_math_expression_equivalence import (
    STATUS,CLAUSES,PUBLISHER_TERMS,exact_symbolic_derivative_identity,
    symbolic_source_mathematics,
)

class ThreePublisherOriginalMathSlides(unittest.TestCase):
    def test_requires_original_source_pages_and_equation_clauses(self):
        self.assertEqual(sorted(CLAUSES),[5,7,8])
        self.assertEqual(sum(len(v) for v in CLAUSES.values()),14)
        self.assertIn("EXAMPLE 2",PUBLISHER_TERMS[5])
        self.assertIn("Reduction Formulas",PUBLISHER_TERMS[7])
        self.assertIn("EXAMPLE 4",PUBLISHER_TERMS[8])
        self.assertIn("NONPRODUCTION",STATUS)

    @unittest.skipUnless(importlib.util.find_spec("sympy"),"SymPy unavailable")
    def test_exact_source_derivative_checks_pass(self):
        science=symbolic_source_mathematics()
        self.assertTrue(science[
            "slide5_table29b_general_and_substituted_positive_domain_derivatives"])
        self.assertTrue(science[
            "slide8_example4_two_independent_primitives_and_composed_chain"])
        self.assertFalse(science[
            "complete_publisher_math_proof_for_all_lecture_formulas"])

    @unittest.skipUnless(importlib.util.find_spec("sympy"),"SymPy unavailable")
    def test_trig_reduction_canonicalization_avoids_false_failure(self):
        import sympy as s
        x=s.symbols("x",real=True)
        i5=s.tan(x)**4/4-s.tan(x)**2/2-s.log(s.cos(x))
        # Single trigsimp genuinely can leave an unreduced nonzero expression.
        self.assertTrue(exact_symbolic_derivative_identity(
            primitive=i5,integrand=s.tan(x)**5,variable=x))

    @unittest.skipUnless(importlib.util.find_spec("sympy"),"SymPy unavailable")
    def test_incorrect_integrand_does_not_get_false_positive(self):
        import sympy as s
        x=s.symbols("x",real=True)
        i5=s.tan(x)**4/4-s.tan(x)**2/2-s.log(s.cos(x))
        self.assertFalse(exact_symbolic_derivative_identity(
            primitive=i5,integrand=s.tan(x)**3,variable=x))
        self.assertFalse(exact_symbolic_derivative_identity(
            primitive=i5+s.sin(x),integrand=s.tan(x)**5,variable=x))

if __name__=="__main__":
    unittest.main()
