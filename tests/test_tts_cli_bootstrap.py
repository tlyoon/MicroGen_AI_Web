"""Authorized standalone TTS must load AppData credentials before synthesis."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline import tts


class StandaloneTTSBootstrapTests(unittest.TestCase):
    def test_gemini_cli_bootstraps_user_env_before_speech(self):
        order=[]
        def load():
            order.append("load")
        def run(*args):
            order.append(("synthesize",)+args)
        with patch("selenium_pipeline.runner.load_microvid_env",side_effect=load),\
             patch.object(tts,"synthesize_folder",side_effect=run):
            result=tts.main(["--folder",r"C:\fixture","--provider","gemini",
                             "--model","gemini-3.8-flash-lite-tts","--voice","Kore",
                             "--confirm-gemini-api-cost"])
        self.assertEqual(result,0)
        self.assertEqual(order[0],"load")
        self.assertEqual(order[1],("synthesize",Path(r"C:\fixture"),"gemini",
                                  "gemini-3.8-flash-lite-tts","Kore"))

    def test_chirp_cli_also_bootstraps_appdata(self):
        with patch("selenium_pipeline.runner.load_microvid_env") as load,\
             patch.object(tts,"synthesize_folder") as synth:
            self.assertEqual(tts.main(["--folder","example","--provider","chirp3",
                                       "--model","cloud-tts","--voice","Corey",
                                       "--confirm-google-cloud-tts-cost"]),0)
        load.assert_called_once_with()
        synth.assert_called_once()

    def test_loader_errors_block_synthesis(self):
        with patch("selenium_pipeline.runner.load_microvid_env",
                   side_effect=ValueError("duplicate key")):
            with patch.object(tts,"synthesize_folder") as synth:
                with self.assertRaisesRegex(ValueError,"duplicate key"):
                    tts.main(["--folder","example","--confirm-gemini-api-cost"])
                synth.assert_not_called()


if __name__=="__main__":
    unittest.main()
