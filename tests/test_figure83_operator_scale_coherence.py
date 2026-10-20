import unittest
from selenium_pipeline.figure83_slide_inverse_glyph_correspondence import validate_scale_coherence
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

def samples(scales):
    return [[{"relative_pixel_scale":(scales[i] if i==j else .5)}
             for j in range(3)] for i in range(3)]
class GlyphScaleCoherenceTests(unittest.TestCase):
    def test_normal_registration(self):
        self.assertTrue(validate_scale_coherence(samples([.39,.42,.41]))["matched_operator_label_scales_consistent"])
    def test_suspicious_mixed_scale(self):
        self.assertFalse(validate_scale_coherence(samples([.27,.30,.85]))["matched_operator_label_scales_consistent"])
    def test_malformed_and_nan(self):
        for values in [[.3,.4,float("nan")],[.3,.4,True],[.3,.4,-1]]:
            with self.assertRaises(FigureIdentityReviewRequired):
                validate_scale_coherence(samples(values))
    def test_invalid_threshold(self):
        for value in [0,float("nan"),float("inf"),4]:
            with self.assertRaises(FigureIdentityReviewRequired):
                validate_scale_coherence(samples([.4,.4,.4]),max_ratio=value)
