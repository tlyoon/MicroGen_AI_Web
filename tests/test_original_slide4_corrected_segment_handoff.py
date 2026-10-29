"""Actual original Thomas 8.4 endpoint/segment-source geometry verification."""
from __future__ import annotations
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.automatic_math_semantic_qa import inspect_math_semantics
from selenium_pipeline.original_slide4_math_correction_pilot import (
    prepare_corrected_original_slide4,exact_math_counterexamples,
)
from selenium_pipeline.original_slide4_corrected_segment_handoff import (
    stage_corrected_five_unit_handoff,
)

class EndpointCorrectedSegments(unittest.TestCase):
    def folder(self):
        p=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not p:
            self.skipTest("Genuine original textbook available only on Dell-115")
        return Path(p)

    def test_exact_boundary_degeneracy(self):
        report=exact_math_counterexamples()
        self.assertEqual(report["right_triangle_degenerate_boundary_cases_proven"],4)
        self.assertFalse(report["all_included_boundary_triangles_nondegenerate"])
        self.assertFalse(report["independent_academic_model_consensus_approved"])

    def test_generic_endpoint_lint(self):
        incorrect=("For x equals a tangent u, at u equals zero, "
                   "x equals zero and this forms a right triangle.")
        flagged=inspect_math_semantics(incorrect)["findings"]
        self.assertIn("zero_leg_triangle_degeneracy",
                      [x["rule"] for x in flagged])
        revised=("For x equals a tangent u, at u equals zero, the opposite "
                 "leg is zero and the diagram is degenerate.")
        self.assertNotIn("zero_leg_triangle_degeneracy",
                         [x["rule"] for x in inspect_math_semantics(revised)["findings"]])

    def test_revised_real_original_is_endpoint_explicit(self):
        p=self.folder()
        previous={name:hashlib.sha256((p/name).read_bytes()).hexdigest()
                  for name in ("source.pdf","slides.pdf","script.txt","slide4.wav")}
        bundle=prepare_corrected_original_slide4(folder=p)
        self.assertEqual(len(bundle["corrected_utterances"]),5)
        for i in range(4):
            self.assertIn("degenerate",bundle["corrected_utterances"][i]["revised_narration"].lower())
        self.assertNotEqual(bundle["corrected_utterances"][0]["revised_text_sha256"],
                            bundle["corrected_utterances"][0]["original_spoken_sha256"])
        self.assertEqual({name:hashlib.sha256((p/name).read_bytes()).hexdigest()
                          for name in previous},previous)
        self.assertFalse(bundle["corrected_mathematics_independently_ai_approved"])

    def test_real_five_new_source_bound_visuals_and_no_WAV(self):
        p=self.folder()
        old_hashes={name:hashlib.sha256((p/name).read_bytes()).hexdigest()
                    for name in ("source.pdf","slides.pdf","script.txt","slide4.wav")}
        with tempfile.TemporaryDirectory() as temp:
            dst=Path(temp)/"corrected_review_only"
            bundle=stage_corrected_five_unit_handoff(folder=p,output_dir=dst)
            self.assertEqual(bundle["segment_count"],5)
            self.assertEqual(bundle["mathematical_endpoint_sign_guard_findings"],0)
            self.assertEqual(bundle["real_new_TTS_WAV_count"],0)
            self.assertFalse(bundle["genuine_tts_provider_request_sent"])
            self.assertFalse(bundle["independent_two_pass_math_acceptance"])
            self.assertFalse(bundle["student_publication_authorized"])
            self.assertEqual(len(bundle["source_verified_tts_highlight_units"]),5)
            for row in bundle["source_verified_tts_highlight_units"]:
                png=dst/row["preview_png_relative_path"]
                self.assertTrue(png.is_file())
                self.assertEqual(hashlib.sha256(png.read_bytes()).hexdigest(),
                                 row["preview_png_sha256"])
                self.assertFalse((dst/row["tts_audio_relative_path_expected"]).exists())
                self.assertFalse(row["corrected_real_WAV_exists"])
                self.assertIsNone(row["actual_chunk_start_ms"])
                self.assertIsNone(row["actual_chunk_end_ms"])
            with self.assertRaises(Exception):
                stage_corrected_five_unit_handoff(folder=p,output_dir=dst)
        self.assertEqual({name:hashlib.sha256((p/name).read_bytes()).hexdigest()
                          for name in old_hashes},old_hashes)

if __name__=="__main__":
    unittest.main()
