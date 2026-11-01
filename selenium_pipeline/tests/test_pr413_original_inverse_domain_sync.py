"""Fail closed on corrupted original inverse domain boundaries and labels."""
import unittest
from selenium_pipeline.original_thomas84_slide7_inverse_domain_sync import (
    LATEX_WITNESSES,KINDS,RECTS,prove_publisher_math,_compact)

class InversePrincipalBranchSourceGuard(unittest.TestCase):
    @staticmethod
    def publisher():
        return ("As we know from Section 1.6\n"
                "x = a sin u\nrequires\nu = sin-1\n"
                "x = a sec u\nrequires\nu = sec-1\n"
                "0 … u 6 p\np\n2 6 u … p\n"
                "free of absolute values\nFIGURE 8.3")
    @staticmethod
    def latex():
        return "\n".join(LATEX_WITNESSES)
    @staticmethod
    def pdf():
        return "sin−1 sec−1 ≤θ ≥1 ≤−1 √ a tan θ"

    def test_real_source_math_constraints_kept_distinct(self):
        proof=prove_publisher_math(self.publisher(),self.latex(),self.pdf())
        self.assertTrue(proof["original_arcsine_endpoints_inclusive"])
        self.assertTrue(proof["original_arcsecant_positive_branch_halfopen"])
        self.assertTrue(proof["original_positive_tangent_abs_removed_valid"])

    def test_arcsine_endpoint_changed_to_strict_is_blocked(self):
        altered=self.latex().replace(
            r"-\frac{\pi}{2} \le \theta \le \frac{\pi}{2}",
            r"-\frac{\pi}{2} < \theta < \frac{\pi}{2}")
        with self.assertRaises(Exception):
            prove_publisher_math(self.publisher(),altered,self.pdf())

    def test_arcsecant_wrong_negative_branch_sign_blocked(self):
        changed=self.latex().replace(
            r"\frac{x}{a} \le -1",r"\frac{x}{a} \ge -1")
        with self.assertRaises(Exception):
            prove_publisher_math(self.publisher(),changed,self.pdf())

    def test_nonnegative_tangent_claim_must_be_retained(self):
        altered=self.latex().replace(
            r"\tan \theta \ge 0",r"\tan \theta \le 0")
        with self.assertRaises(Exception):
            prove_publisher_math(self.publisher(),altered,self.pdf())

    def test_missing_publisher_positive_branch_blocks(self):
        with self.assertRaises(Exception):
            prove_publisher_math(self.publisher().replace("0 … u 6 p",""),
                                 self.latex(),self.pdf())

    def test_missing_actual_visible_arcsecant_symbol_blocks(self):
        with self.assertRaises(Exception):
            prove_publisher_math(self.publisher(),self.latex(),
                                 self.pdf().replace("sec−1","sin−1"))

    def test_separate_three_source_math_regions(self):
        self.assertEqual(len(KINDS),3)
        self.assertEqual(set(KINDS),set(RECTS))
        self.assertLess(RECTS[KINDS[0]][3],RECTS[KINDS[1]][1])
        self.assertLess(RECTS[KINDS[1]][3],RECTS[KINDS[2]][1])

if __name__=="__main__":
    unittest.main()
