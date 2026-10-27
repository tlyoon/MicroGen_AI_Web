"""Fail-closed original-media word-timed PDF-element evidence, no remote ASR."""
from __future__ import annotations
import tempfile
from pathlib import Path
import unittest
from selenium_pipeline.original_thomas84_offline_word_pdf_timing import (
    normalize,tokenize_reference_sentences,real_word_anchor_candidates,
    source_ranked_target_candidates,original_audio_pdf_timing_worklist,
)


class RealOriginalWordToPDFCandidates(unittest.TestCase):
    def test_real_audio_words_produce_measured_not_evenly_split_segments(self):
        expected="For tangent, u is positive. The hypotenuse is nonnegative."
        units,tokens=tokenize_reference_sentences(expected)
        self.assertEqual(len(units),2)
        recognized=[
            {"word":"for","start":1.5,"end":1.8},
            {"word":"tangent","start":1.9,"end":2.3},
            {"word":"you","start":2.4,"end":2.7},
            {"word":"is","start":2.8,"end":2.9},
            {"word":"positive","start":3.1,"end":3.6},
            {"word":"the","start":7.3,"end":7.7},
            {"word":"hypotenuse","start":8.8,"end":9.2},
            {"word":"is","start":9.6,"end":9.9},
            {"word":"nonnegative","start":10.7,"end":11.2},
        ]
        rows=real_word_anchor_candidates(tokens,recognized,units)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["first_matched_real_audio_second"],1.5)
        self.assertEqual(rows[1]["first_matched_real_audio_second"],7.3)
        self.assertEqual(rows[1]["last_matched_real_audio_second"],11.2)
        self.assertFalse(any(x["real_speech_to_source_element_semantics_verified"]
                             for x in rows))

    def test_no_real_vosk_audio_anchors_means_no_fake_timing(self):
        units,words=tokenize_reference_sentences(
            "A square root requires a positive quantity.")
        result=real_word_anchor_candidates(words,[],units)[0]
        self.assertIsNone(result["first_matched_real_audio_second"])
        self.assertIsNone(result["last_matched_real_audio_second"])
        self.assertFalse(result["word_timing_hypothesis_available"])

    def test_distinct_math_signs_not_normalized_away(self):
        self.assertNotEqual(normalize("negative"),normalize("nonnegative"))
        self.assertNotEqual(normalize("plus"),normalize("minus"))

    def test_pdf_candidate_lexical_overlap_is_not_semantic_approval(self):
        speech={
            "mapping_ambiguous":False,
            "candidate_target_rankings_unverified":[
                {"draft_element_id":"a","overlap_hint":0.90},
                {"draft_element_id":"b","overlap_hint":0.30},
            ]}
        targets={x:{"draft_element_id":x,
                    "rendered_rect_pt":[12,30,200,70],
                    "visible_text":text,
                    "panel_identity_review_required":False,
                    "author_reviewed":False,
                    "source_evidence_verified":False}
                 for x,text in (("a","Tangent is positive"),
                                ("b","Sine is negative"))}
        result=source_ranked_target_candidates(speech,targets)
        self.assertEqual(result["top_visual_id_only_candidate"],"a")
        self.assertFalse(result["source_semantic_speech_element_match_proven"])
        self.assertFalse(result["academic_mathematics_approved"])

    def test_missing_original_model_never_creates_approved_timeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            out=root/"would_be_report.json"
            with self.assertRaises((ValueError,FileNotFoundError)):
                original_audio_pdf_timing_worklist(
                    original=root/"missing",model_dir=root/"model",output_receipt=out)
            self.assertFalse(out.exists())


if __name__=="__main__":
    unittest.main()
