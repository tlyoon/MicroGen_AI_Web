"""Adversarial original-WAV highlight event provenance and replay tests."""
from __future__ import annotations
import json
import struct
import tempfile
import unittest
import wave
from pathlib import Path
import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.original_multipart_review_encode import stage_original_multipart_review
from selenium_pipeline.original_audio_element_reconciliation import (
    parse_original_review_timeline, verify_full_staged_element_coverage,
    summarize_source_bound_tts_repair,
)


class ElementReconciliationTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.orig=self.root/"original"
        self.orig.mkdir()
        self.out=self.root/"staged"
        with pymupdf.open() as source:
            source.new_page(width=400,height=300)
            source.save(self.orig/"source.pdf")
        with pymupdf.open() as deck:
            for i in range(2):
                page=deck.new_page(width=400,height=300)
                page.insert_text((30,80),f"First narrated element {i}")
                page.insert_text((30,155),f"Second narrated element {i}")
            deck.save(self.orig/"slides.pdf")
        for i in (1,2):
            hz=24000
            pcm=[800]*int(hz*1.0)+[0]*int(hz*.45)+[900]*int(hz*1.0)
            with wave.open(str(self.orig/f"slide{i}.wav"),"wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(hz)
                out.writeframes(struct.pack(f"<{len(pcm)}h",*pcm))

    def stage(self):
        return stage_original_multipart_review(folder=self.orig,output=self.out)

    def test_all_actual_mp4_pixels_are_checked_without_forged_speech_acceptance(self):
        self.stage()
        result=verify_full_staged_element_coverage(
            original=self.orig,staged=self.out)
        self.assertEqual(result["verified_original_slide_count"],2)
        self.assertEqual(result["total_provisional_highlight_events"],
                         result["all_events_encoded_pixel_recheck_count"])
        self.assertFalse(result["audio_to_element_semantic_correspondence_verified"])
        self.assertFalse(result["technical_production_approved"])
        self.assertFalse(result["student_publication_authorized"])

    def test_broken_concatenation_or_outside_reference_is_rejected(self):
        self.stage()
        manifest=self.out/"part_01"/"frames.ffconcat"
        old=manifest.read_text()
        manifest.write_text(old.replace("highlight_001.png","highlight_999.png",1))
        with self.assertRaises(FigureIdentityReviewRequired):
            verify_full_staged_element_coverage(
                original=self.orig,staged=self.out,check_all_pixels=False)
        manifest.write_text(old)
        data=parse_original_review_timeline(
            manifest,self.out/"part_01"/"reference_frames")
        self.assertGreaterEqual(len(data),2)

    def test_missing_event_or_forged_event_duration_rejected(self):
        self.stage()
        path=self.out/"part_01"/"frames.ffconcat"
        data=path.read_text()
        path.write_text(data.replace("duration ","duration 700",1))
        with self.assertRaises(FigureIdentityReviewRequired):
            verify_full_staged_element_coverage(
                original=self.orig,staged=self.out,check_all_pixels=False)

    def test_replaced_staged_reference_is_detected_from_original_pdf(self):
        self.stage()
        image=next((self.out/"part_01"/"reference_frames").rglob("highlight_*.png"))
        from PIL import Image
        with Image.open(image) as picture:
            rendered=picture.convert("RGB")
        rendered.putpixel((1,1),(0,0,0))
        rendered.save(image)
        with self.assertRaises(FigureIdentityReviewRequired):
            verify_full_staged_element_coverage(
                original=self.orig,staged=self.out,check_all_pixels=True)

    def test_source_draft_repair_queue_never_fakes_tts_authorization(self):
        self.stage()
        report=verify_full_staged_element_coverage(
            original=self.orig,staged=self.out,check_all_pixels=False)
        draft={
            "status":"REVIEW_REQUIRED_NOT_TTS_READY",
            "can_stage_or_synthesize_audio":False,
            "source_sha256":report["source_sha256"],
            "slides_sha256":report["slides_sha256"],
            "script_sha256":"a"*64,
            "slide_count":2,"utterance_count":2,
            "candidate_target_count":2,"ambiguous_utterance_count":1,
            "slides":[{
                "slide_number":i,
                "proposed_utterances":[{
                    "mapping_ambiguous":i==1,
                    "spoken_word_fidelity_verified":False,
                    "approved_for_tts":False}],
                "figure_panel_review_required":False,
                "auto_candidate_targets":[{"kind":"text_block"}],
            } for i in (1,2)],
        }
        result=summarize_source_bound_tts_repair(media=report,draft=draft)
        self.assertEqual(result["unresolved_utterance_visual_target_mappings"],1)
        self.assertFalse(result["unreviewed_auto_tts_execution_authorized"])
        self.assertFalse(result["student_publication_authorized"])
        forged={**draft,"source_sha256":"0"*64}
        with self.assertRaises(FigureIdentityReviewRequired):
            summarize_source_bound_tts_repair(media=report,draft=forged)

    def test_sourced_pcm_does_not_count_as_verified_element_spoken_text(self):
        self.stage()
        a=verify_full_staged_element_coverage(
            original=self.orig,staged=self.out,check_all_pixels=False)
        self.assertEqual(a["all_events_encoded_pixel_recheck_count"],0)
        self.assertTrue(a["per_element_tts_or_manual_speech_alignment_needed"])
        self.assertTrue(all(not x["speech_semantic_alignment_verified"]
                            for p in a["parts"] for x in p["slide_repair_worklist"]))
