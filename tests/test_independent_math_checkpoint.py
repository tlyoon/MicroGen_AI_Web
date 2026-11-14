"""End-to-end historical script_qa upgrade without report overwrite or paid TTS.

Real PDF source and actual accepted cached-stage receipts. A modern verifier
must not force a previously accepted old QA stage through regeneration.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pymupdf

from selenium_pipeline import runner
from selenium_pipeline.figure_source_identity import (
    FigureIdentityReviewRequired, _sha)
from selenium_pipeline.independent_math_checkpoint import (
    ensure, NAME, MANIFEST)
from selenium_pipeline.automatic_math_semantic_qa import (
    inspect_math_semantics,repair_prompt)
from selenium_pipeline.runner_stage_artifact_evidence import build_stage_evidence


def _source(parent: Path, *,actual_drag: bool=True) -> tuple[Path,Path]:
    parent.mkdir(parents=True,exist_ok=True)
    with pymupdf.open() as doc:
        p=doc.new_page()
        if actual_drag:
            p.insert_text((50,70),"Model 1: resistive force Proportional to Object Velocity")
            p.insert_text((50,100),"The sphere is released from rest and approaches terminal speed.")
            p.insert_text((50,200),"Model 2: resistive force Proportional to Object Speed Squared")
            p.insert_text((50,230),"The object air drag follows the square of the speed.")
        else:
            p.insert_text((50,100),"A lesson on trigonometric identities.")
        doc.save(parent/"source.pdf")
    script=parent/"script.txt"
    script.write_text(
        "**Slide 1 [15 sec]:\nThe falling object starts at rest and accelerates.**\n",
        encoding="utf8")
    return parent/"source.pdf",script


class IndependentSourceMathStageCheckpointTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp=Path(td.name)
        self.root=self.tmp/"proofs"
        self.root.mkdir()
        self.source,self.script=_source(self.tmp/"original")

    def test_write_once_then_reuse_with_old_source_bytes_unchanged(self):
        original={x.name:_sha(x) for x in (self.source,self.script)}
        first=ensure(source=self.source,script=self.script,
                     checkpoint_root=self.root)
        self.assertEqual(first["status"],"CREATED_SOURCE_SHA_LOCKED_MATH_PROOF")
        self.assertTrue(first["symbolic_proof_available"])
        self.assertEqual(first["new_model_or_tts_requests"],0)
        receipt=Path(first["checkpoint"])
        expected={name:_sha(receipt/name) for name in (NAME,MANIFEST)}
        second=ensure(source=self.source,script=self.script,
                      checkpoint_root=self.root)
        self.assertEqual(second["status"],"REUSED_IMMUTABLE_SOURCE_MATH_PROOF")
        self.assertEqual(first["proof_sha256"],second["proof_sha256"])
        self.assertEqual(expected,{name:_sha(receipt/name)
                                   for name in expected})
        self.assertEqual(original,{x.name:_sha(x)
                                   for x in (self.source,self.script)})
        self.assertFalse(second["G2_approved"])

    def test_corrupted_or_claimed_approved_receipt_never_regenerated(self):
        first=ensure(source=self.source,script=self.script,
                     checkpoint_root=self.root)
        file=Path(first["checkpoint"])/NAME
        payload=json.loads(file.read_text("utf8"))
        payload["G2_approved"]=True
        file.write_text(json.dumps(payload),encoding="utf8")
        corrupted=_sha(file)
        with self.assertRaises(FigureIdentityReviewRequired):
            ensure(source=self.source,script=self.script,
                   checkpoint_root=self.root)
        self.assertEqual(_sha(file),corrupted)

    def test_unsafe_in_source_checkpoint_root_rejected_before_mkdir(self):
        unsafe=self.source.parent/"forbidden_math_cache"
        self.assertFalse(unsafe.exists())
        with self.assertRaises(FigureIdentityReviewRequired):
            ensure(source=self.source,script=self.script,
                   checkpoint_root=unsafe)
        self.assertFalse(unsafe.exists())

    def test_script_input_change_creates_new_checkpoint_not_old_mutation(self):
        first=ensure(source=self.source,script=self.script,
                     checkpoint_root=self.root)
        source_original=_sha(self.source)
        old_manifest=_sha(Path(first["checkpoint"])/MANIFEST)
        self.script.write_text(
            "**Slide 1 [15 sec]:\nThe lecture now has different narration.**\n",
            encoding="utf8")
        next_run=ensure(source=self.source,script=self.script,
                        checkpoint_root=self.root)
        self.assertNotEqual(first["checkpoint"],next_run["checkpoint"])
        self.assertEqual(_sha(self.source),source_original)
        self.assertEqual(_sha(Path(first["checkpoint"])/MANIFEST),
                         old_manifest)

    def test_non_applicable_source_fails_open_for_other_subjects_not_G2(self):
        source,script=_source(self.tmp/"unrelated",actual_drag=False)
        result=ensure(source=source,script=script,checkpoint_root=self.root)
        self.assertEqual(result["status"],"CREATED_NOT_APPLICABLE_SOURCE_MATH_PROOF")
        self.assertFalse(result["symbolic_proof_available"])
        self.assertFalse(result["G2_approved"])

    def test_real_old_serway_script_qa_legacy_receipt_reused_without_repair(self):
        folder=(Path.home()/"AppData"/"Local"/"MicroGen_AI_Web_Checkpoints"
                /"20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"
                /"source_tree"/"6"/"6.4")
        if not (folder/"source.pdf").is_file():
            self.skipTest("Frozen Serway real source on Dell-115 only")
        files=("source.pdf","slides.pdf","script.txt",
               "math_semantic_report.json","math_semantic_repair_prompt.json",
               ".selenium_pipeline_state.json")
        before={f:_sha(folder/f) for f in files}
        old=json.loads((folder/"math_semantic_report.json").read_text("utf8"))
        self.assertNotIn("source_grounded_symbolic_drag_proof_v1",old)
        result=ensure(source=folder/"source.pdf",
                      script=folder/"script.txt",checkpoint_root=self.root)
        self.assertTrue(result["symbolic_proof_available"])
        again=ensure(source=folder/"source.pdf",
                     script=folder/"script.txt",checkpoint_root=self.root)
        self.assertEqual(again["status"],"REUSED_IMMUTABLE_SOURCE_MATH_PROOF")
        self.assertEqual(before,{f:_sha(folder/f) for f in files})

    def test_direct_video_handoff_executes_math_remedy_before_mapping_gate(self):
        from selenium_pipeline.full_pipeline_video_handoff import (
            complete_from_published)
        from selenium_pipeline.rich_element_mapping_checkpoint import (
            ElementMappingCheckpointBlocked)
        with pymupdf.open() as doc:
            p=doc.new_page()
            p.insert_text((50,100),"An original authored slide.")
            doc.save(self.source.parent/"slides.pdf")
        (self.source.parent/"slides.tex").write_text(
            r"\\begin{document}\\end{document}",encoding="utf8")
        with patch("selenium_pipeline.source_numbered_example_coverage.require_coverage"),\
             patch("selenium_pipeline.independent_math_checkpoint.ensure",
                   return_value={"status":"REUSED_IMMUTABLE_SOURCE_MATH_PROOF"}) as proof,\
             patch("selenium_pipeline.rich_element_mapping_checkpoint."
                   "require_automatic_mapping_or_checkpoint",
                   side_effect=ElementMappingCheckpointBlocked(
                       "Expected unfinished rich visual mapping")) as mapping:
            with self.assertRaisesRegex(
                    ElementMappingCheckpointBlocked,
                    "Expected unfinished rich visual mapping"):
                complete_from_published(source=self.source)
        proof.assert_called_once_with(source=self.source,
                                     script=self.script)
        mapping.assert_called_once()
        self.assertFalse((self.source.parent/"lecture_completion.json").exists())
        self.assertFalse((self.source.parent/"slides.mp4").exists())

    def test_real_runner_cached_script_qa_invokes_remedy_without_rerun(self):
        source_root=self.tmp/"publisher"
        work_root=self.tmp/"workspace"
        source,script=_source(source_root/"8"/"8.4",actual_drag=False)
        where=work_root/"8"/"8.4"
        where.mkdir(parents=True)
        (where/"source.pdf").write_bytes(source.read_bytes())
        (where/"script.txt").write_bytes(script.read_bytes())
        with pymupdf.open() as doc:
            p=doc.new_page()
            p.insert_text((60,100),"Original source analytic QA slide.")
            doc.save(where/"slides.pdf")
        (where/"slides.tex").write_text(r"\\begin{document}\\end{document}")
        for name in ("slides.pdf","slides.tex"):
            (source.parent/name).write_bytes((where/name).read_bytes())
        sha=runner.digest(source)
        old_report=inspect_math_semantics(script.read_text("utf8"),
                                          source_sha256=sha)
        (where/"math_semantic_report.json").write_text(json.dumps(old_report))
        (where/"math_semantic_repair_prompt.json").write_text(
            json.dumps(repair_prompt(old_report)))
        (where/"script_risk_report.json").write_text(
            json.dumps({"summary":{"blocking":0}}))
        (where/"script_risk_report.md").write_text("No local risks")
        for name in ("math_semantic_report.json","math_semantic_repair_prompt.json",
                     "script_risk_report.json","script_risk_report.md"):
            (source.parent/name).write_bytes((where/name).read_bytes())
        evidence=build_stage_evidence(where,"script_qa",sha)
        stage={"model":"script-risk-v1:math-domain-sign-graph-v2",
               "artifact_evidence":evidence}
        (where/".selenium_pipeline_state.json").write_text(json.dumps({
            "source_sha256":sha,"completed":{"script_qa":stage}}))
        prior={name:_sha(where/name) for name in (
            "source.pdf","script.txt","math_semantic_report.json",
            "math_semantic_repair_prompt.json","script_risk_report.json")}
        settings=runner.Settings(source_root=source_root,work_root=work_root,
            subchapter="8.4",from_stage="script_qa",through_stage="script_qa")
        with patch.dict(os.environ,{"LOCALAPPDATA":str(self.tmp)}),\
             patch("selenium_pipeline.inverse_trig_principal_domain_guard.enforce"),\
             patch("selenium_pipeline.figure_audit.enforce_graphics"),\
             patch("selenium_pipeline.runner.run_cmd",
                   side_effect=AssertionError("Must not rerun accepted QA")),\
             patch("selenium_pipeline.launch_gemini.launch",
                   side_effect=AssertionError("Must not launch browser")):
            runner._execute_unlocked(settings)
            runner._execute_unlocked(settings)
        restored=json.loads((where/".selenium_pipeline_state.json").read_text("utf8"))
        self.assertEqual(restored["completed"]["script_qa"]["artifact_evidence"],
                         evidence)
        self.assertEqual(prior,{name:_sha(where/name) for name in prior})
        copies=list((self.tmp/"MicroGen_AI_Web_Checkpoints"/
                     "_source_math_gate").glob("source_math_*"))
        self.assertEqual(len(copies),1)
        self.assertEqual(json.loads((copies[0]/NAME).read_text("utf8"))[
            "status"],"SOURCE_DRAG_PROOF_NOT_APPLICABLE")


if __name__=="__main__":
    unittest.main()
