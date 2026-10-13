"""Synthetic encoded H.264/AAC audit with segment-level highlight/no-highlight intervals."""
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import wave

import pymupdf
from PIL import Image, ImageChops, ImageStat

from selenium_pipeline.pdf_element_geometry import (
    extract_element_geometry, strip_instrumentation_links,
)
from selenium_pipeline.speech_segment_timing import build_segment_timeline
from selenium_pipeline.highlight_video_preview import (
    HighlightVideoError, compose_highlight_preview, ffmpeg_path, probe_mp4,
)


class PreviewEncoderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/"instrumented.pdf"
        self.clean=self.root/"clean.pdf"
        self.audio_dir=self.root/"wav"
        self.audio_dir.mkdir()
        self.sandbox=self.root/"work"
        self.sandbox.mkdir()
        self.output=self.root/"highlight_preview.mp4"
        self.board={
            "schema_version":1,"part_id":"part_01","plan_sha256":"c"*64,
            "slides":[{
                "slide_id":"part_01.s001","title":"Part 1 of 1 test",
                "elements":[{
                    "element_id":f"part_01.s001.e{i}",
                    "kind":"text","source_concept_ids":["c1"],"source_page":1,
                } for i in range(1,4)],
            }],
            "narration_segments":[{
                "segment_id":f"n{i}","slide_id":"part_01.s001",
                "element_ids":[f"part_01.s001.e{i}"],
                "spoken_text":f"This test narrator discusses visual region {i}.",
                "estimated_duration_s":2,
            } for i in range(1,4)],
        }
        doc=pymupdf.open()
        page=doc.new_page(width=360,height=270)
        for i in range(1,4):
            x0=25+i*65
            rect=pymupdf.Rect(x0,85,x0+45,115)
            page.draw_rect(rect,color=(0.3,0.3,0.5),fill=(0.95,0.95,0.95))
            page.insert_text((x0+5,100),f"Region {i}",fontsize=7)
            page.insert_link({"kind":pymupdf.LINK_URI,"from":rect,
                              "uri":f"microgen-element:part_01.s001.e{i}"})
        doc.save(self.source)
        doc.close()
        self.geometry=extract_element_geometry(self.source,self.board)
        self.cleaned=strip_instrumentation_links(self.source,self.clean,self.geometry)
        manifest=[]
        for i,seg in enumerate(self.board["narration_segments"],1):
            name=f"n{i}.wav"
            with wave.open(str(self.audio_dir/name),"wb") as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
                frame_count=int([1.0,1.2,1.4][i-1]*16000)
                sound=b"".join(
                    struct.pack("<h",int(1500*math.sin(2*math.pi*220*n/16000)))
                    for n in range(frame_count)
                )
                f.writeframes(sound)
            manifest.append({
                "segment_id":seg["segment_id"],"filename":name,
                "speech_sha256":hashlib.sha256(seg["spoken_text"].encode()).hexdigest(),
                "voice_id":"consistent_voice",
                "pause_after_ms":100 if i<3 else 0,
            })
        self.wav=self.root/"combined.wav"
        self.timeline,self.audio_receipt=build_segment_timeline(
            self.board,self.geometry,manifest,
            audio_root=self.audio_dir,output_wav=self.wav,
        )

    def compose(self):
        return compose_highlight_preview(
            clean_pdf=self.clean,clean_receipt=self.cleaned,
            storyboard=self.board,geometry=self.geometry,
            timeline=self.timeline,wav_file=self.wav,
            workspace=self.sandbox,output_mp4=self.output,
        )

    def test_encoding_produces_strict_duration_and_timed_highlight_intervals(self):
        result=self.compose()
        self.assertTrue(self.output.is_file())
        self.assertGreater(self.output.stat().st_size,1000)
        self.assertAlmostEqual(result["duration_s"],3.8,delta=0.25)
        self.assertEqual(result["highlight_segments"],3)
        self.assertLessEqual(result["encoded_transition_qa"]["max_encoded_frame_drift_s"],0.15)
        self.assertEqual([round(x["duration_s"],1)
                          for x in result["base_and_highlight_intervals"]],
                         [1.0,0.1,1.2,0.1,1.4])
        self.assertEqual([x["highlight"] for x in result["base_and_highlight_intervals"]],
                         [True,False,True,False,True])
        self.assertTrue(probe_mp4(self.output,exe=ffmpeg_path())["audio"])
        with self.assertRaisesRegex(HighlightVideoError,"output already exists"):
            self.compose()

    def test_input_mutation_blocks_encoding_before_workspace_changes(self):
        altered=copy.deepcopy(self.timeline)
        altered["audio_sha256"]="0"*64
        with self.assertRaisesRegex(HighlightVideoError,"Narration WAV"):
            compose_highlight_preview(
                clean_pdf=self.clean,clean_receipt=self.cleaned,
                storyboard=self.board,geometry=self.geometry,timeline=altered,
                wav_file=self.wav,workspace=self.sandbox,output_mp4=self.output,
            )
        self.assertEqual(list(self.sandbox.iterdir()),[])

    def test_video_frames_change_around_pause(self):
        self.compose()
        ffmpeg=ffmpeg_path()
        def grab(sec,filename):
            res=subprocess.run([
                ffmpeg,"-hide_banner","-loglevel","error","-ss",str(sec),
                "-i",str(self.output),"-frames:v","1","-y",str(filename)
            ],capture_output=True,text=True,timeout=25)
            self.assertEqual(res.returncode,0,res.stderr)
            return Image.open(filename).convert("RGB")
        during=grab(0.52,self.root/"during.png")
        gap=grab(1.06,self.root/"gap.png")
        next_seg=grab(1.65,self.root/"next.png")
        try:
            a=ImageStat.Stat(ImageChops.difference(during,gap)).mean
            b=ImageStat.Stat(ImageChops.difference(next_seg,gap)).mean
            self.assertGreater(sum(a),0.2)
            self.assertGreater(sum(b),0.2)
        finally:
            during.close();gap.close();next_seg.close()


if __name__=="__main__":
    unittest.main()
