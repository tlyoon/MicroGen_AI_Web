"""No-network tests: every supported paid TTS CLI fails closed without its own cost consent."""
from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.tts_billing_guard import (
    TTSCostAuthorizationError, require_tts_cost_authorization,
)


class TTSPaidEntrypointTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)

    def test_provider_specific_consent_no_inferred_billing(self):
        for provider in ("gemini","chirp3"):
            with self.subTest(provider=provider):
                with self.assertRaises(TTSCostAuthorizationError):
                    require_tts_cost_authorization(provider)
        with self.assertRaises(TTSCostAuthorizationError):
            require_tts_cost_authorization("chirp3",gemini_approved=True)
        with self.assertRaises(TTSCostAuthorizationError):
            require_tts_cost_authorization("gemini",cloud_approved=True)
        require_tts_cost_authorization("gemini",gemini_approved=True)
        require_tts_cost_authorization("chirp3",cloud_approved=True)
        require_tts_cost_authorization("gemini",routine_gemini=True)
        require_tts_cost_authorization("chirp3",conditional_cloud_fallback=True)
        with self.assertRaises(TTSCostAuthorizationError):
            require_tts_cost_authorization("unknown",gemini_approved=True,
                                           cloud_approved=True)

    def test_routine_gemini_cli_permitted_but_direct_cloud_needs_cost_flag(self):
        from selenium_pipeline.tts import main
        with patch("selenium_pipeline.runner.load_microvid_env") as loader, \
             patch("selenium_pipeline.tts.synthesize_folder") as synth:
            self.assertEqual(main(["--folder",str(self.root),"--provider","gemini"]),0)
            with self.assertRaisesRegex(TTSCostAuthorizationError,"Cloud"):
                main(["--folder",str(self.root),"--provider","chirp3"])
            with self.assertRaises(TTSCostAuthorizationError):
                main(["--folder",str(self.root),"--provider","chirp3",
                      "--confirm-gemini-api-cost"])
            self.assertEqual(loader.call_count,1)
            self.assertEqual(synth.call_count,1)
            self.assertEqual(synth.call_args.args[1],"gemini")

    def test_direct_tts_cli_explicit_consent_is_provider_bound(self):
        from selenium_pipeline.tts import main
        with patch("selenium_pipeline.runner.load_microvid_env"), \
             patch("selenium_pipeline.tts.synthesize_folder") as synth:
            self.assertEqual(main(["--folder",str(self.root),"--provider","gemini",
                                   "--confirm-gemini-api-cost"]),0)
            self.assertEqual(main(["--folder",str(self.root),"--provider","chirp3",
                                   "--confirm-google-cloud-tts-cost"]),0)
            self.assertEqual(synth.call_count,2)
            self.assertEqual(synth.call_args_list[0].args[1],"gemini")
            self.assertEqual(synth.call_args_list[1].args[1],"chirp3")

    def test_worker_cannot_bypass_tts_cli_authorization(self):
        from selenium_pipeline.tts_worker import main
        args=["--output",str(self.root/"trial.wav"),"--model",
              "gemini-3.8-flash-lite-tts","--voice","Kore","--number","1"]
        with patch("selenium_pipeline.tts_worker._gemini_failover_request") as req, \
             patch("sys.stdin",io.StringIO("private lecture")):
            with self.assertRaises(TTSCostAuthorizationError):
                main(args)
            req.assert_not_called()
        self.assertFalse((self.root/"trial.wav").exists())

    def test_worker_existing_output_blocks_even_with_cost_approval(self):
        from selenium_pipeline.tts_worker import main
        protected=self.root/"trial.wav"
        protected.write_bytes(b"Original user WAV remains unchanged")
        args=["--output",str(protected),"--model",
              "gemini-3.8-flash-lite-tts","--voice","Kore","--number","1",
              "--provider","gemini","--confirm-gemini-api-cost"]
        with patch("selenium_pipeline.tts_worker._gemini_failover_request") as req, \
             patch("sys.stdin",io.StringIO("synthetic narration")):
            with self.assertRaisesRegex(FileExistsError,"existing TTS worker WAV"):
                main(args)
            req.assert_not_called()
        self.assertEqual(protected.read_bytes(),b"Original user WAV remains unchanged")

    def test_worker_creates_new_output_exclusively(self):
        from selenium_pipeline.tts_worker import main
        fresh=self.root/"new_test.wav"
        args=["--output",str(fresh),"--model",
              "gemini-3.8-flash-lite-tts","--voice","Kore","--number","1",
              "--provider","gemini","--confirm-gemini-api-cost"]
        with patch("selenium_pipeline.tts_worker._gemini_failover_request",
                   return_value=b"RIFF"+b"M"*64) as req, \
             patch("sys.stdin",io.StringIO("synthetic narration")):
            self.assertEqual(main(args),0)
            req.assert_called_once()
        self.assertEqual(fresh.read_bytes(),b"RIFF"+b"M"*64)

    def test_routine_gemini_qa_allowed_but_cloud_requires_approval(self):
        from selenium_pipeline.tts_qa_repair import main
        args=["--folder",str(self.root),"--model","gemini-3.8-flash",
              "--threshold","99","--provider","gemini",
              "--tts-model","gemini-3.8-flash-lite-tts","--voice","Kore"]
        with patch("selenium_pipeline.tts_qa_repair.load_microvid_env") as loader, \
             patch("selenium_pipeline.tts_qa_repair.repair") as rep:
            self.assertEqual(main(args),0)
            loader.assert_called_once()
            rep.assert_called_once()
        cloud=args.copy()
        cloud[cloud.index("gemini",cloud.index("--provider")+1)]="chirp3"
        with patch("selenium_pipeline.tts_qa_repair.load_microvid_env") as loader:
            with self.assertRaises(TTSCostAuthorizationError):
                main(cloud)
            loader.assert_not_called()

    def test_direct_cloud_runner_requires_separate_approval_before_mutation(self):
        from selenium_pipeline.runner import Settings,_execute_unlocked
        teaching=self.root/"tree"/"8"/"8.4"
        teaching.mkdir(parents=True)
        (teaching/"source.pdf").write_bytes(b"%PDF-1.4\nsynthetic")
        work=self.root/"workspace"
        setting=Settings(source_root=self.root/"tree",work_root=work,
                         subchapter="8.4",from_stage="tts",through_stage="tts",
                         tts_provider="chirp3")
        with patch("selenium_pipeline.runner.verify_source_tree") as verify, \
             patch("selenium_pipeline.runner.prepare") as prep:
            with self.assertRaises(TTSCostAuthorizationError):
                _execute_unlocked(setting)
            verify.assert_called_once()
            prep.assert_not_called()
        self.assertFalse(work.exists())
        self.assertFalse((teaching/"slide1.wav").exists())

    def test_runner_video_only_dry_run_remains_unbilled(self):
        from selenium_pipeline.runner import Settings,_execute_unlocked
        teaching=self.root/"tree"/"8"/"8.4"
        teaching.mkdir(parents=True)
        (teaching/"source.pdf").write_bytes(b"%PDF-1.4\nsynthetic")
        setting=Settings(source_root=self.root/"tree",work_root=self.root/"scratch",
                         subchapter="8.4",from_stage="tts",through_stage="video",
                         dry_run=True)
        self.assertEqual(_execute_unlocked(setting),setting.directory())
        self.assertFalse(setting.directory().exists())


if __name__=="__main__":
    unittest.main()
