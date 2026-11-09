"""Offline regression: forked PR369 Cloud catalogue and circuit remedy in normal TTS."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from selenium_pipeline.cloud_voice_preflight import (
    CloudVoicePreflightError, verify_catalogue_voice
)
from selenium_pipeline.tts import synthesize_folder


class CloudVoicePreflightTests(unittest.TestCase):
    def test_kore_from_provider_catalogue(self):
        client = Mock()
        client.list_voices.return_value = SimpleNamespace(voices=[
            SimpleNamespace(name="en-US-Chirp3-HD-Kore"),
            SimpleNamespace(name="en-US-Chirp3-HD-Aoede"),
        ])
        report = verify_catalogue_voice(client, "en-US-Chirp3-HD-Kore")
        self.assertTrue(report["catalogue_verified"])
        self.assertFalse(report["paid_synthesis_dispatched"])
        client.list_voices.assert_called_once_with(
            request={"language_code": "en-US"}, timeout=20
        )

    def test_corey_absent_is_not_relabelled(self):
        client = Mock()
        client.list_voices.return_value = SimpleNamespace(voices=[
            SimpleNamespace(name="en-US-Chirp3-HD-Kore"),
        ])
        with self.assertRaisesRegex(CloudVoicePreflightError, "absent"):
            verify_catalogue_voice(client, "en-US-Chirp3-HD-Corey")

    def test_missing_provider_catalogue_is_fail_closed(self):
        client = Mock()
        client.list_voices.side_effect = TimeoutError("unavailable")
        with self.assertRaisesRegex(CloudVoicePreflightError, "Cannot verify"):
            verify_catalogue_voice(client, "en-US-Chirp3-HD-Kore")

    def test_malformed_identity_never_calls_catalogue(self):
        client = Mock()
        for voice in ("Corey", "en-US-Chirp3-HD-", "en-US-Wavenet-Kore"):
            with self.subTest(voice=voice):
                with self.assertRaises(CloudVoicePreflightError):
                    verify_catalogue_voice(client, voice)
        client.list_voices.assert_not_called()

    def test_missing_voice_blocks_normal_synthesis_before_any_paid_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "script.txt").write_text(
                "**Slide 1 [3 sec]:\nA verified original equation.", encoding="utf8"
            )
            with patch("selenium_pipeline.tts._preflight_cloud_voice",
                       side_effect=CloudVoicePreflightError("catalogue missing")), \
                 patch("selenium_pipeline.tts._chirp_say_with_watchdog") as paid:
                with self.assertRaisesRegex(CloudVoicePreflightError, "missing"):
                    synthesize_folder(
                        folder, "chirp3", "chirp3-hd", "en-US-Chirp3-HD-Kore"
                    )
                paid.assert_not_called()
            self.assertFalse(list(folder.glob("slide*.wav")))
            self.assertFalse((folder / "tts_input_manifest.json").exists())
            self.assertFalse((folder / ".tts_candidate").exists())

    def test_one_cloud_permanent_failure_stops_later_billed_slides(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "script.txt").write_text(
                "**Slide 1 [3 sec]:\nFirst verified equation.\n\n"
                "**Slide 2 [3 sec]:\nSecond verified equation.",
                encoding="utf8"
            )
            with patch("selenium_pipeline.tts._preflight_cloud_voice",
                       return_value={"catalogue_verified": True}) as check, \
                 patch("selenium_pipeline.tts._chirp_say_with_watchdog",
                       side_effect=RuntimeError("400 InvalidArgument")) as paid, \
                 patch.dict("os.environ", {"MICROGEN_TTS_QUEUE_DELAY_SECONDS": "0"}):
                with self.assertRaisesRegex(RuntimeError, "permanent failure"):
                    synthesize_folder(
                        folder, "chirp3", "chirp3-hd", "en-US-Chirp3-HD-Kore"
                    )
                check.assert_called_once_with("en-US-Chirp3-HD-Kore")
                self.assertEqual(paid.call_count, 1)
            self.assertFalse(list(folder.glob("slide*.wav")))
            self.assertFalse((folder / "tts_input_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
