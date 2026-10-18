"""Real synthetic FFmpeg tests for automatic Video 00.

No paid model, OAuth, browser, YouTube uploads or original lecture material.
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.video_ffmpeg import ffmpeg_executable
from selenium_pipeline.youtube_course_publish import YouTubeCourseError, sha256
from selenium_pipeline.course_video00 import (
    plan_video00,render_video00,verify_video00,
)


class Video00Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exe=ffmpeg_executable()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.folders={}
        for topic in ("8.1","8.2","10.1"):
            parent=self.root/topic.split(".")[0]
            parent.mkdir(exist_ok=True)
            folder=parent/topic
            folder.mkdir()
            self.folders[topic]=folder
            (folder/"source.pdf").write_bytes(("Synthetic lecture "+topic).encode())
            (folder/"script.txt").write_text("**Slide 1 [16 sec]:\nSynthetic narration**",encoding="utf-8")
            (folder/"tts_input_manifest.json").write_text(json.dumps({
                "primary":{"provider":"gemini",
                           "model":"gemini-3.8-flash-lite-tts","voice":"Kore"},
                "slides":[{"slide":1,"source_text":"Synthetic narration",
                           "tts_text":"Synthetic narration","provider":"gemini",
                           "model":"gemini-3.8-flash-lite-tts","voice":"Kore",
                           "fallback_used":False}],
            }),encoding="utf-8")
            part=folder/"part_01"
            part.mkdir()
            (part/"narration_alignment.json").write_text(json.dumps({
                "events":[
                    {"start_ms":0,"end_ms":8000,"slide_id":"s1","target_id":"a"},
                    {"start_ms":9000,"end_ms":17000,"slide_id":"s1","target_id":"b"}]}))
            video=part/"part_01.mp4"
            color={"8.1":"red","8.2":"green","10.1":"blue"}[topic]
            cmd=[self.exe,"-hide_banner","-loglevel","error","-y",
                 "-f","lavfi","-i",f"color=c={color}:s=320x180:r=12:d=18",
                 "-f","lavfi","-i","sine=frequency=420:sample_rate=22050:duration=18",
                 "-c:v","libx264","-preset","ultrafast",
                 "-pix_fmt","yuv420p","-c:a","aac","-shortest",str(video)]
            proc=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
            self.assertEqual(proc.returncode,0,proc.stderr)

    def tech(self,folder):
        return {"status":"accepted_synchronized_series",
                "verification_scope":"technical_media_only",
                "parts":[{"part_id":"part_01","duration_s":18.0,
                          "highlight_events":2}]}

    def planned(self):
        with patch("selenium_pipeline.youtube_course_publish.verify_series",
                   side_effect=self.tech):
            return plan_video00(self.root,course_title="Physics Showcase")

    def test_selects_whole_events_and_representative_lessons(self):
        plan=self.planned()
        self.assertEqual(plan["duration_s"],48.0)
        self.assertEqual(len(plan["clips"]),6)
        self.assertEqual(len(plan["voice"]),3)
        self.assertEqual(set(x["topic"] for x in plan["clips"]),set(self.folders))
        self.assertTrue(all(x["duration_s"]==8.0 for x in plan["clips"]))
        self.assertFalse(plan["synthesized_narration"])
        self.assertFalse((self.root/".microgen_youtube").exists())

    def test_strict_voice_mixing_rejected(self):
        path=self.folders["8.2"]/"tts_input_manifest.json"
        data=json.loads(path.read_text())
        data["primary"]["model"]="gemini-3.8-flash-tts"
        data["slides"][0]["model"]="gemini-3.8-flash-tts"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(YouTubeCourseError,"mixed TTS"):
            self.planned()

    def test_immutable_source_audio_timing_preflight(self):
        plan=self.planned()
        video=self.folders["8.1"]/"part_01"/"part_01.mp4"
        video.write_bytes(video.read_bytes()+b"changed")
        with self.assertRaisesRegex(YouTubeCourseError,"Source video changed"):
            render_video00(plan,source_root=self.root)
        self.assertFalse((self.root/".microgen_youtube"/"trailer").exists())

    def test_change_of_source_pdf_or_tts_identity_blocks_existing_plan(self):
        plan=self.planned()
        source=self.folders["8.2"]/"source.pdf"
        source.write_bytes(source.read_bytes()+b"new")
        with self.assertRaisesRegex(YouTubeCourseError,"Source PDF changed"):
            render_video00(plan,source_root=self.root)
        source.write_bytes(b"Synthetic lecture 8.2")
        voice=self.folders["10.1"]/"tts_input_manifest.json"
        manifest=json.loads(voice.read_text(encoding="utf-8"))
        manifest["primary"]["model"]="gemini-3.8-flash-tts"
        manifest["slides"][0]["model"]="gemini-3.8-flash-tts"
        voice.write_text(json.dumps(manifest),encoding="utf-8")
        with self.assertRaisesRegex(YouTubeCourseError,"TTS identity changed"):
            render_video00(plan,source_root=self.root)

    def test_real_ffmpeg_video00_and_strict_receipt(self):
        plan=self.planned()
        # The generator must safely create its own metadata tree.
        self.assertFalse((self.root/".microgen_youtube").exists())
        receipt=render_video00(plan,source_root=self.root,ffmpeg=self.exe)
        self.assertEqual(receipt["status"],"SOURCE_BOUND_VIDEO00_VERIFIED")
        clip=self.root/".microgen_youtube"/"trailer"/"video_00.mp4"
        self.assertTrue(clip.is_file())
        self.assertTrue(45<=receipt["mp4_duration_s"]<=55)
        self.assertEqual(sha256(clip),receipt["mp4_sha256"])
        self.assertEqual(sha256(clip.parent/"title_card.jpg"),
                         receipt["title_card_sha256"])
        verify_video00(clip,source_root=self.root)
        with self.assertRaisesRegex(YouTubeCourseError,"fresh, non-symlink directory"):
            render_video00(plan,source_root=self.root,ffmpeg=self.exe)
        clip.write_bytes(clip.read_bytes()+b"tamper")
        with self.assertRaisesRegex(YouTubeCourseError,"MP4 changed"):
            verify_video00(clip,source_root=self.root)


if __name__=="__main__":
    unittest.main()
