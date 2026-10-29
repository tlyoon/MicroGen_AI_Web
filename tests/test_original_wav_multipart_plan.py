"""Original slide WAV boundary proposals are read-only and never video QA."""
from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path

import pymupdf

from selenium_pipeline.original_wav_multipart_plan import (
    choose_contiguous_wav_parts,inspect_original_slide_wav_plan,
)
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired


class OriginalWavMultipartTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder=Path(tmp.name)

    def make(self, durations):
        with pymupdf.open() as book:
            book.new_page(width=400,height=300)
            book.save(self.folder/"source.pdf")
        with pymupdf.open() as slides:
            for _ in durations:
                slides.new_page(width=400,height=300)
            slides.save(self.folder/"slides.pdf")
        for i,dur in enumerate(durations,1):
            with wave.open(str(self.folder/f"slide{i}.wav"),"wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(100)
                f.writeframes(b"\x00\x00"*(int(dur*100)))

    def test_balanced_boundary_and_no_media_authorization(self):
        original=[42.0,120.0,160.0,170.0,140.0]
        self.make(original)
        before={p.name:p.read_bytes() for p in self.folder.iterdir()}
        receipt=inspect_original_slide_wav_plan(self.folder)
        self.assertEqual(receipt["proposed_part_count"],2)
        self.assertEqual(receipt["proposed_parts"][0]["slide_end"],3)
        self.assertEqual(receipt["proposed_parts"][1]["slide_start"],4)
        self.assertFalse(receipt["encoded_video_part_strictly_below_600_verified"])
        self.assertFalse(receipt["student_publication_authorized"])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.folder.iterdir()})

    def test_two_parts_not_one_six_hundred_second_media(self):
        self.assertEqual(choose_contiguous_wav_parts([350,310]),[(0,1),(1,2)])
        self.assertEqual(choose_contiguous_wav_parts([100]*7),[(0,3),(3,7)])

    def test_exact_540_budget_allowed_but_600_budget_rejected(self):
        self.assertEqual(choose_contiguous_wav_parts([540]),[(0,1)])
        with self.assertRaises(FigureIdentityReviewRequired):
            choose_contiguous_wav_parts([100],audio_budget_s=600)

    def test_oversize_atomic_wav_cannot_be_split(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            choose_contiguous_wav_parts([541,50])
        with self.assertRaises(FigureIdentityReviewRequired):
            choose_contiguous_wav_parts([0,20])
        with self.assertRaises(FigureIdentityReviewRequired):
            choose_contiguous_wav_parts([float("nan")])

    def test_missing_slide_number_never_produces_a_partial_plan(self):
        self.make([10,20,30])
        (self.folder/"slide2.wav").unlink()
        with self.assertRaises(FigureIdentityReviewRequired):
            inspect_original_slide_wav_plan(self.folder)

    def test_nonmatching_slide_pdf_count_blocks(self):
        self.make([10,20])
        with pymupdf.open(self.folder/"slides.pdf") as deck:
            deck.new_page(width=400,height=300)
            deck.saveIncr()
        with self.assertRaises(FigureIdentityReviewRequired):
            inspect_original_slide_wav_plan(self.folder)
