"""Finite historical parser ABI recovery: only immutable saved-source review."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.historical_pdf_parser_abi_recovery import (
    recover_readonly, HistoricalParserABIBlocked, MISMATCH)
from selenium_pipeline.rich_element_model_alignment import RichMappingError


class HistoricalPDFParserABIRecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.local = self.root / "Local"
        self.local.mkdir()
        self.compat = self.local / "miniconda3" / "python.exe"
        self.compat.parent.mkdir()
        self.compat.write_bytes(b"synthetic test executable no real process")
        self.lecture = self.root / "lecture"
        self.checkpoint = self.root / "checkpoint"
        self.fallback = self.root / "fallback"
        self.queue = self.root / "queue"
        for p in (self.lecture, self.checkpoint, self.fallback, self.queue):
            p.mkdir()
        self.hashes = {}
        for name in ("source.pdf", "slides.pdf", "script.txt"):
            raw = ("immutable " + name).encode()
            (self.lecture/name).write_bytes(raw)
            self.hashes[name] = hashlib.sha256(raw).hexdigest()
        (self.fallback/"SAFE_PROSE_FALLBACK_MANIFEST.json").write_text(
            json.dumps({
                "status":"DETERMINISTIC_SOURCE_GROUNDED_SAFE_PROSE_CANDIDATES_REVIEW_ONLY",
                "source_inputs_sha256": self.hashes,
                "model_provider_invoked":False,
                "paid_tts_authorized":False,
                "student_publication_authorized":False,
            }), encoding="utf8")
        self.report = {
            "schema_version":1,
            "status":"BLOCKED_UNRESOLVED_SOURCE_VISUAL_NARRATION",
            "source_inputs_sha256":self.hashes,
            "original_slide_count":14,
            "independently_previously_verified_text_links":7,
            "unresolved_source_element_mappings":67,
            "existing_per_element_recorded_audio_available":False,
            "actual_audio_text_fidelity_independently_verified":False,
            "original_source_assets_modified":False,
            "execution_allowed_without_new_paid_or_model_calls":False,
            "new_model_or_tts_calls":False,
            "student_publication_authorized":False,
        }
        self.calls=0

    def child(self, args, **kwargs):
        self.calls+=1
        self.assertEqual(args[0], str(self.compat))
        self.assertIn("--readonly-parser-abi-child",args)
        self.assertNotIn("--execute-prepared",args)
        self.assertEqual(kwargs["env"].get("MICROGEN_PARSER_ABI_CHILD"),"1")
        return subprocess.CompletedProcess(
            args, 0, json.dumps(self.report), "")

    def run_case(self, *, cause=None, child=None, expected=None,
                 model_responses=None):
        return recover_readonly(
            cause=cause if cause is not None else RichMappingError(MISMATCH),
            lecture=self.lecture,checkpoint=self.checkpoint,
            fallback_dir=self.fallback,queue_dir=self.queue,
            model_responses=model_responses,
            expected_publisher_sha256=(
                self.hashes["source.pdf"] if expected is None else expected),
            localappdata=self.local,
            run_child=self.child if child is None else child)

    def test_exact_source_recheck_is_idempotent_and_never_approves(self):
        before={n:(self.lecture/n).read_bytes() for n in self.hashes}
        a=self.run_case()
        b=self.run_case()
        self.assertEqual(a,b)
        self.assertEqual(self.calls,2) # Recheck, never trust receipt alone.
        self.assertEqual(a["historical_pdf_parser_abi_recovery"],
                         "VERIFIED_READONLY_NO_SEND")
        receipt=Path(a["historical_pdf_parser_abi_receipt"])
        self.assertTrue(receipt.is_file())
        self.assertEqual(json.loads(receipt.read_text())["model_or_tts_requests"],0)
        self.assertFalse(a["student_publication_authorized"])
        self.assertFalse(a["execution_allowed_without_new_paid_or_model_calls"])
        self.assertEqual(before,{n:(self.lecture/n).read_bytes() for n in self.hashes})

    def test_invalid_reason_does_not_trigger_fallback(self):
        with self.assertRaises(HistoricalParserABIBlocked):
            self.run_case(cause=RichMappingError("Other geometry problem"))
        self.assertEqual(self.calls,0)

    def test_wrong_source_sha_refuses_before_subprocess(self):
        with self.assertRaises(HistoricalParserABIBlocked):
            self.run_case(expected="f"*64)
        self.assertEqual(self.calls,0)

    def test_manifest_tamper_refused(self):
        f=self.fallback/"SAFE_PROSE_FALLBACK_MANIFEST.json"
        x=json.loads(f.read_text())
        x["source_inputs_sha256"]["source.pdf"]="0"*64
        f.write_text(json.dumps(x),encoding="utf8")
        with self.assertRaises(HistoricalParserABIBlocked):
            self.run_case()
        self.assertEqual(self.calls,0)

    def test_model_responses_may_not_use_parser_fallback(self):
        with self.assertRaises(HistoricalParserABIBlocked):
            self.run_case(model_responses=self.root/"model_responses")
        self.assertEqual(self.calls,0)

    def test_child_cannot_promote_paid_or_academic_permissions(self):
        for k,v in (("student_publication_authorized",True),
                    ("execution_allowed_without_new_paid_or_model_calls",True),
                    ("status","READY_FOR_STRICT_RECORDED_AUDIO_MULTIPART_RENDER")):
            with self.subTest(field=k):
                previous=self.report[k]
                self.report[k]=v
                with self.assertRaises(HistoricalParserABIBlocked):
                    self.run_case()
                self.report[k]=previous
        self.assertFalse((self.local/"MicroGen_AI_Web_Checkpoints").exists())

    def test_child_invalid_output_refused(self):
        def invalid(args,**kwargs):
            return subprocess.CompletedProcess(args,0,"not-json","")
        with self.assertRaises(HistoricalParserABIBlocked):
            self.run_case(child=invalid)

    def test_changed_original_during_child_refused(self):
        def mutate(args,**kwargs):
            (self.lecture/"script.txt").write_text("changed")
            return subprocess.CompletedProcess(args,0,json.dumps(self.report),"")
        with self.assertRaises(HistoricalParserABIBlocked):
            self.run_case(child=mutate)

    def test_registry_retirement_fails_closed(self):
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with self.assertRaises(HistoricalParserABIBlocked):
                self.run_case()
        self.assertEqual(self.calls,0)

    def test_missing_compatible_interpreter_blocks(self):
        self.compat.unlink()
        with self.assertRaises(HistoricalParserABIBlocked):
            self.run_case()
        self.assertEqual(self.calls,0)

    def test_direct_normal_wrapper_not_affected_for_other_errors(self):
        from selenium_pipeline import original_source_e2e_acceptance as src
        with patch.object(src,"_inspect_source_e2e_native",
                          side_effect=src.SourceReleaseBlocked("Wrong publisher")):
            with self.assertRaisesRegex(src.SourceReleaseBlocked,
                                        "Wrong publisher"):
                src.inspect_source_e2e(lecture=self.lecture)

    def test_direct_normal_wrapper_uses_registered_recovery_on_exact_error(self):
        from selenium_pipeline import original_source_e2e_acceptance as src
        with patch.object(src,"_inspect_source_e2e_native",
                          side_effect=RichMappingError(MISMATCH)), patch(
            "selenium_pipeline.historical_pdf_parser_abi_recovery.recover_readonly",
            return_value=self.report) as recovery:
            x=src.inspect_source_e2e(lecture=self.lecture,
                                    checkpoint=self.checkpoint,
                                    fallback_dir=self.fallback,
                                    queue_dir=self.queue)
        self.assertIs(x,self.report)
        self.assertEqual(recovery.call_count,1)

    def test_internal_cli_flag_rejected_without_recovery_child_marker(self):
        from selenium_pipeline import original_source_e2e_acceptance as src
        with patch.dict(os.environ,{"MICROGEN_PARSER_ABI_CHILD":""}):
            with self.assertRaises(src.SourceReleaseBlocked):
                src.main(["--lecture",str(self.lecture),
                          "--readonly-parser-abi-child"])


if __name__=="__main__":
    unittest.main()
