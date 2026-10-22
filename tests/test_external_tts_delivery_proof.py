import unittest,tempfile,wave,hashlib
from pathlib import Path
from selenium_pipeline.external_tts_delivery_proof import verify_external_tts_delivery
from selenium_pipeline.incremental_chunk_tts_requests import DEFAULT_MODEL,DEFAULT_VOICE
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
class ProviderAudioReceiptTests(unittest.TestCase):
    def test_real_pcm_externally_staged_and_tamper_checked(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/"source";source.mkdir()
            wav=root/"pcm.wav"
            with wave.open(str(wav),"wb") as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000)
                f.writeframes(b"\x00\x01"*12000)
            job={"job_id":"j","spoken_text_sha256":"c"*64}
            receipt={"job_id":"j","spoken_text_sha256":"c"*64,
                     "model":DEFAULT_MODEL,"voice":DEFAULT_VOICE,
                     "provider_receipt_present":True,"execution_id":"exec-1234567",
                     "pcm_wav_path":str(wav),"wav_sha256":hashlib.sha256(wav.read_bytes()).hexdigest()}
            got=verify_external_tts_delivery(job=job,delivery=receipt,original_folder=source)
            self.assertAlmostEqual(got["measured_duration_s"],.5)
            self.assertFalse(got["audio_actually_speaks_requested_text_verified"])
            receipt["wav_sha256"]="0"*64
            with self.assertRaises(FigureIdentityReviewRequired):
                verify_external_tts_delivery(job=job,delivery=receipt,original_folder=source)
    def test_no_fake_delivery_without_provider_receipt(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(FigureIdentityReviewRequired):
                verify_external_tts_delivery(job={},delivery={},original_folder=Path(t))
