"""On-flight conditional drag theorem v2; no old academic/Gemini replay.

Tests actual source physics independently of source/voice/pixel semantics.
Runs via the normal immutable math sidecar used by cached script QA/video.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import pymupdf

from selenium_pipeline.figure_source_identity import _sha, FigureIdentityReviewRequired
from selenium_pipeline.source_physics_drag_symbolic_qa import (
    inspect, prove_conditional_drag_challenges_v2)
from selenium_pipeline.independent_math_checkpoint import (
    ensure, NAME, MANIFEST, REVISION, _pack)
from selenium_pipeline.automatic_math_semantic_qa import main as script_qa


class DragConditionalSourceEvidenceV2(TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.folder=self.root/"lecture"
        self.folder.mkdir()
        with pymupdf.open() as pdf:
            page=pdf.new_page(width=600,height=500)
            page.insert_text((45,70),
                "Model 1: Resistive Force Proportional to Object Velocity")
            page.insert_text((45,105),
                "A sphere released from rest approaches its terminal speed.")
            page.insert_text((45,143),
                "The time constant depends on its mass and drag coefficient.")
            page.insert_text((45,210),
                "Model 2: Resistive Force Proportional to Object Speed Squared")
            page.insert_text((45,250),
                "The air drag grows with the square of the speed.")
            page.insert_text((45,290),
                "A skysurfer can open his parachute at terminal speed.")
            pdf.save(self.folder/"source.pdf")
        (self.folder/"script.txt").write_text(
            "**Slide 1 [20 sec]:\nCompare terminal speeds and time constants.\n"
            "**Slide 2 [20 sec]:\nDiscuss the parachute after terminal speed.**",
            encoding="utf8")
        self.source=self.folder/"source.pdf"
        self.script=self.folder/"script.txt"
        self.cache=self.root/"external_immutable_proofs"
        self.cache.mkdir()

    def test_theorem_independently_proves_conditional_mass_and_force_signs(self):
        proof=prove_conditional_drag_challenges_v2()
        self.assertEqual(proof["schema_version"],2)
        self.assertEqual(len(proof["checks"]),13)
        self.assertTrue(all(proof["checks"].values()))
        self.assertIn("same_b_linear_terminal_speed_ratio_equals_mass_ratio",
                      proof["checks"])
        self.assertIn("post_opening_net_force_upward_minus_qmg",
                      proof["checks"])
        self.assertIn("above_new_terminal_acceleration_is_upward",
                      proof["checks"])
        self.assertTrue(proof["mathematical_conditional_results_proven"])
        for deny in ("printed_source_equations_independently_glyph_verified",
                     "original_narration_utterance_semantics_approved",
                     "word_level_audio_correspondence_verified",
                     "student_publication_authorized","G2_approved"):
            self.assertIs(proof[deny],False)
        self.assertIn("SAME drag coefficient b"," ".join(proof["conditions"]))

    def test_actual_source_qualifies_but_math_does_not_mean_approved_narration(self):
        before={x:_sha(self.folder/x)
                for x in ("source.pdf","script.txt")}
        result=inspect(source=self.source,script=self.script)
        self.assertTrue(result["source_physically_has_relevant_model_headings"])
        self.assertTrue(result["printed_time_constant_and_parachute_topics_cooccur"])
        self.assertEqual(
            len(result["conditional_physics_challenges_v2"]["checks"]),13)
        self.assertFalse(result["conditional_math_is_independent_narration_review"])
        self.assertFalse(result["G2_approved"])
        self.assertEqual(before,{x:_sha(self.folder/x)for x in before})

    def test_onflight_cached_stage_v2_immutable_and_preserves_legacy_v1(self):
        # Simulate an old immutable v1 checkpoint *at its own SHA scope*.
        source_hash,script_hash=_sha(self.source),_sha(self.script)
        old_fingerprint=hashlib.sha256(_pack({
            "engine_revision":1,
            "source_sha256":source_hash,
            "script_sha256":script_hash})).hexdigest()[:28]
        old=self.cache/("source_math_"+old_fingerprint)
        old.mkdir()
        old_file=old/"source_math_symbolic_proof_v1.json"
        old_file.write_bytes(b'{"status":"HISTORICAL_V1_UNTOUCHED"}\n')
        old_receipt=old/"receipt.json"
        old_receipt.write_text("old immutable engine receipt",encoding="utf8")
        old_hashes=(_sha(old_file),_sha(old_receipt))
        with (patch("selenium_pipeline.series_gemini._browser_request",
                    side_effect=AssertionError("Never resend old Gemini")),
              patch("selenium_pipeline.tts._gemini_say_with_watchdog",
                    side_effect=AssertionError("No synthesis"))):
            first=ensure(source=self.source,script=self.script,
                         checkpoint_root=self.cache)
            again=ensure(source=self.source,script=self.script,
                         checkpoint_root=self.cache)
        self.assertEqual(first["status"],"CREATED_SOURCE_SHA_LOCKED_MATH_PROOF")
        self.assertEqual(again["status"],"REUSED_IMMUTABLE_SOURCE_MATH_PROOF")
        self.assertEqual(first["engine_revision"],REVISION)
        self.assertEqual(REVISION,2)
        self.assertNotEqual(Path(first["checkpoint"]),old)
        self.assertEqual(first["proof_sha256"],again["proof_sha256"])
        self.assertTrue(again["conditional_drag_challenge_proof_available"])
        self.assertEqual(again["conditional_drag_challenge_identities_proven"],13)
        report=json.loads((Path(first["checkpoint"])/NAME).read_text("utf8"))
        self.assertFalse(report["G2_approved"])
        self.assertFalse(report["audio_or_TTS_authorized"])
        self.assertEqual((_sha(old_file),_sha(old_receipt)),old_hashes)

    def test_cached_proof_cannot_promote_forged_independent_approval(self):
        result=ensure(source=self.source,script=self.script,
                      checkpoint_root=self.cache)
        target=Path(result["checkpoint"])/NAME
        payload=json.loads(target.read_text("utf8"))
        payload["conditional_physics_challenges_v2"]["G2_approved"]=True
        target.write_text(json.dumps(payload),encoding="utf8")
        changed=_sha(target)
        with self.assertRaises(FigureIdentityReviewRequired):
            ensure(source=self.source,script=self.script,
                   checkpoint_root=self.cache)
        self.assertEqual(_sha(target),changed)

    def test_normal_pre_tts_script_semantic_qa_includes_conditional_proof(self):
        report_path=self.root/"independent_math_v2.json"
        code=script_qa(["--script",str(self.script),
                        "--source-pdf",str(self.source),
                        "--report",str(report_path),"--strict"])
        self.assertEqual(code,0)
        doc=json.loads(report_path.read_text("utf8"))
        result=doc["source_grounded_symbolic_drag_proof_v1"]
        self.assertEqual(len(result["conditional_physics_challenges_v2"]["checks"]),13)
        self.assertFalse(result["G2_approved"])
        self.assertFalse(doc["all_mathematics_verified"])
        self.assertFalse(doc["automatic_tts_authorized"])

    def test_unrelated_subject_does_not_receive_drag_theorems(self):
        with pymupdf.open() as pdf:
            page=pdf.new_page()
            page.insert_text((50,100),"An integral uses inverse tangent.")
            pdf.save(self.root/"unrelated.pdf")
        result=inspect(source=self.root/"unrelated.pdf",script=self.script)
        self.assertIsNone(result["proof"])
        self.assertIsNone(result["conditional_physics_challenges_v2"])
        self.assertFalse(result["G2_approved"])

    def test_real_serway_6_4_existing_claims_remain_unchanged(self):
        root=Path.home()/"AppData"/"Local"/"MicroGen_AI_Web_Checkpoints"
        source=(root/
            "20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"/
            "source_tree"/"6"/"6.4")
        if not (source/"source.pdf").is_file():
            self.skipTest("Real source only on authorized Dell-115")
        original={x:_sha(source/x)for x in
                  ("source.pdf","slides.pdf","script.txt")}
        with (patch("selenium_pipeline.series_gemini._browser_request",
                    side_effect=AssertionError("No source review replay")),
              patch("selenium_pipeline.tts._gemini_say_with_watchdog",
                    side_effect=AssertionError("No paid audio"))):
            report=ensure(source=source/"source.pdf",
                          script=source/"script.txt",
                          checkpoint_root=self.cache)
        self.assertEqual(report["engine_revision"],2)
        self.assertEqual(report["conditional_drag_challenge_identities_proven"],13)
        self.assertEqual(report["new_model_or_tts_requests"],0)
        self.assertFalse(report["G2_approved"])
        self.assertEqual(original,{x:_sha(source/x)for x in original})
