import unittest,tempfile,wave
from pathlib import Path
from selenium_pipeline.offline_real_pcm_envelope import inspect_pcm_wav_envelope
class OfflinePCM(unittest.TestCase):
 def make(self,root,name="clip.wav",channels=1,rate=24000,frames=24000):
    p=Path(root)/name
    with wave.open(str(p),"wb") as w:
        w.setnchannels(channels);w.setsampwidth(2);w.setframerate(rate)
        w.writeframes(b"\x01\x02"*frames*channels)
    return p
 def test_two_distinct_real_pcm_headers_and_timing(self):
    with tempfile.TemporaryDirectory() as d:
        a=self.make(d);b=self.make(d,"second.wav")
        out=inspect_pcm_wav_envelope([a,b])
        self.assertEqual((out["pcm_count"],out["total_seconds"]),(2,2.0))
        self.assertFalse(out["single_voice_acoustically_verified"])
 def test_reused_wav_cannot_impersonate_new_speech(self):
    with tempfile.TemporaryDirectory() as d:
        a=self.make(d)
        with self.assertRaises(ValueError):inspect_pcm_wav_envelope([a,a])
 def test_bad_rate_and_excess_length_fail_closed(self):
    with tempfile.TemporaryDirectory() as d:
        a=self.make(d,rate=22050)
        with self.assertRaises(ValueError):inspect_pcm_wav_envelope([a])
        a=self.make(d,frames=24000)
        with self.assertRaises(ValueError):inspect_pcm_wav_envelope([a],max_program_seconds=1)
