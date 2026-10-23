"""Fail-closed unattended source-grounded text narration and element TTS QA.

Synthetic WAV fixture only; no paid Gemini, Cloud, browser or YouTube calls.
"""
from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
import pymupdf

from selenium_pipeline.automatic_element_narration import (
    inspect_text_only, plan_for_audio, AutomaticElementAudioError)
from selenium_pipeline.automatic_element_audio_stage import (
    produce_element_audio)
from selenium_pipeline.sourcebound_production_video import (
    verify_element_tts_batch,render_and_install_prepared,ProductionRenderError)
from selenium_pipeline.production_video_contract import verify_series
from selenium_pipeline.runner import blocks
from selenium_pipeline.tts_effective_identity import DEFAULT


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def synth_fixture(work:Path,provider:str,model:str,voice:str):
    """Fake output representing a clean paid-batch source receipt, no API."""
    assert (provider,model,voice)==("gemini","gemini-3.8-flash-lite-tts","Kore")
    items=blocks((work/"script.txt").read_text(encoding="utf-8"))
    for n,_ in items:
        with wave.open(str(work/f"slide{n}.wav"),"wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(24000)
            # Deterministic voiced changing samples: a constant-valued
            # placeholder has zero variance and cannot test encoded AAC audio.
            import math,struct
            samples=[int(10000*(.63*math.sin(2*math.pi*(125+30*n)*t/24000)
                       +.28*math.sin(2*math.pi*(430+25*n)*t/24000)))
                     for t in range(24000)]
            out.writeframes(struct.pack("<24000h",*samples))
    receipt={"version":2,"primary":DEFAULT,"slides":[
        {"slide":n,"source_text":text,"tts_text":text,
         "provider":"gemini","model":model,"voice":voice,
         "fallback_used":False}
        for n,text in items]}
    (work/"tts_input_manifest.json").write_text(
        json.dumps(receipt),encoding="utf-8")

class ElementAutomaticTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.folder=self.root/"source"/"8"/"8.4"
        self.folder.mkdir(parents=True)
        self.source=self.folder/"source.pdf"
        self.slides=self.folder/"slides.pdf"
        self.script=self.folder/"script.txt"
        self.outroot=self.root/"local_work"
        self.outroot.mkdir()
        self.text=[
            "The magnetic field of a solenoid is nearly uniform inside its coil.",
            "A charged particle experiences a magnetic force when it moves.",
            "The electric field points in the direction of positive test force.",
        ]
        with pymupdf.open() as src:
            p=src.new_page()
            for i,t in enumerate(self.text):
                p.insert_text((70,95+i*65),t,fontsize=11)
            src.save(self.source)
        with pymupdf.open() as deck:
            for t in self.text:
                p=deck.new_page()
                p.insert_text((70,110),t,fontsize=11)
            deck.save(self.slides)
        self.script.write_text("".join(
            f"**Slide {i} [4s]:\n\n{text}\n\n" for i,text in enumerate(self.text,1)),
            encoding="utf-8")
        self.original={name:sha(p) for name,p in (
            ("source.pdf",self.source),("slides.pdf",self.slides),
            ("script.txt",self.script))}

    def test_readonly_plan_is_exact_source_and_block_grounded(self):
        result=inspect_text_only(source=self.source,slides=self.slides,
                                 script=self.script)
        self.assertEqual(len(result["elements"]),3)
        self.assertFalse(result["human_review_required"])
        self.assertEqual([x["elements"][0]["spoken_text"] for x in result["elements"]],
                         self.text)
        self.assertEqual([x["source_page"] for x in result["elements"]],[1,1,1])
        self.assertFalse((self.folder/"element_wav").exists())

    def test_fake_provider_produces_genuine_immutable_element_package(self):
        result=produce_element_audio(
            source=self.source,slides=self.slides,script=self.script,
            local_work_root=self.outroot,synthesizer=synth_fixture)
        self.assertEqual(result["status"],
                         "ELEMENT_AUDIO_READY_FOR_AUTOMATIC_VIDEO_STAGE")
        self.assertEqual(result["elements"],3)
        self.assertEqual(result["parts"],1)
        authored=self.folder/"element_narration_plan.json"
        audio=self.folder/"element_wav"
        verified=verify_element_tts_batch(
            source=self.source,slides=self.slides,authored=authored,audio=audio)
        self.assertEqual(verified["model"],"gemini-3.8-flash-lite-tts")
        self.assertEqual(verified["element_count"],3)
        self.assertEqual({name:sha(self.folder/name) for name in self.original},
                         self.original)
        with self.assertRaisesRegex(AutomaticElementAudioError,
                                    "never overwrite"):
            produce_element_audio(source=self.source,slides=self.slides,
                script=self.script,local_work_root=self.outroot,
                synthesizer=synth_fixture)
        self.assertEqual({name:sha(self.folder/name) for name in self.original},
                         self.original)

    def test_producer_manifest_or_pcm_modification_prevents_video(self):
        self.test_fake_provider_produces_genuine_immutable_element_package()
        record=self.folder/"element_wav"/"_producer"/"tts_input_manifest.json"
        record.write_text('{"fake":"tampered"}',encoding="utf-8")
        with self.assertRaisesRegex(ProductionRenderError,"TTS batch identity"):
            verify_element_tts_batch(
                source=self.source,slides=self.slides,
                authored=self.folder/"element_narration_plan.json",
                audio=self.folder/"element_wav")

    def test_ambiguous_source_blocks_before_paid_synthesis(self):
        original=self.text[0]
        self.script.write_text(self.script.read_text().replace(
            original,"A fictional magnetic statement absent from the PDF."),
            encoding="utf-8")
        hits=[]
        with self.assertRaises(AutomaticElementAudioError):
            produce_element_audio(source=self.source,slides=self.slides,
                script=self.script,local_work_root=self.outroot,
                synthesizer=lambda *a: hits.append(a))
        self.assertFalse(hits)
        self.assertFalse((self.folder/"element_wav").exists())

    def test_figure_slide_blocks_before_paid_synthesis(self):
        from PIL import Image
        pic=self.root/"diagram.png"
        Image.new("RGB",(100,100),(30,120,45)).save(pic)
        with pymupdf.open(self.slides) as deck:
            deck[1].insert_image(pymupdf.Rect(80,160,300,320),filename=str(pic))
            out=self.root/"new_slides.pdf"
            deck.save(out)
        out.replace(self.slides)
        hits=[]
        with self.assertRaisesRegex(AutomaticElementAudioError,"figure"):
            produce_element_audio(source=self.source,slides=self.slides,
                script=self.script,local_work_root=self.outroot,
                synthesizer=lambda *a: hits.append(a))
        self.assertFalse(hits)

    def test_producer_failure_rolls_back_only_its_own_outputs(self):
        def failure(*_):
            raise RuntimeError("synthetic Gemini queue failed")
        with self.assertRaisesRegex(RuntimeError,"synthetic Gemini queue"):
            produce_element_audio(source=self.source,slides=self.slides,
                script=self.script,local_work_root=self.outroot,
                synthesizer=failure)
        self.assertFalse((self.folder/"element_narration_plan.json").exists())
        self.assertFalse((self.folder/"element_wav").exists())
        self.assertEqual({name:sha(self.folder/name) for name in self.original},
                         self.original)
        # Retain local diagnostics for safe provider retry review.
        self.assertTrue(any(self.outroot.iterdir()))

    def test_partitioner_never_crosses_540_second_safe_limit(self):
        evidence={"source_sha256":"A","slides_sha256":"B","script_sha256":"C",
                  "elements":[{"slide":n,"elements":[{"wav":f"e{n}.wav",
                        "spoken_text":"Grounded slide element narration"}]}
                         for n in range(1,14)]}
        plan=plan_for_audio(evidence,[65.0]*13,
                            provider="gemini",
                            model="gemini-3.8-flash-lite-tts",voice="Kore")
        self.assertEqual([len(x["slides"]) for x in plan["parts"]],[8,5])

    def test_normal_video_runner_unattended_from_script_to_real_mp4(self):
        import os
        from selenium_pipeline.runner import Settings, _execute_unlocked
        before=dict(self.original)
        settings=Settings(
            source_root=self.root/"source",work_root=None,
            subchapter="8.4",from_stage="video",through_stage="video")
        with patch("selenium_pipeline.runner.verify_source_tree"),patch(
                "selenium_pipeline.runner.load_microvid_env"),patch(
                "selenium_pipeline.tts.synthesize_folder",
                side_effect=synth_fixture),patch.dict(
                os.environ,{"LOCALAPPDATA":str(self.outroot)}):
            _execute_unlocked(settings)
            # A second invocation reuses the accepted source-bound MP4, never
            # invokes the paid TTS generator or overwrites historical outputs.
            with patch("selenium_pipeline.tts.synthesize_folder",
                       side_effect=AssertionError("no additional TTS allowed")):
                _execute_unlocked(settings)
        self.assertEqual(verify_series(self.folder)["status"],
                         "accepted_synchronized_series")
        self.assertEqual({n:sha(self.folder/n) for n in before},before)
        self.assertFalse((self.folder/"lecture_human_approval.json").exists())

    def test_full_real_ffmpeg_video_from_automated_element_wavs(self):
        produce_element_audio(source=self.source,slides=self.slides,
            script=self.script,local_work_root=self.outroot,
            synthesizer=synth_fixture)
        result=render_and_install_prepared(
            source=self.source,slides=self.slides,
            authored=self.folder/"element_narration_plan.json",
            audio=self.folder/"element_wav",local_work_root=self.outroot)
        self.assertEqual(result["status"],
                         "INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO")
        self.assertEqual(verify_series(self.folder)["status"],
                         "accepted_synchronized_series")
        self.assertEqual({name:sha(self.folder/name) for name in self.original},
                         self.original)

if __name__=="__main__":
    unittest.main()
