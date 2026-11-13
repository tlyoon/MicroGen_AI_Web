"""Generic exact SymPy force/terminal-speed verification in normal script QA.

The source statement witness is distinct from theorem proof; negative fixtures
must not be promoted and unrelated subjects remain supported by the pipeline.
"""
import json
from pathlib import Path
import tempfile
import unittest

import pymupdf

from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.source_physics_drag_symbolic_qa import (
    inspect, prove_model_identities)
from selenium_pipeline.automatic_math_semantic_qa import main


class DragSymbolicProofTests(unittest.TestCase):
    def test_linear_quadratic_laws_and_numeric_examples_are_exact(self):
        result=prove_model_identities()
        self.assertEqual(len(result["equation_identity_checks"]),10)
        self.assertTrue(all(result["equation_identity_checks"].values()))
        numbers=result["numeric_predictions"]
        self.assertAlmostEqual(numbers[
            "oil_sphere_5_cm_per_s_and_980_cm_per_s_squared_tau_s"],
            5/980,places=12)
        self.assertAlmostEqual(numbers["oil_sphere_t90_s"],
                               0.01174788312752,places=10)
        self.assertAlmostEqual(numbers["one_tau_terminal_speed_fraction"],
                               .6321205588285577,places=12)
        self.assertAlmostEqual(numbers["baseball_145g_speed40_2_terminal43_drag_N"],
                               1.2419647593,places=7)
        self.assertFalse(result["theorem_proof_is_textbook_glyph_verification"])
        self.assertFalse(result["entire_original_narration_scientifically_approved"])

    def test_unrelated_math_source_is_not_mistaken_for_drag(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"source.pdf"
            with pymupdf.open() as pdf:
                pg=pdf.new_page()
                pg.insert_text((70,100),"Trigonometric substitution of an integral.")
                pdf.save(source)
            a=inspect(source=source)
            self.assertEqual(a["status"],"SOURCE_DRAG_PROOF_NOT_APPLICABLE")
            self.assertIsNone(a["proof"])
            self.assertFalse(a["G2_approved"])

    def test_real_original_serway_six_chapter_physics_witness_no_release(self):
        folder=(Path.home()/"AppData"/"Local"/"MicroGen_AI_Web_Checkpoints"
                /"20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"
                /"source_tree"/"6"/"6.4")
        if not (folder/"source.pdf").is_file():
            self.skipTest("Frozen Serway real source only on Dell-115")
        before={name:_sha(folder/name)
                for name in ("source.pdf","slides.pdf","script.txt")}
        proof=inspect(source=folder/"source.pdf",script=folder/"script.txt")
        self.assertTrue(proof["source_physically_has_relevant_model_headings"])
        self.assertTrue(proof["proof"]["symbolic_identity_proof_passed"])
        self.assertEqual(len(proof["proof"]["equation_identity_checks"]),10)
        self.assertFalse(proof["source_script_math_equations_all_semantically_verified"])
        self.assertFalse(proof["audio_or_TTS_authorized"])
        self.assertFalse(proof["G2_approved"])
        self.assertEqual(before,{name:_sha(folder/name) for name in before})

    def test_standard_script_qa_cli_reuses_symbolic_source_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            source=folder/"source.pdf"
            script=folder/"script.txt"
            with pymupdf.open() as pdf:
                pg=pdf.new_page()
                pg.insert_text((50,100),
                    "Model 1: resistive force Proportional to Object Velocity")
                pg.insert_text((50,120),
                    "A sphere released from rest approaches terminal speed.")
                pg.insert_text((50,175),
                    "Model 2: resistive force Proportional to Object Speed Squared")
                pg.insert_text((50,195),
                    "Drag grows with the square of the speed.")
                pdf.save(source)
            script.write_text(
                "**Slide 1 [1 sec]:\nThis is a source-grounded physics test.**\n",
                encoding="utf8")
            report=folder/"report.json"
            code=main(["--script",str(script),"--source-pdf",str(source),
                       "--report",str(report),"--strict"])
            self.assertEqual(code,0)
            results=json.loads(report.read_text("utf8"))
            obj=results["source_grounded_symbolic_drag_proof_v1"]
            self.assertTrue(obj["proof"]["symbolic_identity_proof_passed"])
            self.assertFalse(obj["G2_approved"])
            self.assertFalse(results["all_mathematics_verified"])


if __name__=="__main__":
    unittest.main()
