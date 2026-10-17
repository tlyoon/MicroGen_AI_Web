"""Offline structural audio acceptance independent of SHA receipts or Gemini SDK."""
from __future__ import annotations

import io
import struct
import unittest
import wave

from selenium_pipeline.tts_pcm_contract import TTSPCMContractError, verify_pcm


def make_wav(*, channels=1, sample_width=2, sample_rate=24000,
             frames=24000, symbol=b"\x11\x12") -> bytes:
    buf=io.BytesIO()
    with wave.open(buf,"wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(sample_width)
        output.setframerate(sample_rate)
        output.writeframes(symbol[:sample_width].ljust(sample_width,b"\x11")
                           *frames*channels)
    return buf.getvalue()


class PCMContractTests(unittest.TestCase):
    def test_valid_mono_24k_pcm(self):
        proof=verify_pcm(make_wav())
        self.assertEqual(proof["sample_rate_hz"],24000)
        self.assertEqual(proof["channels"],1)
        self.assertEqual(proof["sample_width_bytes"],2)
        self.assertAlmostEqual(proof["duration_seconds"],1)

    def test_header_only_riff_is_not_audio(self):
        fake=b"RIFF"+b"0"*100
        with self.assertRaises(TTSPCMContractError):
            verify_pcm(fake)

    def test_trailing_bytes_are_rejected(self):
        with self.assertRaisesRegex(TTSPCMContractError,"byte length"):
            verify_pcm(make_wav()+b"trailing")

    def test_truncated_frames_are_rejected(self):
        with self.assertRaisesRegex(TTSPCMContractError,"byte length"):
            verify_pcm(make_wav()[:-80])

    def test_declared_truncated_pcm_not_accepted(self):
        data=bytearray(make_wav()[:-80])
        struct.pack_into("<I",data,4,len(data)-8)
        with self.assertRaises(TTSPCMContractError):
            verify_pcm(bytes(data))

    def test_wrong_sample_rate_rejected(self):
        with self.assertRaisesRegex(TTSPCMContractError,"24kHz"):
            verify_pcm(make_wav(sample_rate=16000))

    def test_stereo_rejected(self):
        with self.assertRaisesRegex(TTSPCMContractError,"mono PCM"):
            verify_pcm(make_wav(channels=2))

    def test_eight_bit_audio_rejected(self):
        with self.assertRaisesRegex(TTSPCMContractError,"16-bit"):
            verify_pcm(make_wav(sample_width=1))

    def test_too_short_rejected(self):
        with self.assertRaisesRegex(TTSPCMContractError,"duration"):
            verify_pcm(make_wav(frames=1200))

    def test_more_than_two_minutes_rejected(self):
        with self.assertRaisesRegex(TTSPCMContractError,"duration"):
            verify_pcm(make_wav(frames=120*24000+1))


if __name__=="__main__":
    unittest.main()
