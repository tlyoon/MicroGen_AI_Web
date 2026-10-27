"""New production-stage v2 sound-alike contract; no external API calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

from selenium_pipeline.tts_flexible_pronunciation_contract import QA_VERSION
from selenium_pipeline.tts_fidelity import (
    evaluate_slide, _rescore_result, build_report,
)
from selenium_pipeline.runner import valid


def _wav(path:Path):
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000)
        w.writeframes(b"\x01\x10" * 24000)


class RealProductionSoundAlikeQA(unittest.TestCase):
    def test_normal_slide_sounds_similar_despite_raw_wer_and_old_99_threshold(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"slide1.wav";_wav(p)
            expected="The hypotenuse is the square root and cosine u is nonnegative."
            heard="the high pot news is the square root and coast sign you is non negative"
            with patch("selenium_pipeline.tts_fidelity.inspect_audio",
                       return_value={"transcript":heard,
                                     "pronunciation_issues":[],
                                     "critical_token_issues":[],
                                     "audio_defects":[]}):
                report=evaluate_slide(1,expected,p,threshold=50)
            self.assertEqual(report["status"],"pass")
            self.assertGreaterEqual(report["tts_quality_percent"],90)
            self.assertLess(report["fidelity_percent"],99)
            self.assertTrue(report["tts_qa_phonetic_evidence"]["tts_qa_soundalike_pass"])
            self.assertFalse(report["tts_qa_phonetic_evidence"][
                "student_publication_authorized_by_this_check"])
            # Cached report must yield the SAME v2 status without another API.
            rescored=_rescore_result(report,50)
            self.assertEqual(rescored["status"],"pass")
            self.assertEqual(rescored["tts_quality_percent"],
                             report["tts_quality_percent"])

    def test_main_stage_rejects_audible_circa_even_if_other_text_similar(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"slide1.wav";_wav(p)
            with patch("selenium_pipeline.tts_fidelity.inspect_audio",
                       return_value={"transcript":"the symbol circa is constant",
                                     "pronunciation_issues":[],
                                     "critical_token_issues":[],
                                     "audio_defects":[]}):
                report=evaluate_slide(1,"The symbol c is constant.",p,threshold=50)
            self.assertEqual(report["status"],"review")
            self.assertIn("LETTER_C_INCORRECTLY_EXPANDED_TO_CIRCA",
                          report["tts_qa_phonetic_evidence"]["critical_errors"])

    def test_actual_report_v2_uses_phonetic_quality_not_old_raw_fidelity(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)
            (folder/"script.txt").write_text("**Slide 1 [1 sec]:\nThe cosine is nonnegative.",
                                             encoding="utf8")
            _wav(folder/"slide1.wav")
            with patch("selenium_pipeline.tts_fidelity.inspect_audio",
                       return_value={"transcript":"the coast sign is non negative",
                                     "pronunciation_issues":[],
                                     "critical_token_issues":[],
                                     "audio_defects":[]}), \
                 patch("selenium_pipeline.runner.slide_pages",return_value=1):
                report=build_report(folder,threshold=50)
                self.assertEqual(report["version"],2)
                self.assertEqual(report["tts_qa_policy_version"],QA_VERSION)
                self.assertEqual(report["summary"]["passed"],1)
                self.assertEqual(report["summary"]["blocking_failures"],0)
                (folder/"tts_fidelity_report.json").write_text(
                    json.dumps(report),encoding="utf8")
                self.assertTrue(valid("tts_qa",folder))
                # Forged per-slide phonetic acceptance cannot pass a mere
                # changed summary count or benign source audio label.
                report["slides"][0]["tts_qa_phonetic_evidence"][
                    "critical_errors"]=["LETTER_C_INCORRECTLY_EXPANDED_TO_CIRCA"]
                (folder/"tts_fidelity_report.json").write_text(
                    json.dumps(report),encoding="utf8")
                self.assertFalse(valid("tts_qa",folder))

    def test_v1_historical_99_percent_gate_is_not_retroactively_relaxed(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)
            legacy={"version":1,"threshold_percent":99.0,
                    "summary":{"slides":1,"passed":1,"review":0,
                               "blocking_failures":0,
                               "minimum_fidelity_percent":78.0}}
            (folder/"tts_fidelity_report.json").write_text(json.dumps(legacy))
            with patch("selenium_pipeline.runner.slide_pages",return_value=1):
                self.assertFalse(valid("tts_qa",folder))


if __name__=="__main__":
    unittest.main()
