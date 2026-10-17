"""Offline source-bound compatibility tests: slide audio is NOT element narration."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

import test_generic_element_highlight_workflow as scene_fixture
from selenium_pipeline.tts_reviewed_element_compat import (
    ElementAudioIncompatible, check,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReviewedSlideAudioCompatibilityTests(unittest.TestCase):
    def setUp(self):
        fixture = scene_fixture.GenericHighlightWorkflowTests(
            "test_valid_any_three_slide_two_part_scene_coverage")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.source = fixture.source
        self.slides = fixture.slides
        self.plan = fixture.plan
        self.audio = fixture.root / "reviewed_slide_audio"
        self.audio.mkdir()
        self.text = "This illustrates a mathematical concept on slide number."
        transcript = "\n\n".join(
            f"**Slide {n} [1 min]:\n{self.text}" for n in range(1,4))
        (self.audio/"script.txt").write_text(transcript,encoding="utf-8")
        rows = []
        hashes = {}
        for n in range(1,4):
            wav = f"slide{n}.wav"
            (self.audio/wav).write_bytes(
                (fixture.audio/f"s{n:02d}_e01.wav").read_bytes())
            hashes[wav] = sha(self.audio/wav)
            rows.append({"slide":n, "source_text":self.text,
                         "tts_text":self.text, "provider":"gemini",
                         "model":"gemini-3.8-flash-lite-tts", "voice":"Kore",
                         "fallback_used":False})
        manifest={"primary":{"provider":"gemini",
                              "model":"gemini-3.8-flash-lite-tts","voice":"Kore"},
                  "slides":rows}
        (self.audio/"tts_input_manifest.json").write_text(
            json.dumps(manifest),encoding="utf-8")
        receipt={"status":"AUDIO_REVIEWED_ISOLATED_COPY",
                 "human_review_approved":True,
                 "video_publication_approved":False,
                 "provider":"gemini","tts_model":"gemini-3.8-flash-lite-tts",
                 "voice":"Kore", "source":str(self.source.parent.resolve()),
                 "destination":str(self.audio.resolve()),
                 "source_script_sha256":sha(self.audio/"script.txt"),
                 "source_manifest_sha256":sha(self.audio/"tts_input_manifest.json"),
                 "candidate_wav_sha256":hashes}
        (self.audio/"tts_reviewed_handoff.json").write_text(
            json.dumps(receipt),encoding="utf-8")
        for part in fixture.plan_data["parts"]:
            for slide in part["slides"]:
                slide["elements"][0]["wav"] = f"slide{slide['slide']}.wav"
        fixture.save()

    def check(self):
        return check(source_pdf=self.source,slides_pdf=self.slides,
                     authored_plan=self.plan,reviewed_audio=self.audio)

    def test_single_element_per_slide_can_be_checked_read_only(self):
        before = {p.name:sha(p) for p in self.audio.iterdir()}
        result = self.check()
        self.assertEqual(result["status"],"REVIEW_ONLY_AUDIO_ELEMENT_COMPATIBILITY")
        self.assertEqual(result["matched_slide_elements"],3)
        self.assertEqual(result["parts"],2)
        self.assertFalse(result["scientific_element_mapping_approved"])
        self.assertFalse(result["production_approved"])
        self.assertFalse(result["student_published"])
        self.assertEqual(before,{p.name:sha(p) for p in self.audio.iterdir()})

    def test_multi_element_on_a_slide_is_not_mapped_from_one_wav(self):
        entry = self.fixture.plan_data["parts"][0]["slides"][0]
        extra = dict(entry["elements"][0], wav="some_other_element.wav")
        entry["elements"].append(extra)
        self.fixture.save()
        with self.assertRaisesRegex(ElementAudioIncompatible,
                                    "NOT sufficient for multiple"):
            self.check()

    def test_per_element_spoken_text_mismatch_is_rejected(self):
        self.fixture.plan_data["parts"][0]["slides"][0]["elements"][0]["spoken_text"] = (
            "This is entirely different narration with many words.")
        self.fixture.save()
        with self.assertRaisesRegex(ElementAudioIncompatible,
                                    "cannot be equated"):
            self.check()

    def test_tampered_wav_rejected_even_with_a_reviewed_receipt(self):
        (self.audio/"slide2.wav").write_bytes(
            (self.audio/"slide2.wav").read_bytes() + b"silently_changed")
        with self.assertRaisesRegex(ElementAudioIncompatible,"SHA mismatch"):
            self.check()

    def test_wrong_model_or_voice_is_not_reused(self):
        record=self.audio/"tts_reviewed_handoff.json"
        receipt=json.loads(record.read_text(encoding="utf-8"))
        receipt["voice"]="OtherVoice"
        record.write_text(json.dumps(receipt),encoding="utf-8")
        with self.assertRaisesRegex(ElementAudioIncompatible,
                                    "approval/provenance"):
            self.check()

    def test_audio_lacks_independent_review_receipt(self):
        (self.audio/"tts_reviewed_handoff.json").unlink()
        with self.assertRaisesRegex(ElementAudioIncompatible,
                                    "independently reviewed"):
            self.check()

    def test_review_audio_has_wrong_source_folder(self):
        p=self.audio/"tts_reviewed_handoff.json"
        obj=json.loads(p.read_text(encoding="utf-8"))
        obj["source"]=str(self.audio)
        p.write_text(json.dumps(obj),encoding="utf-8")
        with self.assertRaisesRegex(ElementAudioIncompatible,
                                    "source-bound"):
            self.check()

    def test_scene_source_changed_blocked_before_video_render(self):
        self.source.write_bytes(b"source changed after scene review")
        with self.assertRaisesRegex(ElementAudioIncompatible,
                                    "same source/model"):
            self.check()


if __name__ == "__main__":
    unittest.main()
