"""The ordinary math-element route must recover 4-8 PDF fraction glyph blocks.

No semantic equation proof, timestamp, model send, file overwrite or TTS is
inferred by recovering an original physically anchored visual rectangle.
"""
from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.sourcebound_math_row_focus import (
    MathRowBlocked, math_row_rect, discover_math_rows, digest)
from selenium_pipeline.element_narration_stage import rectangle, ElementStageError
from selenium_pipeline.scene_candidate_authoring import draft
from selenium_pipeline.rich_element_mapping_checkpoint import (
    ElementMappingCheckpointBlocked, require_automatic_mapping_or_checkpoint)
from selenium_pipeline.rich_element_model_alignment import request_for_slide


# Eight deliberately separate text blocks with the geometry of genuine
# numerator / denominator / radical-glyph PDF fragments, not eight words
# hallucinated by a model.
EIGHT = [
    (80.5, 127.7, 109.6, 146, "R = 1"),
    (104.1, 127.7, 164.6, 153.5, "2 DAv2 = 1"),
    (159.1, 142.6, 164.6, 153.5, "2"),
    (167.6, 119.7, 198.6, 138.6, "2mg"),
    (176.8, 141.4, 202.1, 156.7, "vT2 A"),
    (203.3, 119.7, 286.0, 146, "= mg (v"),
    (277.9, 142.6, 288.7, 154.6, "vT"),
    (291.4, 124.7, 303.7, 138.5, ")2"),
]


class OriginalBlockGeometryPage:
    rect = pymupdf.Rect(0, 0, 400, 300)

    def __init__(self, items):
        self.items = items

    def get_text(self, mode):
        assert mode == "blocks"
        return [(x0, y0, x1, y1, text, i, 0)
                for i, (x0, y0, x1, y1, text) in enumerate(self.items)]


class SourceboundMathRowRecoveryTests(unittest.TestCase):
    def test_eight_physically_adjacent_fragment_glyphs_are_one_candidate(self):
        page = OriginalBlockGeometryPage(EIGHT)
        rows = discover_math_rows(page, 12, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["anchor"]["indices"], list(range(8)))
        self.assertTrue(rows[0]["mathematical_equivalence_proof_required"])
        self.assertFalse(rows[0]["narration_timing_verified"])
        rect, kind = rectangle(page, rows[0]["anchor"])
        self.assertEqual(kind, "text")
        self.assertTrue(page.rect.contains(rect))
        self.assertAlmostEqual(rect.x0, 80.5)
        self.assertAlmostEqual(rect.x1, 303.7, places=2)

    def test_glyph_tamper_or_cross_column_gap_fails_closed(self):
        page = OriginalBlockGeometryPage(EIGHT)
        anchor = discover_math_rows(page, 12, [])[0]["anchor"]
        corrupted = dict(anchor, text_sha256=[digest("NOT THIS GLYPH")] +
                         anchor["text_sha256"][1:])
        with self.assertRaisesRegex(MathRowBlocked, "hash or geometry"):
            math_row_rect(page, corrupted)
        moved = [*EIGHT]
        x0, y0, x1, y1, text = moved[4]
        moved[4] = (x0 + 100, y0, x1 + 100, y1, text)
        with self.assertRaises(MathRowBlocked):
            math_row_rect(OriginalBlockGeometryPage(moved), anchor)
        with self.assertRaises(ElementStageError):
            rectangle(page, corrupted)

    def test_unrelated_distant_equations_are_never_combined(self):
        items = [(44, 85, 133, 103, "x = sin theta"),
                 (45, 205, 140, 225, "x = tan theta")]
        self.assertEqual(discover_math_rows(OriginalBlockGeometryPage(items),
                                            1, []), [])

    def test_authentic_pdf_draft_preserves_external_review_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "source" / "6.4"
            folder.mkdir(parents=True)
            source = folder / "source.pdf"
            slides = folder / "slides.pdf"
            script = folder / "script.txt"
            with pymupdf.open() as pdf:
                pg = pdf.new_page(width=420, height=350)
                pg.insert_text((60, 85), "A resistive force acts on a moving object.")
                pdf.save(source)
            with pymupdf.open() as pdf:
                pg = pdf.new_page(width=420, height=350)
                pg.insert_text((50, 77), "We compute the ratio of force and speed.")
                pg.insert_text((120, 143), "R = 1", fontsize=12)
                pg.insert_text((158, 154), "2 DAv2", fontsize=12)
                pg.draw_line((70, 200), (245, 220))
                pdf.save(slides)
            script.write_text(
                "**Slide 1 [13 sec]:\nThe expression gives the force for an object.",
                encoding="utf8")
            originals = [x.read_bytes() for x in (source, slides, script)]
            candidate = draft(source, slides)
            self.assertFalse(candidate["automatic_approval"])
            for t in candidate["slides"][0]["targets"]:
                if t["type"] == "math_row_group":
                    self.assertFalse(t["narration_timing_verified"])
                    with pymupdf.open(slides) as pdf:
                        rectangle(pdf[0], t["anchor"])
            review = root / "independent"
            review.mkdir()
            with self.assertRaises(ElementMappingCheckpointBlocked):
                require_automatic_mapping_or_checkpoint(
                    source=source, slides=slides, script=script,
                    checkpoint_root=review)
            checkpoint = next(review.glob("rich_element_map_*"))
            req = request_for_slide(
                source_folder=folder, checkpoint=checkpoint, slide_number=1)
            self.assertFalse(req["audio_generation_authorized"])
            self.assertFalse(req["student_publication_authorized"])
            self.assertEqual([x.read_bytes() for x in (source, slides, script)],
                             originals)


if __name__ == "__main__":
    unittest.main()
