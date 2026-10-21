import unittest
from pathlib import Path
from selenium_pipeline.figure83_slide_page_coordinates import (
    bitmap_box_to_page,actual_slide_figure_placement,transform_review_boxes)
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

REAL=Path(r"G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4\slides.pdf")
class PageCoordinateTests(unittest.TestCase):
    def test_numerical_transform(self):
        self.assertEqual(bitmap_box_to_page([0,0,100,50],[10,20,210,120],[200,100]),
                         [10.,20.,110.,70.])
    def test_out_of_bounds_and_bool_rejected(self):
        for b in ([0,0,201,30],[-1,0,10,20],[True,0,10,20],[0,0,0,1]):
            with self.assertRaises(FigureIdentityReviewRequired):
                bitmap_box_to_page(b,[10,20,210,120],[200,100])
    def test_ambiguous_review_stays_unmapped(self):
        place={"figure_coordinate_transform_verified":True,
               "original_slides_sha256":"a"*64,"slide_page":5,
               "figure_placement_pdf_pt":[10,20,210,120],
               "bitmap_dimensions_px":[200,100]}
        ans=transform_review_boxes(placement=place,boxes=[
            {"utterance_id":"u1","candidate_full_expression_bitmap_bbox_for_review":[0,0,100,50]},
            {"utterance_id":"u2","candidate_full_expression_bitmap_bbox_for_review":None}])
        self.assertIsNone(ans["review_anchors"][1]["candidate_equation_pdf_points"])
        self.assertFalse(ans["publication_authorized"])
    @unittest.skipUnless(REAL.is_file(),"Original Thomas slide only available on Dell-115")
    def test_real_existing_embedded_figure_not_changed(self):
        r=actual_slide_figure_placement(slides=REAL)
        self.assertEqual(r["bitmap_dimensions_px"],[744,173])
        self.assertFalse(r["audio_timing_verified"])
