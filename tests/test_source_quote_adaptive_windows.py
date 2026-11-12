"""Adaptive source quotation recovery is physically verified, bounded, never an AI verdict."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired, _sha
from selenium_pipeline.source_verified_quote_candidates import (
    _numeric_tokens, build_verified_source_candidates, verify_witnessed_candidate)


class AdaptiveSourceQuoteRecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name) / "original"
        self.folder.mkdir()
        self.source = self.folder / "source.pdf"
        self.slides = self.folder / "slides.pdf"
        self.script = self.folder / "script.txt"
        self.line_one = ("A sphere falling in a liquid experiences upward "
                         "resistive force opposing the downward velocity.")
        self.line_two = ("The measured time constant uses g = 980 cm/s2 "
                         "and determines how rapidly terminal speed is approached.")
        with pymupdf.open() as book:
            page = book.new_page(width=600, height=400)
            page.insert_textbox(pymupdf.Rect(50, 62, 565, 160),
                                self.line_one + "\n" + self.line_two,
                                fontsize=10, lineheight=1.1)
            book.save(self.source)
        with pymupdf.open() as slide:
            page = slide.new_page(width=600, height=400)
            page.insert_text((58, 120),
                             "We use g = 980 cm/s2 for a time constant.")
            slide.save(self.slides)
        self.script.write_text("**Slide 1 [5 sec]:\n"
                              "Using the gravitational acceleration we find "
                              "the time constant.", encoding="utf8")

    def job(self, count=1):
        return {
            "source_sha256": _sha(self.source),
            "slides_sha256": _sha(self.slides),
            "script_sha256": _sha(self.script),
            "slides": [{
                "slide": 1,
                "visual_targets": [{
                    "id": "s001.text.001",
                    "visible_text": "The time constant uses g = 980 cm/s2."}],
                "utterances": [{
                    "id": f"s001.utterance.{i:03d}",
                    "spoken_text": ("Using the gravitational acceleration "
                                    "we find the time constant."),
                    "spoken_sha256": hashlib.sha256(str(i).encode()).hexdigest(),
                    "ranked_candidates": ["s001.text.001"],
                } for i in range(1, count+1)],
            }],
        }

    def test_numerical_slide_text_can_find_original_980_line_without_numeric_speech(self):
        self.assertIn("980", _numeric_tokens("g = 980 cm/s2"))
        job = self.job()
        result = build_verified_source_candidates(folder=self.folder, job=job)
        citations = result["utterances"][0]["allowed_citations"]
        self.assertTrue(citations)
        self.assertTrue(any("980" in c["verbatim_source_quote"]
                            for c in citations))
        self.assertFalse(result["citations_are_scientific_proof"])
        self.assertFalse(result["all_mathematics_verified"])
        self.assertFalse(result["student_publication_authorized"])
        self.assertTrue(verify_witnessed_candidate(
            job={**job, "verified_source_quote_candidates_v1": result},
            utterance=job["slides"][0]["utterances"][0],
            guess={"source_page": citations[0]["source_page"],
                   "verbatim_source_quote": citations[0]["verbatim_source_quote"]},
            source_pdf=self.source))

    def test_bounded_adaptive_packet_preserves_one_proven_quote_per_utterance(self):
        job = self.job(count=20)
        result = build_verified_source_candidates(folder=self.folder, job=job)
        self.assertLessEqual(len(json.dumps(result, ensure_ascii=False)), 13000)
        self.assertEqual(len(result["utterances"]), 20)
        self.assertTrue(all(row["allowed_citations"]
                            for row in result["utterances"]))
        self.assertTrue(any(len(row["allowed_citations"]) == 1
                            for row in result["utterances"]))
        self.assertFalse(result["student_publication_authorized"])

    def test_utterance_quotations_are_not_transferable_and_source_tamper_rejected(self):
        job = self.job()
        result = build_verified_source_candidates(folder=self.folder, job=job)
        scope = {**job, "verified_source_quote_candidates_v1": result}
        unit = job["slides"][0]["utterances"][0]
        with self.assertRaises(FigureIdentityReviewRequired):
            verify_witnessed_candidate(
                job=scope, utterance=unit,
                guess={"source_page": 1,
                       "verbatim_source_quote": "A fabricated speed formula."},
                source_pdf=self.source)
        self.source.write_bytes(self.source.read_bytes() + b"\n")
        with self.assertRaises(FigureIdentityReviewRequired):
            build_verified_source_candidates(folder=self.folder, job=job)


if __name__ == "__main__":
    unittest.main()
