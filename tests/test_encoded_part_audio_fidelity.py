import math,random,struct,subprocess,tempfile,unittest,wave
from pathlib import Path
from selenium_pipeline.encoded_part_audio_fidelity import verify_encoded_part_audio
from selenium_pipeline.independent_encoded_audio_temporal_audit import AudioTemporalAuditError
from selenium_pipeline.highlight_video_preview import ffmpeg_path
class AudioFidelity(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  self.folder=Path(tmp.name)
  rnd=random.Random(123)
  n=24000*4
  raw=struct.pack("<"+str(n)+"h",*(
    int(10000*(.63*math.sin(2*math.pi*(130*i/24000+30*(i/24000)**2))+
          .25*math.sin(2*math.pi*420*i/24000)+.02*rnd.uniform(-1,1)))
    for i in range(n)))
  self.original=self.folder/"narration.wav"
  self.write_wav(self.original,raw)
  self.clip=self.folder/"part.mp4"
  self.encode(self.original)
 def write_wav(self,path,raw):
  with wave.open(str(path),"wb") as f:
   f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000);f.writeframes(raw)
 def encode(self,wav):
  p=subprocess.run([ffmpeg_path(),"-nostdin","-v","error","-f","lavfi",
    "-i","color=c=black:s=160x120:r=5","-i",str(wav),"-shortest",
    "-c:v","mpeg4","-c:a","aac","-b:a","160k","-y",str(self.clip)],
    capture_output=True,timeout=45)
  self.assertEqual(p.returncode,0,p.stderr[-200:])
 def test_real_enc_audio_integrity(self):
  x=verify_encoded_part_audio(mp4=self.clip,wav=self.original)
  self.assertGreater(min(x["window_correlations"]),.78)
  self.assertFalse(x["student_publication_authorized"])
 def test_replaces_audio_and_original_wav_not_matching(self):
  rnd=random.Random(45)
  raw=struct.pack("<96000h",*(rnd.randrange(-8000,8000) for _ in range(96000)))
  substitute=self.folder/"sub.wav";self.write_wav(substitute,raw);self.encode(substitute)
  with self.assertRaises(AudioTemporalAuditError):
   verify_encoded_part_audio(mp4=self.clip,wav=self.original)
 def test_offset_audio_fails(self):
  with wave.open(str(self.original),"rb") as f:raw=f.readframes(f.getnframes())
  shift=self.folder/"shift.wav"
  self.write_wav(shift,b"\x00"*12000+raw[:-12000])
  self.encode(shift)
  with self.assertRaises(AudioTemporalAuditError):
   verify_encoded_part_audio(mp4=self.clip,wav=self.original)
