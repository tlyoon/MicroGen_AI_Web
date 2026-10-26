"""Regression and adversarial tests for generic narration math-domain QA."""
import hashlib,json,os,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
from selenium_pipeline.automatic_math_semantic_qa import inspect_math_semantics,repair_prompt

def grammar(*slides):
    return "\n\n".join(f"**Slide {i} [30 sec]:\n{body}**" for i,body in enumerate(slides,1))

class GeneralMathDomainGuard(unittest.TestCase):
    def test_negative_tangent_and_sine_reference_triangle_defects(self):
        s=grammar(" ".join((
           "These algebraic substitutions correspond directly to right triangles with acute angle u.",
           "When x equals a tangent u, x and a represent the opposite and adjacent legs, making the hypotenuse the square root of a-squared plus x-squared.",
           "For sine, x is the opposite leg and a is the hypotenuse.",
           "For secant, the hypotenuse is x and the adjacent leg is a.")))
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

    def test_exact_constant_root_is_not_a_branch_sign_issue(self):
        constant=grammar(
            "Substituting four gives two over the square root of four, which simplifies to one.",
            "The square root of nine simplifies to three.",
            "The square root of four plus five equals three.")
        self.assertEqual(inspect_math_semantics(constant)["blocking_count"],0)
        conditional=grammar("The square root of x squared simplifies to x.")
        self.assertIn("unchecked_principal_root_sign",
                      [x["rule"] for x in inspect_math_semantics(conditional)["findings"]])

    def test_independent_original_sections_do_not_create_false_positive_stalls(self):
        root=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not root:
            self.skipTest("Original Thomas 8.5 and 8.6 exist only on Dell-115")
        chapter=Path(root).parent
        for subchapter in ("8.5","8.6"):
            candidate=chapter/subchapter
            if not (candidate/"script.txt").is_file():
                self.skipTest("Original independently generated subchapter absent")
            transcript=(candidate/"script.txt").read_text(encoding="utf8")
            checked=inspect_math_semantics(transcript)
            with self.subTest(subchapter=subchapter):
                self.assertEqual(checked["blocking_count"],0)
                self.assertFalse(checked["independent_source_math_ai_review_approved"])

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

    def test_production_runner_rejects_stale_semantic_receipts(self):
        from selenium_pipeline.runner import valid
        from selenium_pipeline.automatic_math_semantic_qa import inspect_math_semantics
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            (p/"source.pdf").write_bytes(b"Source-only fixture")
            source_hash=hashlib.sha256(b"Source-only fixture").hexdigest()
            body=grammar("This right triangle has a known acute angle.")
            (p/"script.txt").write_text(body,encoding="utf8")
            (p/"script_risk_report.json").write_text(
                json.dumps({"summary":{"blocking":0}}),encoding="utf8")
            (p/"script_risk_report.md").write_text("TTS risks checked",encoding="utf8")
            (p/"math_semantic_repair_prompt.json").write_text("{}",encoding="utf8")
            self.assertFalse(valid("script_qa",p))
            report=inspect_math_semantics(body,source_sha256=source_hash)
            (p/"math_semantic_report.json").write_text(json.dumps(report),encoding="utf8")
            self.assertTrue(valid("script_qa",p))
            (p/"script.txt").write_text(body+" Another new sentence.",encoding="utf8")
            self.assertFalse(valid("script_qa",p))
            (p/"script.txt").write_text(body,encoding="utf8")
            (p/"math_semantic_report.json").write_text(
                json.dumps({**report,"blocking_count":1}),encoding="utf8")
            self.assertFalse(valid("script_qa",p))

    def test_normal_gemini_regeneration_receives_scientific_feedback(self):
        from selenium_pipeline.vendor_template_v2 import gen_script_selenium_v15 as gen
        original=grammar(
            "For tangent u, our reference triangles always use acute angle u. "
            "When x equals a tangent u, x and a represent the opposite and adjacent legs.")
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"script.txt"
            p.write_text(original,encoding="utf8")
            with patch.object(gen,"SOURCE_PDF",Path(td)/"absent_source.pdf"):
                warnings=gen.find_math_domain_warnings(p)
            self.assertGreaterEqual(len(warnings),2)
            self.assertIn("signed_angle_not_always_acute"," ".join(warnings))
            revised=gen.retry_instruction("Existing Gemini instruction",warnings)
            self.assertIn("Regenerate the COMPLETE script",revised)
            self.assertIn("Mathematical domain QA",revised)
            self.assertEqual(p.read_text(encoding="utf8"),original)

    def test_cli_receipt_and_no_mutation_for_blocking_math(self):
        import subprocess,sys
        script=grammar("For tangent u, reference triangles always use acute angle u. "
                       "When x equals a tangent u, x and a represent the opposite and adjacent legs.")
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/"script.txt";src.write_text(script,encoding="utf8")
            report=root/"scientific.json";instructions=root/"repair.json"
            outcome=subprocess.run([sys.executable,"-m","selenium_pipeline.automatic_math_semantic_qa",
                       "--script",str(src),"--report",str(report),
                       "--repair-prompt",str(instructions),"--strict"],
                      capture_output=True,text=True)
            self.assertEqual(outcome.returncode,2,outcome.stderr)
            self.assertTrue(report.is_file())
            self.assertGreaterEqual(json.loads(report.read_text())["blocking_count"],2)
            self.assertFalse(json.loads(instructions.read_text())["model_web_dispatch_performed"])
            self.assertEqual(src.read_text(encoding="utf8"),script)

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
