"""Fail-closed original speech -> distinct Figure8.2 strip *candidates*."""
import os
from copy import deepcopy
from pathlib import Path
import unittest

from selenium_pipeline.original_slide4_figure_highlight_candidates import (
    propose_original_triangle_mentions,inspect_original_slide4_highlight_candidates,
)


def fixture():
    utterances=[
        {"id":f"s004.utterance.{i:03d}",
         "spoken_sha256":f"{i:064x}","spoken_text":speech}
        for i,speech in enumerate((
            "These geometric substitutions correspond to the reference triangles.",
            "When x equals a tangent u, the opposite leg is x.",
            "For sine, the opposite leg is x.",
            "For secant, x is the hypotenuse.",
            "The principal square root requires attention to absolute values."
        ),1)]
    left=48.421
    cut=[left,126.4618,208.4046,314.4101]
    strips=[
        {
            "candidate_index":i,
            "candidate_slide_bbox_pdf_pt":[cut[i-1],91.9534,cut[i],179.099],
            "panel_native_pixel_sha256":f"{i:064x}",
        } for i in (1,2,3)]
    labels=["x = a tan u","x = a sin u","x = a sec u"]
    return utterances,strips,labels


class SourceBoundSlide4HighlightCandidates(unittest.TestCase):
    def evaluate(self,utterances=None,strips=None,labels=None,size=(400.,300.)):
        raw=fixture()
        return propose_original_triangle_mentions(
            utterances=raw[0] if utterances is None else utterances,
            rectangles=raw[1] if strips is None else strips,
            source_formulas=raw[2] if labels is None else labels,
            slide_size=size)

    def test_three_distinct_figure_candidates_two_explicit_abstentions(self):
        report=self.evaluate()
        self.assertEqual(report["original_utterance_count"],5)
        self.assertEqual(report["proposed_figure_region_utterance_count"],3)
        self.assertEqual(report["unmapped_original_utterance_count"],2)
        self.assertEqual([r["candidate_panel_id"] for r in report["utterance_candidates"]],
                         [None,"s004.figure82.strip.001","s004.figure82.strip.002",
                          "s004.figure82.strip.003",None])
        self.assertTrue(all(r["speaking_start_s"] is None
                            and r["speaking_end_s"] is None
                            and not r["speech_to_visual_sync_verified"]
                            for r in report["utterance_candidates"]))
        self.assertFalse(report["all_utterances_highlightable"])
        self.assertFalse(report["student_publication_authorized"])

    def test_missing_reordered_or_duplicated_original_units_refused(self):
        raw=fixture()
        for changed in (raw[0][:-1],
                        [raw[0][1],raw[0][0],*raw[0][2:]],
                        [*raw[0][:-1],raw[0][-2]]):
            with self.assertRaises(ValueError):
                self.evaluate(utterances=changed)

    def test_ambiguous_competing_trig_words_refused(self):
        units=fixture()[0]
        units[1]["spoken_text"]="The tangent and sine substitutions."
        with self.assertRaises(ValueError):
            self.evaluate(utterances=units)

    def test_changed_phrase_or_missing_unique_math_word_refused(self):
        units=fixture()[0]
        units[2]["spoken_text"]="For cosine, the hypotenuse is a."
        with self.assertRaises(ValueError):
            self.evaluate(utterances=units)

    def test_duplicate_specific_trig_word_refused(self):
        units=fixture()[0]
        units[3]["spoken_text"]="For secant, secant is repeated twice."
        with self.assertRaises(ValueError):
            self.evaluate(utterances=units)

    def test_changed_printed_textbook_panel_order_refused(self):
        labels=fixture()[2]
        labels[1],labels[2]=labels[2],labels[1]
        with self.assertRaises(ValueError):
            self.evaluate(labels=labels)

    def test_duplicate_or_missing_native_image_strip_refused(self):
        for bad in (fixture()[1][:2],
                    [*fixture()[1][:2],fixture()[1][1]]):
            with self.assertRaises(ValueError):
                self.evaluate(strips=bad)

    def test_empty_or_invalid_source_strip_hash_refused(self):
        strips=fixture()[1]
        strips[1]["panel_native_pixel_sha256"]="not-a-real-sha"
        with self.assertRaises(ValueError):
            self.evaluate(strips=strips)

    def test_overlapping_or_noncontiguous_figures_refused(self):
        strips=fixture()[1]
        strips[1]["candidate_slide_bbox_pdf_pt"][0]-=15
        with self.assertRaises(ValueError):
            self.evaluate(strips=strips)

    def test_out_of_page_or_corrupted_target_geometry_refused(self):
        with self.assertRaises(ValueError):
            self.evaluate(size=(180.,300.))
        strips=fixture()[1]
        strips[0]["candidate_slide_bbox_pdf_pt"][2]=strips[0]["candidate_slide_bbox_pdf_pt"][0]
        with self.assertRaises(ValueError):
            self.evaluate(strips=strips)

    def test_untrusted_original_utterance_sha_rejected(self):
        units=fixture()[0]
        units[4]["spoken_sha256"]="0000"
        with self.assertRaises(ValueError):
            self.evaluate(utterances=units)

    def test_real_original_source_only_on_authorized_pc(self):
        root=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not root:
            self.skipTest("Original textbook and slides only on authorized Dell-115")
        report=inspect_original_slide4_highlight_candidates(folder=Path(root))
        self.assertEqual(report["original_utterance_count"],5)
        self.assertEqual(report["proposed_figure_region_utterance_count"],3)
        self.assertEqual(report["unmapped_original_utterance_count"],2)
        self.assertEqual(report["source_figure_radical_glyph_verified"] if
                         "source_figure_radical_glyph_verified" in report else False,False)
        self.assertFalse(report["original_encoded_highlighted_mp4_verified"])
        self.assertFalse(report["student_publication_authorized"])


if __name__=="__main__":
    unittest.main()
