"""Cumulative math corrections are genuinely paired, never source WAV re-use."""
import unittest

from selenium_pipeline.original_thomas84_cumulative_academic_repairs import (
    OLD_REVIEW_SPEECH,CORRECT_REVIEW_SPEECH)
from selenium_pipeline.original_thomas84_endpoint_repair import OLD as TEX_BAD,NEW as TEX_GOOD
from selenium_pipeline.original_thomas84_arctangent_paired_repair import (
    OLD_WORDS,NEW_WORDS,OLD_TEX,NEW_TEX)
from selenium_pipeline.inverse_trig_principal_domain_guard import inspect_tex
from selenium_pipeline.automatic_math_semantic_qa import _detect

class CumulativeSourceRepairTests(unittest.TestCase):
    def test_review_narration_does_not_repeat_inclusive_sine_error(self):
        self.assertIn("for sine and tangent",OLD_REVIEW_SPEECH)
        self.assertNotIn("for sine and tangent",CORRECT_REVIEW_SPEECH)
        self.assertIn("principal arcsine interval includes both endpoints",
                      CORRECT_REVIEW_SPEECH)

    def test_corrected_slides_have_disjoint_exact_replacements(self):
        original=OLD_TEX+"\n"+TEX_BAD
        combined=original.replace(OLD_TEX,NEW_TEX).replace(TEX_BAD,TEX_GOOD)
        self.assertNotIn(OLD_TEX,combined)
        self.assertNotIn(TEX_BAD,combined)
        self.assertEqual(combined.replace(NEW_TEX,OLD_TEX)
                         .replace(TEX_GOOD,TEX_BAD),original)

    def test_original_slide6_math_confusion_fails_semantic_qa(self):
        incorrect=" ".join(OLD_WORDS)
        names={f["rule"] for f in _detect(6,incorrect)}
        self.assertIn("inverse_function_one_to_one_confusion",names)
        self.assertIn("arctangent_horizontal_not_vertical_asymptotes",names)

    def test_corrected_slide6_source_math_qa_passes(self):
        self.assertEqual(_detect(6," ".join(NEW_WORDS)),[])

    def test_corrected_review_slide_rejects_old_strict_sine_domain(self):
        old=(r"\begin{frame}{Review Questions}\item Why do domain restrictions "
             "matter ("+TEX_BAD+r")?\end{frame}")
        fixed=old.replace(TEX_BAD,TEX_GOOD)
        self.assertEqual(inspect_tex(old)["blocking_count"],1)
        self.assertEqual(inspect_tex(fixed)["blocking_count"],0)

if __name__=="__main__":
    unittest.main()
