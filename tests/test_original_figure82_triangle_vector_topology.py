"""Adversarial checks for ORIGINAL Figure 8.2 vector triangle line topology."""
import os
from pathlib import Path
import unittest

import pymupdf

from selenium_pipeline.original_figure82_triangle_vector_topology import (
    classify_panel_segments, original_panel_line_observations,
    inspect_original_figure82_triangle_topology,
)


def panel(cx):
    left=cx-32.5;right=left+66.;top=508.;bottom=556.
    return [
        (left,bottom,right,bottom),
        (right,bottom,right,top),
        (right,top,left,bottom),
    ]


def drawing_page(*,alter=None):
    segments=[]
    for center in (300.,384.,468.):
        segments.extend(panel(center))
    if alter is not None:
        alter(segments)
    class Page:
        def get_drawings(self):
            return [{"items":[("l",pymupdf.Point(x0,y0),
                               pymupdf.Point(x1,y1))]}
                    for x0,y0,x1,y1 in segments]
    return Page()


class SourceTriangleGeometry(unittest.TestCase):
    def test_three_closed_realistic_right_angle_vector_panels(self):
        got=original_panel_line_observations(drawing_page(),
                                              (300.,384.,468.))
        self.assertEqual(len(got),3)
        self.assertTrue(all(x["explicit_axis_aligned_corner_witnessed"]
                            for x in got))
        self.assertTrue(all(x["all_three_triangle_edges_explicitly_witnessed"]
                            for x in got))
        self.assertTrue(all(x["diagonal_width_pt"]==66.
                            and x["diagonal_height_pt"]==48. for x in got))
        self.assertFalse(any(x["mathematical_right_triangle_approved"]
                             or x["side_length_label_meanings_verified"]
                             for x in got))

    def test_reverse_vector_endpoints_does_not_change_geometry(self):
        original=panel(300.)
        reversed_edges=[(x1,y1,x0,y0) for x0,y0,x1,y1 in original]
        a=classify_panel_segments(original,label_x=300.)
        b=classify_panel_segments(reversed_edges,label_x=300.)
        self.assertEqual(a,b)

    def test_missing_diagonal_fails_closed(self):
        with self.assertRaises(ValueError):
            classify_panel_segments(panel(300.)[:2],label_x=300.)

    def test_diagonal_flipped_upside_down_fails_closed(self):
        edges=panel(300.)
        lx=267.5;rx=333.5
        edges[-1]=(lx,508.,rx,556.)
        with self.assertRaises(ValueError):
            classify_panel_segments(edges,label_x=300.)

    def test_wrong_diagonal_dimensions_fail_closed(self):
        edges=panel(300.)
        edges[-1]=(333.5,505.,267.5,556.)
        with self.assertRaises(ValueError):
            classify_panel_segments(edges,label_x=300.)

    def test_disjoint_legs_do_not_make_a_right_angle_corner(self):
        edges=panel(300.)
        edges[0]=(267.5,559.,333.5,559.)
        with self.assertRaises(ValueError):
            classify_panel_segments(edges,label_x=300.)

    def test_extra_duplicated_vector_segment_refused(self):
        edges=panel(300.)
        edges.append(edges[0])
        with self.assertRaises(ValueError):
            classify_panel_segments(edges,label_x=300.)

    def test_one_incomplete_panel_reports_missing_corner_without_approval(self):
        edges=panel(300.)[1:]
        result=classify_panel_segments(edges,label_x=300.)
        self.assertFalse(result["all_three_triangle_edges_explicitly_witnessed"])
        self.assertFalse(result["mathematical_right_triangle_approved"])

    def test_real_original_source_requires_authorized_mount(self):
        source=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not source:
            self.skipTest("Real original textbook only mounted on authorized Dell-115")
        got=inspect_original_figure82_triangle_topology(folder=Path(source))
        self.assertEqual(got["triangle_vector_candidate_count"],3)
        self.assertEqual(got["complete_explicit_three_edge_panel_count"],3)
        self.assertTrue(got["all_three_triangle_geometries_explicitly_verified"])
        self.assertTrue(got["source_to_slide_pixel_similarity_verified"])
        self.assertFalse(got["independent_source_academic_consensus_verified"])
        self.assertFalse(got["student_publication_authorized"])


if __name__=="__main__":
    unittest.main()
