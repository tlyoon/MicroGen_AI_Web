"""Native-raster gutter candidate QA; no invented author triangle labels."""
import unittest

from PIL import Image, ImageDraw

from selenium_pipeline.original_composite_gutter_proposals import (
    propose_native_vertical_gutters,
)


def synthetic(*,missing=False,extra=False,blank=False):
    img=Image.new("RGB",(420,130),"white")
    if blank:
        return img
    d=ImageDraw.Draw(img)
    segments=[(0,120),(140,260),(280,420)]
    for a,b in segments:
        for y in (20,45,75,105):
            d.line([(a,y),(b-1,y)],fill="black",width=2)
    if missing:
        d.line([(120,45),(139,45)],fill="black",width=2)
    if extra:
        d.rectangle((80,0,90,129),fill="white")
    return img


class OriginalGutterCandidateTests(unittest.TestCase):
    def test_exact_two_non_semantic_gutters_and_three_distinct_strips(self):
        report=propose_native_vertical_gutters(synthetic())
        self.assertEqual(report["candidate_separator_x_px"],[130,270])
        self.assertEqual(len(report["candidate_strips"]),3)
        self.assertEqual(
            [x["native_bbox_px"] for x in report["candidate_strips"]],
            [[0,0,130,130],[130,0,270,130],[270,0,420,130]])
        self.assertFalse(report["author_intended_panel_count_verified"])
        self.assertFalse(report["approved_for_narration_highlight"])
        self.assertFalse(report["publication_authorized"])
        self.assertEqual(len({x["panel_native_pixel_sha256"]
                              for x in report["candidate_strips"]}),3)

    def test_bridge_across_gutter_removes_clean_candidate(self):
        with self.assertRaises(ValueError):
            propose_native_vertical_gutters(synthetic(missing=True))

    def test_extra_gutter_is_ambiguous_and_fails_closed(self):
        with self.assertRaises(ValueError):
            propose_native_vertical_gutters(synthetic(extra=True))

    def test_all_blank_composite_is_rejected(self):
        with self.assertRaises(ValueError):
            propose_native_vertical_gutters(synthetic(blank=True))

    def test_too_many_or_too_few_declared_panels_are_refused(self):
        for count in (1,5,7,0):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    propose_native_vertical_gutters(synthetic(),expected_panels=count)

    def test_tiny_image_is_not_acceptable_source_raster(self):
        with self.assertRaises(ValueError):
            propose_native_vertical_gutters(Image.new("RGB",(80,45),"white"))

    def test_subminimum_panel_width_is_not_misrepresented(self):
        with self.assertRaises(ValueError):
            propose_native_vertical_gutters(synthetic(),min_panel_width=155)

    def test_nonsemantic_grayscale_image_is_equivalently_detected(self):
        report=propose_native_vertical_gutters(synthetic().convert("L"))
        self.assertEqual(report["candidate_separator_x_px"],[130,270])


if __name__=="__main__":
    unittest.main()
