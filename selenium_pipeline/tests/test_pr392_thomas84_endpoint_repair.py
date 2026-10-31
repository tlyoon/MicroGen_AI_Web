"""One evidenced Thomas 8.4 domain correction; source files remain immutable."""
import unittest

from selenium_pipeline.original_thomas84_endpoint_repair import OLD, NEW


class DomainBoundaryTest(unittest.TestCase):
    def test_tangent_is_open_and_sine_is_closed(self):
        self.assertIn(r"$-\frac{\pi}{2} < \theta < \frac{\pi}{2}$ for tangent",NEW)
        self.assertIn(r"$-\frac{\pi}{2} \le \theta \le \frac{\pi}{2}$ for sine",NEW)

    def test_original_review_question_was_incorrect(self):
        self.assertIn("for sine and tangent",OLD)
        self.assertNotIn("for sine and tangent",NEW)

    def test_exact_one_change_and_reversible_text_repair(self):
        original=r"\begin{frame}"+"\n"+OLD+"\n"+r"\end{frame}"
        edited=original.replace(OLD,NEW)
        self.assertNotEqual(edited,original)
        self.assertEqual(edited.replace(NEW,OLD),original)
        self.assertEqual(edited.count(NEW),1)

    def test_sine_endpoint_not_altered_by_tangent_restriction(self):
        self.assertNotEqual(
            r"-\frac{\pi}{2} < \theta < \frac{\pi}{2}",
            r"-\frac{\pi}{2} \le \theta \le \frac{\pi}{2}")

if __name__=="__main__":
    unittest.main()
