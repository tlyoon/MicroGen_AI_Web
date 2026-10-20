"""Unmatched source PDF drawing operations must not be promoted."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_unmatched_vector_operations import characterize_unmatched_drawing_objects

class UnmatchedDrawingOperationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)/"x.pdf"
        with pymupdf.open() as doc:
            page=doc.new_page(width=500,height=600)
            page.draw_line((50,60),(150,60),color=(0,0,0))
            page.draw_rect(pymupdf.Rect(50,100,140,170),color=(0,0,0))
            page.insert_text((60,115),"word",fontsize=10)
            doc.save(self.p)
        with pymupdf.open(self.p) as doc:
            page=doc[0]
            self.drawings=page.get_drawings()
            self.words=page.get_text("words")

    def test_line_and_rect_unmatched_are_only_geometry(self):
        obs=[{"drawing_index":0,"classification":"NO_NEARBY_SOURCE_FEATURES"},
             {"drawing_index":1,"classification":"NO_NEARBY_SOURCE_FEATURES"}]
        r=characterize_unmatched_drawing_objects(
            observations=obs,drawings=self.drawings,words=self.words)
        self.assertEqual(r["unmatched_object_count"],2)
        self.assertEqual(r["line_or_curve_like_count"],1)
        self.assertEqual(r["nearby_word_overlap_count"],1)
        for row in r["unmatched_source_drawings"]:
            self.assertFalse(row["missing_from_slide_proven"])
            self.assertFalse(row["original_figure_membership_proven"])

    def test_not_unmatched_is_not_reported(self):
        r=characterize_unmatched_drawing_objects(
            observations=[{"drawing_index":0,
                           "classification":"NEAR_ONE_UNVERIFIED_REGISTRATION_GROUP"}],
            drawings=self.drawings,words=self.words)
        self.assertEqual(r["unmatched_object_count"],0)

    def test_malicious_duplicate_index_is_rejected(self):
        obs=[{"drawing_index":0,"classification":"NO_NEARBY_SOURCE_FEATURES"}]*2
        with self.assertRaises(FigureIdentityReviewRequired):
            characterize_unmatched_drawing_objects(
                observations=obs,drawings=self.drawings,words=self.words)

    def test_nonexistent_index_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            characterize_unmatched_drawing_objects(
                observations=[{"drawing_index":99,
                               "classification":"NO_NEARBY_SOURCE_FEATURES"}],
                drawings=self.drawings,words=self.words)
