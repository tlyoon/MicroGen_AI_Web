"""Offline tests for explicitly review-only legacy real-narration bridge."""
from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path
import pymupdf

from thomas84_real_speech_pilot import prepare


def hashfile(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Thomas84LegacyPilotPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/"source"
        self.source.mkdir()
        self.stage=self.root/"staged"
        source_pdf=pymupdf.open()
        sp=source_pdf.new_page()
        sp.insert_text((50,60),"Fictitious exercise source")
        source_pdf.save(self.source/"source.pdf")
        source_pdf.close()
        slides=pymupdf.open()
        for i in range(1,18):
            p=slides.new_page(width=363,height=272)
            p.insert_text((12,20),f"Title {i}")
            p.insert_textbox(pymupdf.Rect(35,65,300,185),
                 f"Slide {i} body text with a mathematical equation concept " * 3,
                 fontsize=12)
        slides.save(self.source/"slides.pdf")
        slides.close()
        sidecar={"slides":[]}
        receipts=[]
        for i in range(1,18):
            with wave.open(str(self.source/f"slide{i}.wav"),"wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(b"\x00\x10"*16000)
            receipts.append(hashfile(self.source/f"slide{i}.wav"))
            sidecar["slides"].append({"slide":i,"title":f"Slide {i}",
                      "narration":f"Narration {i}.",
                      "tts_text":f"Narration {i}."})
        sidepath=self.source/"script_tts.json"
        sidepath.write_text(json.dumps(sidecar),encoding="utf8")
        receipt={"source_sha256":hashfile(self.source/"source.pdf"),
                 "slides_pdf_sha256":hashfile(self.source/"slides.pdf"),
                 "sidecar_sha256":hashfile(sidepath),
                 "slide_count":17,"wav_sha256":receipts}
        (self.source/".microgen_verified_completion.json").write_text(
                json.dumps(receipt),encoding="utf8")

    def test_staging_covers_each_slide_and_preserves_origins(self):
        original=hashfile(self.source/"source.pdf")
        prepare(self.source,self.stage)
        self.assertEqual(hashfile(self.source/"source.pdf"),original)
        self.assertTrue((self.stage/"part_01"/"instrumented.pdf").exists())
        evidence=json.loads((self.stage/"pilot_provenance.json").read_text())
        self.assertEqual(len(evidence["anchors"]),17)
        self.assertIn("NOT_PRODUCTION_COMPLIANT",evidence["status"])
        for part_id,count in (("part_01",8),("part_02",9)):
            folder=self.stage/part_id
            board=json.loads((folder/"storyboard.json").read_text())
            with pymupdf.open(folder/"instrumented.pdf") as doc:
                self.assertEqual(len(doc),count)
                self.assertTrue(all(len(p.get_links())==1 for p in doc))
            self.assertEqual(len(board["narration_segments"]),count)

    def test_reject_preexisting_destination_without_touching_it(self):
        self.stage.mkdir()
        sentinel=self.stage/"keep.txt"
        sentinel.write_text("preserve")
        with self.assertRaisesRegex(ValueError,"must not already exist"):
            prepare(self.source,self.stage)
        self.assertEqual(sentinel.read_text(),"preserve")

    def test_tampered_original_wav_blocks_before_creating_staging(self):
        with (self.source/"slide9.wav").open("ab") as f:
            f.write(b"tampered")
        with self.assertRaisesRegex(ValueError,"changed verified WAV"):
            prepare(self.source,self.stage)
        self.assertFalse(self.stage.exists())

    def test_staging_inside_source_blocked(self):
        with self.assertRaisesRegex(ValueError,"textbook folder"):
            prepare(self.source,self.source/"stage")
        self.assertFalse((self.source/"stage").exists())


if __name__=="__main__":
    unittest.main()
