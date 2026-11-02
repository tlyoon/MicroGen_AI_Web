"""Keep source-printed glyph pixel QA viable in BOTH native Windows CI jobs."""
import unittest
from pathlib import Path


class WindowsFigurePixelDependencyContract(unittest.TestCase):
    def test_both_windows_jobs_install_opencv_for_live_pixel_unit_regressions(self):
        p=(Path(__file__).resolve().parents[1]/".github"/"workflows"/
           "microgen-reliability-tests.yml")
        text=p.read_text("utf8")
        first,second=text.split("  full-regressions:",1)
        self.assertIn("runs-on: windows-latest",first)
        self.assertIn("runs-on: windows-latest",second)
        self.assertIn("pip install",first)
        self.assertIn("pip install",second)
        self.assertIn("opencv-python-headless",first)
        self.assertIn("opencv-python-headless",second)
        self.assertIn('"tests.test_original_fig83_source_math_glyph_pixel_proof"',first)
        self.assertIn('"tests.test_original_fig83_four_endpoint_tick_science"',first)
        self.assertNotIn("ubuntu-latest",text)
if __name__=="__main__":
    unittest.main()
