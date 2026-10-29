"""Conservative affine clustering; scan bins must not become figure panels."""
from __future__ import annotations
import copy
import unittest
from unittest.mock import patch
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_transform_groups import group_coherent_scan_transforms


def fixture():
    rows=[]
    for i, shift in enumerate((0.0, 252.0, 253.0, 495.0)):
        rows.append({
            "scan_bin":i,
            "geometrically_coherent_candidate":True,
            "ransac_inlier_count":(58,18,31,20)[i],
            "affine_source_render_to_slide_px":[[.5,0.0,shift], [0.0,.5,-100.0]],
            "source_keypoint_extent_pdf":[40.0,90.0+i*40,125.0,140.0+i*40],
            "slide_keypoint_extent_px":[15.0+i*180,35.0,130.0+i*180,145.0],
        })
    return {"arbitrary_four_width_bins":rows}


class TransformGroupTests(unittest.TestCase):
    def test_adjacent_shared_transform_is_one_hypothesis(self):
        r=group_coherent_scan_transforms(fixture())
        self.assertEqual(r["candidate_transform_group_count"],3)
        self.assertEqual([g["slide_scan_bin_indices"] for g in
                          r["candidate_transform_groups"]],[[0],[1,2],[3]])
        self.assertEqual(r["candidate_transform_groups"][1]["joint_ransac_inlier_count"],49)
        self.assertFalse(r["source_figure_panel_count_certified"])
        self.assertFalse(r["source_to_slide_full_coverage_verified"])
        self.assertFalse(r["video_or_publication_authorized"])

    def test_nearly_same_scale_but_different_translation_no_merge(self):
        f=fixture()
        f["arbitrary_four_width_bins"][2]["affine_source_render_to_slide_px"][0][2]=260
        r=group_coherent_scan_transforms(f)
        self.assertEqual(r["candidate_transform_group_count"],4)

    def test_changed_scale_no_merge(self):
        f=fixture()
        f["arbitrary_four_width_bins"][2]["affine_source_render_to_slide_px"][0][0]=.54
        self.assertEqual(group_coherent_scan_transforms(f)["candidate_transform_group_count"],4)

    def test_missing_or_unverified_bin_breaks_chain(self):
        f=fixture()
        f["arbitrary_four_width_bins"][1]["geometrically_coherent_candidate"]=False
        self.assertEqual(group_coherent_scan_transforms(f)["candidate_transform_group_count"],3)

    def test_nan_and_forged_inliers_fail_closed(self):
        for kind in ("nan","fake"):
            f=fixture()
            if kind=="nan":
                f["arbitrary_four_width_bins"][1]["affine_source_render_to_slide_px"][1][2]=float("nan")
            else:
                f["arbitrary_four_width_bins"][1]["ransac_inlier_count"]=2
            with self.subTest(kind=kind):
                with self.assertRaises(FigureIdentityReviewRequired):
                    group_coherent_scan_transforms(f)

    def test_missing_bin_set_fails_closed(self):
        f=fixture()
        f["arbitrary_four_width_bins"].pop()
        with self.assertRaises(FigureIdentityReviewRequired):
            group_coherent_scan_transforms(f)

    def test_all_rejected_bins_never_authorize(self):
        f=fixture()
        for row in f["arbitrary_four_width_bins"]:
            row["geometrically_coherent_candidate"]=False
        r=group_coherent_scan_transforms(f)
        self.assertEqual(r["candidate_transform_groups"],[])
        self.assertFalse(r["video_or_publication_authorized"])
