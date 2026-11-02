"""Figure8.2/8.3 visual geometry needs true source inliers in all panels."""
import unittest
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.original_figure82_83_actual_publisher_feature_registration import (
    STATUS,PUBLISHER_IMAGE_CORRIDOR,classify_feature_evidence,
)
def evidence(fig="8.3"):
    spec=PUBLISHER_IMAGE_CORRIDOR[fig]
    return {
        "publisher_page":spec["original_publisher_page"],
        "original_author_slide":spec["author_slide"],
        "corridor_2x":spec["source_raster_crop_2x"],
        "ratio_test_matching_keypoints":50,
        "geometric_RANSAC_inliers":42,
        "author_image_thirds_inlier_counts":[16,14,12],
        "estimated_source_image_similarity_transform":[
            [1.332,0.004,56.4],[0.003,1.331,148.0],[0.000001,-0.000001,1]],
    }

class PublisherSourceThreePanelGeometry(unittest.TestCase):
    def test_true_original_both_figure_images_match_all_three_bands(self):
        for fig in ("8.2","8.3"):
            result=classify_feature_evidence(figure_id=fig,data=evidence(fig))
            self.assertTrue(result[
                "all_three_source_image_panel_artwork_correspondence_proven"])
            self.assertFalse(result[
                "publisher_caption_math_labels_and_axis_semantics_full_proven"])
        self.assertIn("LABELS_PENDING",STATUS)

    def test_wrong_source_page_or_author_slide_must_fail(self):
        v=evidence()
        v["original_author_slide"]=5
        with self.assertRaises(FigureIdentityReviewRequired):
            classify_feature_evidence(figure_id="8.3",data=v)

    def test_one_panel_only_match_is_not_complete(self):
        v=evidence()
        v["author_image_thirds_inlier_counts"]=[21,21,0]
        with self.assertRaises(FigureIdentityReviewRequired):
            classify_feature_evidence(figure_id="8.3",data=v)

    def test_spurious_geometric_mismatch_cannot_be_promoted(self):
        v=evidence()
        v["estimated_source_image_similarity_transform"][0][1]=.3
        with self.assertRaises(FigureIdentityReviewRequired):
            classify_feature_evidence(figure_id="8.3",data=v)

    def test_weak_keypoint_matches_do_not_certify(self):
        v=evidence()
        v["ratio_test_matching_keypoints"]=100
        with self.assertRaises(FigureIdentityReviewRequired):
            classify_feature_evidence(figure_id="8.3",data=v)
if __name__=="__main__":
    unittest.main()
