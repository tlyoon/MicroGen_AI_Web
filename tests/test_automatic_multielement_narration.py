"""Exact source-grounded multiple narrated text elements per slide.

No semantic figure guessing, paid TTS, browser or YouTube activity.
Uses actual synthetic PDFs and decoded synchronized FFmpeg video.
"""
from __future__ import annotations
import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from selenium_pipeline.automatic_element_narration import (
    inspect_text_only, plan_for_audio, AutomaticElementAudioError,
    verify_automatic_source_mapping,
)
from selenium_pipeline.automatic_element_audio_stage import produce_element_audio
from selenium_pipeline.sourcebound_production_video import (
    verify_element_tts_batch, render_and_install_prepared,
)
from selenium_pipeline.production_video_contract import verify_series
from tests.test_automatic_element_audio_stage import (
    ElementAutomaticTests, synth_fixture, sha,
)


class MultipleElementTests(unittest.TestCase):
    """Reuse the real PDFs and mocked TTS from the previous PR's fixture."""

    def setUp(self):
        self.fixture=ElementAutomaticTests("test_readonly_plan_is_exact_source_and_block_grounded")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        for name in ("root","folder","source","slides","script","outroot","text","original"):
            setattr(self,name,getattr(self.fixture,name))
        self.paragraphs=[
            ("The magnetic field strength is measured in tesla.",
             "The magnetic field direction follows the right hand rule."),
            ("Electric field lines point away from positive charges.",
             "Electric potential energy changes as charges move."),
            ("An induced current opposes the change in magnetic flux.",
             "Faraday law predicts the magnitude of induced voltage."),
        ]
        with pymupdf.open() as textbook:
            page=textbook.new_page()
            for slide_no,parts in enumerate(self.paragraphs):
                for elem_no,text in enumerate(parts):
                    page.insert_text((70,90+slide_no*125+elem_no*42),
                                     text,fontsize=11)
            textbook.save(self.root/"source_new.pdf")
        (self.root/"source_new.pdf").replace(self.source)
        with pymupdf.open() as deck:
            for parts in self.paragraphs:
                page=deck.new_page()
                for elem_no,text in enumerate(parts):
                    page.insert_text((70,110+elem_no*52),text,fontsize=11)
            deck.save(self.root/"slide_new.pdf")
        (self.root/"slide_new.pdf").replace(self.slides)
        self.script.write_text("".join(
            f"**Slide {n} [8s]:\n\n{a}\n\n{b}\n\n"
            for n,(a,b) in enumerate(self.paragraphs,1)),encoding="utf-8")
        self.original={n:sha(p) for n,p in (
            ("source.pdf",self.source),("slides.pdf",self.slides),
            ("script.txt",self.script))}

    def test_exact_multiple_distinct_blocks_no_writes(self):
        evidence=inspect_text_only(
            source=self.source,slides=self.slides,script=self.script)
        self.assertEqual([len(s["elements"]) for s in evidence["elements"]],
                         [2,2,2])
        self.assertEqual(
            [[x["wav"] for x in slide["elements"]]
             for slide in evidence["elements"]],
            [["s001_e01.wav","s001_e02.wav"],
             ["s002_e01.wav","s002_e02.wav"],
             ["s003_e01.wav","s003_e02.wav"]])
        self.assertEqual(
            [[x["anchor"]["index"] for x in slide["elements"]]
             for slide in evidence["elements"]],
            [[0,1],[0,1],[0,1]])
        self.assertFalse((self.folder/"element_wav").exists())
        plan=plan_for_audio(evidence,[1.0]*6,
                provider="gemini",model="gemini-3.8-flash-lite-tts",
                voice="Kore")
        self.assertEqual(len(plan["parts"]),1)
        verify_automatic_source_mapping(
            source=self.source,slides=self.slides,plan=plan)

    def test_full_real_ffmpeg_six_highlight_elements(self):
        produced=produce_element_audio(
            source=self.source,slides=self.slides,script=self.script,
            local_work_root=self.outroot,synthesizer=synth_fixture)
        self.assertEqual(produced["elements"],6)
        plan=self.folder/"element_narration_plan.json"
        audio=self.folder/"element_wav"
        manifest=verify_element_tts_batch(
            source=self.source,slides=self.slides,authored=plan,audio=audio)
        self.assertEqual(manifest["element_count"],6)
        installed=render_and_install_prepared(
            source=self.source,slides=self.slides,authored=plan,
            audio=audio,local_work_root=self.outroot)
        self.assertEqual(installed["status"],
                         "INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO")
        proof=verify_series(self.folder)
        self.assertEqual(proof["status"],"accepted_synchronized_series")
        self.assertEqual(len(proof["parts"]),1)
        self.assertEqual({n:sha(self.folder/n) for n in self.original},
                         self.original)

    def test_reverse_element_order_rejected_before_tts(self):
        self.script.write_text(self.script.read_text().replace(
            "\n\n"+self.paragraphs[0][0]+"\n\n"+self.paragraphs[0][1],
            "\n\n"+self.paragraphs[0][1]+"\n\n"+self.paragraphs[0][0]),
            encoding="utf-8")
        sent=[]
        with self.assertRaises(AutomaticElementAudioError):
            produce_element_audio(source=self.source,slides=self.slides,
                script=self.script,local_work_root=self.outroot,
                synthesizer=lambda *args:sent.append(args))
        self.assertFalse(sent)

    def test_duplicate_rendered_paragraph_rejected(self):
        with pymupdf.open(self.slides) as deck:
            deck[0].insert_text((70,250),self.paragraphs[0][0],fontsize=11)
            tmp=self.root/"duplicate.pdf"
            deck.save(tmp)
        tmp.replace(self.slides)
        with self.assertRaisesRegex(AutomaticElementAudioError,"ambiguous"):
            inspect_text_only(source=self.source,slides=self.slides,
                              script=self.script)

    def test_unsupported_figure_blocks_before_any_paid_tts(self):
        from PIL import Image
        image=self.root/"figure.png"
        Image.new("RGB",(120,120),(30,120,45)).save(image)
        with pymupdf.open(self.slides) as deck:
            deck[1].insert_image(pymupdf.Rect(260,280,430,420),
                                 filename=str(image))
            tmp=self.root/"withfigure.pdf"
            deck.save(tmp)
        tmp.replace(self.slides)
        used=[]
        with self.assertRaisesRegex(AutomaticElementAudioError,"figure"):
            produce_element_audio(source=self.source,slides=self.slides,
                script=self.script,local_work_root=self.outroot,
                synthesizer=lambda *args:used.append(args))
        self.assertEqual(used,[])

    def test_vector_only_figure_rejected_before_paid_tts(self):
        with pymupdf.open(self.slides) as deck:
            page=deck[1]
            shape=page.new_shape()
            shape.draw_rect(pymupdf.Rect(260,280,440,405))
            shape.finish(color=(0,0,0), fill=(.9,.9,.9))
            shape.commit()
            tmp=self.root/"vector-figure.pdf"
            deck.save(tmp)
        tmp.replace(self.slides)
        sent=[]
        with self.assertRaisesRegex(AutomaticElementAudioError,"figure/vector"):
            produce_element_audio(source=self.source,slides=self.slides,
                script=self.script,local_work_root=self.outroot,
                synthesizer=lambda *args:sent.append(args))
        self.assertFalse(sent)

    def test_same_source_paragraph_repeated_on_two_pages_rejected(self):
        with pymupdf.open(self.source) as original:
            extra=original.new_page()
            for slide_no,parts in enumerate(self.paragraphs):
                for elem_no,text in enumerate(parts):
                    extra.insert_text((70,90+slide_no*125+elem_no*42),
                                      text,fontsize=11)
            tmp=self.root/"duplicate-source.pdf"
            original.save(tmp)
        tmp.replace(self.source)
        with self.assertRaisesRegex(AutomaticElementAudioError,"unique textbook page"):
            inspect_text_only(source=self.source,slides=self.slides,
                              script=self.script)

    def test_one_slide_audio_exceeding_safe_540_seconds_rejected(self):
        evidence=inspect_text_only(
            source=self.source,slides=self.slides,script=self.script)
        # 12 real elements at 50s each would exceed safe single-slide budget.
        evidence["elements"][0]["elements"]=evidence["elements"][0]["elements"]*6
        with self.assertRaisesRegex(AutomaticElementAudioError,"single slide exceeds"):
            plan_for_audio(evidence,[50.0]*12+[1.0]*4,
                provider="gemini",model="gemini-3.8-flash-lite-tts",voice="Kore")

    def test_source_mutation_invalidates_mapping(self):
        evidence=inspect_text_only(
            source=self.source,slides=self.slides,script=self.script)
        plan=plan_for_audio(evidence,[1.0]*6,
                provider="gemini",model="gemini-3.8-flash-lite-tts",voice="Kore")
        with pymupdf.open(self.source) as original:
            original[0].insert_text((70,570),"New unrelated factual statement.")
            tmp=self.root/"modified.pdf"
            original.save(tmp)
        tmp.replace(self.source)
        with self.assertRaises(AutomaticElementAudioError):
            verify_automatic_source_mapping(
                source=self.source,slides=self.slides,plan=plan)
