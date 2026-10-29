import sys
import tempfile
import unittest
import wave
from pathlib import Path
from selenium_pipeline.original_corrected_kore_candidate_batch import (
    OneShotKoreBatchError, run_remaining_corrected_utterances, _wave_receipt,
)


class SourceLockedKoreBatch(unittest.TestCase):
    def test_absent_explicit_authorization_fails_before_any_paid_request(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            output=root/"new_candidate_batch"
            with self.assertRaisesRegex(OneShotKoreBatchError,
                                        "explicit dispatch flag"):
                run_remaining_corrected_utterances(
                    original=root/"no_original",bundle=root/"no_source_packet",
                    previous_one_shot=root/"old_audio",
                    out=output,worker_python=Path(sys.executable),
                    dispatch_one_request_per_utterance=False)
            self.assertFalse(output.exists())

    def test_pcm_duration_is_measured_not_assumed_from_text(self):
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)/"new_Kore_utterance_004.wav"
            with wave.open(str(dest),"wb") as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000)
                wav.writeframes(b"\x01\x10"*48000)
            result=_wave_receipt(dest)
            self.assertEqual(result["duration_s"],2.0)
            self.assertEqual(result["rate_hz"],24000)
            self.assertEqual(result["frames"],48000)
            self.assertEqual(len(result["sha256"]),64)

    def test_invalid_or_missing_WAV_cannot_be_labeled_Kore(self):
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)/"new_Kore_utterance_004.wav"
            dest.write_bytes(b"RIFF"+b"\x00"*15000)
            with self.assertRaises((ValueError,OneShotKoreBatchError,
                                    EOFError,wave.Error)):
                _wave_receipt(dest)

if __name__=="__main__":
    unittest.main()
