"""Synthetic audio used ONLY for fail-closed contract tests, not real media evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import wave

from selenium_pipeline.automatic_math_semantic_qa import inspect_math_semantics
from selenium_pipeline.windows_slide_audio_timing_review import (
    inspect,SlideTimingReviewBlocked)
from selenium_pipeline.tts_effective_identity import DEFAULT

class OriginalBoundTimingInspector(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.original=root/"original"
        self.original.mkdir()
        self.audio=root/"audio"
        self.audio.mkdir()
        import pymupdf
        doc=pymupdf.open()
        doc.new_page(width=600,height=400)
        doc.save(self.original/"source.pdf")
        doc.close()
        doc=pymupdf.open()
        for i in (1,2):
            pg=doc.new_page(width=600,height=400)
            pg.insert_text((60,80),f"Slide {i} explanation")
        doc.save(self.original/"slides.pdf")
        doc.close()
        self.script="**Slide 1 [3 sec]:**\n\nA short introduction.\n\n**Slide 2 [3 sec]:**\n\nA short conclusion.\n"
        (self.original/"script.txt").write_text(self.script,encoding="utf8")
        (self.original/"slides.tex").write_text("source-pinned latex content",encoding="utf8")
        result=inspect_math_semantics(
            self.script,source_sha256=self.sha(self.original/"source.pdf"))
        (self.original/"math_semantic_report.json").write_text(
            json.dumps(result),encoding="utf8")
        (self.original/"script_risk_report.json").write_text(
            json.dumps({"summary":{"blocking":0}}),encoding="utf8")
        (self.original/"script_risk_report.md").write_text("no blockers",encoding="utf8")
        (self.original/"math_semantic_repair_prompt.json").write_text("{}",encoding="utf8")
        names=("source.pdf","slides.pdf","slides.tex","script.txt",
               "script_risk_report.json","script_risk_report.md",
               "math_semantic_report.json","math_semantic_repair_prompt.json")
        for n in names:
            (self.audio/n).write_bytes((self.original/n).read_bytes())
        record={
            "status":"SOURCE_SHA_BOUND_ROUTINE_GEMINI_TTS_CANDIDATE_STAGED",
            "source_trial":str(self.original),
            "source_sha256":self.sha(self.original/"source.pdf"),
            "slides_sha256":self.sha(self.original/"slides.pdf"),
            "script_sha256":self.sha(self.original/"script.txt"),
            "model":DEFAULT["model"],"voice":DEFAULT["voice"],
            "slide_count":2,"element_highlight_semantics_verified":False,
            "student_publication_authorized":False}
        (self.audio/"source_audio_stage_manifest.json").write_text(
            json.dumps(record),encoding="utf8")
        texts=["A short introduction.","A short conclusion."]
        manifest={
            "version":2,"primary":dict(DEFAULT),
            "slides":[{
                "slide":i,"source_text":speech,"tts_text":speech,
                "provider":DEFAULT["provider"],"model":DEFAULT["model"],
                "voice":DEFAULT["voice"],"fallback_used":False}
                for i,speech in enumerate(texts,1)]}
        (self.audio/"tts_input_manifest.json").write_text(
            json.dumps(manifest),encoding="utf8")
        for i in (1,2):
            with wave.open(str(self.audio/f"slide{i}.wav"),"wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(24000)
                f.writeframes(b"\0\0"*24000)
    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    def test_valid_exact_audio_review_inspection(self):
        result=inspect(audio_folder=self.audio,original_source=self.original)
        self.assertEqual(result["parts"],[[1,2]])
        self.assertEqual(len(result["segments"]),2)
        self.assertFalse(result["per_element_sync_verified"])
        self.assertFalse(result["student_publication_authorized"])
    def test_actual_ffmpeg_review_remains_unapproved(self):
        from selenium_pipeline.windows_slide_audio_timing_review import render
        from selenium_pipeline.highlight_video_preview import ffmpeg_path
        try:
            ffmpeg_path()
        except (OSError, RuntimeError):
            self.skipTest("FFmpeg not installed on this test device")
        dest=self.audio.parent/"external_review"
        result=render(audio_folder=self.audio,
                      original_source=self.original,output_dir=dest)
        self.assertEqual(result["part_count"],1)
        self.assertFalse(result["actual_per_element_highlight_sync_verified"])
        self.assertFalse(result["student_publication_authorized"])
        self.assertFalse(result["video_production_or_release_accepted"])
        self.assertTrue((dest/result["parts"][0]["mp4_file"]).is_file())
        self.assertLess(result["parts"][0]["actual_container_duration_s"],600)
        with self.assertRaises(SlideTimingReviewBlocked):
            render(audio_folder=self.audio,
                   original_source=self.original,output_dir=dest)

    def test_missing_wav_or_changed_source_fails(self):
        (self.audio/"slide2.wav").unlink()
        with self.assertRaises(SlideTimingReviewBlocked):
            inspect(audio_folder=self.audio,original_source=self.original)
        (self.audio/"slide1.wav").write_bytes(b"not a PCM WAV")
        with self.assertRaises((SlideTimingReviewBlocked,ValueError)):
            inspect(audio_folder=self.audio,original_source=self.original)

if __name__=="__main__":
    unittest.main()
