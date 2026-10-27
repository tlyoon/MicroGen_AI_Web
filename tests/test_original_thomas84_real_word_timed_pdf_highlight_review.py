"""Source-PCM-exact, actual acoustic four-PDF-highlight REVIEW rendering tests."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
import wave
from selenium_pipeline.original_thomas84_real_word_timed_pdf_highlight_review import (
    EXPECTED_REAL_CANDIDATES,
    actual_word_timed_pdf_targets,
    exact_original_pcm_word_splits,
    _write_pcm_window,
    encode_provisional_two_part_real_original_highlights,
)


class ActualAcousticPDFReview(unittest.TestCase):
    def real_inputs(self):
        source=os.getenv("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        audit=os.getenv("MICROGEN_ASR_16_ORIGINAL_WAVS_EVIDENCE")
        if not source or not audit:
            self.skipTest("Authoritative original Thomas8.4 WAV/ASR only on Dell")
        return Path(source),Path(audit)

    def test_provisional_four_does_not_claim_semantic_approval(self):
        source,audit=self.real_inputs()
        before={name:hashlib.sha256((source/name).read_bytes()).hexdigest()
                for name in ("source.pdf","slides.pdf","script.txt",
                             "slides.mp4","slide4.wav")}
        targets=actual_word_timed_pdf_targets(original=source,receipt=audit)
        self.assertEqual(set(targets),set(EXPECTED_REAL_CANDIDATES))
        for slide,candidate in targets.items():
            with self.subTest(slide=slide):
                self.assertFalse(candidate["source_semantic_approval"])
                self.assertGreaterEqual(candidate["actual_anchored_word_fraction"],.7)
                self.assertGreater(candidate["real_vosk_last_word_s"],
                                   candidate["real_vosk_first_word_s"])
        self.assertEqual(before,{
            name:hashlib.sha256((source/name).read_bytes()).hexdigest()
            for name in before})

    def test_real_pcm_splits_sum_to_exacts_not_rounded_fabrications(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"historical.wav"
            original=b"".join((i%65536).to_bytes(
                2,byteorder="little",signed=False) for i in range(24000*7))
            with wave.open(str(source),"wb") as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000)
                w.writeframes(original)
            orig,sections=exact_original_pcm_word_splits(
                wav=source,begin_s=1.13,end_s=4.79)
            self.assertEqual(orig,original)
            self.assertEqual(len(sections),3)
            self.assertEqual(sum(len(s["source_pcm_bytes"]) for s in sections),
                             len(original))
            self.assertEqual(sections[1]["source_first_pcm_sample"],
                             round(1.13*24000))
            self.assertEqual(sections[1]["source_last_pcm_sample_exclusive"],
                             round(4.79*24000))
            self.assertEqual(sum(s["highlight_provisional_PDF_target"]
                                 for s in sections),1)
            rejoined=b""
            for i,section in enumerate(sections):
                p=Path(temp)/f"part{i}.wav"
                _write_pcm_window(path=p,content=section["source_pcm_bytes"])
                with wave.open(str(p),"rb") as reader:
                    rejoined+=reader.readframes(reader.getnframes())
            self.assertEqual(rejoined,original)

    def test_30ms_intro_is_bounded_pcm_lead_not_fake_timebin(self):
        with tempfile.TemporaryDirectory() as temp:
            wav=Path(temp)/"original.wav"
            with wave.open(str(wav),"wb") as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000)
                w.writeframes(b"\x01\x10"*24000*5)
            data,segments=exact_original_pcm_word_splits(
                wav=wav,begin_s=.03,end_s=1.4)
            self.assertEqual(len(segments),2)
            self.assertTrue(segments[0]["highlight_provisional_PDF_target"])
            self.assertEqual(segments[0]["source_first_pcm_sample"],0)
            self.assertEqual(b"".join(s["source_pcm_bytes"] for s in segments),
                             data)

    def test_bad_sample_timing_fails_without_any_output(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"original.wav"
            with wave.open(str(p),"wb") as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000)
                wav.writeframes(b"\0\0"*24000)
            with self.assertRaisesRegex(ValueError,"inside actual original"):
                exact_original_pcm_word_splits(wav=p,begin_s=0.9,end_s=2.1)
            forbidden=Path(temp)/"not_created"
            with self.assertRaises(ValueError):
                encode_provisional_two_part_real_original_highlights(
                    original=Path(temp)/"missing",
                    bundle=Path(temp)/"missing_bundle",
                    audio_dir=Path(temp)/"missing_audio",
                    timing_receipt=Path(temp)/"missing_asr_receipt",
                    out=forbidden)
            self.assertFalse(forbidden.exists())


if __name__=="__main__":
    unittest.main()
