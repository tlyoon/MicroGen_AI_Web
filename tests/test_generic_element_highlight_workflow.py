"""Generic highlight contract tests, not tied to Thomas Calculus 8.4."""
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import pymupdf
from selenium_pipeline.element_highlight_workflow import (
    HighlightReviewGateError, source_bound_plan, review, verify_rendered,
)
from selenium_pipeline.runner import Settings, _execute_unlocked


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GenericHighlightWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.root=root
        self.source_folder=root/"source"/"8"/"8.4"
        self.source_folder.mkdir(parents=True)
        self.source=self.source_folder/"source.pdf"
        self.slides=self.source_folder/"slides.pdf"
        for target in (self.source,self.slides):
            doc=pymupdf.open()
            for i in range(3 if target==self.slides else 1):
                page=doc.new_page()
                page.insert_text((70,100),f"Mathematical concept slide {i+1}")
            doc.save(target)
            doc.close()
        self.audio=root/"frozen_audio";self.audio.mkdir()
        self.plan=root/"author_plan.json"
        self.output=root/"review_run"
        parts=[]
        for partnumber,slide_numbers in ((1,[1,2]),(2,[3])):
            entries=[]
            for i in slide_numbers:
                name=f"s{i:02d}_e01.wav"
                with wave.open(str(self.audio/name),"wb") as w:
                    w.setnchannels(1);w.setsampwidth(2)
                    w.setframerate(24000)
                    w.writeframes(b"\x10\x11"*24000)
                entries.append({"slide":i,"source_page":1,
                    "source_evidence":"Mathematical concept slide 1",
                    "elements":[{"anchor":{"type":"text_block","index":0,
                                           "text_evidence":f"Mathematical concept slide {i}"},
                                 "wav":name,
                                 "spoken_text":"This illustrates a mathematical concept on slide number."}]})
            parts.append({"part_id":f"part_{partnumber:02d}","slides":entries})
        self.plan_data={"schema_version":1,
            "status":"author_specified_unapproved_element_narration",
            "source_sha256":sha(self.source),"slides_sha256":sha(self.slides),
            "voice_id":"gemini_gemini-3.8-flash-lite-tts_Kore_REVIEW_ONLY",
            "parts":parts}
        self.save()

    def save(self):
        self.plan.write_text(json.dumps(self.plan_data),encoding="utf8")

    def preflight(self):
        return source_bound_plan(source=self.source,slides=self.slides,
                                 plan=self.plan,audio=self.audio)

    def test_valid_any_three_slide_two_part_scene_coverage(self):
        result=self.preflight()
        self.assertEqual(result["slides"],3)
        self.assertEqual(result["parts"],2)
        self.assertEqual(result["elements"],3)
        self.assertEqual(result["part_audio_s"],[2,1])

    def test_missing_slide_fails_closed(self):
        self.plan_data["parts"][0]["slides"].pop(0);self.save()
        with self.assertRaisesRegex(HighlightReviewGateError,"cover every slide"):
            self.preflight()

    def test_repeated_slide_fails_closed(self):
        self.plan_data["parts"][1]["slides"][0]["slide"]=2;self.save()
        with self.assertRaisesRegex(HighlightReviewGateError,"cover every slide"):
            self.preflight()

    def test_missing_element_anchor_fails_closed(self):
        self.plan_data["parts"][0]["slides"][0]["elements"][0].pop("anchor")
        self.save()
        with self.assertRaisesRegex(HighlightReviewGateError,"no source-linked"):
            self.preflight()

    def test_missing_real_wav_fails_closed(self):
        (self.audio/"s01_e01.wav").unlink()
        with self.assertRaisesRegex(HighlightReviewGateError,"audio missing"):
            self.preflight()

    def test_changed_source_sha_fails_closed(self):
        self.source.write_bytes(b"different textbook content")
        with self.assertRaisesRegex(HighlightReviewGateError,"Stale"):
            self.preflight()

    def test_no_preflight_write_to_source(self):
        before={p.name:sha(p) for p in self.source_folder.iterdir()}
        self.preflight()
        self.assertEqual(before,{p.name:sha(p) for p in self.source_folder.iterdir()})
        self.assertFalse(self.output.exists())

    def test_review_refuses_published_destination_without_side_effects(self):
        existing=self.source_folder/"historical"
        existing.mkdir()
        marker=existing/"marker.txt";marker.write_text("preserve")
        with self.assertRaisesRegex(HighlightReviewGateError,"Never overwrite"):
            review(source=self.source,slides=self.slides,authored=self.plan,
                   audio=self.audio,output_root=existing)
        self.assertEqual(marker.read_text(),"preserve")

    def test_actual_three_slide_mp4_has_one_decoded_highlight_per_audio(self):
        """Real FFmpeg/encoded-pixel test on a non-Thomas 3-slide lecture."""
        from selenium_pipeline.highlight_video_preview import ffmpeg_path
        try:
            ffmpeg_path()
        except Exception as exc:
            self.skipTest("No FFmpeg executable: " + str(exc))
        source_before=sha(self.source)
        slide_before=sha(self.slides)
        audio_before={p.name:sha(p) for p in self.audio.iterdir()}
        result=review(source=self.source,slides=self.slides,authored=self.plan,
                      audio=self.audio,output_root=self.output)
        self.assertEqual(result["covered_slides"],3)
        self.assertEqual(result["covered_elements"],3)
        self.assertEqual(len(result["parts"]),2)
        self.assertEqual([x["narrated_highlight_events"] for x in result["parts"]],[2,1])
        self.assertTrue(all(x["encoded_pixels_rechecked"] for x in result["parts"]))
        self.assertTrue(all(x["encoded_duration_s"]<600 for x in result["parts"]))
        self.assertFalse(result["production_approved"])
        self.assertFalse(result["student_published"])
        self.assertFalse((self.output/"lecture_completion.json").exists())
        self.assertEqual(source_before,sha(self.source))
        self.assertEqual(slide_before,sha(self.slides))
        self.assertEqual(audio_before,{p.name:sha(p) for p in self.audio.iterdir()})
        with self.assertRaisesRegex(HighlightReviewGateError,"Never overwrite"):
            review(source=self.source,slides=self.slides,authored=self.plan,
                   audio=self.audio,output_root=self.output)

    def test_count_only_pixel_verification_is_forbidden(self):
        with self.assertRaisesRegex(HighlightReviewGateError,"pixel verification is mandatory"):
            verify_rendered(source=self.source,slides=self.slides,
                            authored=self.plan,audio=self.audio,
                            staged=self.root/"absent_stage",
                            rendered=self.root/"absent_render",
                            output=self.root/"never_allowed.json",
                            recheck_pixels=False)
        self.assertFalse((self.root/"never_allowed.json").exists())

    def test_runner_routes_video_stage_to_isolated_review_only(self):
        settings=Settings(source_root=self.root/"source",work_root=None,
                          subchapter="8.4",from_stage="video",through_stage="video",
                          element_plan=self.plan,element_audio=self.audio,
                          element_slides=self.slides,element_review_root=self.output)
        # Even a historical published MP4 cannot be overwritten by this route.
        old_video=self.source_folder/"slides.mp4"
        old_video.write_bytes(b"historic lecture remains unchanged")
        with patch("selenium_pipeline.runner.verify_source_tree"), patch(
             "selenium_pipeline.element_highlight_workflow.review") as fake:
            fake.return_value={"covered_slides":3,"covered_elements":3}
            ret=_execute_unlocked(settings)
        self.assertEqual(ret,self.output)
        self.assertEqual(old_video.read_bytes(),b"historic lecture remains unchanged")
        self.assertFalse(self.output.exists())
        fake.assert_called_once()

    def test_runner_refuses_missing_or_partial_highlight_inputs(self):
        settings=Settings(source_root=self.root/"source",work_root=None,
                          subchapter="8.4",from_stage="video",through_stage="video",
                          element_plan=self.plan)
        with self.assertRaisesRegex(ValueError,"requires all plan/audio/output"):
            _execute_unlocked(settings)
        self.assertFalse(self.output.exists())

    def test_runner_cannot_use_review_to_bypass_standard_stages(self):
        settings=Settings(source_root=self.root/"source",work_root=None,
                          subchapter="8.4",from_stage="figures",
                          through_stage="video",element_plan=self.plan,
                          element_audio=self.audio,element_review_root=self.output)
        with self.assertRaisesRegex(ValueError,"--from-stage video"):
            _execute_unlocked(settings)


if __name__=="__main__":
    unittest.main()
