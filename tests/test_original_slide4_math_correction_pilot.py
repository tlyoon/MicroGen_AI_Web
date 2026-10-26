"""Real original Slide-4 math correction pilot; no academic/media self-approval."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import unittest
from selenium_pipeline.original_slide4_math_correction_pilot import (
    exact_math_counterexamples,prepare_corrected_original_slide4,
)

class OriginalSlide4MathCorrections(unittest.TestCase):
    def root(self):
        directory=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not directory:
            self.skipTest("Genuine Thomas 8.4 source available only on authorized Dell")
        return Path(directory)

    def test_exact_counterexamples_and_sign_lemmas(self):
        result=exact_math_counterexamples()
        self.assertTrue(result["narration_claim_all_angles_acute_refuted"])
        self.assertEqual(result["conditional_principal_root_forms_verified"],3)
        self.assertEqual([x["x"] for x in result["exact_counterexamples"]],["-2","-1"])
        self.assertFalse(result["independent_academic_model_consensus_approved"])
        self.assertFalse(result["student_release_authorized"])

    def test_absent_original_source_fails_closed(self):
        with self.assertRaises((ValueError,FileNotFoundError)):
            prepare_corrected_original_slide4(folder=Path("Z:/no-original-thomas8.4"))

    def test_real_immutable_original_five_corrections(self):
        root=self.root()
        protected={f:hashlib.sha256((root/f).read_bytes()).hexdigest()
                   for f in ("source.pdf","slides.pdf","script.txt","slide4.wav")}
        candidate=prepare_corrected_original_slide4(folder=root)
        self.assertEqual(candidate["original_utterances"],5)
        self.assertEqual(candidate["exact_original_source_quote_count"],10)
        self.assertTrue(candidate["new_audio_required"])
        self.assertEqual(len(candidate["corrected_utterances"]),5)
        for unit in candidate["corrected_utterances"]:
            self.assertNotEqual(unit["old_narration"].strip(),
                                unit["revised_narration"].strip())
            self.assertEqual(hashlib.sha256(
                unit["revised_narration"].encode("utf-8")).hexdigest(),
                             unit["revised_text_sha256"])
            self.assertFalse(unit["new_same_voice_TTS_wav_received"])
            self.assertFalse(unit["synchronized_highlight_media_accepted"])
        self.assertFalse(candidate["corrected_mathematics_independently_ai_approved"])
        self.assertFalse(candidate["student_publication_authorized"])
        self.assertEqual(protected,{f:hashlib.sha256((root/f).read_bytes()).hexdigest()
                                  for f in protected})
if __name__=="__main__":
    unittest.main()
