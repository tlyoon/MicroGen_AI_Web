"""Source-bound true per-element narration staging regressions (offline)."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path

import pymupdf
from PIL import Image

from selenium_pipeline.element_narration_stage import (
    ElementStageError, prepare,
)


def checksum(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


class ElementSpeechStageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source_folder=self.root/"original"
        self.source_folder.mkdir()
        self.audio=self.root/"audio"
        self.audio.mkdir()
        self.source=self.source_folder/"source.pdf"
        self.slides=self.source_folder/"slides.pdf"
        self.planfile=self.root/"scene_plan.json"
        self.staged=self.root/"stage"
        textbook=pymupdf.open()
        p=textbook.new_page()
        p.insert_textbox(pymupdf.Rect(50,70,450,150),
            "We want any substitution we use in integration to be reversible "
            "so that we can recover the original variable.",fontsize=10)
        textbook.save(self.source)
        textbook.close()
        image=self.root/"composite.png"
        Image.new("RGB",(900,130),(220,230,243)).save(image)
        slides=pymupdf.open()
        p=slides.new_page(width=363,height=272)
        p.insert_text((25,20),"A mathematical concept",fontsize=14)
        p.insert_textbox(pymupdf.Rect(25,65,320,95),
            "We must reverse the substitution.",fontsize=12)
        p.insert_image(pymupdf.Rect(30,135,330,195),filename=str(image))
        slides.save(self.slides)
        slides.close()
        for name in ("e01.wav","e02.wav"):
            with wave.open(str(self.audio/name),"wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(16000)
                w.writeframes(b"\x01\x10"*32000)
        with pymupdf.open(self.slides) as pdf:
            indices=[i for i,b in enumerate(pdf[0].get_text("blocks"))
                     if len(b)>4 and "must reverse" in str(b[4])]
            self.assertEqual(len(indices),1)
            self.block=indices[0]
        self.plan={
           "schema_version":1,
           "status":"author_specified_unapproved_element_narration",
           "source_sha256":checksum(self.source),
           "slides_sha256":checksum(self.slides),
           "voice_id":"windows_sapi_test_voice_REVIEW_ONLY",
           "parts":[{"part_id":"part_01","slides":[{
               "slide":1,"source_page":1,
               "source_evidence":"any substitution we use in integration to be reversible",
               "title":"Source-grounded review",
               "elements":[
                 {"anchor":{"type":"text_block","index":self.block,
                            "text_evidence":"must reverse"},
                  "wav":"e01.wav",
                  "spoken_text":"We must reverse the substitution carefully."},
                 {"anchor":{"type":"image_panel","index":0,"panels":3,"panel":2},
                  "wav":"e02.wav",
                  "spoken_text":"The middle figure shows the required inverse branch."}
               ]
           }]}]}
        self.write()

    def write(self):
        self.planfile.write_text(json.dumps(self.plan),encoding="utf8")

    def stage(self):
        return prepare(source_pdf=self.source,slides_pdf=self.slides,
                 authored_json=self.planfile,recorded_audio=self.audio,
                 destination=self.staged)

    def test_source_bound_two_elements_and_two_real_wavs(self):
        before=checksum(self.slides)
        result=self.stage()
        self.assertEqual(result["status"],"review_only")
        self.assertEqual(checksum(self.slides),before)
        part=self.staged/"part_01"
        board=json.loads((part/"storyboard.json").read_text())
        self.assertEqual(len(board["narration_segments"]),2)
        self.assertEqual(len(board["slides"][0]["elements"]),2)
        self.assertEqual([x["kind"] for x in board["slides"][0]["elements"]],
                         ["text","figure_panel"])
        with pymupdf.open(part/"instrumented.pdf") as pdf:
            self.assertEqual(len(pdf[0].get_links()),2)
            self.assertTrue(all(str(x.get("uri")).startswith("microgen-element:")
                                for x in pdf[0].get_links()))
        state=json.loads((self.staged/"element_stage_receipt.json").read_text())
        self.assertTrue(state["complete_lecture_coverage"])
        self.assertFalse(state["audio_text_fidelity_verified"])
        self.assertFalse(state["mathematical_approval"])

    def test_stale_source_sha_blocks_without_writing(self):
        self.plan["source_sha256"]="0"*64
        self.write()
        with self.assertRaisesRegex(ElementStageError,"Stale source"):
            self.stage()
        self.assertFalse(self.staged.exists())

    def test_missing_source_evidence_blocks_without_writing(self):
        self.plan["parts"][0]["slides"][0]["source_evidence"]="not present in source textbook"
        self.write()
        with self.assertRaisesRegex(ElementStageError,"Verbatim evidence"):
            self.stage()
        self.assertFalse(self.staged.exists())

    def test_incorrect_rendered_text_anchor_blocks(self):
        self.plan["parts"][0]["slides"][0]["elements"][0]["anchor"]["text_evidence"]="not on slide"
        self.write()
        with self.assertRaisesRegex(ElementStageError,"Text evidence"):
            self.stage()
        self.assertFalse(self.staged.exists())

    def test_missing_audio_and_duplicates_block_without_writing(self):
        self.plan["parts"][0]["slides"][0]["elements"][1]["wav"]="nonexistent.wav"
        self.write()
        with self.assertRaisesRegex(ElementStageError,"Missing source narration"):
            self.stage()
        self.assertFalse(self.staged.exists())
        self.plan["parts"][0]["slides"][0]["elements"][1]["wav"]="e01.wav"
        self.write()
        with self.assertRaisesRegex(ElementStageError,"repeated or unsafe WAV"):
            self.stage()
        self.assertFalse(self.staged.exists())

    def test_reject_unsafe_dest_and_existing_dest(self):
        bad=self.source_folder/"forbidden"
        with self.assertRaisesRegex(ElementStageError,"Cannot stage inside"):
            prepare(source_pdf=self.source,slides_pdf=self.slides,
                    authored_json=self.planfile,recorded_audio=self.audio,
                    destination=bad)
        self.staged.mkdir()
        keep=self.staged/"keep.txt"
        keep.write_text("preserve")
        with self.assertRaisesRegex(ElementStageError,"Destination must be new"):
            self.stage()
        self.assertEqual(keep.read_text(),"preserve")

    def test_composite_panel_rejects_impossible_index(self):
        self.plan["parts"][0]["slides"][0]["elements"][1]["anchor"]["panel"]=4
        self.write()
        with self.assertRaisesRegex(ElementStageError,"composite panel"):
            self.stage()
        self.assertFalse(self.staged.exists())


if __name__=="__main__":
    unittest.main()
