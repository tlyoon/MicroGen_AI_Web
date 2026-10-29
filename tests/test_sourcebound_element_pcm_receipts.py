import hashlib,tempfile,unittest,wave
from pathlib import Path
from selenium_pipeline.sourcebound_element_pcm_receipts import inspect_supplied_element_wavs
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired,_sha
from test_incremental_lecture_sync_queue import make_subchapter

class SourceBoundPCMChunkTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.folder=make_subchapter(self.root/"original","8.4")
        uid="s001.utterance.001";txt="A genuine original segment."
        self.jobs={"status":"REVIEWED_ELEMENT_CHUNK_REQUESTS_NOT_YET_DISPATCHED",
            "source_sha256":_sha(self.folder/"source.pdf"),
            "slides_sha256":_sha(self.folder/"slides.pdf"),
            "script_sha256":_sha(self.folder/"script.txt"),
            "paid_tts_execution_authorized":False,
            "student_publication_authorized":False,"model":"gemini-3.8-flash-lite-tts",
            "voice":"Kore","job_count":1,"chunk_jobs":[{
                "job_id":uid,"spoken_text_sha256":hashlib.sha256(txt.encode()).hexdigest(),
                "tts_generated":False,"audio_fidelity_to_script_verified":False}]}
        self.file=self.root/"external_element.wav"
        with wave.open(str(self.file),"wb") as a:
            a.setnchannels(1);a.setsampwidth(2);a.setframerate(16000)
            a.writeframes(b"\x01\x08"*9600)
        self.receipt={"job_id":uid,
                      "original_spoken_text_sha256":self.jobs["chunk_jobs"][0]["spoken_text_sha256"],
                      "claimed_model":"gemini-3.8-flash-lite-tts","claimed_voice":"Kore",
                      "provider_output_not_verified_acoustically":True,
                      "wav_path":str(self.file),"wav_sha256":_sha(self.file)}
    def test_real_pcm_frame_boundaries_inspected_not_acoustic_speech_approved(self):
        report=inspect_supplied_element_wavs(folder=self.folder,
                   jobs=self.jobs,receipts=[self.receipt])
        self.assertEqual(report["audio_clip_count"],1)
        self.assertAlmostEqual(report["measured_pcm_duration_s"],.6)
        self.assertFalse(report["actual_audio_text_fidelity_independently_verified"])
    def test_forged_voice_and_recycled_byte_identity_rejected(self):
        changed=dict(self.receipt);changed["claimed_voice"]="Corey"
        with self.assertRaises(FigureIdentityReviewRequired):
            inspect_supplied_element_wavs(folder=self.folder,
                                         jobs=self.jobs,receipts=[changed])
        with self.file.open("ab") as f:f.write(b"tamper")
        with self.assertRaises(FigureIdentityReviewRequired):
            inspect_supplied_element_wavs(folder=self.folder,
                                         jobs=self.jobs,receipts=[self.receipt])
