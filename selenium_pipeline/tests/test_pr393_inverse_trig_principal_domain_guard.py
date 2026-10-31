"""Regression of original Thomas 8.4 sine/tangent principal-domain confusion."""
import unittest
from selenium_pipeline.inverse_trig_principal_domain_guard import inspect_tex

STRICT=(r"$-\frac{\pi}{2} < \theta < \frac{\pi}{2}$")
OPENING=r"\begin{frame}{Review Questions}"+"\n"+r"\begin{enumerate}"+"\n"
CLOSING=r"\end{enumerate}"+"\n"+r"\end{frame}"

def slide(statement):
    return OPENING+r"\item "+statement+"\n"+CLOSING

class PrincipalDomainPreTtsGuardTests(unittest.TestCase):
    def test_strict_domain_for_both_inverse_functions_blocks(self):
        report=inspect_tex(slide("Why do domain restrictions matter for reversibility"
            " (such as "+STRICT+" for sine and tangent)?"))
        self.assertEqual(report["blocking_count"],1)
        self.assertEqual(report["findings"][0]["slide"],1)

    def test_tangent_strict_plus_sine_inclusive_passes(self):
        good=slide("For inverses and reversibility, "+
                   STRICT+" for tangent versus "+
                   r"$-\frac{\pi}{2} \le \theta \le \frac{\pi}{2}$ for sine.")
        self.assertEqual(inspect_tex(good)["blocking_count"],0)

    def test_allowed_open_sine_for_singular_integrand_not_flagged(self):
        singular=slide("For this singular integral x=3 sine theta, "+
                       STRICT+" for sine and tangent; endpoints excluded "
                       "because the original integrand is undefined.")
        self.assertEqual(inspect_tex(singular)["blocking_count"],0)

    def test_unrelated_math_slides_do_not_cross_join(self):
        mix=slide("For tangent, "+STRICT+" permits reversibility.")+"\n"+slide(
            "Sine and tangent appear in integrals with separate domains.")
        self.assertEqual(inspect_tex(mix)["blocking_count"],0)

    def test_everything_else_remains_unapproved(self):
        self.assertFalse(inspect_tex(slide("A sine substitution."))[
            "all_other_mathematics_semantically_verified"])

if __name__=="__main__":
    unittest.main()
