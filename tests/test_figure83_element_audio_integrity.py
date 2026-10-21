import tempfile,unittest,hashlib,wave
from pathlib import Path
from selenium_pipeline.figure83_element_audio_integrity import inspect_element_wav_claims
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

def packet():
    return {"status":"ORIGINAL_FIGURE83_REVIEW_ONLY",
            "paid_tts_authorized":False,"student_publication_authorized":False,
            "review_utterances":[{"utterance_id":"u1"}]}
def clip(path,*,engine="gemini-flash-lite",voice="Kore",failures=0):
    audio=path.read_bytes()
    return {"utterance_id":"u1","wav_path":str(path),
            "sha256":hashlib.sha256(audio).hexdigest(),
            "voice_id":voice,"engine":engine,"primary_attempts_failed":failures,
            "duration_s":.1,"human_math_and_speech_approved":False}
class WaveIntegrityOnlyTests(unittest.TestCase):
    def test_empty_review_has_zero_authorized_tts(self):
        r=inspect_element_wav_claims(packet(),[])
        self.assertEqual(r["integrity_checked_clip_count"],0)
        self.assertFalse(r["spoken_element_timing_verified"])
        self.assertFalse(r["production_video_authorized"])
    def test_real_pcm_integrity_never_semantic_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"segment.wav"
            with wave.open(str(path),"wb") as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
                w.writeframes(bytes(1600*2))
            r=inspect_element_wav_claims(packet(),[clip(path)])
            self.assertEqual(r["integrity_checked_clip_count"],1)
            self.assertFalse(r["spoken_element_timing_verified"])
            self.assertFalse(r["mathematical_utterance_semantics_verified"])
            bad=clip(path);bad["sha256"]="0"*64
            with self.assertRaises(FigureIdentityReviewRequired):
                inspect_element_wav_claims(packet(),[bad])
            with self.assertRaises(FigureIdentityReviewRequired):
                inspect_element_wav_claims(packet(),[clip(path,engine="google-cloud-tts",failures=2)])
            with self.assertRaises(FigureIdentityReviewRequired):
                inspect_element_wav_claims(packet(),[clip(path),clip(path)])
            wrong=clip(path);wrong["duration_s"]=1.
            with self.assertRaises(FigureIdentityReviewRequired):
                inspect_element_wav_claims(packet(),[wrong])
