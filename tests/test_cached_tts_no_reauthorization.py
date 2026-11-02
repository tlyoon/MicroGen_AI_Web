"""Accepted source-WAV cache must not require new paid TTS authorizations."""
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline import runner
from selenium_pipeline.runner_stage_artifact_evidence import build_stage_evidence
from selenium_pipeline.tts_billing_guard import TTSCostAuthorizationError

class CachedAudioNoRebilling(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root=Path(td.name)
        self.published=root/"pub"/"8"/"8.4"
        self.work_root=root/"work"
        self.workspace=self.work_root/"8"/"8.4"
        self.workspace.mkdir(parents=True)
        self.published.mkdir(parents=True)
        import pymupdf
        with pymupdf.open() as doc:
            doc.new_page()
            doc.save(self.published/"source.pdf")
        (self.workspace/"source.pdf").write_bytes((self.published/"source.pdf").read_bytes())
        with pymupdf.open() as doc:
            doc.new_page()
            doc.save(self.workspace/"slides.pdf")
        (self.workspace/"slides.tex").write_text(r"\begin{document}\end{document}")
        (self.workspace/"script.txt").write_text(
            "**Slide 1 [5 seconds]: A graph with an inverse function, explained clearly.")
        (self.workspace/"slide1.wav").write_bytes(b"RIFF"+b"physical-pcm"*60)
        self.signature=runner.digest(self.published/"source.pdf")
        self.setting=runner.Settings(
            source_root=root/"pub",work_root=self.work_root,
            subchapter="8.4",tts_provider="chirp3",
            confirm_google_cloud_tts_cost=False,
            from_stage="tts",through_stage="tts")
        self.model=f"chirp3:{self.setting.tts_model}:{self.setting.tts_voice}"

    def _no_external_call(self):
        stack=ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch(
            "selenium_pipeline.inverse_trig_principal_domain_guard.enforce",return_value=None))
        stack.enter_context(patch(
            "selenium_pipeline.figure_audit.enforce_graphics",return_value=None))
        stack.enter_context(patch(
            "selenium_pipeline.source_numbered_example_coverage.require_coverage",
            return_value=None))
        return stack

    def test_exact_cached_cloud_WAV_reuses_without_billing_authorization(self):
        self._no_external_call()
        prev={
            "source_sha256":self.signature,
            "completed":{"tts":{"model":self.model,
                "artifact_evidence":build_stage_evidence(
                    self.workspace,"tts",self.signature)}}}
        (self.workspace/".selenium_pipeline_state.json").write_text(
            json.dumps(prev),encoding="utf8")
        with patch("selenium_pipeline.tts_billing_guard.require_tts_cost_authorization",
                   side_effect=AssertionError("Cached physical audio must not rebill")) as billing:
            with patch("selenium_pipeline.runner.run_cmd",
                       side_effect=AssertionError("Must not generate same WAV twice")) as command:
                result=runner._execute_unlocked(self.setting)
        self.assertEqual(result,self.workspace)
        billing.assert_not_called()
        command.assert_not_called()
        self.assertEqual((self.published/"slide1.wav").read_bytes(),
                         (self.workspace/"slide1.wav").read_bytes())

    def test_uncached_direct_cloud_still_rejected_before_generation(self):
        self._no_external_call()
        with patch("selenium_pipeline.runner.run_cmd",
                   side_effect=AssertionError("Unapproved paid audio invoked")) as proc:
            with self.assertRaises(TTSCostAuthorizationError):
                runner._execute_unlocked(self.setting)
        proc.assert_not_called()
        self.assertFalse((self.workspace/".history").exists())

    def test_damaged_cached_audio_does_not_trigger_paid_retry(self):
        self._no_external_call()
        prev={"source_sha256":self.signature,
              "completed":{"tts":{"model":self.model,
              "artifact_evidence":build_stage_evidence(
                  self.workspace,"tts",self.signature)}}}
        (self.workspace/".selenium_pipeline_state.json").write_text(
            json.dumps(prev),encoding="utf8")
        (self.workspace/"slide1.wav").write_bytes(b"RIFF"+b"new-unauthorized"*10)
        with patch("selenium_pipeline.tts_billing_guard.require_tts_cost_authorization",
                   side_effect=AssertionError("No cost after tampered old WAV")) as billing:
            with self.assertRaisesRegex(RuntimeError,"evidence changed"):
                runner._execute_unlocked(self.setting)
        billing.assert_not_called()

    def test_cost_guard_stays_before_invalidating_uncached_provider(self):
        from inspect import getsource
        src=getsource(runner._execute_unlocked)
        pos=src.index('if stage in {"tts","tts_qa"}:')
        self.assertGreater(pos,src.index("decide_stage_reuse("))
        self.assertLess(pos,src.index('state["completed"].pop(stage, None)',pos))
if __name__=="__main__":
    unittest.main()
