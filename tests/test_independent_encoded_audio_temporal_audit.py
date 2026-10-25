import hashlib,json,math,random,struct,subprocess,tempfile,unittest,wave
from pathlib import Path
from selenium_pipeline.highlight_video_preview import ffmpeg_path
from selenium_pipeline.independent_encoded_audio_temporal_audit import (
    audit_encoded_original_pcm,AudioTemporalAuditError)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class ActualEncodedAudioQA(unittest.TestCase):
 def setUp(self):
    tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
    self.base=Path(tmp.name)
    self.src=self.base/"original";self.src.mkdir()
    self.review=self.base/"review";self.review.mkdir()
    for name in ("source.pdf","slides.pdf","script.txt"):
        (self.src/name).write_text("unaltered test original "+name)
    self.audio=self.review/"narration.wav"
    rate=24000;n=rate*3
    rnd=random.Random(14)
    samples=[]
    for i in range(n):
        t=i/rate
        voice=(.62*math.sin(2*math.pi*(130*t+35*t*t))+
               .3*math.sin(2*math.pi*(480*t+25*t*t))+
               .04*(2*rnd.random()-1))
        envelope=.75+.22*math.sin(2*math.pi*.7*t)
        samples.append(round(10000*voice*envelope))
    self.sample_bytes=struct.pack("<"+str(len(samples))+"h",*samples)
    self.writewav(self.audio,self.sample_bytes)
    self.encode(self.audio,self.review/"element_highlight_review.mp4")
    self.rebind()

 def writewav(self,path,data):
    with wave.open(str(path),"wb") as audio:
        audio.setnchannels(1);audio.setsampwidth(2)
        audio.setframerate(24000);audio.writeframes(data)

 def encode(self,audio,output):
    p=subprocess.run([ffmpeg_path(),"-nostdin","-v","error",
        "-f","lavfi","-i","color=c=black:s=160x120:r=25",
        "-i",str(audio),"-shortest","-c:v","mpeg4","-q:v","5",
        "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k",
        "-y",str(output)],capture_output=True,timeout=40)
    if p.returncode:
        self.fail("FFmpeg did not create synthetic test MP4: "+
                  p.stderr.decode(errors="replace")[-400:])

 def rebind(self):
    manifest={"status":"REAL_ORIGINAL_SINGLE_UTTERANCE_ELEMENT_HIGHLIGHT_REVIEW_ONLY",
       "student_publication_authorized":False,
       "independent_second_ai_review_pass_complete":False,
       "original_WAV_is_new_element_TTS":False,
       "original_audio_sha256":sha(self.audio),
       "encoded_mp4_sha256":sha(self.review/"element_highlight_review.mp4"),
       "original_source_asset_sha256":{
            name:sha(self.src/name) for name in ("source.pdf","slides.pdf","script.txt")}}
    (self.review/"source_aware_pilot_receipt.json").write_text(json.dumps(manifest))

 def audit(self):
    return audit_encoded_original_pcm(original_folder=self.src,
             review_folder=self.review)

 def test_real_encoded_pcm_matches_all_three_temporal_windows(self):
    report=self.audit()
    self.assertGreater(min(report["three_independent_window_correlations"]),.78)
    self.assertEqual(report["global_sample_alignment_offset"],0)
    self.assertFalse(report["student_publication_authorized"])
    self.assertFalse(report["audio_spoken_words_listening_verified"])

 def test_alternate_audio_with_fresh_receipt_cannot_impersonate_original(self):
    alternate=self.base/"alternate.wav"
    rnd=random.Random(99)
    noise=struct.pack("<"+str(len(self.sample_bytes)//2)+"h",
                       *(int(10000*(2*rnd.random()-1))
                         for _ in range(len(self.sample_bytes)//2)))
    self.writewav(alternate,noise)
    self.encode(alternate,self.review/"element_highlight_review.mp4")
    self.rebind()
    with self.assertRaises(AudioTemporalAuditError):self.audit()

 def test_delayed_audio_cannot_pass_as_time_synchronized(self):
    altered=self.base/"delayed.wav"
    offset=round(.25*24000)*2
    self.writewav(altered,(b"\x00"*offset+self.sample_bytes)[:len(self.sample_bytes)])
    self.encode(altered,self.review/"element_highlight_review.mp4")
    self.rebind()
    with self.assertRaises(AudioTemporalAuditError):self.audit()

 def test_original_source_tamper_or_video_replacement_fails_before_analysis(self):
    (self.src/"slides.pdf").write_text("changed")
    with self.assertRaises(AudioTemporalAuditError):self.audit()
    (self.src/"slides.pdf").write_text("unaltered test original slides.pdf")
    with (self.review/"element_highlight_review.mp4").open("ab") as f:
        f.write(b"forged tail")
    with self.assertRaises(AudioTemporalAuditError):self.audit()
