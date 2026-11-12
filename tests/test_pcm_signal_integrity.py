"""Gross acoustic damage must be rejected by the real PCM review path.

These are objective amplitude/PCM tests, not word recognition, independent
listening, voice matching, or mathematically synchronized narration.
"""
from __future__ import annotations

from array import array
import io
import math
import tempfile
import unittest
import wave
from pathlib import Path

from selenium_pipeline.pcm_signal_integrity import (
    PCMIntegrityBlocked, inspect_pcm_file, inspect_pcm_signal)
from selenium_pipeline.tts_pcm_contract import TTSPCMContractError


RATE = 24000


def wav(samples: list[int], *, rate: int = RATE) -> bytes:
    with io.BytesIO() as memory:
        with wave.open(memory, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(rate)
            f.writeframes(array("h", samples).tobytes())
        return memory.getvalue()


def tone(seconds: float, *, amplitude: float = .2, dc: float = 0) -> list[int]:
    return [int(32767 * (amplitude *
            math.sin(2 * math.pi * 440 * i / RATE) + dc))
            for i in range(round(seconds * RATE))]


class SignalIntegrityRegressionTests(unittest.TestCase):
    def test_good_voice_like_pcm_is_objectively_healthy_but_not_approved(self):
        payload=wav(tone(1.5) + [0] * (RATE // 4) + tone(1.5))
        proof=inspect_pcm_signal(payload,label="example.wav")
        self.assertTrue(proof["objective_pcm_signal_integrity_passed"])
        self.assertEqual(proof["near_rail_sample_fraction"],0)
        self.assertAlmostEqual(proof["duration_s"],3.25)
        self.assertFalse(proof["pronunciation_and_words_verified"])
        self.assertFalse(proof["single_voice_identity_verified"])
        self.assertFalse(proof["acoustic_listening_qa_verified"])
        self.assertFalse(proof["narration_to_element_sync_verified"])
        self.assertFalse(proof["student_publication_authorized"])

    def test_silent_but_structurally_valid_wav_is_rejected(self):
        with self.assertRaisesRegex(PCMIntegrityBlocked,"silent"):
            inspect_pcm_signal(wav([0]*RATE))

    def test_nearly_inaudible_output_is_rejected(self):
        with self.assertRaisesRegex(PCMIntegrityBlocked,"inaudible|silent"):
            inspect_pcm_signal(wav(tone(2,amplitude=.001)))

    def test_long_mid_stream_dropout_is_rejected(self):
        damaged=wav(tone(2)+[0]*(RATE*7)+tone(2))
        with self.assertRaisesRegex(PCMIntegrityBlocked,"dropout"):
            inspect_pcm_signal(damaged)

    def test_valid_short_pause_does_not_trigger_dropout(self):
        accepted=inspect_pcm_signal(
            wav(tone(2)+[0]*(RATE*2)+tone(2)))
        self.assertGreaterEqual(accepted["max_interior_quiet_seconds"],1.9)
        self.assertTrue(accepted["objective_pcm_signal_integrity_passed"])

    def test_long_leading_or_trailing_silence_rejected(self):
        for samples in ([0] * (RATE * 7) + tone(3),
                        tone(3) + [0] * (RATE * 7)):
            with self.subTest(kind="lead" if samples[0] == 0 else "tail"):
                with self.assertRaisesRegex(PCMIntegrityBlocked,
                                            "leading or trailing"):
                    inspect_pcm_signal(wav(samples))

    def test_extreme_hard_clipping_is_rejected(self):
        saturated=wav([32767]*RATE)
        with self.assertRaisesRegex(PCMIntegrityBlocked,"clipping|DC"):
            inspect_pcm_signal(saturated)

    def test_big_dc_offset_without_clipping_is_rejected(self):
        with self.assertRaisesRegex(PCMIntegrityBlocked,"DC offset"):
            inspect_pcm_signal(wav(tone(2,amplitude=.2,dc=.18)))

    def test_bad_container_rejected_by_existing_pcm_gate(self):
        with self.assertRaises(TTSPCMContractError):
            inspect_pcm_signal(b"RIFF"+b"X"*80)

    def test_original_file_bytes_never_modified(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"original.wav"
            original=wav(tone(2))
            path.write_bytes(original)
            proof=inspect_pcm_file(path)
            self.assertEqual(path.read_bytes(),original)
            self.assertTrue(proof["objective_pcm_signal_integrity_passed"])
            with self.assertRaises(PCMIntegrityBlocked):
                inspect_pcm_file(Path(t)/"missing.wav")


if __name__ == "__main__":
    unittest.main()
