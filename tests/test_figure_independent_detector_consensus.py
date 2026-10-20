"""An independent feature detector does not certify scientific panel identity."""
import copy
import unittest
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_independent_detector_consensus import detector_consensus


def make():
    a=[];b=[]
    for i in range(4):
        m=[[.5,0,10.0+i*120], [0,.5,-100.0]]
        a.append(dict(scan_bin=i,geometrically_coherent_candidate=True,
                      ransac_inlier_count=25,
                      affine_source_render_to_slide_px=copy.deepcopy(m)))
        b.append(dict(scan_bin=i,inlier_count=9,
                      affine_source_render_to_slide_px=copy.deepcopy(m)))
    return {"arbitrary_four_width_bins":a},{"akaze_bins":b}


class IndependentDetectorTests(unittest.TestCase):
    def test_consensus_is_not_scientific_certification(self):
        a,b=make()
        result=detector_consensus(a,b)
        self.assertEqual(result["consistent_scan_bin_count"],4)
        for label in ("complete_original_figure_verified",
                      "original_panel_count_and_labels_verified",
                      "source_to_slide_full_coverage_verified",
                      "narrated_highlights_verified",
                      "publication_authorized"):
            self.assertFalse(result[label])
        self.assertFalse(result["scan_bin_crosschecks"][0]["author_intended_panel_certified"])

    def test_inconsistent_translation_rejected(self):
        a,b=make()
        b["akaze_bins"][1]["affine_source_render_to_slide_px"][0][2]+=15
        self.assertEqual(detector_consensus(a,b)["consistent_scan_bin_count"],3)

    def test_scale_mismatch_rejected(self):
        a,b=make()
        b["akaze_bins"][2]["affine_source_render_to_slide_px"][0][0]+=.06
        self.assertEqual(detector_consensus(a,b)["consistent_scan_bin_count"],3)

    def test_weak_secondary_detector_does_not_confirm(self):
        a,b=make()
        b["akaze_bins"][3]["inlier_count"]=4
        self.assertEqual(detector_consensus(a,b)["consistent_scan_bin_count"],3)

    def test_missing_secondary_fit_does_not_confirm(self):
        a,b=make()
        b["akaze_bins"][0]["affine_source_render_to_slide_px"]=None
        self.assertEqual(detector_consensus(a,b)["consistent_scan_bin_count"],3)

    def test_malformed_and_nonfinite_transform_fails(self):
        for fault in ("inf","shape"):
            a,b=make()
            if fault=="inf":
                b["akaze_bins"][0]["affine_source_render_to_slide_px"][0][0]=float("inf")
            else:
                b["akaze_bins"][0]["affine_source_render_to_slide_px"]=[[.5,.5],[.5,.5]]
            with self.subTest(fault=fault):
                with self.assertRaises(FigureIdentityReviewRequired):
                    detector_consensus(a,b)

    def test_nonconsecutive_bin_indices_fail(self):
        a,b=make()
        b["akaze_bins"][2]["scan_bin"]=1
        with self.assertRaises(FigureIdentityReviewRequired):
            detector_consensus(a,b)
