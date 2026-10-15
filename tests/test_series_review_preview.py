"""Actual two-part FFmpeg + PDF geometry + WAV highlight review bridge."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

import pymupdf

from selenium_pipeline.series_review_preview import (
    PreviewSeriesError, render_review_series,
)
from selenium_pipeline.encoded_highlight_pixels import (
    EncodedPixelQAError, verify_encoded_highlight_pixels,
)
from selenium_pipeline.highlight_video_preview import ffmpeg_path
from selenium_pipeline.production_video_contract import (
    VideoContractError, verify_series,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, indent=2), encoding="utf8")


class MultiPartPreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        textbook = self.root/"textbook"
        textbook.mkdir()
        self.source = textbook/"source.pdf"
        book = pymupdf.open()
        p = book.new_page(width=500, height=350)
        p.insert_text((30,50), "Synthetic textbook source for offline tests")
        book.save(self.source)
        book.close()
        self.staged = self.root/"staged"
        self.staged.mkdir()
        self.output = self.root/"rendered_review"
        self.plan_sha = "b"*64
        self.parts = ["part_01","part_02"]
        for part_id in self.parts:
            self.make_part(part_id)
        self.series={"schema_version":1,
           "status":"review_only_source_bound_inputs",
           "source_sha256":_sha(self.source),
           "plan_sha256":self.plan_sha,"parts":self.parts}
        _write(self.staged/"series_inputs.json", self.series)

    def make_part(self, part_id):
        stage = self.staged/part_id
        stage.mkdir()
        (stage/"wav").mkdir()
        slide = part_id+".s001"
        labels = [slide+".e1",slide+".e2"]
        snippets=[f"The first highlighted region in {part_id}.",
                  f"The second highlighted region in {part_id}."]
        board={
          "schema_version":1,"part_id":part_id,"plan_sha256":self.plan_sha,
          "slides":[{"slide_id":slide,"title":"Part review-only synthetic",
                     "elements":[{"element_id":key,"kind":"text",
                       "source_concept_ids":["concept1"],"source_page":1}
                        for key in labels]}],
          "narration_segments":[{"segment_id":f"n{i}","slide_id":slide,
                "element_ids":[key],"spoken_text":words,
                "estimated_duration_s":2}
                 for i,(key,words) in enumerate(zip(labels,snippets),1)]}
        _write(stage/"storyboard.json",board)
        pdf=pymupdf.open()
        page=pdf.new_page(width=360,height=270)
        for i,key in enumerate(labels):
            x=70+i*120
            rect=pymupdf.Rect(x,85,x+70,125)
            page.draw_rect(rect,color=(0.2,0.2,0.5),fill=(0.96,0.96,0.96))
            page.insert_text((x+7,105),f"Region {i+1}",fontsize=8)
            page.insert_link({"kind":pymupdf.LINK_URI,"from":rect,
                              "uri":"microgen-element:"+key})
        pdf.save(stage/"instrumented.pdf")
        pdf.close()
        chunks=[]
        for i,words in enumerate(snippets,1):
            filename=f"n{i}.wav"
            path=stage/"wav"/filename
            frames=16000 if i==1 else 19200
            with wave.open(str(path),"wb") as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
                w.writeframes(b"".join(struct.pack("<h",
                    int(1400*math.sin(2*math.pi*220*k/16000)))
                    for k in range(frames)))
            chunks.append({"segment_id":f"n{i}","filename":filename,
                 "speech_sha256":hashlib.sha256(words.encode()).hexdigest(),
                 "voice_id":"synthetic_same_voice",
                 "pause_after_ms":100 if i==1 else 0})
        _write(stage/"tts_chunks.json",{"schema_version":1,"part_id":part_id,
                                         "segments":chunks})

    def test_two_part_preview_with_real_ffmpeg_remains_unapproved(self):
        before=_sha(self.source)
        manifest=render_review_series(source_pdf=self.source,
                 inputs_root=self.staged,output_root=self.output)
        self.assertEqual(_sha(self.source),before)
        self.assertEqual(manifest["status"],"review_only_not_approved")
        self.assertEqual([x["part_id"] for x in manifest["parts"]],self.parts)
        for record in manifest["parts"]:
            self.assertGreater(record["highlight_segments"],0)
            self.assertEqual(record["decoded_pixel_verified_events"],
                             record["highlight_segments"])
            self.assertLess(record["encoded_mp4_seconds"],600)
            part=self.output/record["part_id"]
            self.assertEqual(_sha(part/(record["part_id"]+"_review.mp4")),
                             record["mp4_sha256"])
            self.assertEqual(record["status"],"review_only_not_approved")
            self.assertEqual(_sha(part/"encoded_pixel_qa.json"),
                             record["decoded_pixel_qa_sha256"])
        self.assertFalse((self.output/"lecture_completion.json").exists())
        with self.assertRaisesRegex(VideoContractError,"Required receipt missing"):
            verify_series(self.output)

    def test_static_mp4_cannot_claim_speech_timed_highlights(self):
        render_review_series(source_pdf=self.source,
            inputs_root=self.staged,output_root=self.output)
        part=self.output/"part_01"
        fake=part/"static_impostor.mp4"
        exe=ffmpeg_path()
        encoded=subprocess.run([
            exe,"-hide_banner","-loglevel","error",
            "-loop","1","-framerate","2",
            "-i",str(part/"scratch_frames"/"base_0001.png"),
            "-i",str(part/"narration.wav"),
            "-c:v","libx264","-preset","veryfast",
            "-pix_fmt","yuv420p","-c:a","aac",
            "-shortest","-t","2.3",str(fake)
        ],capture_output=True,text=True,timeout=40)
        self.assertEqual(encoded.returncode,0,encoded.stderr)
        geometry=json.loads((part/"element_geometry.json").read_text())
        timeline=json.loads((part/"narration_timeline.json").read_text())
        with self.assertRaisesRegex(
            EncodedPixelQAError,"no verified target highlight"):
            verify_encoded_highlight_pixels(mp4=fake,
                frames_dir=part/"scratch_frames",
                geometry=geometry,timeline=timeline)

    def test_changed_source_prevents_any_output(self):
        self.source.write_bytes(self.source.read_bytes()+b"modified")
        with self.assertRaisesRegex(PreviewSeriesError,"Textbook source hash"):
            render_review_series(source_pdf=self.source,
                inputs_root=self.staged,output_root=self.output)
        self.assertFalse(self.output.exists())

    def test_missing_second_part_chunk_prevents_any_output(self):
        (self.staged/"part_02"/"wav"/"n2.wav").unlink()
        with self.assertRaisesRegex(PreviewSeriesError,"unsafe source WAV"):
            render_review_series(source_pdf=self.source,
                inputs_root=self.staged,output_root=self.output)
        self.assertFalse(self.output.exists())

    def test_existing_output_refused(self):
        self.output.mkdir()
        sentinel=self.output/"keep.txt"
        sentinel.write_text("never overwrite")
        with self.assertRaisesRegex(PreviewSeriesError,"new, nonexistent"):
            render_review_series(source_pdf=self.source,
                inputs_root=self.staged,output_root=self.output)
        self.assertEqual(sentinel.read_text(),"never overwrite")

    def test_missing_or_out_of_order_part_ids_rejected(self):
        self.series["parts"]=["part_02","part_01"]
        _write(self.staged/"series_inputs.json",self.series)
        with self.assertRaisesRegex(PreviewSeriesError,"contiguous"):
            render_review_series(source_pdf=self.source,
                inputs_root=self.staged,output_root=self.output)
        self.assertFalse(self.output.exists())

    def test_source_adjacent_output_blocked(self):
        dest=self.source.parent/"output"
        with self.assertRaisesRegex(PreviewSeriesError,"Output must not be inside source"):
            render_review_series(source_pdf=self.source,
                inputs_root=self.staged,output_root=dest)
        self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
