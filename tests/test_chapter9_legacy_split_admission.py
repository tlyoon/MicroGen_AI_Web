"""Fault-injection for strict historical multipart lecture admission in image retrofits."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import hashlib,json,wave
import pytest
fitz=pytest.importorskip("fitz")
from selenium_pipeline.retrofit_image_repair import (
    _completed_legacy_split_lecture,_source_snapshot,
)

def digest(p):
 return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def fixture(folder):
 source=fitz.open();source.new_page().insert_text((60,80),"Source")
 source.save(folder/"source.pdf");source.close()
 slides=fitz.open();slides.new_page().insert_text((60,80),"Lecture")
 slides.save(folder/"slides.pdf");slides.close()
 (folder/"slides.tex").write_text(r"\begin{frame}Lecture\end{frame}",encoding="utf8")
 (folder/"script.txt").write_text("Narration",encoding="utf8")
 with wave.open(str(folder/"slide1.wav"),"wb") as wav:
  wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(8000)
  wav.writeframes(b"\x00\x00"*8000)
 (folder/"slides_part00.mp4").write_bytes(b"\x00MP4-sample-structural-only"*40)
 basename="slides_part00.mp4"
 hashes={name:digest(folder/name) for name in
         ("slides.tex","slides.pdf","script.txt",basename)}
 parts={"parts":[{"name":basename,"sha256":hashes[basename],"duration_seconds":128.0}]}
 (folder/"slides_parts_manifest.json").write_text(json.dumps(parts),encoding="utf8")
 sync={"pdf_sha256":hashes["slides.pdf"],"script_sha256":hashes["script.txt"],
       "pages":1,"narration_sha256":[hashlib.sha256(b"Test words").hexdigest()],
       "wav":[{"file":"slide1.wav","sha256":digest(folder/"slide1.wav")}]}
 (folder/"slide_narration_sync.json").write_text(json.dumps(sync),encoding="utf8")
 receipt={"source_sha256":digest(folder/"source.pdf"),
          "final_sha256":hashes,
          "structural_sync_sha256":digest(folder/"slide_narration_sync.json")}
 (folder/".microgen_completion.json").write_text(json.dumps(receipt),encoding="utf8")
 fidelity={"threshold_percent":99,
           "summary":{"slides":1,"passed":1,"blocking_failures":0,
                      "review":0,"minimum_fidelity_percent":100}}
 (folder/"tts_fidelity_report.json").write_text(json.dumps(fidelity),encoding="utf8")
 (folder/"script_risk_report.json").write_text(json.dumps({"summary":{"blocking":0}}),encoding="utf8")
 return folder/"source.pdf"

def accepted(source):
 with patch("selenium_pipeline.retrofit_image_repair._probe_duration",return_value=128.0),\
      patch("selenium_pipeline.slide_narration_sync.script_blocks",return_value=["Test words"]):
  return _completed_legacy_split_lecture(source)

def test_complete_legacy_split_packet_accepted_and_snapshot_covers_media(tmp_path):
 src=fixture(tmp_path)
 assert accepted(src)
 snapshot=_source_snapshot(tmp_path)
 for name in ("slides_part00.mp4","slides_parts_manifest.json",
              "slide_narration_sync.json","tts_fidelity_report.json",
              "script_risk_report.json","slide1.wav"):
  assert snapshot[name]==digest(tmp_path/name)

@pytest.mark.parametrize("tampered",[
 "source.pdf","slides.tex","slides.pdf","script.txt","slides_part00.mp4",
 "slide1.wav","slide_narration_sync.json","tts_fidelity_report.json"
])
def test_tampered_legacy_packet_fail_closed(tmp_path,tampered):
 src=fixture(tmp_path)
 p=tmp_path/tampered
 if tampered=="tts_fidelity_report.json":
  j=json.loads(p.read_text("utf8"));j["summary"]["minimum_fidelity_percent"]=98
  p.write_text(json.dumps(j),encoding="utf8")
 else:p.write_bytes(p.read_bytes()+b"tamp")
 assert not accepted(src),tampered

def test_unmanifested_stale_mp4_blocks_admission(tmp_path):
 src=fixture(tmp_path)
 (tmp_path/"slides_part01.mp4").write_bytes(b"extra orphaned video"*20)
 assert not accepted(src)

def test_declared_video_above_600_seconds_is_rejected(tmp_path):
 src=fixture(tmp_path)
 with patch("selenium_pipeline.retrofit_image_repair._probe_duration",return_value=601.0),\
      patch("selenium_pipeline.slide_narration_sync.script_blocks",return_value=["Test words"]):
  assert not _completed_legacy_split_lecture(src)

def test_unapproved_narration_risk_is_rejected(tmp_path):
 src=fixture(tmp_path)
 risk=tmp_path/"script_risk_report.json"
 risk.write_text(json.dumps({"summary":{"blocking":1}}),encoding="utf8")
 assert not accepted(src)
