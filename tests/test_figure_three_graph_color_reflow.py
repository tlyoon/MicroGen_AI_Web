"""Real vertical-to-horizontal textbook graph reflow with adversarial edits."""
from __future__ import annotations

import math
import unittest
import pytest
cv2 = pytest.importorskip("cv2", reason="optional OpenCV figure QA dependency")
np = pytest.importorskip("numpy", reason="optional array figure QA dependency")

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_three_graph_color_reflow import (
    compare_reflowed_graph_color_shapes, _shape_difference, _runs,
)


class ThreeGraphReflowTests(unittest.TestCase):
    def panel(self, number):
        p=np.full((100,120,3),255,dtype=np.uint8)
        cv2.line(p,(8,50),(112,50),(0,0,0),1)
        cv2.line(p,(60,8),(60,92),(0,0,0),1)
        blue=(0,173,239)
        red=(236,24,70)
        if number==0:
            for x in range(12,109):
                y=int(50-29*math.atan((x-60)/17)/(math.pi/2))
                cv2.circle(p,(x,y),1,blue,-1)
            cv2.line(p,(8,18),(112,18),red,1)
            cv2.line(p,(8,82),(112,82),red,1)
        elif number==1:
            for x in range(22,99):
                y=int(50-32*math.asin((x-60)/40)/(math.pi/2))
                cv2.circle(p,(x,y),1,blue,-1)
        else:
            for x in range(10,57):
                y=int(22+28*(1-(x-10)/46)**2)
                cv2.circle(p,(x,y),1,blue,-1)
            for x in range(65,112):
                y=int(82-28*((x-65)/46)**2)
                cv2.circle(p,(x,y),1,blue,-1)
            cv2.line(p,(8,52),(112,52),red,1)
        return p

    def fixture(self, order=(0,1,2), erase_blue=None, erase_red=None):
        source=np.full((365,180,3),255,dtype=np.uint8)
        target=np.full((115,450,3),255,dtype=np.uint8)
        for i in range(3):
            source[12+i*120:112+i*120,30:150]=self.panel(i)
            copied=self.panel(order[i])
            if i==erase_blue:
                blue=(copied[:,:,2]>copied[:,:,0]+100) & (
                    copied[:,:,0]<100)
                copied[blue]=(255,255,255)
            if i==erase_red:
                red=(copied[:,:,0]>150)&(copied[:,:,1]<80)
                copied[red]=(255,255,255)
            target[8:108,10+i*150:130+i*150]=copied
        return source,target

    def check(self, source, target):
        return compare_reflowed_graph_color_shapes(
            source,target,source_bounds=(0,365,25,155),
            slide_bounds=(0,450))

    def test_three_matching_reflowed_curves_pass_but_not_semantics(self):
        r=self.check(*self.fixture())
        self.assertEqual(r["original_vertical_graph_run_count"],3, r)
        self.assertEqual(r["slide_horizontal_graph_run_count"],3)
        self.assertTrue(r["three_graph_curve_shape_sequence_coherent"])
        self.assertTrue(r["three_graph_black_ink_geometry_plausible"])
        self.assertEqual(len(r["graph_correspondence_evidence"]),3)
        for name in ("original_complete_axes_labels_legend_certified",
                     "full_source_figure_equivalence_certified",
                     "scientific_math_review_certified",
                     "video_or_publication_authorized"):
            self.assertFalse(r[name])

    def test_swapped_incompatible_graphs_fail(self):
        r=self.check(*self.fixture(order=(1,0,2)))
        self.assertFalse(r["three_graph_curve_shape_sequence_coherent"])

    def test_removed_blue_curve_fails(self):
        r=self.check(*self.fixture(erase_blue=1))
        self.assertFalse(r["three_graph_curve_shape_sequence_coherent"])

    def test_removed_red_asymptote_fails(self):
        r=self.check(*self.fixture(erase_red=2))
        self.assertFalse(r["three_graph_curve_shape_sequence_coherent"])

    def test_missing_entire_third_graph_fails(self):
        source,target=self.fixture()
        target[:,305:]=255
        r=self.check(source,target)
        self.assertEqual(r["slide_horizontal_graph_run_count"],2)
        self.assertFalse(r["three_graph_curve_shape_sequence_coherent"])

    def test_erasing_black_axes_does_not_create_semantic_approval(self):
        source,target=self.fixture()
        black=(target.max(axis=2)<80)
        target[black]=255
        result=self.check(source,target)
        self.assertTrue(result["three_graph_curve_shape_sequence_coherent"])
        self.assertIsNone(result["graph_correspondence_evidence"][0][
            "black_axes_and_label_ink_shape_diagnostic"])
        self.assertFalse(result["three_graph_black_ink_geometry_plausible"])
        self.assertEqual(result["status"], "THREE_GRAPH_BLACK_INK_INCOMPLETE_REVIEW_REQUIRED")
        self.assertFalse(result["original_complete_axes_labels_legend_certified"])
        self.assertFalse(result["video_or_publication_authorized"])

    def test_two_to_six_original_graphs_support_different_panel_counts(self):
        for count in range(2,7):
            with self.subTest(count=count):
                original=np.full((count*125+20,180,3),255,dtype=np.uint8)
                slide=np.full((115,count*150+5,3),255,dtype=np.uint8)
                for i in range(count):
                    panel=self.panel(i%3)
                    original[10+i*125:110+i*125,30:150]=panel
                    slide[8:108,10+i*150:130+i*150]=panel
                report=compare_reflowed_graph_color_shapes(
                    original,slide,source_bounds=(0,original.shape[0],25,155),
                    slide_bounds=(0,slide.shape[1]))
                self.assertEqual(report["detected_graph_count"],count)
                self.assertTrue(report["three_graph_curve_shape_sequence_coherent"])
                self.assertTrue(report["three_graph_black_ink_geometry_plausible"])
                self.assertFalse(report["video_or_publication_authorized"])

    def test_seven_graphs_are_not_promoted_as_supported_layout(self):
        count=7
        original=np.full((count*125+20,180,3),255,dtype=np.uint8)
        slide=np.full((115,count*150+5,3),255,dtype=np.uint8)
        for i in range(count):
            panel=self.panel(i%3)
            original[10+i*125:110+i*125,30:150]=panel
            slide[8:108,10+i*150:130+i*150]=panel
        report=compare_reflowed_graph_color_shapes(
            original,slide,source_bounds=(0,original.shape[0],25,155),
            slide_bounds=(0,slide.shape[1]))
        self.assertFalse(report["three_graph_black_ink_geometry_plausible"])
        self.assertFalse(report["video_or_publication_authorized"])

    def test_invalid_pixels_or_bounds_rejected(self):
        source,target=self.fixture()
        with self.assertRaises(FigureIdentityReviewRequired):
            self.check(source.astype(np.float32),target)
        with self.assertRaises(FigureIdentityReviewRequired):
            compare_reflowed_graph_color_shapes(
                source,target,source_bounds=(0,365,25,10000),
                slide_bounds=(0,450))

    def test_empty_ink_shapes_do_not_match(self):
        empty=np.zeros((100,100),dtype=bool)
        self.assertIsNone(_shape_difference(empty,empty,cv2,np))

    def test_blank_gutter_segmentation_separates_three(self):
        s=[0]*30+[20]*70+[0]*32+[30]*65+[0]*42+[20]*60
        self.assertEqual(len(_runs(s,max_blank=18,min_width=55)),3)
