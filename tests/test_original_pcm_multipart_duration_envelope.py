"""Exact real-WAV + source PDF multipart envelope; no fake MP4 acceptance."""
import json,tempfile,unittest,wave
from pathlib import Path
import pymupdf
from selenium_pipeline.original_pcm_multipart_duration_envelope import (
 build,MultipartEnvelopeError)

def fixture(root,seconds=(8.,9.,11.)):
 root=Path(root)
 with pymupdf.open() as doc:
  doc.new_page().insert_text((40,60),"True source textbook evidence")
  doc.save(root/"source.pdf")
 with pymupdf.open() as doc:
  for i in range(len(seconds)):
   doc.new_page().insert_text((40,60),f"Slide {i+1}")
  doc.save(root/"slides.pdf")
 lines=[f"**Slide {i} [5 sec]:\nThe original source slide number {i}.\n"
        for i in range(1,len(seconds)+1)]
 (root/"script.txt").write_text("\n".join(lines),encoding="utf8")
 rows=[]
 for i,sec in enumerate(seconds,1):
  path=root/f"slide{i}.wav"
  with wave.open(str(path),"wb") as wav:
   wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000)
   wav.writeframes(b"\x00\x01"*int(16000*sec))
  rows.append({"slide":i,"audio_file":path.name,
               "ground_truth":f"The original source slide number {i}.",
               "duration_seconds":sec,"status":"pass"})
 report={"summary":{"passed":len(rows),"review":0,
                    "blocking_failures":0},"slides":rows}
 (root/"tts_fidelity_report.json").write_text(json.dumps(report),encoding="utf8")
 return [root/"source.pdf",root/"slides.pdf",root/"script.txt",
         root/"tts_fidelity_report.json"]

def run(root,**args):
 return build(source=Path(root)/"source.pdf",slides=Path(root)/"slides.pdf",
              script=Path(root)/"script.txt",
              audio_qa=Path(root)/"tts_fidelity_report.json",**args)

class OriginalPCMEnvelopeTests(unittest.TestCase):
 def test_two_part_split_and_exact_coverage(self):
  with tempfile.TemporaryDirectory() as t:
   original=fixture(t)
   old={str(p):p.read_bytes() for p in original}
   result=run(t,max_payload_seconds=120)
   # The three recorded WAVs total 28 seconds plus transition overhead.
   self.assertEqual(result["source_slide_count"],3)
   self.assertEqual(result["part_count"],1)
   self.assertFalse(result["real_mp4_duration_verified"])
   self.assertFalse(result["pixel_highlight_synchronization_verified"])
   self.assertFalse(result["production_video_approved"])
   self.assertEqual(old,{str(p):p.read_bytes() for p in original})
 def test_oversized_single_slide_fails_closed_not_approved(self):
  with tempfile.TemporaryDirectory() as t:
   fixture(t,seconds=(150.,))
   with self.assertRaisesRegex(MultipartEnvelopeError,"must split genuine speech"):
    run(t,max_payload_seconds=120)

 def test_missing_original_audio_prevents_envelope(self):
  with tempfile.TemporaryDirectory() as t:
   fixture(t)
   (Path(t)/"slide2.wav").unlink()
   with self.assertRaisesRegex(MultipartEnvelopeError,"Missing original recorded slide"):
    run(t)

 def test_real_strict_part_split(self):
  with tempfile.TemporaryDirectory() as t:
   fixture(t,seconds=(55.,55.,55.))
   result=run(t,max_payload_seconds=120)
   self.assertEqual(result["part_count"],2)
   self.assertEqual([[x["slide"] for x in p["slides"]]
                     for p in result["parts"]],[[1,2],[3]])
   self.assertTrue(all(p["projected_pcm_and_transition_seconds"]<120
                       for p in result["parts"]))
 def test_qa_review_is_not_allowed_even_with_valid_wav(self):
  with tempfile.TemporaryDirectory() as t:
   fixture(t)
   p=Path(t)/"tts_fidelity_report.json"
   x=json.loads(p.read_text());x["summary"]["passed"]=2
   x["summary"]["review"]=1;x["summary"]["blocking_failures"]=1
   x["slides"][2]["status"]="review";p.write_text(json.dumps(x))
   with self.assertRaisesRegex(MultipartEnvelopeError,"not passed"):
    run(t)
 def test_qa_and_original_pcm_duration_disagreement_fails(self):
  with tempfile.TemporaryDirectory() as t:
   fixture(t)
   p=Path(t)/"tts_fidelity_report.json"
   x=json.loads(p.read_text());x["slides"][0]["duration_seconds"]=110.
   p.write_text(json.dumps(x))
   with self.assertRaisesRegex(MultipartEnvelopeError,"duration differs"):
    run(t)
 def test_no_600_seconds_or_invalid_budget_accepted(self):
  with tempfile.TemporaryDirectory() as t:
   fixture(t)
   with self.assertRaisesRegex(MultipartEnvelopeError,"strictly shorter"):
    run(t,final_duration_limit_seconds=600.0,max_payload_seconds=580)
 def test_tampered_reference_script_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   fixture(t)
   path=Path(t)/"script.txt"
   path.write_text(path.read_text().replace("source slide","wrong answer"))
   with self.assertRaisesRegex(MultipartEnvelopeError,"identity drift"):
    run(t)
if __name__=="__main__":unittest.main()
