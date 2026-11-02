"""No eager Chrome startup on accepted source/slide stage cache.

True runner integration through temp native Windows source/work trees, but no
network, Google API, TTS cost, original textbook or production modifications.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline import runner

class LazyBrowserSourceStageTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root=Path(td.name)
        self.source_root=root/"publisher"
        self.work_root=root/"work"
        self.section=self.source_root/"8"/"8.4"
        self.section.mkdir(parents=True)
        import pymupdf
        with pymupdf.open() as doc:
            doc.new_page()
            doc.save(self.section/"source.pdf")
        self.workspace=self.work_root/"8"/"8.4"
        self.workspace.mkdir(parents=True)
        with pymupdf.open() as doc:
            doc.new_page()
            doc.save(self.workspace/"slides.pdf")
        (self.workspace/"slides.tex").write_text(r"\begin{document}\end{document}")
        (self.workspace/"Figure 8.3.png").write_bytes(b"original-figure-proof")
        (self.workspace/"source.pdf").write_bytes((self.section/"source.pdf").read_bytes())
        self.source_sha=runner.digest(self.section/"source.pdf")
        self.settings=runner.Settings(source_root=self.source_root,
             work_root=self.work_root,subchapter="8.4",
             from_stage="slides",through_stage="slides")

    def test_accepted_slides_starts_no_browser_no_network_no_paid_generation(self):
        from selenium_pipeline.runner_stage_artifact_evidence import build_stage_evidence
        evidence=build_stage_evidence(self.workspace,"slides",self.source_sha)
        state={"source_sha256":self.source_sha,
               "completed":{"slides":{"model":runner.DEFAULT_SLIDE_MODEL,
                                      "artifact_evidence":evidence}}}
        (self.workspace/".selenium_pipeline_state.json").write_text(
             json.dumps(state),encoding="utf8")
        with patch.dict("os.environ",{"MICROGEN_COMMUNICATION_MODE":"selenium"}):
            with patch("selenium_pipeline.runner.run_cmd",
                       side_effect=AssertionError("Must not run expensive subprocess")) as proc:
                with patch("selenium_pipeline.launch_gemini.launch",
                           side_effect=AssertionError("Must NOT open cached Chrome")) as launch:
                    with patch("selenium_pipeline.gemini_model.ensure_mode",
                               side_effect=AssertionError("Must NOT query Gemini")) as ensure:
                        with patch("selenium_pipeline.figure_audit.enforce_graphics",
                                   return_value=None):
                            result=runner._execute_unlocked(self.settings)
        self.assertEqual(result,self.workspace)
        proc.assert_not_called()
        launch.assert_not_called()
        ensure.assert_not_called()
        final=json.loads((self.workspace/".selenium_pipeline_state.json").read_text("utf8"))
        self.assertEqual(final["completed"]["slides"]["artifact_evidence"],evidence)
        self.assertIsNone(final["requested_models"]["ui_family_evidence"])

    @patch("selenium_pipeline.runner.pipeline_python_executable",
           return_value="CI_SYNTHETIC_PIPELINE_PYTHON_NO_DOCLING_REQUIRED")
    def test_fresh_slides_launch_browser_only_when_actual_stage_must_run(self,unused_pipeline_resolver):
        with patch.dict("os.environ",{"MICROGEN_COMMUNICATION_MODE":"selenium"}):
            with patch("selenium_pipeline.runner.run_cmd",
                       side_effect=RuntimeError("SYNTHETIC_CHEAP_STAGE_STOP")) as proc:
                with patch("selenium_pipeline.launch_gemini.launch",
                           return_value=(9432,object())) as launch:
                    with patch("selenium_pipeline.gemini_model.ensure_mode",
                               return_value="Flash") as ensure:
                        with patch("selenium_pipeline.gemini_model.browser_model_evidence",
                                   return_value={"family":"Flash","precise_id_verified":False}):
                            with self.assertRaisesRegex(RuntimeError,"SYNTHETIC_CHEAP_STAGE_STOP"):
                                runner._execute_unlocked(self.settings)
        launch.assert_called_once()
        ensure.assert_called_once()
        proc.assert_called_once()
        self.assertEqual(self.settings.chrome_port,9432)
        self.assertEqual(proc.call_args.args[3]["GEMINI_DEBUG_PORT"],"9432")
        persisted=json.loads((self.workspace/".selenium_pipeline_state.json").read_text("utf8"))
        self.assertEqual(persisted["requested_models"]["ui_family_evidence"]["family"],"Flash")

    def test_runner_keeps_lock_for_possible_browser_fallback(self):
        from inspect import getsource
        entry=getsource(runner.execute)
        self.assertIn("_may_use_browser(stage)",entry)
        self.assertIn("LocalInstanceLock",entry)

    def test_eager_chrome_startup_is_absent_before_cache_admission(self):
        from inspect import getsource
        src=getsource(runner._execute_unlocked)
        self.assertLess(src.index("decide_stage_reuse("),src.index("from .launch_gemini import launch"))
        self.assertIn("if not browser_initialized:",src)
        self.assertIn('env["GEMINI_DEBUG_PORT"]=str(actual_port)',src)

if __name__=="__main__":unittest.main()
