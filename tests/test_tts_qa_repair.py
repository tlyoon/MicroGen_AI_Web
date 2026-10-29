"""Standard-library offline tests for non-destructive TTS QA repair proposals."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline import tts_qa_repair


def seed_provenance(folder: Path, texts, *, model="gemini-3.8-flash-lite-tts",
                    provider="gemini", voice="Kore"):
    data = {
        "version": 2,
        "primary": {"provider": provider, "model": model, "voice": voice},
        "slides": [
            {"slide": number, "source_text": text, "tts_text": text,
             "provider": provider, "model": model, "voice": voice,
             "fallback_used": False}
            for number, text in texts
        ],
    }
    (folder / "tts_input_manifest.json").write_text(json.dumps(data), encoding="utf-8")


class NonDestructiveTTSRepairTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)

    def run_repair(self, **changes):
        args=dict(folder=self.folder, model="flash", threshold=99,
                  provider="gemini", tts_model="gemini-3.8-flash-lite-tts",
                  voice="Kore")
        args.update(changes)
        return tts_qa_repair.repair(**args)

    def create_script_and_wavs(self, lines):
        script="\n\n".join(
            f"**Slide {i} [1 min]:\n{text}" for i,text in lines)
        (self.folder/"script.txt").write_text(script,encoding="utf-8")
        seed_provenance(self.folder,lines)
        for i,_ in lines:
            (self.folder/f"slide{i}.wav").write_bytes(
                b"RIFF"+bytes([i])*64)

    def test_select_only_nonpassing_slides(self):
        self.assertEqual(
            tts_qa_repair.failing_slides({"slides":[
                {"slide":1,"status":"pass"},
                {"slide":2,"status":"review"},
                {"slide":3,"status":"pass"}]}),[2])

    def test_proposed_repair_never_modifies_originals_or_publishes(self):
        self.create_script_and_wavs([(1,"Good."),(2,"Bad.")])
        before={i:(self.folder/f"slide{i}.wav").read_bytes() for i in (1,2)}
        checked=[]
        proposed=[]
        def fake_report(folder, **kwargs):
            checked.append(folder)
            return {"slides":[
                {"slide":1,"status":"pass"},
                {"slide":2,"status":"review" if len(checked)==1 else "pass"}]}
        def synth(*args):
            proposed.append(args)
            return b"RIFF"+b"z"*64
        with patch.object(tts_qa_repair,"build_report",side_effect=fake_report), \
             patch.object(tts_qa_repair,"write_report"), \
             patch.object(tts_qa_repair,"_gemini_say_with_watchdog",
                          side_effect=synth):
            with self.assertRaisesRegex(RuntimeError,"requires independent review"):
                self.run_repair()
        self.assertEqual(len(proposed),1)
        self.assertEqual(len(checked),2)
        self.assertEqual(checked[0],self.folder)
        review=checked[1]
        self.assertNotEqual(review,self.folder)
        self.assertEqual((review/"slide1.wav").read_bytes(),before[1])
        self.assertEqual((review/"slide2.wav").read_bytes(),b"RIFF"+b"z"*64)
        self.assertEqual((review/"attempt1_slide2.wav").read_bytes(),b"RIFF"+b"z"*64)
        for i in (1,2):
            self.assertEqual((self.folder/f"slide{i}.wav").read_bytes(),before[i])
        receipt=json.loads((review/"review_only_receipt.json").read_text())
        self.assertEqual(receipt["status"],"REVIEW_ONLY_UNPUBLISHED")
        self.assertFalse(receipt["original_audio_modified"])
        self.assertFalse(receipt["academic_approved"])
        self.assertFalse(receipt["video_publication_approved"])
        self.assertEqual(len(receipt["proposed_replacements"]),1)
        self.assertFalse((self.folder/".tts.lock").exists())

    def test_exhausted_repair_keeps_every_attempt_and_original_audio(self):
        self.create_script_and_wavs([(1,"Bad.")])
        original=(self.folder/"slide1.wav").read_bytes()
        with patch.object(tts_qa_repair,"build_report",
                 return_value={"slides":[{"slide":1,"status":"review"}]}), \
             patch.object(tts_qa_repair,"write_report"), \
             patch.object(tts_qa_repair,"_gemini_say_with_watchdog",
                          return_value=b"RIFF"+b"b"*64), \
             patch.dict("os.environ",{"MICROGEN_TTS_QA_REPAIR_DELAY_SECONDS":"0"}):
            with self.assertRaisesRegex(RuntimeError,"still blocked"):
                self.run_repair(max_repairs=2)
        self.assertEqual((self.folder/"slide1.wav").read_bytes(),original)
        roots=list((self.folder/".tts_qa_review_candidates").iterdir())
        self.assertEqual(len(roots),1)
        self.assertTrue((roots[0]/"attempt1_slide1.wav").exists())
        self.assertTrue((roots[0]/"attempt2_slide1.wav").exists())
        receipt=json.loads((roots[0]/"review_only_receipt.json").read_text())
        self.assertEqual(receipt["proposed_remaining_failures"],[1])
        self.assertFalse(receipt["original_audio_modified"])

    def test_mismatched_narration_blocks_before_synthesis(self):
        self.create_script_and_wavs([(1,"Correct.")])
        seed_provenance(self.folder,[(1,"Different narration.")])
        original=(self.folder/"slide1.wav").read_bytes()
        with patch.object(tts_qa_repair,"build_report",
                 return_value={"slides":[{"slide":1,"status":"review"}]}), \
             patch.object(tts_qa_repair,"write_report"), \
             patch.object(tts_qa_repair,"_gemini_say_with_watchdog") as synth:
            with self.assertRaisesRegex(RuntimeError,"provenance mismatch"):
                self.run_repair()
            synth.assert_not_called()
        self.assertEqual((self.folder/"slide1.wav").read_bytes(),original)
        self.assertFalse((self.folder/".tts_qa_review_candidates").exists())

    def test_other_model_voice_provider_fail_closed(self):
        self.create_script_and_wavs([(1,"Text.")])
        with patch.object(tts_qa_repair,"build_report",
                 return_value={"slides":[{"slide":1,"status":"review"}]}), \
             patch.object(tts_qa_repair,"write_report"), \
             patch.object(tts_qa_repair,"_gemini_say_with_watchdog") as synth:
            for changes in (
                {"provider":"chirp3"},
                {"voice":"Other"},
                {"tts_model":"gemini-3.8-flash-tts"},
            ):
                with self.subTest(changes=changes):
                    with self.assertRaisesRegex(
                            RuntimeError,"provider/model/voice"):
                        self.run_repair(**changes)
            synth.assert_not_called()
        self.assertFalse((self.folder/".tts_qa_review_candidates").exists())

    def test_passing_original_needs_no_repair(self):
        self.create_script_and_wavs([(1,"Good.")])
        original=(self.folder/"slide1.wav").read_bytes()
        with patch.object(tts_qa_repair,"build_report",
                 return_value={"slides":[{"slide":1,"status":"pass"}]}), \
             patch.object(tts_qa_repair,"write_report"), \
             patch.object(tts_qa_repair,"_gemini_say_with_watchdog") as synth:
            result=self.run_repair()
            synth.assert_not_called()
        self.assertEqual(result["slides"][0]["status"],"pass")
        self.assertEqual((self.folder/"slide1.wav").read_bytes(),original)
        self.assertFalse((self.folder/".tts_qa_review_candidates").exists())


if __name__ == "__main__":
    unittest.main()
