"""Offline end-to-end reuse: bad slide -> bounded TTS -> actual audited QA -> resume.

No actual TTS/model requests: watchdog and source-aware Gemini listener are
simulated; production code still validates every PCM byte and real QA receipt.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pymupdf

from selenium_pipeline import tts_qa_repair
from selenium_pipeline import tts_qa_autonomous_recovery as auto
from selenium_pipeline import tts_auto_recovery_install as install
from selenium_pipeline.tts_flexible_pronunciation_contract import QA_VERSION
from selenium_pipeline.runner import valid
from tests.test_pcm_signal_integrity import RATE, tone, wav


MODEL = "gemini-3.8-flash-lite-tts"
QA_MODEL = "gemini-3.8-flash"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def qa_report(folder: Path, *, fail_slide: int | None = None):
    texts = ("A clear introduction.", "A correct worked example.")
    slides = []
    for i,text in enumerate(texts, 1):
        passed = i != fail_slide
        slides.append({
            "slide": i, "status": "pass" if passed else "review",
            "audio_file": f"slide{i}.wav", "ground_truth": text,
            "tts_quality_percent": 100.0 if passed else 0.0,
            "fidelity_percent": 100.0 if passed else 0.0,
            "word_error_rate": 0.0, "differences": [],
            "pronunciation_issues": [], "critical_token_issues": [],
            "audio_defects": [],
            "tts_qa_phonetic_evidence": {
                "tts_qa_soundalike_pass": passed,
                "critical_errors": [] if passed else ["test failure"]},
        })
    passed_count = 2 if fail_slide is None else 1
    return {
        "version": 2, "tts_qa_policy_version": QA_VERSION,
        "method": "test-only synthetic source-locked Gemini QA fixture",
        "model": QA_MODEL, "threshold_percent": 50.0,
        "summary": {
            "slides": 2, "passed": passed_count,
            "review": 2-passed_count, "blocking_failures": 2-passed_count,
            "mean_tts_quality_percent": 100.0 if passed_count==2 else 50.0,
            "minimum_tts_quality_percent": 100.0 if passed_count==2 else 0.0,
            "mean_fidelity_percent": 100.0 if passed_count==2 else 50.0,
            "minimum_fidelity_percent": 100.0 if passed_count==2 else 0.0,
        },
        "slides": slides,
    }


class AutomaticTTSRecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)
        script = ("**Slide 1 [10 sec]:**\nA clear introduction.\n\n"
                  "**Slide 2 [10 sec]:**\nA correct worked example.\n")
        (self.folder/"script.txt").write_text(script,encoding="utf8")
        manifest = {
            "version": 2,
            "primary": {"provider":"gemini", "model": MODEL, "voice":"Kore"},
            "slides":[{"slide": i, "source_text":txt, "tts_text":txt,
                       "provider":"gemini", "model":MODEL,
                       "voice":"Kore","fallback_used":False}
                      for i,txt in enumerate(
                          ("A clear introduction.","A correct worked example."), 1)],
        }
        (self.folder/"tts_input_manifest.json").write_text(
            json.dumps(manifest),encoding="utf8")
        with pymupdf.open() as pdf:
            pdf.new_page();pdf.new_page();pdf.save(self.folder/"slides.pdf")
        self.good = wav(tone(2,amplitude=.2))
        self.new = wav(tone(2,amplitude=.28))
        self.bad = wav([0]*RATE*2)
        (self.folder/"slide1.wav").write_bytes(self.good)
        (self.folder/"slide2.wav").write_bytes(self.bad)
        self.source_hashes = {name:digest(self.folder/name)
                              for name in ("script.txt",
                                           "tts_input_manifest.json",
                                           "slides.pdf")}

    def run_auto(self, *, repairs=2):
        return tts_qa_repair.repair(
            self.folder,model=QA_MODEL,threshold=50.0,
            provider="gemini",tts_model=MODEL,voice="Kore",
            max_repairs=repairs,auto_integrate_technical=True)

    def assert_source_unchanged(self):
        for name, prior in self.source_hashes.items():
            self.assertEqual(digest(self.folder/name),prior)

    def test_objectively_silent_slide_only_is_regenerated_then_stage_passes(self):
        requested=[]
        def synth(text, number, model, voice, **kwargs):
            requested.append((number,model,voice,kwargs.get("attempts_override")))
            return self.new
        # Broken input should skip the expensive initial Gemini audio review.
        with patch.object(auto,"_gemini_say_with_watchdog",side_effect=synth), \
             patch.object(auto,"build_report",return_value=qa_report(self.folder)):
            result=self.run_auto()
        self.assertEqual(requested,[(2,MODEL,"Kore",1)])
        self.assertEqual(result["summary"]["passed"],2)
        self.assertTrue(valid("tts_qa",self.folder))
        self.assertEqual((self.folder/"slide1.wav").read_bytes(),self.good)
        self.assertEqual((self.folder/"slide2.wav").read_bytes(),self.new)
        self.assert_source_unchanged()
        self.assertTrue((self.folder/"tts_fidelity_report.json").is_file())
        jobs=list((self.folder/install.ROOT).iterdir())
        self.assertEqual(len(jobs),1)
        receipt=json.loads((jobs[0]/"journal.json").read_text())
        self.assertEqual(receipt["status"],"COMPLETE")
        self.assertFalse(receipt["student_publication_authorized"])
        self.assertTrue(receipt["automatic_pipeline_continuation_eligible"])
        self.assertEqual((jobs[0]/"original"/"slide2.wav").read_bytes(),self.bad)
        self.assertFalse((self.folder/"slide1.wav").is_symlink())

    def test_malformed_riff_original_can_be_selectively_repaired(self):
        # Original produced a RIFF-looking corrupt stream; it is still
        # source-SHA-locked, but the healthy replacement must pass strict
        # PCM and existing phonetic QA. Standard external audio audit keeps
        # rejecting malformed originals without the dedicated repair flag.
        self.bad = b"RIFF" + b"broken WAV frames" * 7
        (self.folder/"slide2.wav").write_bytes(self.bad)
        with patch.object(auto,"_gemini_say_with_watchdog",
                          return_value=self.new) as synth, \
             patch.object(auto,"build_report",return_value=qa_report(self.folder)):
            self.run_auto()
        synth.assert_called_once()
        self.assertEqual((self.folder/"slide2.wav").read_bytes(),self.new)
        self.assertTrue(valid("tts_qa",self.folder))
        self.assertEqual(next((self.folder/install.ROOT).iterdir())
                         .joinpath("original","slide2.wav").read_bytes(),self.bad)

    def test_silent_regenerated_attempt_is_rejected_then_retried(self):
        payloads=[self.bad,self.new]
        requested=[]
        def synth(text,number,model,voice,**kw):
            requested.append(number)
            return payloads.pop(0)
        with patch.object(auto,"_gemini_say_with_watchdog",side_effect=synth), \
             patch.object(auto,"build_report",return_value=qa_report(self.folder)), \
             patch.dict("os.environ",{"MICROGEN_TTS_QA_REPAIR_DELAY_SECONDS":"0"}):
            self.run_auto()
        self.assertEqual(requested,[2,2])
        review=next((self.folder/".tts_qa_review_candidates").iterdir())
        receipt=json.loads((review/"review_only_receipt.json").read_text())
        self.assertEqual(len(receipt["rejected_attempts"]),1)
        self.assertEqual(len(receipt["proposed_replacements"]),1)
        self.assertEqual((self.folder/"slide2.wav").read_bytes(),self.new)

    def test_phonetic_failure_recycles_historical_selective_repair(self):
        # Both original WAVs are structurally healthy, but the source-bound
        # model QA rejects slide 2 for an actual pronounced wrong term.
        (self.folder/"slide2.wav").write_bytes(self.good)
        calls = []
        initial = qa_report(self.folder, fail_slide=2)
        accepted = qa_report(self.folder)
        def reviewed(path, **kwargs):
            calls.append(Path(path))
            return initial if len(calls) == 1 else accepted
        with patch.object(auto,"_gemini_say_with_watchdog",
                          return_value=self.new) as synth, \
             patch.object(auto,"build_report",side_effect=reviewed):
            result=self.run_auto()
        self.assertEqual(len(calls),2)
        self.assertEqual(calls[0],self.folder)
        self.assertNotEqual(calls[1],self.folder)
        synth.assert_called_once()
        self.assertEqual(result["summary"]["passed"],2)
        self.assertEqual((self.folder/"slide1.wav").read_bytes(),self.good)
        self.assertEqual((self.folder/"slide2.wav").read_bytes(),self.new)
        self.assertTrue(valid("tts_qa",self.folder))
        self.assert_source_unchanged()

    def test_existing_good_slide_qa_cache_is_reused_in_review_snapshot(self):
        # Existing SHA-locked QA evidence for unaffected slides is copied.
        # The real listener checks its own WAV/prompt/model/policy cache key.
        cache=self.folder/".tts_qa_cache"
        cache.mkdir()
        original=b'{"old_still_source_bound": true}'
        (cache/"slide1.json").write_bytes(original)
        inspected=[]
        def report(folder, **kwargs):
            path=Path(folder)/".tts_qa_cache"/"slide1.json"
            inspected.append(path.read_bytes() if path.exists() else None)
            return qa_report(folder)
        with patch.object(auto,"_gemini_say_with_watchdog",
                          return_value=self.new), \
             patch.object(auto,"build_report",side_effect=report):
            self.run_auto()
        self.assertEqual(inspected,[original])
        self.assertEqual((cache/"slide1.json").read_bytes(),original)

    def test_exhausted_budget_keeps_original_and_refuses_progression(self):
        requested=[]
        def synth(*args,**kwargs):
            requested.append(args[1])
            return self.bad
        with patch.object(auto,"_gemini_say_with_watchdog",side_effect=synth), \
             patch.object(auto,"build_report") as listener, \
             patch.dict("os.environ",{"MICROGEN_TTS_QA_REPAIR_DELAY_SECONDS":"0"}):
            with self.assertRaisesRegex(RuntimeError,"exhausted its finite budget"):
                self.run_auto()
            listener.assert_not_called()
        self.assertEqual(requested,[2,2])
        self.assertEqual((self.folder/"slide2.wav").read_bytes(),self.bad)
        self.assertFalse((self.folder/install.ROOT).exists())
        self.assert_source_unchanged()

    def test_crash_after_one_atomic_install_rolls_forward_without_model(self):
        original_write=install._atomic_write
        count=[0]
        def crash_after_first(path,payload):
            original_write(path,payload)
            count[0]+=1
            if count[0]==1:
                raise OSError("test injected process interruption")
        with patch.object(auto,"_gemini_say_with_watchdog",return_value=self.new), \
             patch.object(auto,"build_report",return_value=qa_report(self.folder)), \
             patch.object(install,"_atomic_write",side_effect=crash_after_first):
            with self.assertRaisesRegex(OSError,"injected"):
                self.run_auto()
        self.assertEqual((self.folder/"slide2.wav").read_bytes(),self.new)
        with patch.object(auto,"_gemini_say_with_watchdog") as synth, \
             patch.object(auto,"build_report") as listener:
            result=self.run_auto()
            synth.assert_not_called()
            listener.assert_not_called()
        self.assertEqual(result["summary"]["passed"],2)
        self.assertTrue(valid("tts_qa",self.folder))
        self.assert_source_unchanged()
        self.assertEqual(install.resume_pending(self.folder),None)

    def test_approved_candidate_is_reused_without_duplicate_provider_request(self):
        with patch.object(auto,"_gemini_say_with_watchdog",
                          return_value=self.new) as synth, \
             patch.object(auto,"build_report",
                          return_value=qa_report(self.folder)), \
             patch.object(auto,"install_verified",
                          side_effect=OSError("test interruption before install")):
            with self.assertRaisesRegex(OSError,"interruption"):
                self.run_auto()
            synth.assert_called_once()
        self.assertEqual((self.folder/"slide2.wav").read_bytes(),self.bad)
        with patch.object(auto,"_gemini_say_with_watchdog") as synth, \
             patch.object(auto,"build_report") as listener:
            result=self.run_auto()
            synth.assert_not_called()
            listener.assert_not_called()
        self.assertEqual(result["summary"]["passed"],2)
        self.assertTrue(valid("tts_qa",self.folder))
        self.assertEqual((self.folder/"slide2.wav").read_bytes(),self.new)
        self.assert_source_unchanged()

    def test_exhausted_repair_is_not_replayed_after_restart(self):
        with patch.object(auto,"_gemini_say_with_watchdog",
                          return_value=self.bad), \
             patch.dict("os.environ",{"MICROGEN_TTS_QA_REPAIR_DELAY_SECONDS":"0"}):
            with self.assertRaisesRegex(RuntimeError,"exhausted"):
                self.run_auto()
        with patch.object(auto,"_gemini_say_with_watchdog") as synth, \
             patch.object(auto,"build_report") as listener:
            with self.assertRaisesRegex(RuntimeError,"Previous identical"):
                self.run_auto()
            synth.assert_not_called()
            listener.assert_not_called()
        self.assertEqual((self.folder/"slide2.wav").read_bytes(),self.bad)

    def test_tampered_source_manifest_is_blocked_before_provider_call(self):
        doc=json.loads((self.folder/"tts_input_manifest.json").read_text())
        doc["slides"][1]["tts_text"]="wrong text"
        (self.folder/"tts_input_manifest.json").write_text(json.dumps(doc))
        with patch.object(auto,"_gemini_say_with_watchdog") as synth:
            with self.assertRaisesRegex(RuntimeError,"provenance mismatch"):
                self.run_auto()
            synth.assert_not_called()
        self.assertEqual((self.folder/"slide2.wav").read_bytes(),self.bad)

    def test_legacy_non_destructive_interface_preserved_and_runner_is_wired(self):
        from selenium_pipeline import runner
        self.assertIn("--auto-integrate-technical-repair",
                      inspect.getsource(runner._execute_unlocked))
        self.assertIn("if auto_integrate_technical:",
                      inspect.getsource(tts_qa_repair.repair))


if __name__ == "__main__":
    unittest.main()
