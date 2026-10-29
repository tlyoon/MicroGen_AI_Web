"""Adversarial source Figure 8.2 printed label order and raster-candidate matching."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.original_figure82_source_label_order import (
    inspect_original_figure82_label_order, source_diagram_labels,
)


def make_source(root,*,names=("tan","sin","sec"),with_caption=True,
                second_marker=True):
    with pymupdf.open() as pdf:
        page=pdf.new_page(width=612,height=782)
        if second_marker:
            page.insert_text((390,462),"FIGURE 8.2",fontsize=10)
        for x,name in zip((282,366,450),names):
            page.insert_text((x,579),"x = a "+name+" u",fontsize=9)
        if with_caption:
            page.insert_text((266,610),"FIGURE 8.2",fontsize=9)
            page.insert_text((324,611),
                             "Reference triangles for the three basic substitutions",fontsize=9)
        pdf.save(root/"source.pdf")
    (root/"slides.pdf").write_bytes(b"immutable slide PDF fixture")
    (root/"script.txt").write_text("immutable narration")
    return tuple(_sha(root/p) for p in ("source.pdf","slides.pdf","script.txt"))


def mock_gutters(hashes):
    return {
        "status":"VERTICAL_GUTTER_STRIP_PROPOSALS_ONLY",
        "original_source_sha256":hashes[0],
        "original_slides_sha256":hashes[1],
        "original_script_sha256":hashes[2],
        "candidate_strips":[{
            "candidate_index":i,
            "right_triangle_semantics_verified":False,
            "candidate_slide_bbox_pdf_pt":[float(i),2.0,float(i+1),4.0],
            "panel_native_pixel_sha256":f"{i:064x}",
        } for i in range(1,4)],
    }


class Figure82SourceLabelOrderTests(unittest.TestCase):
    def test_three_label_source_printing_has_exact_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); make_source(root)
            with pymupdf.open(root/"source.pdf") as pdf:
                row=source_diagram_labels(page=pdf[0])
            self.assertEqual(row["printed_label_count"],3)
            self.assertEqual(
                [r["source_label_formula"] for r in row["printed_formula_labels"]],
                ["x = a tan u","x = a sin u","x = a sec u"])
            self.assertFalse(row["author_intended_triangle_semantics_verified"])

    def test_label_order_swapped_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); make_source(root,names=("sin","tan","sec"))
            with pymupdf.open(root/"source.pdf") as pdf:
                with self.assertRaises(ValueError):
                    source_diagram_labels(page=pdf[0])

    def test_missing_formula_label_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); make_source(root,names=("tan","sin"))
            with pymupdf.open(root/"source.pdf") as pdf:
                with self.assertRaises(ValueError):
                    source_diagram_labels(page=pdf[0])

    def test_missing_descriptive_caption_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); make_source(root,with_caption=False)
            with pymupdf.open(root/"source.pdf") as pdf:
                with self.assertRaises(ValueError):
                    source_diagram_labels(page=pdf[0])

    def test_missing_second_figure_marker_cannot_be_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); make_source(root,second_marker=False)
            with pymupdf.open(root/"source.pdf") as pdf:
                with self.assertRaises(ValueError):
                    source_diagram_labels(page=pdf[0])

    def test_exact_source_and_slide_candidate_provenance_without_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); hashes=make_source(root)
            pilot={
                "original_source_sha256":hashes[0],
                "original_slides_sha256":hashes[1],
                "original_script_sha256":hashes[2],
            }
            with patch("selenium_pipeline.original_figure82_source_label_order."
                       "inspect_original_three_formula_source",return_value=pilot),patch(
                       "selenium_pipeline.original_figure82_source_label_order."
                       "inspect_original_composite_gutters",return_value=mock_gutters(hashes)),patch(
                       "selenium_pipeline.original_figure82_source_label_order."
                       "prove_source_quote_occurrence",return_value={
                           "quote_occurrences":1,
                           "quote_sha256":"a"*64,
                           "status":"EXACT_ORIGINAL_PDF_PAGE_QUOTE_PRESENT",
                       }):
                report=inspect_original_figure82_label_order(folder=root)
            self.assertEqual(report["printed_label_count"],3)
            self.assertEqual(report["candidate_slide_strips_count"],3)
            self.assertFalse(report["source_to_slide_pixel_equivalence_verified"])
            self.assertFalse(report["independent_math_consensus_verified"])
            self.assertFalse(report["student_publication_authorized"])
            self.assertEqual([x["source_printed_label"] for x in report["ordered_review_candidates"]],
                             ["x = a tan u","x = a sin u","x = a sec u"])

    def test_original_source_hash_divergence_stops_visual_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); hashes=make_source(root)
            wrong={
                "original_source_sha256":"0"*64,
                "original_slides_sha256":hashes[1],
                "original_script_sha256":hashes[2],
            }
            with patch("selenium_pipeline.original_figure82_source_label_order."
                       "inspect_original_three_formula_source",return_value=wrong),patch(
                       "selenium_pipeline.original_figure82_source_label_order."
                       "inspect_original_composite_gutters",return_value=mock_gutters(hashes)):
                with self.assertRaises(ValueError):
                    inspect_original_figure82_label_order(folder=root)


if __name__=="__main__":
    unittest.main()
