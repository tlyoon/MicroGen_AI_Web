"""Source/physics regression for original Thomas §8.6 Exercise 62."""
import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.original_thomas86_tank_ex62_source_provenance import (
    exercise_text_present, exact_tank_math, source_image_match,
)


GOOD = ("62. Volume The head of your firm's accounting department "
        "asked you to find a formula to calculate year-end inventory of gasoline. "
        "The tank is a right circular cylinder of radius r and length L. "
        "The data are depth d measurements with a Measuring stick. "
        "y r -r L d = Depth of gasoline")


class OriginalPublisherExercise62(unittest.TestCase):
    def test_source_uses_exercise_62_not_invented_slide_title(self):
        self.assertTrue(exercise_text_present(GOOD))
        self.assertNotIn("Tank Inventory", GOOD)

    def test_rejects_unrelated_source_even_with_matching_title(self):
        self.assertFalse(exercise_text_present("Tank Inventory Volume exercise"))
        self.assertFalse(exercise_text_present(GOOD.replace("62. Volume", "60. Volume")))

    @unittest.skipUnless(importlib.util.find_spec("sympy"), "SymPy unavailable")
    def test_exact_tank_derivative_empty_full(self):
        proof=exact_tank_math()
        self.assertTrue(proof["symbolic_volume_derivative_equals_2L_sqrt_2rd_minus_d_squared"])
        self.assertTrue(proof["empty_and_full_tank_endpoints_verified"])

    @unittest.skipUnless(importlib.util.find_spec("cv2") and
                         importlib.util.find_spec("numpy") and
                         importlib.util.find_spec("PIL"), "OpenCV figure matcher unavailable")
    def test_unrelated_figure_rejected_fail_closed(self):
        from PIL import Image
        import io
        with TemporaryDirectory() as temp:
            other=Path(temp)/"unrelated.png"
            Image.new("RGB",(236,180),(238,44,33)).save(other)
            src=io.BytesIO()
            Image.new("RGB",(228,172),(33,121,238)).save(src,format="PNG")
            with self.assertRaises(FigureIdentityReviewRequired):
                source_image_match(src.getvalue(),other)


if __name__=="__main__":
    unittest.main()
