"""An entire slide with one source-spoken highlighted element isn't approved."""
import unittest
from selenium_pipeline.original_three_section_academic_remaining_inventory import (
    EXPECTED,STATUS,_slides)
class Original41AcademicDeficitSource(unittest.TestCase):
    def test_three_exact_textbook_sections(self):
        self.assertEqual(EXPECTED,{"8.4":17,"8.5":11,"8.6":13})
        self.assertEqual(sum(EXPECTED.values()),41)
    def test_source_frame_count_does_not_fabricate(self):
        self.assertEqual(len(_slides(
            r"\begin{frame}A\end{frame}"+r"\begin{frame}B\end{frame}")),2)
        with self.assertRaises(Exception):
            _slides("These aren't original Beamer source frames")
    def test_read_only_nonproduction_does_not_claim_academic_approval(self):
        self.assertIn("DEFICIT_INVENTORY_NONPRODUCTION",STATUS)
if __name__=="__main__":
    unittest.main()
