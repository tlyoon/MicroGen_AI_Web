"""No-network regressions for explicit element-level Gemini TTS."""
from __future__ import annotations
import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.element_narration_gemini import main


def mock_wav():
    bio=io.BytesIO()
    with wave.open(bio,"wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(24000)
        stream.writeframes(b"\x01\x10"*24000)
    return bio.getvalue()


class ElementTTSCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.plan=self.root/"authored.json"
        self.out=self.root/"audio"
        self.plan.write_text(json.dumps({
           "schema_version":1,
           "status":"author_specified_unapproved_element_narration",
           "voice_id":"original_windows_review_only",
           "parts":[{"part_id":"part_01","slides":[{
                "elements":[
                    {"wav":"a.wav","spoken_text":"This is a spoken mathematical explanation."},
                    {"wav":"b.wav","spoken_text":"This is another spoken mathematical explanation."}
                ]}]}]
           }),encoding="utf8")
        self.args=["--authored-plan",str(self.plan),
                   "--output-folder",str(self.out),
                   "--model","gemini-3.8-flash-lite-tts",
                   "--voice","Kore"]

    def test_no_network_or_output_without_explicit_confirm(self):
        with self.assertRaises(SystemExit):
            main(self.args)
        self.assertFalse(self.out.exists())

    def test_mocked_live_voice_once_for_each_segment(self):
        with patch("selenium_pipeline.runner.load_microvid_env"), \
             patch("gemini_keys.get_gemini_api_keys",return_value=["test_key_not_real"]), \
             patch("selenium_pipeline.tts._gemini_say_with_watchdog",
                   return_value=mock_wav()) as call:
            self.assertEqual(main(self.args+["--confirm-live"]),0)
        self.assertEqual(call.call_count,2)
        meta=json.loads((self.out/"tts_synthesis_receipt.json").read_text())
        self.assertEqual(meta["voice"],"Kore")
        self.assertTrue(meta["same_declared_voice_all_segments"])
        self.assertFalse(meta["audible_word_fidelity_verified"])
        self.assertFalse(meta["source_academic_approval"])
        board=json.loads((self.out/"gemini_test_voice_plan.json").read_text())
        self.assertIn("gemini",board["voice_id"])
        self.assertTrue((self.out/"a.wav").is_file())
        self.assertTrue((self.out/"b.wav").is_file())

    def test_refuse_existing_output_without_resume(self):
        self.out.mkdir()
        (self.out/"keep.txt").write_text("protected")
        with self.assertRaises(SystemExit):
            main(self.args+["--confirm-live"])
        self.assertEqual((self.out/"keep.txt").read_text(),"protected")

    def test_mismatched_resume_is_rejected_without_network(self):
        self.out.mkdir()
        (self.out/"tts_job_identity.json").write_text("{}")
        with self.assertRaises(SystemExit):
            main(self.args+["--confirm-live","--resume"])

    def test_reject_duplicate_names_and_nonapproved_model_before_network(self):
        document=json.loads(self.plan.read_text())
        document["parts"][0]["slides"][0]["elements"][1]["wav"]="a.wav"
        self.plan.write_text(json.dumps(document))
        with self.assertRaises(SystemExit):
            main(self.args+["--confirm-live"])
        self.assertFalse(self.out.exists())
        with self.assertRaises(SystemExit):
            main(self.args+["--model","unsafe-model","--confirm-live"])


if __name__=="__main__":
    unittest.main()
