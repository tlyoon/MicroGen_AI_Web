"""Original Figure8.2 source word placement adversarial regressions."""
import os
from pathlib import Path
import unittest
from copy import deepcopy

from selenium_pipeline.original_figure82_side_word_positions import (
    verify_panel_word_positions,inspect_original_figure82_side_word_positions,
)


def source_geometry():
    rows=[]
    for idx,left in enumerate((267.535,351.535,435.534),1):
        rows.append({
            "panel_ordinal":idx,
            "all_three_triangle_edges_explicitly_witnessed":True,
            "triangle_vertex_bounds_pdf_pt":[left,507.988,left+66,555.988],
        })
    return rows


def word(a,b,c,d,text):
    return (a,b,c,d,text,10,0,0)


def real_source_word_fixture():
    # Grounded in the original immutable source PDF word-box extraction.
    return [
        word(298.113,561.0485,302.113,569.0485,"a"),
        word(336.105,527.6885,339.657,535.6885,"x"),
        word(268.569,521.0583,283.4,536.2966,'"a2'),
        word(285.4,522.0,292.0,530.5,"+"),
        word(294.,521.1,300.979,530.6,"x2"),
        word(368.033,559.4943,382.8,574.7326,'"a2'),
        word(384.8,559.5,400.443,569.0,"\u2212x2"),
        word(420.105,527.6885,423.657,535.6885,"x"),
        word(382.121,523.0165,386.121,531.0165,"a"),
        word(466.153,561.0485,470.153,569.0485,"a"),
        word(504.32,526.1973,518.7,541.4356,'"x2'),
        word(520.7,526.1973,536.332,535.7,"\u2212a2"),
        word(466.377,523.0165,469.929,531.0165,"x"),
    ]


class PrintedSideWordQA(unittest.TestCase):
    def report(self,words=None,geometry=None):
        return verify_panel_word_positions(
            real_source_word_fixture() if words is None else words,
            source_geometry() if geometry is None else geometry)

    def test_all_three_source_triangle_edge_word_positions(self):
        r=self.report()
        self.assertEqual(len(r),3)
        self.assertEqual([x["original_source_formula_label"] for x in r],
                         ["x = a tan u","x = a sin u","x = a sec u"])
        self.assertTrue(all(x["printed_labels_physically_witnessed"] for x in r))
        self.assertFalse(any(x["triangle_side_symbol_semantics_approved"]
                             or x["complete_radical_notation_proven"] for x in r))

    def test_pdf_wrong_logical_text_order_is_corrected_by_physical_word_order(self):
        rows=self.report(list(reversed(real_source_word_fixture())))
        self.assertEqual(
            rows[0]["physical_source_position_candidates"]["diagonal"]
                ["observed_pdf_word_tokens"],["a2","+","x2"])

    def test_missing_right_edge_label_fails_closed(self):
        words=[w for w in real_source_word_fixture()
               if not (w[4]=="x" and w[0]>415 and w[0]<430)]
        with self.assertRaises(ValueError):
            self.report(words=words)

    def test_wrong_radical_sign_fragment_refused(self):
        words=real_source_word_fixture()
        words=[(*w[:4],"+x2",*w[5:]) if w[4]=="\u2212x2" else w
               for w in words]
        with self.assertRaises(ValueError):
            self.report(words=words)

    def test_wrong_formula_side_location_refused(self):
        words=real_source_word_fixture()
        words=[(w[0]+50,w[1],w[2]+50,w[3],*w[4:])
               if w[4]=="\u2212a2" else w for w in words]
        with self.assertRaises(ValueError):
            self.report(words=words)

    def test_disconnected_source_tokens_refused(self):
        words=real_source_word_fixture()
        words=[(w[0]-8,w[1],w[2]-8,w[3],*w[4:])
               if w[4]=="+" else w for w in words]
        with self.assertRaises(ValueError):
            self.report(words=words)

    def test_duplicate_label_in_same_side_region_refused(self):
        words=real_source_word_fixture()
        words.append(word(341.,528.,344.,536.,"x"))
        with self.assertRaises(ValueError):
            self.report(words=words)

    def test_unverified_original_vector_geometry_refused(self):
        geometry=source_geometry()
        geometry[1]["all_three_triangle_edges_explicitly_witnessed"]=False
        with self.assertRaises(ValueError):
            self.report(geometry=geometry)

    def test_corrupted_source_triangle_bounds_refused(self):
        geometry=source_geometry()
        geometry[2]["triangle_vertex_bounds_pdf_pt"][2]+=10
        with self.assertRaises(ValueError):
            self.report(geometry=geometry)

    def test_real_immutable_original_only_on_authorized_dell(self):
        root=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not root:
            self.skipTest("Private original textbook only mounted on Dell-115")
        result=inspect_original_figure82_side_word_positions(folder=Path(root))
        self.assertEqual(result["printed_side_position_candidate_count"],3)
        self.assertTrue(result["source_pdf_radical_operator_text_not_reliable"])
        self.assertFalse(result["independent_mathematical_academic_consensus_approved"])
        self.assertFalse(result["student_publication_authorized"])


if __name__=="__main__":
    unittest.main()
