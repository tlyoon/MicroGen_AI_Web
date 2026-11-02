import unittest
import sympy as s
from selenium_pipeline.original_figure83_inverse_branch_semantics import branch_science, CLAUSES
class ExactInverseFunctionTests(unittest.TestCase):
    def test_source_scoped_slides(self):
        self.assertEqual(sorted(CLAUSES),[6,7])
        self.assertEqual(sum(len(x) for x in CLAUSES.values()),8)
    def test_formula_domains(self):
        report=branch_science()
        self.assertTrue(report["original_graph_arctangent_inverse_principal_domain_sampled_exact"])
        self.assertTrue(report["original_graph_arcsecant_two_branch_principal_domains_sampled_exact"])
        self.assertFalse(report["spoken_figure_element_word_sync_fully_approved"])
    def test_outside_principal_branch(self):
        self.assertNotEqual(s.atan(s.tan(3*s.pi/4)),3*s.pi/4)
    def test_secant_radicand_domain(self):
        t=-s.pi/6
        x=3*s.sec(t)
        self.assertNotEqual(s.simplify(s.sqrt(x*x-9)-3*s.tan(t)),0)
if __name__=="__main__":
    unittest.main()
