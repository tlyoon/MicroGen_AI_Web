import unittest,tempfile,wave
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline.offline_corrected_audio_intake import inspect_corrected_five_pcm
class OfflineAudioProof(unittest.TestCase):
    def fake_doc(self):
        return {"source_verified_tts_highlight_units":[
            {"original_utterance_id":f"s004.utterance.{i:03}",
             "corrected_tts_text_sha256":str(i)*64,
             "tts_audio_relative_path_expected":f"new_Kore_utterance_{i:03}.wav"}
            for i in range(1,6)]}
    def test_pcm_candidates_not_voice_approved(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);old=root/"old";old.mkdir()
            (old/"slide4.wav").write_bytes(b"historical")
            wavs=root/"waves";wavs.mkdir()
            with wave.open(str(wavs/"new_Kore_utterance_001.wav"),"wb") as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000)
                w.writeframes(b"\x01\x00"*24000)
            with patch("selenium_pipeline.offline_corrected_audio_intake.verify_original_five_bundle",
                       return_value={"verified_image_count":5}),patch(
                     "selenium_pipeline.offline_corrected_audio_intake.strict_json",
                       return_value=self.fake_doc()):
                r=inspect_corrected_five_pcm(original=old,bundle=root,audio_dir=wavs)
            self.assertEqual(r["candidate_audio_count"],1)
            self.assertFalse(r["tts_replacement_eligible"])
            self.assertFalse(r["same_voice_approved"])
    def test_fake_header_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);old=root/"old";old.mkdir()
            (old/"slide4.wav").write_bytes(b"historical")
            wavs=root/"waves";wavs.mkdir()
            (wavs/"new_Kore_utterance_001.wav").write_bytes(b"x"*15000)
            with patch("selenium_pipeline.offline_corrected_audio_intake.verify_original_five_bundle",
                       return_value={"verified_image_count":5}),patch(
                     "selenium_pipeline.offline_corrected_audio_intake.strict_json",
                       return_value=self.fake_doc()):
                with self.assertRaises((ValueError,EOFError)):
                    inspect_corrected_five_pcm(original=old,bundle=root,audio_dir=wavs)
