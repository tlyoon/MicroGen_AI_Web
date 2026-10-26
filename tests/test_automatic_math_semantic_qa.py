"""Regression and adversarial tests for generic narration math-domain QA."""
import hashlib,os,unittest
from pathlib import Path
from selenium_pipeline.automatic_math_semantic_qa import inspect_math_semantics,repair_prompt

def grammar(*slides):
    return "\n\n".join(f"**Slide {i} [30 sec]:\n{body}**" for i,body in enumerate(slides,1))

class GeneralMathDomainGuard(unittest.TestCase):
    def test_negative_tangent_and_sine_reference_triangle_defects(self):
        s=grammar(
           "These algebraic substitutions correspond directly to right triangles with acute angle u.",
           "When x equals a tangent u, x and a represent the opposite and adjacent legs, making the hypotenuse the square root of a-squared plus x-squared.",
           "For sine, x is the opposite leg and a is the hypotenuse.",
           "For secant, the hypotenuse is x and the adjacent leg is a.")
        report=inspect_math_semantics(s)
        rules={x["rule"] for x in report["findings"]}
        self.assertTrue({"signed_angle_not_always_acute","signed_variable_as_side_length",
                         "signed_opposite_sine_length","unsigned_secant_hypotenuse"}.issubset(rules))
        self.assertEqual(report["status"],"MATH_DOMAIN_REPAIR_REQUIRED")
        self.assertFalse(report["independent_source_math_ai_review_approved"])
        fix=repair_prompt(report)
        self.assertIn("signed trigonometric substitutions",fix["instructions"])
        self.assertFalse(fix["model_web_dispatch_performed"])

    def test_corrected_geometry_not_flagged_by_same_rules(self):
        s=grammar(
          "Reference triangles use positive reference angles, even when u is negative.",
          "Assume a is positive. For x equals a tangent u, the adjacent leg is a and the opposite leg has length the absolute value of x.",
          "For x equals a sine u, the opposite side has length the absolute value of x. Cosine is non-negative on its restricted principal interval.",
          "For x equals a secant u, restrict to x at least a, so the hypotenuse has length x.")
        report=inspect_math_semantics(s)
        self.assertEqual(report["blocking_count"],0)
        self.assertFalse(report["all_mathematics_verified"])

    def test_root_principal_branch_and_division_guard(self):
        bad=grammar("The square root of x squared simplifies to x.",
                    "We cancel x on both sides.",
                    "The square root of secant squared eliminates the radical.")
        rules={x["rule"] for x in inspect_math_semantics(bad)["findings"]}
        self.assertIn("unchecked_principal_root_sign",rules)
        self.assertIn("division_by_possible_zero",rules)
        safe=grammar("Assuming x is nonnegative, the square root of x squared simplifies to x.",
                     "If x is nonzero, we cancel x on both sides.",
                     "On the positive cosine domain, the square root of secant squared simplifies to secant.")
        self.assertEqual(inspect_math_semantics(safe)["blocking_count"],0)

    def test_benign_physics_and_arithmetic_not_blocked(self):
        text=grammar("A right triangle with a known acute angle has two legs.",
                     "The factor of two cancels against the denominator.",
                     "Potential energy can be negative. Consider a charge at distance r.",
                     "For x equal to 2, three squared equals nine.")
        self.assertEqual(inspect_math_semantics(text)["blocking_count"],0)

    def test_reject_changed_sha_and_duplicate_slide(self):
        with self.assertRaises(ValueError):
            inspect_math_semantics(grammar("Intro"),source_sha256="madeup")
        with self.assertRaises(ValueError):
            inspect_math_semantics("**Slide 1 [1 sec]:\nOk\n**Slide 1 [1 sec]:\nDuplicate")
        with self.assertRaises(ValueError):
            inspect_math_semantics("")

    def test_real_original_thomas_84_is_flagged_before_TTS(self):
        root=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not root:self.skipTest("Genuine teaching source owned by Dell-115")
        folder=Path(root)
        original=(folder/"script.txt").read_bytes()
        sha=hashlib.sha256((folder/"source.pdf").read_bytes()).hexdigest()
        rep=inspect_math_semantics(original.decode("utf8"),source_sha256=sha)
        slide4=[x for x in rep["findings"] if x["slide"]==4]
        found={x["rule"] for x in slide4}
        self.assertIn("signed_angle_not_always_acute",found)
        self.assertIn("signed_variable_as_side_length",found)
        self.assertIn("signed_opposite_sine_length",found)
        self.assertEqual((folder/"script.txt").read_bytes(),original)

if __name__=="__main__": unittest.main()
