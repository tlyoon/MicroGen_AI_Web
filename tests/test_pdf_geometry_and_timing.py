"""Offline geometry, actual WAV-segment timing and visible overlay regressions."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
import wave

import pymupdf
from PIL import Image
from jsonschema import Draft202012Validator

from selenium_pipeline.pdf_element_geometry import (
    ElementGeometryError, extract_element_geometry, strip_instrumentation_links,
)
from selenium_pipeline.speech_segment_timing import (
    AudioAlignmentError, build_segment_timeline,
)
from selenium_pipeline.highlight_frames import render_highlight_frames
from selenium_pipeline.storyboard_gate import canonical_sha256

ROOT = Path(__file__).resolve().parents[1]


def spoken_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class GeometryAudioTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.board = {
            "schema_version": 1, "part_id": "part_01", "plan_sha256": "a"*64,
            "slides": [{
                "slide_id": "part_01.s001", "title": "Part 1 of 1 — Preview",
                "elements": [
                    {"element_id": f"part_01.s001.{kind}", "kind": kind,
                     "source_concept_ids": ["concept01"], "source_page": 1}
                    for kind in ("text", "equation", "figure", "figure_panel")
                ],
            }],
            "narration_segments": [
                {"segment_id": f"segment{i:02d}", "slide_id": "part_01.s001",
                 "element_ids": [f"part_01.s001.{kind}"],
                 "spoken_text": text, "estimated_duration_s": 1.4}
                for i, (kind, text) in enumerate([
                    ("text", "Here we introduce Newton's second law."),
                    ("equation", "The force equals mass times acceleration."),
                    ("figure_panel", "This diagram illustrates the physical result."),
                ], 1)
            ],
        }
        self.pdf = self.root/"instrumented.pdf"
        doc = pymupdf.open()
        page = doc.new_page(width=362.835, height=272.126)
        marks = [
            ("text", (20, 60, 230, 76)),
            ("equation", (20, 85, 110, 105)),
            ("figure", (20, 114, 200, 155)),
            ("figure_panel", (20, 165, 95, 202)),
        ]
        for i, (kind, box) in enumerate(marks):
            rect = pymupdf.Rect(box)
            page.draw_rect(rect, color=(0.4, 0.4, 0.4), width=0.4)
            page.insert_text((rect.x0+3, rect.y0+12), f"{kind} {i}", fontsize=7)
            page.insert_link({
                "kind": pymupdf.LINK_URI, "from": rect,
                "uri": f"microgen-element:part_01.s001.{kind}",
            })
        doc.save(self.pdf)
        doc.close()
        self.geom = extract_element_geometry(self.pdf, self.board)
        self.clean_pdf = self.root/"clean.pdf"
        self.audio = self.root/"wav"
        self.audio.mkdir()

    def _make_wav(self, name, sec, *, rate=16000):
        path = self.audio/name
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
            frames = b"".join(
                struct.pack("<h", int(4000*math.sin(2*math.pi*160*i/rate)))
                for i in range(round(sec*rate))
            )
            w.writeframes(frames)
        return path

    def _manifest(self, *, alter_voice=False, alter_text=False):
        result = []
        for i, seg in enumerate(self.board["narration_segments"], 1):
            self._make_wav(f"segment{i:02d}.wav", 0.8+0.2*i)
            result.append({
                "segment_id": seg["segment_id"],
                "filename": f"segment{i:02d}.wav",
                "speech_sha256": spoken_hash(seg["spoken_text"]),
                "voice_id": "same_voice",
                "pause_after_ms": 100 if i < 3 else 0,
            })
        if alter_voice:
            result[-1]["voice_id"] = "second_voice"
        if alter_text:
            result[0]["speech_sha256"] = "b"*64
        return result

    def test_actual_pdf_link_bounds_and_normalized_positions(self):
        self.assertEqual(len(self.geom["elements"]), 4)
        self.assertEqual(self.geom["pages"][0]["page_index"], 0)
        for element in self.geom["elements"]:
            self.assertTrue(all(0 <= v <= 1 for v in element["rect_norm"]))
            self.assertGreater(element["rect_pt"][2], element["rect_pt"][0])
        self.assertIn("unreviewed", self.geom["status"])

    def test_clean_pdf_pixel_equal_and_no_hidden_clickable_markers(self):
        receipt = strip_instrumentation_links(self.pdf, self.clean_pdf, self.geom)
        self.assertTrue(receipt["all_annotations_removed"])
        self.assertEqual(receipt["removed_instrumentation_links"], 4)
        with pymupdf.open(self.clean_pdf) as doc:
            self.assertFalse(doc[0].get_links())
        with self.assertRaisesRegex(ElementGeometryError, "overwrite"):
            strip_instrumentation_links(self.pdf, self.clean_pdf, self.geom)

    def test_missing_marker_blocks_coverage(self):
        changed = copy.deepcopy(self.board)
        changed["slides"][0]["elements"].append(
            {"element_id": "part_01.s001.unmapped", "kind": "text",
             "source_concept_ids": ["concept01"], "source_page": 1}
        )
        with self.assertRaisesRegex(ElementGeometryError, "Missing"):
            extract_element_geometry(self.pdf, changed)

    def test_stale_pdf_sha_blocks_cleaning(self):
        changed = copy.deepcopy(self.geom)
        changed["instrumented_pdf_sha256"] = "0"*64
        with self.assertRaisesRegex(ElementGeometryError, "different PDF"):
            strip_instrumentation_links(self.pdf, self.clean_pdf, changed)

    def test_audio_chunks_define_exact_event_start_end(self):
        manifest = self._manifest()
        combined = self.root/"combined.wav"
        timeline, receipt = build_segment_timeline(
            self.board, self.geom, manifest, audio_root=self.audio,
            output_wav=combined,
        )
        expected = [(0,1000),(1100,2300),(2400,3800)]
        self.assertEqual([(x["start_ms"],x["end_ms"]) for x in timeline["events"]],
                         expected)
        self.assertEqual(timeline["duration_ms"], 3800)
        self.assertIn("unreviewed", receipt["status"])
        schema = json.loads((ROOT/"schemas/alignment.schema.json").read_text())
        Draft202012Validator(schema).validate(timeline)
        with wave.open(str(combined),"rb") as w:
            self.assertEqual(w.getnframes(), 60800)
        with self.assertRaisesRegex(AudioAlignmentError,"overwrite"):
            build_segment_timeline(self.board,self.geom,manifest,audio_root=self.audio,
                                   output_wav=combined)

    def test_audio_mismatch_voice_and_spoken_text_block_no_output(self):
        for kind in ("voice", "text"):
            with self.subTest(kind=kind):
                manifest = self._manifest(alter_voice=kind=="voice",
                                          alter_text=kind=="text")
                out = self.root/f"bad_{kind}.wav"
                with self.assertRaises(AudioAlignmentError):
                    build_segment_timeline(self.board,self.geom,manifest,
                                           audio_root=self.audio,output_wav=out)
                self.assertFalse(out.exists())

    def test_stale_geometry_blocks_alignment(self):
        manifest = self._manifest()
        bad = copy.deepcopy(self.geom)
        bad["storyboard_sha256"] = "0"*64
        with self.assertRaisesRegex(AudioAlignmentError,"stale"):
            build_segment_timeline(self.board,bad,manifest,audio_root=self.audio,
                                   output_wav=self.root/"bad.wav")

    def test_actual_rendered_highlight_frames(self):
        clean = strip_instrumentation_links(self.pdf, self.clean_pdf, self.geom)
        self.assertEqual(clean["status"], "clean_static_pdf_exact_pixel_match")
        manifest = self._manifest()
        timeline, _ = build_segment_timeline(
            self.board,self.geom,manifest,audio_root=self.audio,
            output_wav=self.root/"audio.wav",
        )
        preview = self.root/"previews"
        preview.mkdir()
        rendered = render_highlight_frames(
            self.clean_pdf,self.board,self.geom,timeline,output_dir=preview,
        )
        self.assertEqual(len(rendered), 3)
        with Image.open(rendered[0]["file"]) as first, \
                Image.open(rendered[1]["file"]) as second:
            self.assertEqual(first.size, second.size)
            self.assertNotEqual(first.tobytes(), second.tobytes())
        with self.assertRaisesRegex(ElementGeometryError,"overwrite"):
            render_highlight_frames(self.clean_pdf,self.board,self.geom,timeline,
                                    output_dir=preview)

    def test_wrong_element_or_slide_blocks_preview(self):
        strip_instrumentation_links(self.pdf,self.clean_pdf,self.geom)
        manifest=self._manifest()
        timeline,_=build_segment_timeline(self.board,self.geom,manifest,
                                         audio_root=self.audio,output_wav=self.root/"sound.wav")
        timeline["events"][0]["element_ids"]=["part_01.s002.fake"]
        with self.assertRaisesRegex(ElementGeometryError,"wrong slide"):
            render_highlight_frames(self.clean_pdf,self.board,self.geom,timeline,
                                    output_dir=self.root)

    def test_geometry_and_wav_manifest_schemas(self):
        schema=json.loads((ROOT/"schemas/element_geometry.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(self.geom)
        manifest=self._manifest()
        s=json.loads((ROOT/"schemas/speech_wav_manifest.schema.json").read_text())
        Draft202012Validator.check_schema(s)
        Draft202012Validator(s).validate(manifest)

    def test_offline_geometry_cli_extract_and_clean(self):
        import subprocess
        import sys
        board_path=self.root/"storyboard.json"
        board_path.write_text(json.dumps(self.board),encoding="utf-8")
        geom_file=self.root/"rectangles.json"
        a=subprocess.run(
            [sys.executable,"-m","selenium_pipeline.geometry_cli","extract",
             "--pdf",str(self.pdf),"--storyboard",str(board_path),
             "--output",str(geom_file)],
            cwd=ROOT,capture_output=True,text=True,
        )
        self.assertEqual(a.returncode,0,a.stderr)
        self.assertEqual(len(json.loads(geom_file.read_text())["elements"]),4)
        b=subprocess.run(
            [sys.executable,"-m","selenium_pipeline.geometry_cli","clean",
             "--pdf",str(self.pdf),"--geometry",str(geom_file),
             "--output",str(self.clean_pdf)],
            cwd=ROOT,capture_output=True,text=True,
        )
        self.assertEqual(b.returncode,0,b.stderr)
        self.assertTrue(self.clean_pdf.exists())


if __name__ == "__main__":
    unittest.main()
