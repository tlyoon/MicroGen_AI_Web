import math,subprocess,tempfile,unittest,wave
from pathlib import Path
from selenium_pipeline.encoded_audio_fingerprint_audit import audit_muxed_audio_segment_fingerprints
from selenium_pipeline.highlight_video_preview import ffmpeg_path
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
class EncodedAudioPCM(unittest.TestCase):
    def make(self,root):
        import numpy as np
        source=[]
        for i,hz in enumerate((440,880),1):
            f=root/("tone"+str(i)+".wav")
            rate=24000;n=12000
            pcm=(15000*np.sin(2*np.pi*hz*np.arange(n)/rate)).astype("<i2")
            with wave.open(str(f),"wb") as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(pcm.tobytes())
            source.append(f)
        joined=root/"joined.wav"
        with wave.open(str(joined),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000)
            for f in source:
                with wave.open(str(f),"rb") as clip:w.writeframes(clip.readframes(clip.getnframes()))
        out=root/"preview.mp4"
        args=[ffmpeg_path(),"-hide_banner","-loglevel","error","-nostdin",
              "-f","lavfi","-i","color=c=black:s=128x128:r=20",
              "-i",str(joined),"-c:v","libx264","-preset","ultrafast",
              "-c:a","aac","-pix_fmt","yuv420p","-t","1","-y",str(out)]
        result=subprocess.run(args,capture_output=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors="replace"))
        return out,source
    def test_two_genuine_encoded_distinct_pcm_tones_have_correct_timing(self):
        with tempfile.TemporaryDirectory() as t:
            video,tones=self.make(Path(t))
            r=audit_muxed_audio_segment_fingerprints(mp4=video,wavs=tones)
            self.assertEqual(r["source_element_count"],2)
            self.assertFalse(r["audio_segments_are_real_spoken_words_verified"])
    def test_encoded_audio_segment_order_swapped_is_detected(self):
        with tempfile.TemporaryDirectory() as t:
            video,tones=self.make(Path(t))
            with self.assertRaises(FigureIdentityReviewRequired):
                audit_muxed_audio_segment_fingerprints(mp4=video,wavs=tones[::-1])
